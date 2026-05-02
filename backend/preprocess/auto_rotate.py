"""自动旋转模块 — 阶段 A：EXIF 优先 + 宽高比快捷判断。

阶段 B 将在这里插入 PP-LCNet 方向分类器（0.3MB，2ms，90%+ 准确率）。
"""

from typing import Tuple, Optional
import numpy as np
import cv2


# EXIF Orientation → 旋转角度映射
EXIF_ROTATION_MAP = {
    1: 0,    # 正常
    3: 180,  # 旋转 180°
    6: 90,   # 顺时针 90°（需逆时针旋转 90° 修正）
    8: 270,  # 逆时针 90°（需顺时针旋转 90° 修正）
}


def exif_to_angle(orientation: int) -> int:
    """将 EXIF Orientation 标记转为需要旋转的角度（逆时针为正）。"""
    return EXIF_ROTATION_MAP.get(orientation, 0)


def rotate_interpolation(image: np.ndarray, angle: int) -> np.ndarray:
    """以图像中心为轴旋转，使用双线性插值。"""
    angle = angle % 360
    if angle == 0:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    # 计算旋转后画布大小，避免裁剪
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    flags = cv2.INTER_LINEAR
    if angle in (90, 180, 270):
        flags = cv2.INTER_NEAREST  # 正角度用最近邻避免模糊

    return cv2.warpAffine(image, M, (new_w, new_h), flags=flags, borderMode=cv2.BORDER_REPLICATE)


async def auto_rotate(image: np.ndarray, exif: Optional[dict] = None) -> Tuple[np.ndarray, int]:
    """自动判断并旋转图像。

    返回: (旋转后的图像, 旋转角度 0/90/180/270)

    阶段 A 策略：
    1. EXIF Orientation 快捷通道（最准确）
    2. 截图快捷判断：竖屏 9:16 通常无需旋转
    3. 阶段 A 到此为止，返回原图

    TODO 阶段 B：插入 PP-LCNet_x0_25_textline_ori ONNX 模型
         四方向分类（0°/90°/180°/270°），~2ms，准确率 90%+
    """
    # ---- 1. EXIF 快捷通道 ----
    if exif and "Orientation" in exif:
        orientation = exif["Orientation"]
        angle = exif_to_angle(orientation)
        if angle != 0:
            return rotate_interpolation(image, angle), angle
        return image, 0

    # ---- 2. 截图快捷判断 ----
    h, w = image.shape[:2]
    if h > w * 1.5:
        # 竖屏 9:16 截图，通常无需旋转
        return image, 0

    # ---- 3. 阶段 A 到此为止 ----
    # 阶段 B 将在这里插入 PP-LCNet 方向分类器
    return image, 0


# ---- 同步版本（供线程池批量任务使用） ----
def auto_rotate_sync(image: np.ndarray, exif: Optional[dict] = None) -> Tuple[np.ndarray, int]:
    """同步版本的 auto_rotate（无需 await）。"""
    if exif and "Orientation" in exif:
        orientation = exif["Orientation"]
        angle = exif_to_angle(orientation)
        if angle != 0:
            return rotate_interpolation(image, angle), angle
        return image, 0

    h, w = image.shape[:2]
    if h > w * 1.5:
        return image, 0

    return image, 0
