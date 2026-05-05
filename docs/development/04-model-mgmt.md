# 模型管理

VonishOCR 的模型管理涵盖格式要求、元数据规范、切换逻辑与格式转换工具链。

## ONNX 模型格式要求

当前 VonishOCR 的推理引擎基于 ONNXRuntime，所有模型必须符合以下规范：

| 属性 | 要求 |
|------|------|
| 格式 | ONNX（`.onnx`） |
| Opset | >= 12 |
| 输入 | 单张 RGB 图像，NCHW 格式，归一化至 [0, 1] |
| 输出 | 文本框坐标 + 识别文本 + 置信度 |
| 动态轴 | 支持 batch 维度动态 |

模型文件命名规范：

```
{model_id}_{version}.onnx
```

示例：`rapidocr-mobile-cn_v2.0.onnx`、`cnocr-standard-cn_v1.2.onnx`

## manifest.json 结构

`models/manifest.json` 描述所有可用模型的元数据：

```json
{
  "schema_version": "1.0",
  "models": [
    {
      "id": "rapidocr-mobile-cn",
      "version": "2.0",
      "name": "极速模型",
      "size_mb": 22,
      "sha256": "a1b2c3d4...",
      "languages": ["zh", "en"],
      "capabilities": ["text"],
      "scenes": ["print", "screenshot"],
      "default_for": ["print"],
      "url": "https://github.com/.../model.onnx",
      "engine": "onnxruntime"
    },
    {
      "id": "cnocr-standard-cn",
      "version": "1.2",
      "name": "标准模型",
      "size_mb": 80,
      "sha256": "e5f6g7h8...",
      "languages": ["zh", "en"],
      "capabilities": ["text", "table"],
      "scenes": ["print", "handwritten", "mixed"],
      "default_for": ["handwritten", "mixed"],
      "url": "https://github.com/.../model.onnx",
      "engine": "onnxruntime"
    },
    {
      "id": "paddleocr-vl-1.5",
      "version": "1.5",
      "name": "专业模型",
      "size_mb": 1870,
      "sha256": "i9j0k1l2...",
      "languages": ["zh", "en"],
      "capabilities": ["text", "table", "layout", "formula"],
      "scenes": ["complex", "degraded"],
      "default_for": ["complex", "degraded"],
      "url": "https://huggingface.co/.../model.safetensors",
      "engine": "transformers",
      "status": "pending_conversion"
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 模型唯一标识，用于代码引用 |
| `version` | string | 语义化版本 |
| `size_mb` | int | 模型文件大小（解压后）|
| `sha256` | string | 文件校验值 |
| `capabilities` | array | 支持的能力：text/table/layout/formula |
| `scenes` | array | 适用场景标签 |
| `default_for` | array | 作为默认推荐的场景 |
| `engine` | string | 推理引擎：onnxruntime / transformers |
| `status` | string | 可用状态：ready / pending_conversion |

## 模型切换逻辑

模型切换的执行流程：

```python
def switch_model(target_id: str):
    # 1. 校验目标模型是否存在
    if target_id not in manifest:
        raise ModelNotFoundError(target_id)
    
    # 2. 卸载当前模型
    if current_model is not None:
        current_model.unload()
        gc.collect()
        # 显存释放提示（异步）
    
    # 3. 校验目标模型文件完整性
    model_path = MODELS_DIR / f"{target_id}.onnx"
    if not model_path.exists():
        raise ModelFileMissingError(target_id)
    
    expected_sha256 = manifest[target_id].sha256
    actual_sha256 = compute_sha256(model_path)
    if expected_sha256 != actual_sha256:
        raise ModelCorruptedError(target_id)
    
    # 4. 加载目标模型
    new_model = InferenceSession(model_path, providers=['DmlExecutionProvider', 'CPUExecutionProvider'])
    
    # 5. 预热推理（首次推理较慢）
    dummy_input = np.zeros((1, 3, 640, 640), dtype=np.float32)
    new_model.run(None, {'input': dummy_input})
    
    # 6. 更新当前模型引用
    current_model = new_model
```

切换期间的识别服务短暂不可用（通常 < 5 秒），前端显示「模型切换中」遮罩。

## PaddleOCR 格式转换

PaddleOCR VL 1.5 当前使用 HuggingFace Transformers 格式（safetensors），体积约 1.87GB。要接入 VonishOCR 的 ONNX 引擎，需要完成格式转换。

### 转换路径

```
safetensors -> PyTorch 状态字典 -> ONNX
```

### 工具链

1. **导出 PyTorch**：使用 PaddleOCR 官方导出工具将推理模型转为 PyTorch 格式
2. **PyTorch -> ONNX**：使用 `torch.onnx.export` 导出为 ONNX
3. **ONNX 优化**：使用 ONNXRuntime 工具进行图优化与常量折叠
4. **验证**：对比 PyTorch 与 ONNX 的输出一致性（余弦相似度 > 0.999）

### 已知问题

- PaddleOCR 的版面分析模块包含动态控制流（如 `if` 分支），部分操作在 ONNX 中需要展开为静态图
- 公式检测模块的注意力机制在导出时可能需要简化（如固定序列长度）

当前状态：专业模型在 UI 中显示为「即将可用」，转换工具链正在开发中。

---

> 模型管理是 VonishOCR 的核心竞争力之一。用户应该像管理文件一样管理自己的模型——下载、切换、校验、删除，全部自主可控，无需等待厂商推送。
