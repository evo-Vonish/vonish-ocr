import io
import gc
import time
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from core.ocr_engine import BaseOCREngine

logger = logging.getLogger(__name__)


class ONNXOCREngine(BaseOCREngine):
    """基于 rapidocr-onnxruntime 的 OCR 引擎。

    扫描模型目录动态匹配 det/rec/cls 三个 ONNX 文件，
    支持 rapidocr-mobile-cn、cnocr-standard-cn 等同架构模型。
    """

    def __init__(self, model_path: Path, model_id: str = ""):
        super().__init__(model_path)
        self.model_id = model_id
        self._ocr: Optional[object] = None
        self._det_path: Optional[Path] = None
        self._rec_path: Optional[Path] = None
        self._cls_path: Optional[Path] = None
        self._dict_path: Optional[Path] = None

    def _scan_models(self) -> tuple[Optional[Path], Optional[Path], Optional[Path], Optional[Path]]:
        """扫描模型目录，按文件名关键词匹配 det/rec/cls。"""
        if not self.model_path.exists() or not self.model_path.is_dir():
            raise FileNotFoundError(f"模型目录不存在: {self.model_path}")

        onnx_files = list(self.model_path.glob("*.onnx"))
        if not onnx_files:
            raise FileNotFoundError(f"模型目录中未找到 .onnx 文件: {self.model_path}")

        det_path = rec_path = cls_path = dict_path = None
        for f in onnx_files:
            name_lower = f.name.lower()
            if "det" in name_lower:
                det_path = f
            elif "rec" in name_lower:
                rec_path = f
            elif "cls" in name_lower:
                cls_path = f

        for f in self.model_path.glob("*.txt"):
            name_lower = f.name.lower()
            if "dict" in name_lower or "keys" in name_lower:
                dict_path = f
                break

        if not det_path:
            raise FileNotFoundError(f"未找到检测模型 (det): {self.model_path}")
        if not rec_path:
            raise FileNotFoundError(f"未找到识别模型 (rec): {self.model_path}")
        if not cls_path:
            logger.warning(f"未找到方向分类模型 (cls)，将跳过方向校正: {self.model_path}")

        logger.info(
            "扫描到模型文件: det=%s, rec=%s, cls=%s",
            det_path.name,
            rec_path.name,
            cls_path.name if cls_path else "N/A",
        )
        return det_path, rec_path, cls_path, dict_path

    async def load(self) -> None:
        if self.loaded:
            return

        self._det_path, self._rec_path, self._cls_path, self._dict_path = self._scan_models()

        try:
            from rapidocr_onnxruntime import RapidOCR
            from rapidocr_onnxruntime.main import DEFAULT_CFG_PATH
            from rapidocr_onnxruntime.utils import read_yaml
            import yaml
        except ImportError as e:
            raise RuntimeError(
                "rapidocr-onnxruntime 未安装，请运行: pip install rapidocr-onnxruntime"
            ) from e

        kwargs = {
            "det_model_path": str(self._det_path),
            "rec_model_path": str(self._rec_path),
        }
        if self._cls_path:
            kwargs["cls_model_path"] = str(self._cls_path)
        config_path = None
        if self._dict_path:
            # rapidocr-onnxruntime 的 kwargs 解析器无法可靠注入 Rec.rec_keys_path，
            # 因此语言包带 dict.txt 时生成一份本地配置文件，让识别字典真实生效。
            config = read_yaml(DEFAULT_CFG_PATH)
            config["Global"]["use_cls"] = bool(self._cls_path)
            config["Global"]["intra_op_num_threads"] = 2
            config["Global"]["inter_op_num_threads"] = 2
            config["Det"]["model_path"] = str(self._det_path)
            config["Det"]["use_dml"] = True
            config["Det"]["intra_op_num_threads"] = 2
            config["Det"]["inter_op_num_threads"] = 2
            config["Rec"]["model_path"] = str(self._rec_path)
            config["Rec"]["rec_keys_path"] = str(self._dict_path)
            config["Rec"]["use_dml"] = True
            config["Rec"]["intra_op_num_threads"] = 2
            config["Rec"]["inter_op_num_threads"] = 2
            if self._cls_path:
                config["Cls"]["model_path"] = str(self._cls_path)
                config["Cls"]["use_dml"] = True
                config["Cls"]["intra_op_num_threads"] = 2
                config["Cls"]["inter_op_num_threads"] = 2
            config_path = self.model_path / "vonish_rapidocr_config.yaml"
            config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

        # 启用 DirectML GPU 加速（Windows 专用，绕过 Blackwell CUDA 限制）
        kwargs["use_dml"] = True

        # 限制线程数以避免占用过多 CPU（GPU 模式下 CPU 只做预处理）
        kwargs["intra_op_num_threads"] = 2
        kwargs["inter_op_num_threads"] = 2

        self._ocr = RapidOCR(config_path=str(config_path), **kwargs) if config_path else RapidOCR(**kwargs)
        self.loaded = True
        gc.collect()
        logger.info("ONNX OCR 引擎加载完成: %s", self.model_id)

    async def unload(self) -> None:
        if self._ocr is not None:
            self._ocr = None
        self.loaded = False
        gc.collect()
        logger.info("ONNX OCR 引擎已卸载: %s", self.model_id)

    async def recognize(self, image_bytes: bytes, options: dict) -> dict:
        return self.recognize_sync(image_bytes, options)

    def recognize_sync(self, image_bytes: bytes, options: dict) -> dict:
        if not self.loaded or self._ocr is None:
            raise RuntimeError("OCR 引擎未加载")

        start = time.perf_counter()

        # 将 bytes 转为 numpy.ndarray (BGR)
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # PIL 默认 RGB，转为 BGR 供 OpenCV 使用
            img_array = np.array(img)
            if img_array.ndim == 3 and img_array.shape[2] == 3:
                img_array = img_array[:, :, ::-1]  # RGB -> BGR
            elif img_array.ndim == 3 and img_array.shape[2] == 4:
                # RGBA -> BGR
                img_array = img_array[:, :, :3][:, :, ::-1]
        except Exception as e:
            raise ValueError(f"不支持的图片格式: {e}") from e

        # 调用 rapidocr
        try:
            ocr_res = self._ocr(img_array)
        except Exception as e:
            raise RuntimeError(f"OCR 引擎推理失败: {e}") from e

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # 解析结果
        blocks = []
        total_conf = 0.0
        count = 0

        if ocr_res and ocr_res[0]:
            for item in ocr_res[0]:
                # item 格式: [box_coords, text, conf]
                # box_coords: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                box = item[0]
                text = item[1]
                conf = float(item[2]) if len(item) > 2 else 0.0

                blocks.append(
                    {
                        "text": str(text),
                        "box": box,
                        "confidence": round(conf, 4),
                    }
                )
                total_conf += conf
                count += 1

        # 按从上到下、从左到右排序
        blocks.sort(key=lambda b: (b["box"][0][1], b["box"][0][0]))

        # 合并文本（简单按行合并，相邻 box y 坐标接近则视为同一行）
        merged_text = self._merge_blocks_to_text(blocks)

        avg_conf = round(total_conf / count, 4) if count > 0 else 0.0

        return {
            "text": merged_text,
            "blocks": blocks,
            "confidence": avg_conf,
            "time_ms": elapsed_ms,
        }

    @staticmethod
    def _merge_blocks_to_text(blocks: list[dict]) -> str:
        """将文字块按行合并为完整文本。

        按 box 中心 y 坐标分行，同一行内按 x 坐标排序。
        相邻 box 间距大于平均字符宽度的 0.4 倍时插入空格。
        """
        if not blocks:
            return ""

        # ---- 第一步：按行分组 ----
        lines = []
        current_line = [blocks[0]]
        current_y = sum(p[1] for p in blocks[0]["box"]) / 4  # box 中心 y

        for block in blocks[1:]:
            y = sum(p[1] for p in block["box"]) / 4
            # 用当前行第一个 box 的高度作为行高基准
            first_box = current_line[0]
            line_height = max(
                abs(first_box["box"][3][1] - first_box["box"][0][1]), 10
            )
            if abs(y - current_y) < line_height * 0.8:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
                current_y = y

        if current_line:
            lines.append(current_line)

        # ---- 第二步：每行内合并，动态判断是否加空格 ----
        text_lines = []
        for line in lines:
            line.sort(key=lambda b: b["box"][0][0])

            # 计算该行平均字符宽度
            total_chars = sum(len(b["text"]) for b in line)
            total_width = sum(
                abs(b["box"][2][0] - b["box"][0][0]) for b in line
            )
            avg_char_width = (total_width / total_chars) if total_chars > 0 else 10
            # 空格阈值：间距大于平均字符宽度的 0.4 倍
            space_threshold = avg_char_width * 0.4

            parts = []
            for i, b in enumerate(line):
                parts.append(b["text"])
                if i < len(line) - 1:
                    right_x = b["box"][2][0]  # 当前块右上角 x
                    next_left_x = line[i + 1]["box"][0][0]  # 下一块左上角 x
                    gap = next_left_x - right_x
                    next_box = line[i + 1]
                    next_width = abs(next_box["box"][2][0] - next_box["box"][0][0])
                    curr_width = abs(b["box"][2][0] - b["box"][0][0])
                    min_width = min(curr_width, next_width)

                    if gap > space_threshold:
                        # box 之间有明确间隔 → 加空格
                        parts.append(" ")
                    elif gap <= 0 and min_width > 0:
                        # box 有重叠：轻微重叠（<30%）说明是分开的单词
                        overlap_ratio = abs(gap) / min_width
                        if overlap_ratio < 0.3:
                            parts.append(" ")
            text_lines.append("".join(parts))

        return "\n".join(text_lines)
