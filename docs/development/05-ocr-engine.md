# OCR 引擎接入

VonishOCR 的 OCR 引擎层通过统一的 `OCREngineManager` 管理多种底层引擎的加载与调用。

## 引擎架构

```
OCREngineManager
├── ONNXOCREngine
│   ├── rapidocr-mobile-cn    (22MB)
│   └── cnocr-standard-cn     (80MB)
├── TransformersEngine (开发中)
│   └── paddleocr-vl-1.5      (1.87GB)
└── PreprocessPipeline
    ├── auto_rotate
    ├── deskew
    ├── denoise
    ├── contrast_enhance
    └── quality_check
```

## rapidocr 接入

rapidocr 是 VonishOCR 的极速模型引擎，基于轻量级 CNN。

### 推理流程

```python
from onnxruntime import InferenceSession
import numpy as np
from PIL import Image

class RapidOCREngine:
    def __init__(self, model_path: str):
        self.session = InferenceSession(
            model_path,
            providers=['DmlExecutionProvider', 'CPUExecutionProvider']
        )
    
    def recognize(self, image: Image.Image) -> dict:
        # 1. 预处理：resize → normalize → NCHW
        input_tensor = self.preprocess(image)
        
        # 2. ONNX 推理
        outputs = self.session.run(None, {'input': input_tensor})
        
        # 3. 后处理：解码文本、提取坐标、计算置信度
        result = self.postprocess(outputs)
        
        return {
            'text': result.text,
            'confidence': result.confidence,
            'boxes': result.boxes
        }
    
    def preprocess(self, image: Image.Image) -> np.ndarray:
        image = image.convert('RGB')
        image = image.resize((640, 640))
        arr = np.array(image).astype(np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))  # HWC → CHW
        arr = np.expand_dims(arr, 0)         # CHW → NCHW
        return arr
```

### 关键点

- **输入尺寸**：rapidocr 使用 640×640 固定输入，大图像会被缩放，小图像会被放大
- **文本方向**：模型本身不支持旋转识别，旋转检测由预处理管线的 `auto_rotate` 完成
- **GPU 加速**：`DmlExecutionProvider` 提供 DirectML 加速，支持 NVIDIA/AMD/Intel 显卡

## cnocr 接入

cnocr 是标准模型引擎，支持文字与基础表格结构识别。

### 推理流程

cnocr 的推理与 rapidocr 类似，但输出包含额外的表格结构信息：

```python
{
    'text': '识别的完整文本',
    'confidence': 0.87,
    'boxes': [[x1,y1,x2,y2,x3,y3,x4,y4], ...],
    'table_cells': [  # 仅表格场景
        {'text': '单元格文本', 'row': 0, 'col': 1, 'bbox': [...]},
        ...
    ]
}
```

### 表格结构输出

当场景分类为「表格」或用户手动指定时，cnocr 尝试检测表格单元格边界。检测结果以 `table_cells` 数组返回，每个单元格包含：

- `text`：单元格内识别文本
- `row` / `col`：单元格在行/列中的位置
- `bbox`：单元格四边形坐标

表格结构可导出为 Markdown 或 CSV：

```markdown
| 姓名 | 年龄 | 科室 |
|------|------|------|
| 张三 | 45 | 内科 |
| 李四 | 32 | 外科 |
```

## paddleocr 接入（规划中）

PaddleOCR VL 1.5 将提供版面分析与公式检测能力。当前架构已为其实现预留接口：

```python
class TransformersEngine:
    """PaddleOCR VL adapter engine (in development)"""
    
    def __init__(self, model_path: str):
        # 加载 Transformers 模型
        pass
    
    def recognize(self, image: Image.Image) -> dict:
        # 版面分析 → 区域检测 → 逐区域 OCR → 结构化输出
        return {
            'text': '...',
            'layout_blocks': [
                {'type': 'title', 'text': '...', 'bbox': [...]},
                {'type': 'paragraph', 'text': '...', 'bbox': [...]},
                {'type': 'table', 'cells': [...]},
                {'type': 'formula', 'latex': '...', 'bbox': [...]}
            ]
        }
```

## 预处理管线代码

预处理管线在引擎推理前执行，根据场景分类动态调整步骤：

```python
class PreprocessPipeline:
    def __init__(self, scene: str):
        self.scene = scene
        self.steps = self._build_pipeline(scene)
    
    def _build_pipeline(self, scene: str) -> list:
        base = [auto_rotate]
        
        if scene in ['print', 'screenshot']:
            return base + [quality_check]
        
        if scene == 'handwritten_note':
            return base + [deskew, denoise, contrast_enhance, quality_check]
        
        if scene in ['complex', 'degraded']:
            return base + [deskew, denoise, contrast_enhance, sharpen, quality_check]
        
        return base + [deskew, denoise, quality_check]
    
    def run(self, image: Image.Image) -> Image.Image:
        for step in self.steps:
            image = step(image)
        return image
```

### 各步骤实现要点

| 步骤 | 关键算法 | 触发条件 |
|------|---------|---------|
| `auto_rotate` | 笔画方向直方图 | 文本方向非水平 |
| `deskew` | 霍夫变换 + 透视矫正 | 倾斜角 > 5° |
| `denoise` | 高斯/中值/频域滤波 | 噪声能量 > 阈值 |
| `contrast_enhance` | CLAHE | 对比度 < 0.3 |
| `sharpen` | 拉普拉斯卷积核 | 边缘清晰度 < 0.4 |
| `quality_check` | 综合评分 | 所有场景最后一步 |

---

> 引擎层的设计目标是「统一接口，差异实现」。无论底层是 rapidocr、cnocr 还是未来的 PaddleOCR，前端与业务逻辑层看到的都是相同的 `recognize(image) → result` 接口。
