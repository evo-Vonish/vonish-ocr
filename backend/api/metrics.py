"""Prometheus metrics endpoint and helper functions."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
except Exception:  # pragma: no cover - fallback for minimal local envs
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _Metric:
        def labels(self, **_labels):
            return self

        def inc(self, *_args, **_kwargs):
            pass

        def observe(self, *_args, **_kwargs):
            pass

        def set(self, *_args, **_kwargs):
            pass

    Counter = Histogram = Gauge = lambda *_args, **_kwargs: _Metric()

    def generate_latest():
        return b"# prometheus_client unavailable\n"


ocr_requests_total = Counter(
    "vonishocr_requests_total",
    "Total OCR requests",
    ["model_tier", "status", "tenant_id"],
)
ocr_duration_seconds = Histogram(
    "vonishocr_duration_seconds",
    "OCR latency",
    ["model_tier"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)
queue_depth_gauge = Gauge("vonishocr_queue_depth", "Current queue depth")
gpu_vram_bytes = Gauge("vonishocr_gpu_vram_used_bytes", "GPU VRAM used")
gpu_utilization = Gauge("vonishocr_gpu_utilization_percent", "GPU utilization")
cpu_temperature = Gauge("vonishocr_cpu_temperature_celsius", "CPU temperature")


@router.get("")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_ocr_request(model_tier: str, status: str, tenant_id: str):
    ocr_requests_total.labels(model_tier=model_tier, status=status, tenant_id=tenant_id).inc()


def record_ocr_duration(model_tier: str, seconds: float):
    ocr_duration_seconds.labels(model_tier=model_tier).observe(seconds)


def set_queue_depth(depth: int):
    queue_depth_gauge.set(depth)


def set_gpu_stats(vram_bytes: int, util_percent: float):
    gpu_vram_bytes.set(vram_bytes)
    gpu_utilization.set(util_percent)


def set_cpu_temperature(temp_celsius: float | None):
    if temp_celsius is not None:
        cpu_temperature.set(temp_celsius)
