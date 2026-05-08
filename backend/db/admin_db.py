"""Admin SQLite storage for API keys and service queue tasks."""
import asyncio
import hashlib
import sqlite3
import time
import uuid
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash TEXT PRIMARY KEY,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    tenant_id TEXT DEFAULT 'default',
    rate_limit INTEGER DEFAULT 60,
    usage_count INTEGER DEFAULT 0,
    last_used REAL,
    created_at REAL NOT NULL,
    revoked_at REAL
);

CREATE TABLE IF NOT EXISTS queue_tasks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'default',
    filename TEXT NOT NULL,
    file_path TEXT,
    file_size INTEGER DEFAULT 0,
    model_tier TEXT,
    status TEXT DEFAULT 'queued',
    priority INTEGER DEFAULT 0,
    queue_pos INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    result_json TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_queue_tasks_status_created
ON queue_tasks(status, created_at);

CREATE INDEX IF NOT EXISTS idx_queue_tasks_tenant_created
ON queue_tasks(tenant_id, created_at);
"""


def admin_base_dir() -> Path:
    base = Path.home() / "AppData" / "Local" / "VonishOCR" / "admin"
    base.mkdir(parents=True, exist_ok=True)
    return base


def admin_db_path() -> Path:
    return admin_base_dir() / "admin.db"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(admin_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


class AdminDB:
    """Small async wrapper around sqlite3.

    sqlite3 is synchronous, so every DB operation is pushed to a worker thread.
    """

    async def execute(self, sql: str, params=(), *, fetch: bool = False):
        def run():
            conn = _connect()
            try:
                cur = conn.execute(sql, params)
                if fetch:
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

        return await asyncio.to_thread(run)

    async def create_api_key(self, *, name: str, raw_key: str, tenant_id: str = "default", rate_limit: int = 60):
        now = time.time()
        prefix = raw_key[:12]
        await self.execute(
            """
            INSERT INTO api_keys(key_hash,key_prefix,name,tenant_id,rate_limit,usage_count,last_used,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (hash_api_key(raw_key), prefix, name, tenant_id, rate_limit, 0, None, now),
        )
        return {
            "key": raw_key,
            "key_prefix": prefix,
            "name": name,
            "tenant_id": tenant_id,
            "rate_limit": rate_limit,
            "created_at": now,
        }

    async def list_api_keys(self):
        return await self.execute(
            """
            SELECT key_prefix,name,tenant_id,rate_limit,usage_count,last_used,created_at,revoked_at
            FROM api_keys
            ORDER BY created_at DESC
            """,
            fetch=True,
        )

    async def revoke_api_key(self, key_or_prefix: str) -> bool:
        now = time.time()
        if len(key_or_prefix) > 24:
            rows = await self.execute(
                "UPDATE api_keys SET revoked_at=? WHERE key_hash=? AND revoked_at IS NULL",
                (now, hash_api_key(key_or_prefix)),
            )
        else:
            rows = await self.execute(
                "UPDATE api_keys SET revoked_at=? WHERE key_prefix=? AND revoked_at IS NULL",
                (now, key_or_prefix),
            )
        return rows is not None

    async def verify_api_key(self, raw_key: str):
        if not raw_key:
            return None
        rows = await self.execute(
            """
            SELECT key_hash,key_prefix,name,tenant_id,rate_limit,usage_count,last_used,created_at
            FROM api_keys
            WHERE key_hash=? AND revoked_at IS NULL
            """,
            (hash_api_key(raw_key),),
            fetch=True,
        )
        if not rows:
            return None
        row = rows[0]
        await self.execute(
            "UPDATE api_keys SET usage_count=usage_count+1,last_used=? WHERE key_hash=?",
            (time.time(), row["key_hash"]),
        )
        return row

    async def insert_queue_task(self, data: dict):
        task_id = data.get("id") or str(uuid.uuid4())
        now = time.time()
        await self.execute(
            """
            INSERT INTO queue_tasks(id,tenant_id,filename,file_path,file_size,model_tier,status,priority,queue_pos,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                data.get("tenant_id", "default"),
                data["filename"],
                data.get("file_path"),
                int(data.get("file_size") or 0),
                data.get("model_tier", "auto"),
                data.get("status", "queued"),
                int(data.get("priority") or 0),
                int(data.get("queue_pos") or 0),
                now,
            ),
        )
        return task_id

    async def update_task(self, task_id: str, **fields):
        if not fields:
            return
        allowed = {
            "status",
            "queue_pos",
            "started_at",
            "completed_at",
            "result_json",
            "error",
        }
        items = [(key, value) for key, value in fields.items() if key in allowed]
        if not items:
            return
        sql = "UPDATE queue_tasks SET " + ",".join(f"{key}=?" for key, _ in items) + " WHERE id=?"
        await self.execute(sql, [value for _, value in items] + [task_id])

    async def get_task(self, task_id: str):
        rows = await self.execute("SELECT * FROM queue_tasks WHERE id=?", (task_id,), fetch=True)
        return rows[0] if rows else None

    async def list_tasks(self, *, tenant_id: str | None = None, limit: int = 100):
        params = []
        where = "1=1"
        if tenant_id and tenant_id != "default":
            where += " AND tenant_id=?"
            params.append(tenant_id)
        rows = await self.execute(
            f"SELECT * FROM queue_tasks WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
            fetch=True,
        )
        return rows

    async def task_stats(self):
        rows = await self.execute(
            "SELECT status,COUNT(*) AS count FROM queue_tasks GROUP BY status",
            fetch=True,
        )
        return {row["status"]: row["count"] for row in rows}
