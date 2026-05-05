# 后端控制台开发

后端控制台是 VonishOCR 的运维仪表板，其开发涉及机柜面板布局、硬件监控数据获取与实时日志推送。

## 机柜面板布局思路

后端控制台的视觉隐喻是服务器机柜的前面板：信息密集、状态明确、操作直接。

```vue
<!-- BackendConsole.vue -->
<template>
  <div class="console-modal">
    <header class="console-header">
      <h2>后端控制台</h2>
      <button @click="close">关闭</button>
    </header>
    
    <section class="dashboard-grid">
      <!-- 算力仪表盘卡片 -->
      <HardwareCard
        v-for="metric in hardwareMetrics"
        :key="metric.id"
        :title="metric.title"
        :value="metric.value"
        :unit="metric.unit"
        :status="metric.status"
      />
    </section>
    
    <section class="model-control">
      <h3>模型管理</h3>
      <ModelSwitcher :current="currentModel" :available="availableModels" />
    </section>
    
    <section class="api-control">
      <h3>本地 API</h3>
      <ApiConfig :config="apiConfig" @restart="restartApi" />
    </section>
    
    <section class="log-stream">
      <h3>实时日志</h3>
      <LogTerminal :logs="logs" :filter="logFilter" />
    </section>
  </div>
</template>

<style scoped>
.console-modal {
  background: var(--bg-panel);
  border: 1px solid var(--border-steel);
  box-shadow: inset 0 0 20px rgba(143, 246, 210, 0.04);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
```

## 硬件监控数据获取

### GPU 监控（NVIDIA）

```python
# backend/core/hardware.py
import psutil
try:
    import nvidia_ml_py3 as nvidia
    NVIDIA_AVAILABLE = True
except ImportError:
    NVIDIA_AVAILABLE = False

def get_gpu_metrics():
    if not NVIDIA_AVAILABLE:
        return None
    
    nvidia.nvmlInit()
    handle = nvidia.nvmlDeviceGetHandleByIndex(0)
    
    # 显存
    mem_info = nvidia.nvmlDeviceGetMemoryInfo(handle)
    mem_used = mem_info.used / 1024**2  # MB
    mem_total = mem_info.total / 1024**2
    
    # 利用率
    utilization = nvidia.nvmlDeviceGetUtilizationRates(handle)
    gpu_util = utilization.gpu
    
    # 温度
    temp = nvidia.nvmlDeviceGetTemperature(handle, nvidia.NVML_TEMPERATURE_GPU)
    
    # 功耗
    power = nvidia.nvmlDeviceGetPowerUsage(handle) / 1000  # W
    
    return {
        'memory_used_mb': mem_used,
        'memory_total_mb': mem_total,
        'utilization_percent': gpu_util,
        'temperature_c': temp,
        'power_w': power
    }
```

### CPU 与内存监控

```python
def get_cpu_metrics():
    return {
        'percent': psutil.cpu_percent(interval=1),
        'freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
        'core_count': psutil.cpu_count()
    }

def get_memory_metrics():
    mem = psutil.virtual_memory()
    return {
        'used_gb': mem.used / 1024**3,
        'total_gb': mem.total / 1024**3,
        'percent': mem.percent
    }
```

### DirectML 设备监控

对于非 NVIDIA 设备（AMD/Intel），通过 DirectML API 获取有限信息：

```python
try:
    import onnxruntime as ort
    providers = ort.get_available_providers()
    
    if 'DmlExecutionProvider' in providers:
        # DirectML 不提供显存查询 API，只能通过系统级工具估算
        pass
except ImportError:
    pass
```

## 实时日志 WebSocket / SSE 推送

后端控制台需要实时推送日志，可选 WebSocket 或 SSE 两种方案。

### WebSocket 方案

```python
# backend/api/routes.py
from fastapi import WebSocket

@app.websocket("/ws/logs")
async def log_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # 注册到日志广播器
    log_broadcaster.register(websocket)
    
    try:
        while True:
            # 保持连接，接收前端的心跳或筛选指令
            data = await websocket.receive_text()
            filter_config = json.loads(data)
            log_broadcaster.update_filter(websocket, filter_config)
    except WebSocketDisconnect:
        log_broadcaster.unregister(websocket)
```

### SSE 方案（推荐）

SSE 更适合单向日志推送场景，实现更简单：

```python
@app.get("/stream/logs")
async def log_stream(
    level: str = "INFO",
    tag: str = None
):
    async def event_generator():
        queue = asyncio.Queue()
        log_broadcaster.subscribe(queue, level=level, tag=tag)
        
        try:
            while True:
                log_line = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(log_line)}\n\n"
        except asyncio.TimeoutError:
            yield f"event: heartbeat\ndata: {{}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 日志广播器实现

```python
import asyncio
from typing import Dict, Set

class LogBroadcaster:
    def __init__(self):
        self.subscribers: Dict[asyncio.Queue, dict] = {}
    
    def subscribe(self, queue: asyncio.Queue, level="INFO", tag=None):
        self.subscribers[queue] = {"level": level, "tag": tag}
    
    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.pop(queue, None)
    
    def broadcast(self, log_line: dict):
        for queue, filter_config in list(self.subscribers.items()):
            if self._match_filter(log_line, filter_config):
                try:
                    queue.put_nowait(log_line)
                except asyncio.QueueFull:
                    pass
    
    def _match_filter(self, log_line: dict, config: dict) -> bool:
        level_order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
        if level_order.get(log_line["level"], 1) < level_order.get(config["level"], 1):
            return False
        if config["tag"] and log_line.get("tag") != config["tag"]:
            return False
        return True
```

---

> 后端控制台是 VonishOCR 的「机柜面板」——信息必须高密度、反馈必须即时、操作必须有确认。等宽字体显示数值，颜色编码状态，边框定义区域，内发光营造深度。这不是装饰，而是工业界面的人因工程学。
