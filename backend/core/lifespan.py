"""Graceful shutdown helpers."""
import asyncio
import signal
import time

shutdown_event = None


def _event() -> asyncio.Event:
    global shutdown_event
    if shutdown_event is None:
        shutdown_event = asyncio.Event()
    return shutdown_event


def register_signals():
    """Register SIGTERM/SIGINT handlers that only mark shutdown intent."""
    def handler(signum, frame):
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(_event().set)
        except Exception:
            pass

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


async def wait_for_shutdown():
    await _event().wait()


async def drain_queue(task_queue, timeout: float = 30.0):
    """Wait for a queue-like object to drain, up to *timeout* seconds.

    TODO: external queues should expose depth(). For current VonishOCR queues,
    this helper also accepts `.queue.qsize()`.
    """
    start = time.time()
    while time.time() - start < timeout:
        if hasattr(task_queue, "depth"):
            depth = task_queue.depth()
        elif hasattr(task_queue, "queue"):
            depth = task_queue.queue.qsize()
        else:
            depth = 0
        if depth <= 0:
            return True
        await asyncio.sleep(0.5)
    return False
