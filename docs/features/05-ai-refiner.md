# AI 精修

AI 精修是 VonishOCR 的后处理层，通过大语言模型对原始 OCR 结果进行上下文修正。它不改变图片，只改进文本的可读性与准确性。

## 多厂商配置中心

AI 精修能力由 AI Provider Center 统一管理。用户可以创建多个方案，按需切换。

### 创建方案

1. 打开 AI Provider Center（左侧工具抽屉 → AI 精修 → 配置中心）
2. 点击「新建方案」
3. 填写方案名称（如「医学文档专用」）
4. 选择厂商（DeepSeek / OpenAI / Qwen / Custom）
5. 填写 API Key（以 `sk-` 开头的密钥）
6. 设置优先级（1-10，数字越小优先级越高）
7. 点击保存

API Key 经加密后存储于系统密钥库（Windows DPAPI / macOS Keychain / Linux Secret Service），不以明文形式保存在配置文件中。

### 支持的厂商

| 厂商 | 模型推荐 | 特点 |
|------|---------|------|
| DeepSeek | deepseek-chat | 中文理解强，性价比高 |
| OpenAI | gpt-4o-mini | 通用能力强，英文场景优 |
| Qwen | qwen-turbo | 中文长文本支持好 |
| Custom | 任意 OpenAI 兼容 API | 自建代理或国内中转 |

## 故障自动切换

AI 精修支持多厂商 failover。当优先级最高的方案失败时，系统自动降级至次优方案。

触发 failvoer 的错误条件：

| 错误码 | 含义 | 处理 |
|--------|------|------|
| 404 | 模型不可用 | 立即降级 |
| 429 | 速率限制 | 延迟 3 秒后重试，仍失败则降级 |
| 5xx | 服务端错误 | 立即降级 |
| 超时 | 30 秒无响应 | 立即降级 |

全部方案均失败时，系统聚合报错，向用户展示每家厂商的失败原因，并建议检查网络或 API Key 有效性。

## 流式输出

手动触发「重新精修」时，结果以 SSE（Server-Sent Events）流式推送：

```
event: start
data: {"status": "started"}

event: chunk
data: {"text": "患者于"}

event: chunk
data: {"text": "2026 年"}

event: done
data: {"status": "completed", "full_text": "..."}
```

前端通过 `EventSource` 或 `fetch + ReadableStream` 接收流，逐字追加到 AI 精修栏，形成打字机效果。流式渲染的间隔通过 `requestAnimationFrame` 控制，确保不阻塞 UI。

## 额度机制

| 项目 | 额度 | 说明 |
|------|------|------|
| 基础 OCR | 无限 | 本地模型，无费用 |
| AI 精修（内置） | 每日 500 次 | 官方 API 用户附赠额度 |
| AI 精修（自备 Key） | 取决于厂商 | 使用自己的 API Key，无限制 |

免费额度每日 UTC 0:00 重置。超额后，已配置自备 Key 的用户可继续正常使用；未配置者，AI 精修按钮显示为灰色不可用状态，提示「额度已用完，请配置自备 Key」。

---

> AI 精修不是替代原始 OCR，而是叠加在原始 OCR 之上的可选增强层。对高精度要求的场景（如古籍数字化、法律文书），建议始终开启 AI 精修并逐字复核 Diff。对速度优先的场景（如截图取字），可直接使用原始 OCR。
