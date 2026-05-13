from pathlib import Path
from typing import Any

from fastapi import HTTPException


def normalize_ocr_language(value: str | None) -> str | None:
    """Normalize UI/API language values to a langpack spec string.

    中文说明：
    前端可能传入 ch、en、pp-ocrv5:en 或 auto。后端统一转成
    pp-ocrv5:<language>，让模型加载链路只处理一种格式。
    """
    if not value:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() == "auto":
        return None
    if ":" in raw:
        return raw
    return f"pp-ocrv5:{raw}"


def selected_ocr_language(cfg: Any, options: dict | None = None, payload: dict | None = None) -> str | None:
    """Read OCR language from request options first, then persisted config."""
    options = options or {}
    payload = payload or {}
    return normalize_ocr_language(
        payload.get("ocr_language")
        or payload.get("language")
        or options.get("ocr_language")
        or options.get("language")
        or getattr(cfg, "ocr_language", None)
    )


def lang_engine_id(model_id: str, language_spec: str) -> str:
    """Build a stable runtime cache key for one model tier + language pack."""
    return f"{model_id}::lang::{language_spec}"


def resolve_langpack_model_dir(language_spec: str) -> Path:
    """Resolve an installed language pack to the real ONNX model directory.

    中文说明：
    如果用户选择了某个 OCR 语言，识别必须从 models/langpacks 对应目录
    加载模型。没有安装或文件不完整时直接报错，避免继续偷偷使用默认中文模型。
    """
    try:
        from cli.core.langpacks import LangPackError, LangPackManager, parse_lang_spec

        return LangPackManager().installed_model_dir(parse_lang_spec(language_spec))
    except Exception as exc:
        # LangPackError lives in cli.core.langpacks; keep this helper import-light and
        # convert all known resolution failures to a user-facing API error.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LANGPACK_NOT_READY",
                "message": f"OCR 语言包未安装或不可用: {language_spec}",
                "hint": "请在语言包库安装该语言包，或把 OCR 语言切回已安装语言。",
                "cause": str(exc),
            },
        ) from exc
