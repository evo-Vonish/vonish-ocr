"""预处理临时任务存储。

这个模块只负责管理预处理图片和元数据，不参与 OCR 识别逻辑。
预处理结果会写入 temp/preprocess/{job_id}/，避免把大图塞进前端持久化。
"""

import json
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


JOB_TTL_SECONDS = 24 * 60 * 60


@dataclass
class PreprocessJob:
    job_id: str
    original_path: str
    processed_path: str
    scene: str
    frontend_scene: str
    scene_confidence: float
    steps_applied: list
    quality_score: float
    quality_metrics: dict
    elapsed_ms: int
    fallback: bool
    strategy: str
    created_at: float
    cleanable: bool = False


class PreprocessJobStore:
    """文件系统型 job store。

    当前应用是本地单进程 sidecar，不需要数据库；用 metadata.json 足够可靠。
    """

    def __init__(self, root: Optional[Path] = None):
        project_root = Path(__file__).resolve().parents[2]
        self.root = root or (project_root / "temp" / "preprocess")
        self.root.mkdir(parents=True, exist_ok=True)

    def cleanup_old(self) -> None:
        now = time.time()
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            meta = child / "metadata.json"
            created_at = child.stat().st_ctime
            if meta.exists():
                try:
                    created_at = json.loads(meta.read_text(encoding="utf-8")).get("created_at", created_at)
                except Exception:
                    pass
            if now - float(created_at) > JOB_TTL_SECONDS:
                shutil.rmtree(child, ignore_errors=True)

    def create_dir(self) -> tuple[str, Path]:
        self.cleanup_old()
        job_id = f"prep_{uuid.uuid4().hex[:12]}"
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_id, job_dir

    def save(self, job: PreprocessJob) -> PreprocessJob:
        job_dir = self.root / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "metadata.json").write_text(json.dumps(asdict(job), ensure_ascii=False, indent=2), encoding="utf-8")
        return job

    def get(self, job_id: str) -> Optional[PreprocessJob]:
        if not job_id.startswith("prep_"):
            return None
        meta = self.root / job_id / "metadata.json"
        if not meta.exists():
            return None
        try:
            return PreprocessJob(**json.loads(meta.read_text(encoding="utf-8")))
        except Exception:
            return None

    def get_image_path(self, job_id: str, kind: str) -> Optional[Path]:
        job = self.get(job_id)
        if not job:
            return None
        path = Path(job.original_path if kind == "original" else job.processed_path).resolve()
        try:
            path.relative_to((self.root / job_id).resolve())
        except ValueError:
            return None
        return path if path.exists() else None

    def mark_cleanable(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        job.cleanable = True
        self.save(job)
