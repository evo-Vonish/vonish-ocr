"""SQLite vault database — async via asyncio.to_thread"""
import sqlite3
import asyncio
import uuid
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    color_tag TEXT DEFAULT '#8FF6D2',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    is_default INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evidences (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    filename TEXT NOT NULL,
    original_path TEXT,
    file_size INTEGER,
    mime_type TEXT,
    scene_type TEXT,
    model_tier TEXT,
    ocr_confidence REAL,
    process_time_ms INTEGER,
    raw_text TEXT,
    refined_text TEXT,
    diff_json TEXT,
    thumbnail_path TEXT,
    original_copy_path TEXT,
    preprocessed_path TEXT,
    export_format TEXT,
    status TEXT DEFAULT 'complete',
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS evidences_fts USING fts5(
    evidence_id,
    filename,
    raw_text,
    refined_text,
    content='evidences',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS evidences_ai AFTER INSERT ON evidences BEGIN
    INSERT INTO evidences_fts(evidence_id, filename, raw_text, refined_text)
    VALUES (new.id, new.filename, new.raw_text, new.refined_text);
END;

CREATE TRIGGER IF NOT EXISTS evidences_ad AFTER DELETE ON evidences BEGIN
    INSERT INTO evidences_fts(evidences_fts, rowid, evidence_id, filename, raw_text, refined_text)
    VALUES ('delete', old.rowid, old.id, old.filename, old.raw_text, old.refined_text);
END;

CREATE TRIGGER IF NOT EXISTS evidences_au AFTER UPDATE ON evidences BEGIN
    INSERT INTO evidences_fts(evidences_fts, rowid, evidence_id, filename, raw_text, refined_text)
    VALUES ('delete', old.rowid, old.id, old.filename, old.raw_text, old.refined_text);
    INSERT INTO evidences_fts(evidence_id, filename, raw_text, refined_text)
    VALUES (new.id, new.filename, new.raw_text, new.refined_text);
END;
"""


def _vault_base_dir():
    appdata = Path.home() / "AppData" / "Local" / "VonishOCR"
    return appdata / "vault"


def _get_db_path():
    d = _vault_base_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "vault.db"


def _connect():
    db_path = str(_get_db_path())
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


class VaultDB:
    def __init__(self):
        self._db_path = str(_get_db_path())

    async def _execute(self, sql, params=(), fetch=False):
        def _run():
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute(sql, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()
        return await asyncio.to_thread(_run)

    # --- Sessions ---
    async def create_session(self, name, description=None, color_tag=None):
        sid = str(uuid.uuid4())
        now = time.time()
        await self._execute(
            "INSERT INTO sessions(id,name,description,color_tag,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (sid, name, description, color_tag or "#8FF6D2", now, now),
        )
        return {"id": sid, "name": name}

    async def list_sessions(self):
        rows = await self._execute(
            "SELECT id, name, color_tag, created_at, updated_at, "
            "(SELECT COUNT(*) FROM evidences WHERE session_id=sessions.id) as cnt,"
            "is_default "
            "FROM sessions ORDER BY is_default ASC, updated_at DESC",
            fetch=True,
        )
        return [
            {"id": r[0], "name": r[1], "color_tag": r[2], "created_at": r[3],
             "updated_at": r[4], "count": r[5], "is_default": bool(r[6])}
            for r in rows
        ]

    # --- Evidences ---
    async def insert_evidence(self, data: dict):
        eid = data.get("id", str(uuid.uuid4()))
        now = time.time()
        await self._execute(
            """INSERT INTO evidences(id,session_id,filename,original_path,file_size,mime_type,
            scene_type,model_tier,ocr_confidence,process_time_ms,
            raw_text,refined_text,diff_json,
            thumbnail_path,original_copy_path,preprocessed_path,export_format,
            status,error_message,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid, data.get("session_id"), data.get("filename"),
                data.get("original_path"), data.get("file_size"), data.get("mime_type"),
                data.get("scene_type"), data.get("model_tier"), data.get("ocr_confidence"),
                data.get("process_time_ms"), data.get("raw_text"), data.get("refined_text"),
                data.get("diff_json"), data.get("thumbnail_path"), data.get("original_copy_path"),
                data.get("preprocessed_path"), data.get("export_format"),
                data.get("status", "complete"), data.get("error_message"), now, now,
            ),
        )
        return eid

    async def list_evidences(self, *, session_id=None, scene_type=None,
                               model_tier=None, status=None, search=None,
                               limit=50, offset=0, date_from=None, date_to=None):
        where = ["1=1"]
        params = []
        if session_id:
            where.append("session_id=?")
            params.append(session_id)
        elif session_id == "":  # unfiled
            where.append("session_id IS NULL")
        if scene_type:
            where.append("scene_type=?")
            params.append(scene_type)
        if model_tier:
            where.append("model_tier=?")
            params.append(model_tier)
        if status:
            where.append("status=?")
            params.append(status)
        if date_from:
            where.append("created_at>=?")
            params.append(date_from)
        if date_to:
            where.append("created_at<=?")
            params.append(date_to)

        if search:
            where.append(
                "rowid IN (SELECT rowid FROM evidences_fts WHERE evidences_fts MATCH ?)"
            )
            params.append(f'"{search}"')

        count_sql = f"SELECT COUNT(*) FROM evidences WHERE {' AND '.join(where)}"
        data_sql = f"SELECT id,session_id,filename,file_size,mime_type,scene_type,model_tier,ocr_confidence,process_time_ms,raw_text,refined_text,diff_json,thumbnail_path,original_copy_path,status,error_message,created_at,updated_at FROM evidences WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT ? OFFSET ?"

        total_row = await self._execute(count_sql, params, fetch=True)
        total = total_row[0][0] if total_row else 0

        rows = await self._execute(data_sql, params + [limit, offset], fetch=True)
        items = []
        for r in rows:
            items.append({
                "id": r[0], "session_id": r[1], "filename": r[2],
                "file_size": r[3], "mime_type": r[4], "scene_type": r[5],
                "model_tier": r[6], "ocr_confidence": r[7], "process_time_ms": r[8],
                "raw_text": r[9], "refined_text": r[10], "diff_json": r[11],
                "thumbnail_path": r[12], "original_copy_path": r[13],
                "status": r[14], "error_message": r[15],
                "created_at": r[16], "updated_at": r[17],
            })
        return {"total": total, "items": items}

    async def get_evidence(self, evidence_id):
        rows = await self._execute(
            "SELECT id,session_id,filename,file_size,mime_type,scene_type,model_tier,ocr_confidence,process_time_ms,raw_text,refined_text,diff_json,thumbnail_path,original_copy_path,preprocessed_path,status,error_message,created_at,updated_at FROM evidences WHERE id=?",
            (evidence_id,), fetch=True,
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "id": r[0], "session_id": r[1], "filename": r[2],
            "file_size": r[3], "mime_type": r[4], "scene_type": r[5],
            "model_tier": r[6], "ocr_confidence": r[7], "process_time_ms": r[8],
            "raw_text": r[9], "refined_text": r[10], "diff_json": r[11],
            "thumbnail_path": r[12], "original_copy_path": r[13],
            "preprocessed_path": r[14], "status": r[15],
            "error_message": r[16], "created_at": r[17], "updated_at": r[18],
        }

    async def delete_evidence(self, evidence_id):
        await self._execute("DELETE FROM evidences WHERE id=?", (evidence_id,))

    async def move_to_session(self, evidence_ids, session_id):
        now = time.time()
        placeholders = ",".join("?" * len(evidence_ids))
        await self._execute(
            f"UPDATE evidences SET session_id=?, updated_at=? WHERE id IN ({placeholders})",
            [session_id, now] + evidence_ids,
        )

    async def update_status(self, evidence_id, status, error_message=None):
        await self._execute(
            "UPDATE evidences SET status=?, error_message=?, updated_at=? WHERE id=?",
            (status, error_message, time.time(), evidence_id),
        )
