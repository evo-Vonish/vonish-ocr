import asyncio
import time
import uuid
from typing import Dict, List, Optional


class LocalQueue:
    def __init__(self, max_workers: int = 1):
        self.queue = asyncio.Queue()
        self.tasks: Dict[str, dict] = {}
        self.max_workers = max_workers
        self._workers: List[asyncio.Task] = []
        self._shutdown = False

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
        self.queue.put_nowait((task_id, images, options))
        return task_id

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
        if t and t["status"] == "queued":
            t["status"] = "cancelled"
            return True
        return False

    async def worker_loop(self, recognize_fn):
        while not self._shutdown:
            try:
                task_id, images, options = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = self.tasks[task_id]
            if task["status"] == "cancelled":
                self.queue.task_done()
                continue

            task["status"] = "processing"
            results = []
            for img in images:
                if self._shutdown:
                    break
                try:
                    result = await recognize_fn(img, options)
                    results.append(result)
                    task["completed"] += 1
                except Exception as e:
                    results.append({"error": str(e)})
                    task["failed"] += 1
                    task["completed"] += 1

            task["results"] = results
            if task["status"] != "cancelled":
                task["status"] = "completed"
            self.queue.task_done()

    def start(self, recognize_fn):
        for _ in range(self.max_workers):
            t = asyncio.create_task(self.worker_loop(recognize_fn))
            self._workers.append(t)

    async def stop(self):
        self._shutdown = True
        for w in self._workers:
            w.cancel()
        self._workers.clear()
