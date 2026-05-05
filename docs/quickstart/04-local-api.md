# 本地 API 调用

VonishOCR 本地版在启动后会暴露一个 HTTP API 服务，任何能发送 HTTP 请求的工具或语言都可以调用。

## 服务地址

```
http://localhost:8000
```

端口可在后端控制台中修改。若修改端口，所有示例中的 `8000` 需同步替换。

## Python 示例

```python
import requests

res = requests.post(
    'http://localhost:8000/v1/ocr',
    files={'file': open('scan.jpg', 'rb')}
)
result = res.json()
print(result['text'])
```

带选项的调用：

```python
import requests

res = requests.post(
    'http://localhost:8000/v1/ocr',
    files={'file': open('scan.jpg', 'rb')},
    data={
        'scene': 'handwritten_note',  # 强制指定场景
        'model': 'standard',           # 强制指定模型档位
        'ai_refine': 'true'           # 触发 AI 精修
    }
)
print(res.json()['text'])
```

## cURL 示例

```bash
curl -X POST http://localhost:8000/v1/ocr   -F "file=@scan.jpg"   -F "scene=print"   -F "ai_refine=true"
```

Base64 编码调用（适合前端 JavaScript）：

```bash
curl -X POST http://localhost:8000/v1/ocr   -H "Content-Type: application/json"   -d '{
    "image": "data:image/png;base64,iVBORw0KGgo...",
    "scene": "screenshot",
    "ai_refine": false
  }'
```

## 返回 JSON 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 识别文本（AI 精修后如启用，否则为原始 OCR） |
| `confidence` | float | 整体置信度，范围 0.0 - 1.0 |
| `scene` | string | 实际使用的场景分类标签 |
| `diff` | array | 原始与精修的差异数组（AI 精修启用时） |
| `low_confidence_fields` | array | 低置信字段列表，含坐标、原文、置信度 |

返回示例：

```json
{
  "text": "患者于 2026 年 4 月 18 日复诊，主诉咽部不适三日。",
  "confidence": 0.87,
  "scene": "print",
  "diff": [
    {"original": "仃", "refined": "行", "position": [12, 15]}
  ],
  "low_confidence_fields": [
    {"text": "血常规", "confidence": 0.43, "bbox": [120, 80, 180, 110]}
  ]
}
```

## 批量 API

批量任务通过 WebSocket 获取实时进度：

```python
import requests, json

# 1. 提交批量任务
res = requests.post(
    'http://localhost:8000/v1/ocr/batch/json',
    json={"images": [img1_base64, img2_base64, ...]}
)
task_id = res.json()['task_id']

# 2. 通过 WebSocket 连接获取进度
# wss://localhost:8000/ws/batch/{task_id}
# 进度消息格式: {"type": "progress", "completed": 67, "total": 200}

# 3. 完成后获取结果
results = requests.get(
    f'http://localhost:8000/v1/ocr/batch/{task_id}/results'
).json()
```

---

> 本地 API 与官方云端 API 的返回格式完全一致。开发阶段使用本地 API 调试，生产环境可零成本迁移至云端 API。
