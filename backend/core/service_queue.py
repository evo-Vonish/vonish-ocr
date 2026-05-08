"""Service-facing OCR task queue.

This queue is used by external REST submissions. It records every task in
SQLite, exposes snapshots for the console, and runs OCR work in background
workers with priority ordering and backpressure.
"""
import asyncio
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_TIER_MAP = {
    "auto": "rapidocr-mobile-cn",
    "rapid": "rapidocr-mobile-cn",
    "ultra": "rapidocr-mobile-cn",
    "standard": "cnocr-standard-cn",
    "cnocr": "cnocr-standard-cn",
    "pro": "onnxtr-standard",
    "professional": "onnxtr-standard",
}


class ServiceTaskQueue:
    """Priority queue for API-submitted OCR tasks."""

    def __init__(self, *, admin_db, app, max_workers: int = 2, max_pending: int = 200):
        self.admin_db = admin_db
        self.app = app
        self.max_workers = max(1, int(max_workers or 1))
        self.max_pending = max(1, int(max_pending or 200))
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=self.max_pending)
        self._workers: list[asyncio.Task] = []
        self._shutdown = False
        self._seq = 0
        self._subscribers: set[asyncio.Queue] = set()

    async def start(self):
        if self._workers:
            return
        for idx in range(self.max_workers):
            self._workers.append(asyncio.create_task(self._worker_loop(idx)))

    async def stop(self):
        self._shutdown = True
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    async def submit(self, *, file_path: Path, filename: str, file_size: int, model_tier: str, priority: int, tenant_id: str):
        if self.queue.full():
            raise RuntimeError("QUEUE_BACKPRESSURE")
        self._seq += 1
        queue_pos = self.queue.qsize() + 1
        task_id = await self.admin_db.insert_queue_task({
            "tenant_id": tenant_id,
            "filename": filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "model_tier": model_tier,
            "priority": priority,
            "queue_pos": queue_pos,
        })
        await self.queue.put((-int(priority or 0), self._seq, task_id))
        try:
            from api.metrics import set_queue_depth

            set_queue_depth(self.queue.qsize())
        except Exception:
            pass
        await self.publish()
        return {"task_id": task_id, "queue_pos": queue_pos}

    async def cancel(self, task_id: str):
        task = await self.admin_db.get_task(task_id)
        if not task or task["status"] not in ("queued", "processing"):
            return False
        await self.admin_db.update_task(task_id, status="cancelled", completed_at=time.time())
        try:
            from api.metrics import set_queue_depth

            set_queue_depth(self.queue.qsize())
        except Exception:
            pass
        await self.publish()
        return True

    async def retry(self, task_id: str):
        task = await self.admin_db.get_task(task_id)
        if not task:
            return False
        if task["status"] not in ("failed", "cancelled"):
            return False
        self._seq += 1
        await self.admin_db.update_task(
            task_id,
            status="queued",
            queue_pos=self.queue.qsize() + 1,
            error=None,
            result_json=None,
            started_at=None,
            completed_at=None,
        )
        await self.queue.put((-int(task.get("priority") or 0), self._seq, task_id))
        try:
            from api.metrics import set_queue_depth

            set_queue_depth(self.queue.qsize())
        except Exception:
            pass
        await self.publish()
        return True

    async def snapshot(self, *, tenant_id: str | None = None, limit: int = 100):
        tasks = await self.admin_db.list_tasks(tenant_id=tenant_id, limit=limit)
        stats = await self.admin_db.task_stats()
        return {
            "stats": {
                "queued": int(stats.get("queued", 0)),
                "processing": int(stats.get("processing", 0)),
                "done": int(stats.get("done", 0)),
                "failed": int(stats.get("failed", 0)),
                "cancelled": int(stats.get("cancelled", 0)),
                "pending_runtime": self.queue.qsize(),
                "max_pending": self.max_pending,
            },
            "tasks": [self._public_task(row) for row in tasks],
        }

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=4)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)

    async def publish(self):
        if not self._subscribers:
            return
        payload = await self.snapshot()
        for subscriber in list(self._subscribers):
            if subscriber.full():
                try:
                    subscriber.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                subscriber.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def _worker_loop(self, worker_index: int):
        while not self._shutdown:
            try:
                _, _, task_id = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._run_task(task_id, worker_index)
            finally:
                self.queue.task_done()

    async def _run_task(self, task_id: str, worker_index: int):
        task = await self.admin_db.get_task(task_id)
        if not task or task["status"] == "cancelled":
            return
        await self.admin_db.update_task(task_id, status="processing", started_at=time.time(), queue_pos=0)
        await self.publish()

        try:
            file_path = Path(task["file_path"])
            image_bytes = await asyncio.to_thread(file_path.read_bytes)
            model_id = MODEL_TIER_MAP.get(task["model_tier"], task["model_tier"]) or "rapidocr-mobile-cn"
            engine_mgr = self.app.state.engine_manager
            if model_id == "auto" or model_id not in engine_mgr._factories:
                model_id = "rapidocr-mobile-cn"
            if model_id not in engine_mgr.engines:
                await engine_mgr.load(model_id)

            started = time.time()
            result = await engine_mgr.recognize(image_bytes, model_id=model_id, options={"model": model_id})
            elapsed = time.time() - started
            result["task_id"] = task_id
            result["model"] = model_id
            result["elapsed_ms"] = int(elapsed * 1000)
            await self.admin_db.update_task(
                task_id,
                status="done",
                completed_at=time.time(),
                result_json=json.dumps(result, ensure_ascii=False),
                error=None,
            )
            try:
                from api.metrics import record_ocr_duration, record_ocr_request

                record_ocr_duration(task["model_tier"], elapsed)
                record_ocr_request(task["model_tier"], "done", task.get("tenant_id") or "default")
            except Exception:
                pass
            logger.info("Service queue task %s completed by worker %s", task_id, worker_index)
        except Exception as exc:
            logger.exception("Service queue task failed: %s", task_id)
            await self.admin_db.update_task(
                task_id,
                status="failed",
                completed_at=time.time(),
                error=str(exc),
            )
            try:
                from api.metrics import record_ocr_request

                record_ocr_request(task.get("model_tier") or "auto", "failed", task.get("tenant_id") or "default")
            except Exception:
                pass
        try:
            from api.metrics import set_queue_depth

            set_queue_depth(self.queue.qsize())
        except Exception:
            pass
        await self.publish()

    @staticmethod
    def _public_task(row: dict):
        result = None
        if row.get("result_json"):
            try:
                result = json.loads(row["result_json"])
            except Exception:
                result = None
        return {
            "id": row["id"],
            "tenant_id": row.get("tenant_id") or "default",
            "filename": row.get("filename"),
            "file_size": row.get("file_size") or 0,
            "model_tier": row.get("model_tier") or "auto",
            "status": row.get("status") or "queued",
            "priority": row.get("priority") or 0,
            "queue_pos": row.get("queue_pos") or 0,
            "created_at": row.get("created_at"),
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "elapsed_ms": int(((row.get("completed_at") or time.time()) - row["started_at"]) * 1000)
            if row.get("started_at") else None,
            "error": row.get("error"),
            "result": result,
        }
