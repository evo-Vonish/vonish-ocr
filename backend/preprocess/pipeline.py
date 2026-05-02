"""预处理流水线 — 阶段 A：完整的条件预处理系统。

基于场景类型选择预处理步骤，支持超时保护和回退机制。
"""

import time
import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from scene.classifier import (
    SCENE_PRINTED_DOCUMENT,
    SCENE_HANDWRITTEN_NOTE,
    SCENE_SCREENSHOT,
    SCENE_ID_CARD,
    SCENE_TABLE_FORM,
    SCENE_PHOTO_WITH_TEXT,
    SCENE_LOW_QUALITY_SCAN,
    SCENE_EXAM_PAPER,
    SCENE_PIPELINE_MAP,
)
from preprocess.auto_rotate import rotate_interpolation, auto_rotate_sync

logger = logging.getLogger(__name__)

# 步骤执行预算（ms），总预算 200ms
STEP_BUDGET_MS = 200
# 非核心步骤（超时后可跳过）
NON_CORE_STEPS = {"remove_shadow", "sharpen_usm", "line_enhance", "line_removal"}

# 场景 → 步骤参数配置
SCENE_PARAMS = {
    SCENE_PRINTED_DOCUMENT:   {"clahe_clip": 2.0, "median_ksize": 3},
    SCENE_HANDWRITTEN_NOTE:   {"clahe_clip": 3.0, "sharpen_amount": 0.8},
    SCENE_SCREENSHOT:         {},
    SCENE_ID_CARD:            {"clahe_clip": 2.0, "median_ksize": 3},
    SCENE_TABLE_FORM:         {"clahe_clip": 2.5, "median_ksize": 3},
    SCENE_PHOTO_WITH_TEXT:    {"clahe_clip": 3.0},
    SCENE_LOW_QUALITY_SCAN:   {"clahe_clip": 3.0, "sharpen_amount": 0.8, "use_nlm": True},
    SCENE_EXAM_PAPER:         {"clahe_clip": 2.5, "median_ksize": 3},
}


# =============================================================================
# 底层预处理函数（同步，纯 OpenCV）
# =============================================================================

def _deskew_minarearect(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """基于 minAreaRect 的倾斜校正。返回 (校正后图像, 角度)。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    # 二值化取反（文字为白色）
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # 找轮廓，计算每个轮廓的 minAreaRect
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    angles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 100:
            continue
        rect = cv2.minAreaRect(cnt)
        angle = rect[-1]
        # OpenCV 返回的角度范围是 [-90, 0)，需要规范化
        if angle < -45:
            angle += 90
        elif angle > 45:
            angle -= 90
        angles.append(angle)

    if not angles:
        return image, 0.0

    # 使用中位数避免异常值
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.3:
        return image, 0.0

    # 保护：如果角度接近 45°（或 90° 倍数），可能是误检
    if 40 < abs(median_angle) < 50:
        return image, 0.0

    rotated = rotate_interpolation(image, -median_angle)
    return rotated, -median_angle


def _perspective_rectify(image: np.ndarray) -> Optional[np.ndarray]:
    """四边形检测 + 透视变换。检测失败返回 None。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # 按面积排序，找前 5 个最大的四边形
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    h, w = image.shape[:2]
    min_area = (w * h) * 0.15  # 至少占画面 15%

    for cnt in contours[:5]:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
            rect = _order_points(pts)
            (tl, tr, br, bl) = rect

            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))

            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))

            if maxWidth < 100 or maxHeight < 100:
                continue

            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            return warped

    return None  # 未找到有效四边形


def _order_points(pts: np.ndarray) -> np.ndarray:
    """将 4 个点按左上、右上、右下、左下排序。"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # 左上
    rect[2] = pts[np.argmax(s)]  # 右下
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # 右上
    rect[3] = pts[np.argmax(diff)]  # 左下
    return rect


def _remove_shadow_morphology(image: np.ndarray) -> np.ndarray:
    """形态学闭运算背景估计法去阴影。"""
    is_gray = len(image.shape) == 2
    if is_gray:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 形态学闭运算估计背景（大核）
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
    bg = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    bg = cv2.medianBlur(bg, 21)

    # 除法模型：diff = 255 - (bg - gray)
    diff = 255 - cv2.subtract(bg, gray)

    if is_gray:
        return diff
    return cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)


def _denoise_median(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """中值滤波去噪。"""
    return cv2.medianBlur(image, ksize)


def _denoise_bilateral(image: np.ndarray) -> np.ndarray:
    """双边滤波（保边缘去噪）。"""
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)


def _denoise_nlm(image: np.ndarray) -> np.ndarray:
    """非局部均值去噪（高质量，慢，仅低质量扫描场景使用）。"""
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    else:
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)


def _contrast_clahe(image: np.ndarray, clipLimit: float = 2.0) -> np.ndarray:
    """LAB 空间 L 通道 CLAHE 对比度增强。"""
    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=(8, 8))
        return clahe.apply(image)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _sharpen_usm(image: np.ndarray, amount: float = 1.2) -> np.ndarray:
    """非锐化掩膜锐化。"""
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    return cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)


def _line_enhance(image: np.ndarray) -> np.ndarray:
    """表格场景：增强直线对比度。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    # 形态学闭运算增强水平/垂直线
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    h_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_h, iterations=2)
    v_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_v, iterations=2)
    enhanced = cv2.addWeighted(gray, 1.0, cv2.add(h_lines, v_lines), 0.3, 0)
    if len(image.shape) == 3:
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return enhanced


def _line_removal(image: np.ndarray) -> np.ndarray:
    """试卷场景：去除横线保留文字。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    # 形态学开运算去除水平线
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    no_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=2)
    if len(image.shape) == 3:
        return cv2.cvtColor(no_lines, cv2.COLOR_GRAY2BGR)
    return no_lines


def assess_quality(image: np.ndarray) -> float:
    """图像质量评估：拉普拉斯方差 + 边缘密度综合评分，范围 [0, 1]。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size
    score = min(1.0, lap_var / 500) * 0.5 + min(1.0, edge_density * 20) * 0.5
    return float(score)


# =============================================================================
# 预处理流水线
# =============================================================================

class PreprocessPipeline:
    """条件预处理流水线。

    根据场景类型选择步骤，支持超时保护和质量回退。
    """

    def __init__(self):
        self._step_funcs = {
            "auto_rotate":          self._step_auto_rotate,
            "deskew":               self._step_deskew,
            "perspective_rectify":  self._step_perspective,
            "remove_shadow":        self._step_shadow,
            "denoise_median":       self._step_median,
            "denoise_bilateral":    self._step_bilateral,
            "denoise_nlm":          self._step_nlm,
            "contrast_clahe":       self._step_clahe,
            "sharpen_usm":          self._step_sharpen,
            "line_enhance":         self._step_line_enhance,
            "line_removal":         self._step_line_removal,
        }

    def run(
        self,
        image: np.ndarray,
        scene_type: str,
        options: Optional[dict] = None,
    ) -> dict:
        """执行预处理流水线。

        返回:
            {
                "image": np.ndarray,           # 预处理后的图像（BGR）
                "scene": str,                  # 场景类型
                "steps_applied": [str],        # 步骤描述列表
                "timing_ms": {str: int},       # 各步骤耗时
                "used_original": bool,         # 是否回退到原图
                "quality_before": float,       # 预处理前质量评分
                "quality_after": float,        # 预处理后质量评分
            }
        """
        options = options or {}
        original = image.copy()
        result = image.copy()
        steps_applied: List[str] = []
        timing_ms: Dict[str, int] = {}
        total_ms = 0
        used_original = False

        # 截图场景：完全跳过
        if scene_type == SCENE_SCREENSHOT:
            return {
                "image": original,
                "scene": scene_type,
                "steps_applied": ["skipped: screenshot"],
                "timing_ms": {"total": 0},
                "used_original": False,
                "quality_before": 1.0,
                "quality_after": 1.0,
            }

        # 预处理前质量评估
        quality_before = assess_quality(original)

        # 获取该场景的步骤列表和参数
        step_names = SCENE_PIPELINE_MAP.get(scene_type, [])
        params = SCENE_PARAMS.get(scene_type, {})

        # 逐步执行
        for step_name in step_names:
            # 超时检查：非核心步骤在总耗时 > 预算时跳过
            if total_ms > STEP_BUDGET_MS and step_name in NON_CORE_STEPS:
                steps_applied.append(f"skipped:{step_name}(timeout)")
                continue

            step_fn = self._step_funcs.get(step_name)
            if step_fn is None:
                continue

            t0 = time.perf_counter() * 1000
            try:
                new_result, desc = step_fn(result, params, options)
                if new_result is not None:
                    result = new_result
                    steps_applied.append(desc)
            except Exception as e:
                logger.warning(f"预处理步骤 {step_name} 失败: {e}")
                steps_applied.append(f"failed:{step_name}")
            t1 = time.perf_counter() * 1000
            elapsed = int(t1 - t0)
            timing_ms[step_name] = elapsed
            total_ms += elapsed

        timing_ms["total"] = total_ms

        # 预处理后质量评估
        quality_after = assess_quality(result)

        # 如果预处理导致质量显著下降，回退到原图
        if quality_after < quality_before * 0.5 and quality_before > 0.3:
            logger.warning(
                f"预处理导致质量下降（{quality_before:.2f} → {quality_after:.2f}），回退原图"
            )
            result = original
            used_original = True
            steps_applied.append("fallback:original")
            quality_after = quality_before

        return {
            "image": result,
            "scene": scene_type,
            "steps_applied": steps_applied,
            "timing_ms": timing_ms,
            "used_original": used_original,
            "quality_before": round(quality_before, 3),
            "quality_after": round(quality_after, 3),
        }

    # ------------------------------------------------------------------
    # 步骤包装函数（统一返回 (image, description)）
    # ------------------------------------------------------------------

    def _step_auto_rotate(self, image, params, options):
        exif = options.get("exif")
        rotated, angle = auto_rotate_sync(image, exif=exif)
        if angle != 0:
            return rotated, f"auto_rotate:{angle}°"
        return rotated, "auto_rotate:0°"

    def _step_deskew(self, image, params, options):
        deskewed, angle = _deskew_minarearect(image)
        if abs(angle) > 0.3:
            return deskewed, f"deskew:{angle:.1f}°"
        return image, "deskew:0°"

    def _step_perspective(self, image, params, options):
        rectified = _perspective_rectify(image)
        if rectified is not None:
            return rectified, "perspective_rectify"
        return image, "perspective_rectify:skipped"

    def _step_shadow(self, image, params, options):
        return _remove_shadow_morphology(image), "remove_shadow"

    def _step_median(self, image, params, options):
        ksize = params.get("median_ksize", 3)
        return _denoise_median(image, ksize), f"denoise_median:{ksize}×{ksize}"

    def _step_bilateral(self, image, params, options):
        return _denoise_bilateral(image), "denoise_bilateral"

    def _step_nlm(self, image, params, options):
        if params.get("use_nlm"):
            return _denoise_nlm(image), "denoise_nlm"
        return image, "denoise_nlm:skipped"

    def _step_clahe(self, image, params, options):
        clip = params.get("clahe_clip", 2.0)
        return _contrast_clahe(image, clipLimit=clip), f"contrast_clahe:{clip}"

    def _step_sharpen(self, image, params, options):
        amount = params.get("sharpen_amount", 1.2)
        return _sharpen_usm(image, amount), f"sharpen_usm:{amount}"

    def _step_line_enhance(self, image, params, options):
        return _line_enhance(image), "line_enhance"

    def _step_line_removal(self, image, params, options):
        return _line_removal(image), "line_removal"
