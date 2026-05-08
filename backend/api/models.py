"""Remote model repository operations."""
import hashlib
import os
from pathlib import Path

import aiohttp
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.post("/pull")
async def pull_model(url: str, name: str, sha256: str | None = None, admin_key: str | None = Header(None)):
    """Download a remote ONNX model into the local model cache."""
    if not url or not name:
        raise HTTPException(status_code=400, detail={"code": "MISSING_ARGUMENT", "message": "url 和 name 必填"})

    target_dir = Path(os.environ.get("VONISH_MODEL_DIR", "./models")) / Path(name).name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "model.onnx"
    temp_file = target_dir / "model.onnx.part"

    if target_file.exists():
        return {"status": "already_exists", "name": name, "path": str(target_file), "size": target_file.stat().st_size}

    downloaded = temp_file.stat().st_size if temp_file.exists() else 0
    headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status not in (200, 206):
                raise HTTPException(status_code=400, detail={"code": "DOWNLOAD_FAILED", "message": f"HTTP {resp.status}"})
            mode = "ab" if resp.status == 206 and downloaded else "wb"
            with open(temp_file, mode) as f:
                async for chunk in resp.content.iter_chunked(1024 * 256):
                    f.write(chunk)

    if sha256:
        file_hash = hashlib.sha256(temp_file.read_bytes()).hexdigest()
        if file_hash.lower() != sha256.lower():
            temp_file.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail={"code": "SHA256_MISMATCH", "message": "SHA256 mismatch"})

    try:
        import onnxruntime as ort

        session = ort.InferenceSession(str(temp_file))
        del session
    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail={"code": "MODEL_VALIDATION_FAILED", "message": str(e)})

    temp_file.replace(target_file)
    return {
        "status": "downloaded",
        "name": name,
        "path": str(target_file),
        "size": target_file.stat().st_size,
    }
