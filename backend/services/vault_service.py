"""Vault service — coordinates DB, thumbnail, and file operations"""
import asyncio
import json
import logging
import uuid
from pathlib import Path

from db.vault_db import VaultDB
from services.thumbnail import generate_thumbnail, copy_original, copy_preprocessed, delete_vault_files, resolve_vault_url

logger = logging.getLogger(__name__)


class VaultService:
    def __init__(self):
        self.db = VaultDB()

    # --- Sessions ---
    async def create_session(self, name: str, description: str = None, color_tag: str = None):
        return await self.db.create_session(name, description, color_tag)

    async def list_sessions(self):
        sessions = await self.db.list_sessions()
        has_all = any(s["is_default"] for s in sessions)
        has_unfiled = any(s["name"] == "未分组" for s in sessions)
        if not has_all:
            await self.db.create_session("全部证据", "系统默认", is_default=True)
        if not has_unfiled:
            await self.db.create_session("未分组", "尚未归档的证据")
        return await self.db.list_sessions()

    # --- Save evidence after OCR complete ---
    async def save_ocr_result(self, result: dict, original_bytes: bytes,
                                preprocessed_bytes: bytes = None):
        """Called after OCR completes. Saves evidence to vault."""
        eid = str(uuid.uuid4())
        ext = result.get("ext", "png")

        th_path = await generate_thumbnail(original_bytes, eid)
        orig_path = await copy_original(original_bytes, eid, ext)
        prep_path = None
        if preprocessed_bytes:
            prep_path = await copy_preprocessed(preprocessed_bytes, eid)

        diff_json = json.dumps(result.get("ai", {}).get("diff", []), ensure_ascii=False) if result.get("ai") else None

        data = {
            "id": eid,
            "session_id": result.get("session_id"),
            "filename": result.get("filename", "untitled"),
            "original_path": result.get("original_path"),
            "file_size": result.get("file_size"),
            "mime_type": result.get("mime_type"),
            "scene_type": result.get("scene"),
            "model_tier": result.get("model_tier"),
            "ocr_confidence": result.get("confidence"),
            "process_time_ms": result.get("process_time_ms"),
            "raw_text": result.get("text"),
            "refined_text": result.get("ai", {}).get("polished") if result.get("ai") else None,
            "diff_json": diff_json,
            "thumbnail_path": th_path,
            "original_copy_path": orig_path,
            "preprocessed_path": prep_path,
            "status": "complete" if not result.get("error") else "failed",
            "error_message": result.get("error", {}).get("message") if result.get("error") else None,
        }
        await self.db.insert_evidence(data)
        return eid

    # --- Queries ---
    async def list_evidences(self, **kwargs):
        return await self.db.list_evidences(**kwargs)

    async def get_evidence(self, evidence_id: str):
        evidence = await self.db.get_evidence(evidence_id)
        if evidence:
            evidence["thumbnail_url"] = resolve_vault_url(evidence.get("thumbnail_path"))
            evidence["original_url"] = resolve_vault_url(evidence.get("original_copy_path"))
        return evidence

    async def delete_evidence(self, evidence_id: str):
        evidence = await self.db.get_evidence(evidence_id)
        if evidence:
            await delete_vault_files(evidence)
        await self.db.delete_evidence(evidence_id)

    async def batch_delete(self, evidence_ids: list[str]):
        for eid in evidence_ids:
            await self.delete_evidence(eid)

    async def move_to_session(self, evidence_ids: list[str], session_id: str = None):
        await self.db.move_to_session(evidence_ids, session_id)

    async def update_status(self, evidence_id: str, status: str, error_message: str = None):
        await self.db.update_status(evidence_id, status, error_message)

    async def batch_export(self, evidence_ids: list[str], fmt: str):
        results = []
        for eid in evidence_ids:
            ev = await self.db.get_evidence(eid)
            if ev:
                results.append({"id": eid, "filename": ev["filename"], "format": fmt})
        return results
