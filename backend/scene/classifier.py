from dataclasses import dataclass
from enum import Enum
from typing import List

import cv2
import numpy as np


class SceneType(Enum):
    PRINTED = "printed"
    HANDWRITTEN = "handwritten"
    EXAM = "exam"
    SCREENSHOT = "screenshot"
    PHOTO = "photo"
    IDCARD = "idcard"
    TABLE = "table"
    LOWQUALITY = "lowquality"


@dataclass
class SceneProfile:
    type: SceneType
    confidence: float
    recommended_pipeline: List[str]
    recommended_model: str


class SceneClassifier:
    def __init__(self):
        self._pipelines = {
            SceneType.PRINTED: ["auto_rotate", "deskew", "denoise", "contrast_enhance"],
            SceneType.HANDWRITTEN: ["auto_rotate", "scale_up", "denoise", "sharpen"],
            SceneType.EXAM: ["auto_rotate", "deskew", "binarize"],
            SceneType.SCREENSHOT: ["auto_rotate", "binarize"],
            SceneType.PHOTO: ["auto_rotate", "denoise", "contrast_enhance"],
            SceneType.IDCARD: ["auto_rotate", "perspective_correct", "sharpen"],
            SceneType.TABLE: ["auto_rotate", "perspective_correct", "contrast_enhance"],
            SceneType.LOWQUALITY: ["denoise", "contrast_enhance", "sharpen", "scale_up"],
        }
        self._models = {
            SceneType.PRINTED: "cnocr-standard-cn",
            SceneType.HANDWRITTEN: "cnocr-standard-cn",
            SceneType.EXAM: "cnocr-standard-cn",
            SceneType.SCREENSHOT: "rapidocr-mobile-cn",
            SceneType.PHOTO: "cnocr-standard-cn",
            SceneType.IDCARD: "rapidocr-mobile-cn",
            SceneType.TABLE: "paddleocr-vl-1.5",
            SceneType.LOWQUALITY: "paddleocr-vl-1.5",
        }

    def classify(self, image: np.ndarray) -> SceneProfile:
        h, w = image.shape[:2]
        aspect = w / h if h > 0 else 1.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        variance = float(np.var(gray))
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges) / edges.size)

        if 0.4 < aspect < 2.5 and variance < 2000 and edge_density < 0.05:
            return SceneProfile(
                SceneType.SCREENSHOT, 0.75, self._pipelines[SceneType.SCREENSHOT], self._models[SceneType.SCREENSHOT]
            )

        if 1.4 < aspect < 1.7 and h < 1500:
            return SceneProfile(
                SceneType.IDCARD, 0.7, self._pipelines[SceneType.IDCARD], self._models[SceneType.IDCARD]
            )

        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=w * 0.3, maxLineGap=10)
        if lines is not None and len(lines) > 15:
            return SceneProfile(
                SceneType.TABLE, 0.7, self._pipelines[SceneType.TABLE], self._models[SceneType.TABLE]
            )

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            return SceneProfile(
                SceneType.LOWQUALITY, 0.65, self._pipelines[SceneType.LOWQUALITY], self._models[SceneType.LOWQUALITY]
            )

        if edge_density > 0.15:
            return SceneProfile(
                SceneType.PRINTED, 0.6, self._pipelines[SceneType.PRINTED], self._models[SceneType.PRINTED]
            )

        return SceneProfile(
            SceneType.PRINTED, 0.5, self._pipelines[SceneType.PRINTED], self._models[SceneType.PRINTED]
        )
