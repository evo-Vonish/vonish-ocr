"""Vault file helpers.

中文说明：
案卷库里的缩略图、原图和预处理图都保存在用户本机的 vault 目录。
前端不能直接拼 Vite 地址读取这些文件，因此这里统一提供：
1. 生成缩略图和本地副本；
2. 相对路径到安全绝对路径的解析；
3. 相对路径到后端 HTTP 文件 URL 的转换。
"""
import asyncio
import time
from pathlib import Path
from urllib.parse import quote

from PIL import Image

THUMB_SIZE = (160, 120)
THUMB_QUALITY = 72


def _vault_base_dir() -> Path:
    appdata = Path.home() / "AppData" / "Local" / "VonishOCR"
    return appdata / "vault"


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)


async def generate_thumbnail(source_bytes: bytes, evidence_id: str) -> str:
    """Generate a 160x120 JPEG thumbnail and return its vault-relative path."""
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
    """Copy original file into vault/originals and return its relative path."""
    date_str = time.strftime("%Y/%m/%d")
    orig_dir = _vault_base_dir() / "originals" / date_str
    orig_dir.mkdir(parents=True, exist_ok=True)
    orig_path = orig_dir / f"{evidence_id}.{ext}"

    def _copy():
        orig_path.write_bytes(source_bytes)

    await _to_thread(_copy)
    return f"originals/{date_str}/{evidence_id}.{ext}"


async def copy_preprocessed(image_bytes: bytes, evidence_id: str) -> str:
    """Copy preprocessed image into vault/preprocessed and return its relative path."""
    date_str = time.strftime("%Y/%m/%d")
    prep_dir = _vault_base_dir() / "preprocessed" / date_str
    prep_dir.mkdir(parents=True, exist_ok=True)
    prep_path = prep_dir / f"{evidence_id}.png"

    def _copy():
        prep_path.write_bytes(image_bytes)

    await _to_thread(_copy)
    return f"preprocessed/{date_str}/{evidence_id}.png"


async def delete_vault_files(evidence: dict):
    """Delete all local files associated with an evidence record."""
    for key in ("thumbnail_path", "original_copy_path", "preprocessed_path"):
        rel = evidence.get(key)
        if not rel:
            continue
        try:
            p = resolve_vault_path(rel)
        except ValueError:
            continue
        if p.exists():
            await _to_thread(p.unlink)


def resolve_vault_path(relative_path: str) -> Path:
    """Resolve a vault-relative path and reject path traversal."""
    if not relative_path:
        raise ValueError("empty vault path")
    vault = _vault_base_dir().resolve()
    target = (vault / str(relative_path).replace("\\", "/")).resolve()
    if target != vault and vault not in target.parents:
        raise ValueError("path is outside vault")
    return target


def resolve_vault_url(relative_path: str | None) -> str | None:
    """Convert a vault-relative path to a backend HTTP URL path.

    这里只返回相对 HTTP 路径，前端会补上真实 sidecar 端口。
    """
    if not relative_path:
        return None
    try:
        p = resolve_vault_path(relative_path)
    except ValueError:
        return None
    if not p.exists():
        return None
    normalized = str(relative_path).replace("\\", "/").lstrip("/")
    return f"/vault/file/{quote(normalized)}"
