# AI Refiner 开发

AI Refiner 是 VonishOCR 的后处理模块，负责调用大语言模型修正 OCR 结果，并以 SSE 流式方式输出。

## SSE 流式输出实现

### 后端：FastAPI SSE

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/v1/ocr/refine")
async def refine_stream(request: RefineRequest):
    async def event_generator():
        yield f"event: start\ndata: {json.dumps({'status': 'started'})}\n\n"
        
        for chunk in call_llm(request.text, request.scene):
            yield f"event: chunk\ndata: {json.dumps({'text': chunk})}\n\n"
        
        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
```

### 前端：EventSource 消费

```javascript
// composables/useAIStream.js
export function useAIStream() {
  const result = ref('')
  const isStreaming = ref(false)
  
  function startStream(text, scene, onChunk, onDone) {
    isStreaming.value = true
    result.value = ''
    
    const evtSource = new EventSource(
      `http://localhost:8000/v1/ocr/refine?text=${encodeURIComponent(text)}&scene=${scene}`
    )
    
    evtSource.addEventListener('chunk', (e) => {
      const data = JSON.parse(e.data)
      result.value += data.text
      onChunk?.(data.text)
    })
    
    evtSource.addEventListener('done', (e) => {
      isStreaming.value = false
      evtSource.close()
      onDone?.(result.value)
    })
    
    evtSource.addEventListener('error', (e) => {
      isStreaming.value = false
      evtSource.close()
      throw new Error('SSE connection error')
    })
  }
  
  return { result, isStreaming, startStream }
}
```

### 前端：fetch + ReadableStream（备选）

部分环境（如某些 Tauri WebView）对 EventSource 支持有限，可使用 fetch + ReadableStream：

```javascript
async function startStreamFetch(url, onChunk) {
  const response = await fetch(url)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const text = decoder.decode(value)
    // 解析 SSE 格式：event: chunk\ndata: {...}\n\n
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = JSON.parse(line.slice(5))
        onChunk(data.text)
      }
    }
  }
}
```

## 多厂商 Failover 逻辑

AI Refiner 支持多方案优先级排序，主方案失败时自动降级。

```python
class AIRefiner:
    def __init__(self, schemes: list[AIScheme]):
        # 按优先级排序（数字越小优先级越高）
        self.schemes = sorted(schemes, key=lambda s: s.priority)
    
    async def refine(self, text: str, scene_type: str) -> dict:
        last_error = None
        
        for scheme in self.schemes:
            try:
                result = await self._call_scheme(scheme, text, scene_type)
                return result
            except Exception as e:
                last_error = f"{scheme.provider}: {str(e)}"
                # 根据错误类型决定是否立即降级或重试
                if isinstance(e, RateLimitError):
                    await asyncio.sleep(3)  # 速率限制时延迟重试
                    try:
                        result = await self._call_scheme(scheme, text, scene_type)
                        return result
                    except Exception:
                        pass
                continue
        
        # 全部失败
        raise AllProvidersFailedError(last_error)
    
    async def _call_scheme(self, scheme: AIScheme, text: str, scene_type: str) -> dict:
        prompt = self._build_prompt(text, scene_type)
        
        response = await httpx.post(
            scheme.api_url,
            headers={"Authorization": f"Bearer {scheme.api_key}"},
            json={
                "model": scheme.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 4096
            },
            timeout=30.0
        )
        
        # 流式读取响应
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                yield data["choices"][0]["delta"].get("content", "")
```

### 错误码判断

| 错误码 | 行为 |
|--------|------|
| 404 | 立即降级，模型不可用 |
| 429 | 延迟 3 秒重试一次，仍失败则降级 |
| 5xx | 立即降级，服务端故障 |
| 超时（30s） | 立即降级 |
| JSON 解析失败 | 标记当前方案异常，降级至下一方案 |

## 流式打字机渲染

前端收到 SSE chunk 后，以逐字追加的方式渲染到界面：

```javascript
// 方式一：setInterval（简单）
function typewriterRender(fullText, container, speed = 30) {
  let i = 0
  container.textContent = ''
  
  const timer = setInterval(() => {
    if (i >= fullText.length) {
      clearInterval(timer)
      return
    }
    container.textContent += fullText[i]
    i++
  }, speed)
}

// 方式二：requestAnimationFrame（流畅，推荐）
function typewriterRenderRAF(fullText, container, charsPerFrame = 2) {
  let i = 0
  container.textContent = ''
  
  function render() {
    const end = Math.min(i + charsPerFrame, fullText.length)
    container.textContent += fullText.slice(i, end)
    i = end
    
    if (i < fullText.length) {
      requestAnimationFrame(render)
    }
  }
  
  requestAnimationFrame(render)
}
```

`requestAnimationFrame` 方式与浏览器的渲染帧同步，避免 `setInterval` 可能导致的卡顿与闪烁。

---

> AI Refiner 的开发核心矛盾是「速度与质量的平衡」。流式输出让用户感知到进度，减少等待焦虑；多厂商 failover 保证服务的可用性；而打字机效果则是人机交互层面的「温度」——即使处理的是机器文本，呈现方式仍是人类可阅读的。
