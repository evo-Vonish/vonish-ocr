"""场景分类器 — 阶段 A：传统 CV 规则分类器（零模型依赖，<5ms）"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


# 8 类场景体系（与调研报告对齐）
SCENE_PRINTED_DOCUMENT = "printed_document"
SCENE_HANDWRITTEN_NOTE = "handwritten_note"
SCENE_SCREENSHOT = "screenshot"
SCENE_ID_CARD = "id_card"
SCENE_TABLE_FORM = "table_form"
SCENE_PHOTO_WITH_TEXT = "photo_with_text"
SCENE_LOW_QUALITY_SCAN = "low_quality_scan"
SCENE_EXAM_PAPER = "exam_paper"

ALL_SCENES = [
    SCENE_PRINTED_DOCUMENT,
    SCENE_HANDWRITTEN_NOTE,
    SCENE_SCREENSHOT,
    SCENE_ID_CARD,
    SCENE_TABLE_FORM,
    SCENE_PHOTO_WITH_TEXT,
    SCENE_LOW_QUALITY_SCAN,
    SCENE_EXAM_PAPER,
]

# 场景 → 推荐预处理步骤
SCENE_PIPELINE_MAP = {
    SCENE_PRINTED_DOCUMENT:   ["auto_rotate", "deskew", "denoise_median", "contrast_clahe"],
    SCENE_HANDWRITTEN_NOTE:   ["auto_rotate", "deskew", "denoise_bilateral", "contrast_clahe", "sharpen_usm"],
    SCENE_SCREENSHOT:         [],  # 完全跳过
    SCENE_ID_CARD:            ["auto_rotate", "perspective_rectify", "denoise_median", "contrast_clahe"],
    SCENE_TABLE_FORM:         ["auto_rotate", "deskew", "denoise_median", "contrast_clahe", "line_enhance"],
    SCENE_PHOTO_WITH_TEXT:    ["auto_rotate", "perspective_rectify", "remove_shadow", "denoise_bilateral", "contrast_clahe"],
    SCENE_LOW_QUALITY_SCAN:   ["auto_rotate", "deskew", "remove_shadow", "denoise_nlm", "contrast_clahe", "sharpen_usm"],
    SCENE_EXAM_PAPER:         ["auto_rotate", "deskew", "remove_shadow", "denoise_median", "contrast_clahe", "line_removal"],
}

# 场景 → 推荐模型
SCENE_MODEL_MAP = {
    SCENE_PRINTED_DOCUMENT:   "cnocr-standard-cn",
    SCENE_HANDWRITTEN_NOTE:   "cnocr-standard-cn",
    SCENE_SCREENSHOT:         "rapidocr-mobile-cn",
    SCENE_ID_CARD:            "rapidocr-mobile-cn",
    SCENE_TABLE_FORM:         "cnocr-standard-cn",
    SCENE_PHOTO_WITH_TEXT:    "cnocr-standard-cn",
    SCENE_LOW_QUALITY_SCAN:   "cnocr-standard-cn",
    SCENE_EXAM_PAPER:         "cnocr-standard-cn",
}


@dataclass
class SceneProfile:
    scene: str
    confidence: float
    recommended_steps: List[str]
    recommended_model: str


class RuleBasedSceneClassifier:
    """基于传统 CV 特征的场景粗分类器。

    零模型依赖，单图耗时 < 5ms。
    决策优先级：EXIF/截图 → 身份证 → 低质量 → 试卷 → 户外照片 → 手写 → 表格 → 默认打印文档
    """

    def classify(self, image: np.ndarray, exif: Optional[dict] = None) -> SceneProfile:
        if image is None or image.size == 0:
            logger.warning("场景分类收到空图，返回默认打印文档")
            return self._make_profile(SCENE_PRINTED_DOCUMENT, 0.5)
        h, w = image.shape[:2]
        aspect = w / h if h > 0 else 1.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # ---- 全局特征（只计算一次） ----
        edge_density = self._compute_edge_density(gray)
        color_variance = self._compute_color_variance(image)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        h_lines = self._count_horizontal_lines(gray)
        mser_density = self._compute_mser_density(gray)

        # P0: 截图快捷判断（无相机 EXIF + 常见屏幕分辨率）
        if self._is_screenshot_by_exif(exif or {}, w, h):
            return self._make_profile(SCENE_SCREENSHOT, 0.95)

        # P1: 身份证/银行卡（固定宽高比 + 标准尺寸）
        if 1.4 < aspect < 1.7 and self._is_card_size(w, h):
            return self._make_profile(SCENE_ID_CARD, 0.90)

        # P2: 低质量扫描（模糊度低）
        if lap_var < 80:
            return self._make_profile(SCENE_LOW_QUALITY_SCAN, 0.85)

        # P3: 试卷（水平线密度 + A4/B5 比例）
        # 要求横线贯穿图像宽度 80% 以上（区别于打印文档的短文字行）
        full_width_lines = self._count_horizontal_lines(gray, min_length_ratio=0.8)
        if full_width_lines > 10 and 0.65 < aspect < 0.85:
            return self._make_profile(SCENE_EXAM_PAPER, 0.88)

        # P4: 户外照片（低边缘密度 + 高色彩方差）
        if edge_density < 0.02 and color_variance > 80:
            return self._make_profile(SCENE_PHOTO_WITH_TEXT, 0.82)

        # P5: 手写笔记（不规则边缘 + 中等 MSER）
        if mser_density > 0.02 and self._is_irregular_edges(gray):
            return self._make_profile(SCENE_HANDWRITTEN_NOTE, 0.80)

        # P6: 表格（高直线密度 + 网格感）
        # 表格线不需要贯穿全宽，用较低阈值
        table_h_lines = self._count_horizontal_lines(gray, min_length_ratio=0.2)
        v_lines = self._count_vertical_lines(gray)
        if table_h_lines > 6 and v_lines > 4 and self._has_grid_pattern(gray):
            return self._make_profile(SCENE_TABLE_FORM, 0.85)

        # P7: 打印文档（高边缘密度 + 规整结构）
        if edge_density > 0.08 and lap_var > 200:
            return self._make_profile(SCENE_PRINTED_DOCUMENT, 0.80)

        # 默认：打印文档（置信度最低）
        return self._make_profile(SCENE_PRINTED_DOCUMENT, 0.60)

    # ------------------------------------------------------------------
    # 特征计算方法
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_edge_density(gray: np.ndarray) -> float:
        """Canny 边缘检测后，边缘像素占比。"""
        edges = cv2.Canny(gray, 50, 150)
        return float(np.count_nonzero(edges) / edges.size)

    @staticmethod
    def _compute_color_variance(image: np.ndarray) -> float:
        """LAB 空间 a,b 通道方差（打印文档低，照片高）。"""
        if len(image.shape) != 3:
            return 0.0
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        a_var = float(np.var(lab[:, :, 1]))
        b_var = float(np.var(lab[:, :, 2]))
        return (a_var + b_var) / 2.0

    @staticmethod
    def _count_horizontal_lines(gray: np.ndarray, min_length_ratio: float = 0.0) -> int:
        """HoughLinesP 检测水平线（角度 ±5° 内）。

        Args:
            min_length_ratio: 线长度占图像宽度的最小比例，用于过滤短横线。
                              试卷判断用 0.8（贯穿全宽），表格判断用 0.2。
        """
        h, w = gray.shape[:2]
        edges = cv2.Canny(gray, 50, 150)
        min_length = int(w * min_length_ratio) if min_length_ratio > 0 else int(w * 0.2)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                                minLineLength=min_length, maxLineGap=15)
        if lines is None:
            return 0
        count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 5 or angle > 175:
                count += 1
        return count

    @staticmethod
    def _count_vertical_lines(gray: np.ndarray) -> int:
        """HoughLinesP 检测垂直线（角度 85-95° 内）。"""
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                                minLineLength=gray.shape[0] * 0.15, maxLineGap=15)
        if lines is None:
            return 0
        count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if 85 < angle < 95:
                count += 1
        return count

    @staticmethod
    def _compute_mser_density(gray: np.ndarray) -> float:
        """MSER 检测文字区域，面积占比。"""
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        if not regions:
            return 0.0
        total_area = sum(len(r) for r in regions)
        return float(total_area / gray.size)

    @staticmethod
    def _is_screenshot_by_exif(exif: dict, w: int, h: int) -> bool:
        """无相机 EXIF + 分辨率匹配常见屏幕尺寸。"""
        has_camera_exif = any(k in exif for k in ("Make", "Model", "FNumber", "ExposureTime"))
        if has_camera_exif:
            return False
        # 常见屏幕分辨率
        common_resolutions = {
            (1920, 1080), (1080, 1920), (2560, 1440), (1440, 2560),
            (1280, 720), (720, 1280), (3840, 2160), (2160, 3840),
            (1170, 2532), (2532, 1170), (1125, 2436), (2436, 1125),
            (1080, 2340), (2340, 1080),
        }
        return (w, h) in common_resolutions or (h, w) in common_resolutions

    @staticmethod
    def _is_card_size(w: int, h: int) -> bool:
        """身份证/银行卡尺寸范围：宽 600-1000，高 400-650。"""
        return 600 <= w <= 1000 and 400 <= h <= 650

    @staticmethod
    def _is_irregular_edges(gray: np.ndarray) -> bool:
        """边缘曲率方差高（手写笔画弯曲）。"""
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return False
        variances = []
        for cnt in contours:
            if len(cnt) < 5:
                continue
            try:
                approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
                # 多边形顶点越多，边缘越不规则
                if len(approx) > 8:
                    variances.append(len(approx))
            except Exception:
                pass
        return len(variances) > 5 and np.mean(variances) > 12

    @staticmethod
    def _has_grid_pattern(gray: np.ndarray) -> bool:
        """检测水平和垂直线是否形成网格（交点数量）。"""
        edges = cv2.Canny(gray, 50, 150)
        h_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60,
                                  minLineLength=gray.shape[1] * 0.15, maxLineGap=20)
        v_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60,
                                  minLineLength=gray.shape[0] * 0.15, maxLineGap=20)
        if h_lines is None or v_lines is None:
            return False
        # 简化：水平线和垂直线都有足够数量
        h_count = len(h_lines)
        v_count = len(v_lines)
        return h_count >= 3 and v_count >= 3

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _make_profile(self, scene: str, confidence: float) -> SceneProfile:
        return SceneProfile(
            scene=scene,
            confidence=confidence,
            recommended_steps=SCENE_PIPELINE_MAP.get(scene, []),
            recommended_model=SCENE_MODEL_MAP.get(scene, "rapidocr-mobile-cn"),
        )
