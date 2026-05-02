import asyncio
import time
import uuid
from typing import Callable, Dict, List, Optional


class LocalQueue:
    def __init__(self, max_workers: int = 4, concurrency: int = 8):
        self.queue = asyncio.Queue()
        self.tasks: Dict[str, dict] = {}
        self.max_workers = max_workers
        self.concurrency = concurrency
        self._workers: List[asyncio.Task] = []
        self._shutdown = False
        self._progress_callbacks: Dict[str, Callable] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}

    def submit(self, images: List[bytes], options: dict) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "status": "queued",
            "total": len(images),
            "completed": 0,
            "failed": 0,
            "results": [],
            "submitted_at": time.time(),
        }
        self._cancel_events[task_id] = asyncio.Event()
        self.queue.put_nowait((task_id, images, options))
        return task_id

    def register_progress_callback(self, task_id: str, callback: Callable) -> None:
        """注册进度回调：callback(task_id, completed, total, result_or_none)"""
        self._progress_callbacks[task_id] = callback

    def get_status(self, task_id: str) -> dict:
        t = self.tasks.get(task_id)
        if not t:
            return {"error": "Task not found"}
        return {
            "task_id": task_id,
            "status": t["status"],
            "total": t["total"],
            "completed": t["completed"],
            "failed": t["failed"],
            "progress": t["completed"] / t["total"] if t["total"] > 0 else 0,
        }

    def get_result(self, task_id: str) -> Optional[List[dict]]:
        t = self.tasks.get(task_id)
        if t and t["status"] == "completed":
            return t["results"]
        return None

    def cancel(self, task_id: str) -> bool:
        t = self.tasks.get(task_id)
        if t and t["status"] in ("queued", "processing"):
            t["status"] = "cancelled"
            self._cancel_events[task_id].set()
            return True
        return False

    async def worker_loop(self, recognize_fn, recognize_sync_fn=None):
        """Worker 循环：从队列取任务，内部用 Semaphore + 线程池真正并行。"""
        while not self._shutdown:
            try:
                task_id, images, options = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = self.tasks[task_id]
            cancel_event = self._cancel_events.get(task_id)
            if task["status"] == "cancelled":
                self.queue.task_done()
                continue

            task["status"] = "processing"
            semaphore = asyncio.Semaphore(self.concurrency)
            results: List[dict] = [None] * len(images)

            async def process_one(idx: int, img: bytes):
                if cancel_event and cancel_event.is_set():
                    results[idx] = {"error": "cancelled"}
                    task["completed"] += 1
                    return

                async with semaphore:
                    if cancel_event and cancel_event.is_set():
                        results[idx] = {"error": "cancelled"}
                        task["completed"] += 1
                        return

                    try:
                        # 优先使用同步函数 + asyncio.to_thread 实现真正多线程并行
                        if recognize_sync_fn:
                            result = await asyncio.to_thread(recognize_sync_fn, img, options)
                        else:
                            result = await recognize_fn(img, options)
                        results[idx] = result
                    except Exception as e:
                        results[idx] = {"error": str(e)}
                        task["failed"] += 1
                    task["completed"] += 1

                    # 触发进度回调
                    cb = self._progress_callbacks.get(task_id)
                    if cb:
                        try:
                            await cb(task_id, task["completed"], task["total"], results[idx])
                        except Exception:
                            pass

            # 并发处理所有图片
            await asyncio.gather(*[process_one(i, img) for i, img in enumerate(images)])

            task["results"] = results
            if task["status"] != "cancelled":
                task["status"] = "completed"
            self.queue.task_done()

    def start(self, recognize_fn, recognize_sync_fn=None):
        for _ in range(self.max_workers):
            t = asyncio.create_task(self.worker_loop(recognize_fn, recognize_sync_fn))
            self._workers.append(t)

    async def stop(self):
        self._shutdown = True
        for w in self._workers:
            w.cancel()
        self._workers.clear()
