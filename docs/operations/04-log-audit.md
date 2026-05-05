# 日志审计

VonishOCR 的日志系统记录运行时事件，支持审计、排错与合规需求。

## 日志文件位置

| 系统 | 路径 |
|------|------|
| Windows | `%APPDATA%\VonishOCR\logs\backend.log` |
| macOS | `~/Library/Application Support/VonishOCR/logs/backend.log` |
| Linux | `~/.config/VonishOCR/logs/backend.log` |

日志文件按 10MB 大小自动轮转，保留最近 5 个文件（`backend.log.1` 至 `backend.log.5`）。

## 日志格式

每条日志包含五个字段：

```
2026-05-05 14:36:12.347 | INFO     | [OCR] 模型加载完成：cnocr-standard-cn
2026-05-05 14:36:15.102 | DEBUG    | [PREP] 自动旋转：检测角度 2.3°，无需旋转
2026-05-05 14:36:15.205 | WARN     | [OCR] 低置信字段 detected：3 个
2026-05-05 14:36:18.891 | ERROR    | [AI] deepseek: 429 RateLimitExceeded
```

格式说明：

| 字段 | 说明 | 示例 |
|------|------|------|
| 时间戳 | 精确到毫秒 | `2026-05-05 14:36:12.347` |
| 级别 | DEBUG / INFO / WARN / ERROR | `INFO` |
| 标签 | 模块标识，方括号包围 | `[OCR]` |
| 内容 | 事件描述 | `模型加载完成` |

## 日志级别

| 级别 | 用途 | 生产环境默认 |
|------|------|-------------|
| DEBUG | 开发调试，详细流程跟踪 | 关闭 |
| INFO | 正常运行事件 | 开启 |
| WARN | 异常但可恢复的事件 | 开启 |
| ERROR | 需要人工干预的故障 | 开启 |

日志级别可在后端控制台或 `config.json` 中调整：

```json
{
  "logging": {
    "level": "INFO",
    "output": "file",
    "max_size_mb": 10,
    "backup_count": 5
  }
}
```

## 导出与筛选

后端控制台的日志审计面板提供以下功能：

### 时间范围筛选

- 预设：最近 1 小时 / 今天 / 最近 7 天 / 最近 30 天
- 自定义：选择起止日期

### 标签筛选

- `[OCR]`：识别引擎事件
- `[PREP]`：预处理事件
- `[AI]`：AI 精修事件
- `[QUEUE]`：批量队列事件
- `[API]`：HTTP API 请求
- `[SYS]`：系统级事件

### 级别筛选

多选框：DEBUG / INFO / WARN / ERROR

### 导出

筛选结果可导出为 CSV：

```csv
timestamp,level,tag,message
2026-05-05 14:36:12.347,INFO,[OCR],模型加载完成：cnocr-standard-cn
2026-05-05 14:36:15.205,WARN,[OCR],低置信字段 detected：3 个
```

导出文件保存至用户下载目录，文件名格式：`vonishocr_logs_20260505_143612.csv`。

---

> 日志是软件的「黑匣子」。当问题发生时，日志是唯一的客观记录。VonishOCR 的日志设计追求「足够详细但不过度冗余」——开发者能从中定位 bug，用户能从中理解系统行为，审计员能从中验证合规性。
