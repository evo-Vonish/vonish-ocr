"""Thumbnail generation — 160x120 JPEG via Pillow"""
import asyncio
import time
from pathlib import Path
from PIL import Image

THUMB_SIZE = (160, 120)
THUMB_QUALITY = 72


def _vault_base_dir():
    appdata = Path.home() / "AppData" / "Local" / "VonishOCR"
    return appdata / "vault"


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)


async def generate_thumbnail(source_bytes: bytes, evidence_id: str) -> str:
    """Generate 160x120 JPEG thumbnail, return relative path from vault root"""
    date_str = time.strftime("%Y/%m/%d")
    thumb_dir = _vault_base_dir() / "thumbnails" / date_str
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / f"{evidence_id}.jpg"

    def _generate():
        img = Image.open(__import__("io").BytesIO(source_bytes))
        img = img.convert("RGB")
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumb_path, "JPEG", quality=THUMB_QUALITY)

    await _to_thread(_generate)
    return f"thumbnails/{date_str}/{evidence_id}.jpg"


async def copy_original(source_bytes: bytes, evidence_id: str, ext: str = "png") -> str:
    """Copy original file into vault/originals/, return relative path"""
    date_str = time.strftime("%Y/%m/%d")
    orig_dir = _vault_base_dir() / "originals" / date_str
    orig_dir.mkdir(parents=True, exist_ok=True)
    orig_path = orig_dir / f"{evidence_id}.{ext}"

    def _copy():
        orig_path.write_bytes(source_bytes)

    await _to_thread(_copy)
    return f"originals/{date_str}/{evidence_id}.{ext}"


async def copy_preprocessed(image_bytes: bytes, evidence_id: str) -> str:
    """Copy preprocessed image into vault/preprocessed/, return relative path"""
    date_str = time.strftime("%Y/%m/%d")
    prep_dir = _vault_base_dir() / "preprocessed" / date_str
    prep_dir.mkdir(parents=True, exist_ok=True)
    prep_path = prep_dir / f"{evidence_id}.png"

    def _copy():
        prep_path.write_bytes(image_bytes)

    await _to_thread(_copy)
    return f"preprocessed/{date_str}/{evidence_id}.png"


async def delete_vault_files(evidence: dict):
    """Delete all files associated with an evidence record"""
    vault = _vault_base_dir()
    for key in ("thumbnail_path", "original_copy_path", "preprocessed_path"):
        rel = evidence.get(key)
        if rel:
            p = vault / rel
            if p.exists():
                await _to_thread(p.unlink)


def resolve_vault_url(relative_path: str | None) -> str | None:
    """Convert relative vault path to file:// URL for frontend access"""
    if not relative_path:
        return None
    p = _vault_base_dir() / relative_path
    return p.as_uri() if p.exists() else None
