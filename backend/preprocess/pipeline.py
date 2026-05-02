import numpy as np
from typing import Callable, List


class PreprocessPipeline:
    def __init__(self):
        self.steps: List[Callable] = []
        self._scene_map = {
            "printed": [auto_rotate, deskew, denoise, contrast_enhance],
            "handwritten": [auto_rotate, scale_up, denoise, sharpen],
            "screenshot": [auto_rotate, binarize],
            "table": [auto_rotate, perspective_correct, contrast_enhance],
            "idcard": [auto_rotate, perspective_correct, sharpen],
            "lowquality": [denoise, contrast_enhance, sharpen, scale_up],
            "photo": [auto_rotate, denoise, contrast_enhance],
            "exam": [auto_rotate, deskew, binarize],
        }

    def add(self, step: Callable) -> None:
        self.steps.append(step)

    async def run(self, image: np.ndarray, scene_type: str) -> np.ndarray:
        steps = self._scene_map.get(scene_type, [auto_rotate])
        result = image.copy()
        for step in steps:
            result = await step(result)
        return result


async def auto_rotate(image: np.ndarray) -> np.ndarray:
    return image


async def perspective_correct(image: np.ndarray) -> np.ndarray:
    return image


async def denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    return image


async def contrast_enhance(image: np.ndarray) -> np.ndarray:
    return image


async def sharpen(image: np.ndarray) -> np.ndarray:
    return image


async def binarize(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    return image


async def deskew(image: np.ndarray) -> np.ndarray:
    return image


async def scale_up(image: np.ndarray, factor: float = 1.5) -> np.ndarray:
    return image
