"""OCR language pack management API.

这些端点复用 CLI 里的语言包 manifest / SQLite 安装库，供桌面 GUI 调用。
独立 router 可以避免把功能埋在大 routes.py 里，后续也便于迁移到服务化 API。
"""
from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/v1/langpacks", tags=["langpacks"])


def _manager():
    """延迟加载，避免后端启动阶段和 CLI 模块形成导入环。"""
    from cli.core.langpacks import LangPackManager

    return LangPackManager()


def _bad_request(exc: Exception) -> HTTPException:
    message = str(exc)
    if "all mirrors failed" in message:
        message = "语言包远程镜像不可用或当前网络无法访问，请稍后重试，或选择本地可用的语言包。"
    elif "no download URL" in message:
        message = "该语言包暂未配置可用下载源，不能远程安装。"
    return HTTPException(status_code=400, detail={"code": "LANGPACK_ERROR", "message": message, "cause": str(exc)})


@router.get("")
async def list_langpacks(installed: bool = False):
    """列出可用 / 已安装语言包。"""
    try:
        return {"items": _manager().list(include_remote=not installed)}
    except Exception as e:
        raise _bad_request(e)


@router.get("/{language}")
async def show_langpack(language: str):
    """读取单个语言包 manifest 和本地安装状态。"""
    try:
        from cli.core.langpacks import parse_lang_spec

        return _manager().show(parse_lang_spec(language))
    except Exception as e:
        raise _bad_request(e)


@router.post("/{language}/pull")
async def pull_langpack(language: str, payload: dict = Body(default={})):
    """安装语言包；默认可复用本地模型，远程下载需要 yes=true。"""
    try:
        from cli.core.langpacks import parse_lang_spec

        return _manager().install(
            parse_lang_spec(language),
            mirror=payload.get("mirror"),
            yes=bool(payload.get("yes")),
            offline=bool(payload.get("offline")),
        )
    except Exception as e:
        raise _bad_request(e)


@router.post("/verify")
async def verify_langpacks(payload: dict = Body(default={})):
    """校验一个或全部已安装语言包的文件 SHA256。"""
    try:
        from cli.core.langpacks import parse_lang_spec

        language = payload.get("language")
        spec = parse_lang_spec(language) if language else None
        return {"result": _manager().verify(spec, repair=bool(payload.get("repair")))}
    except Exception as e:
        raise _bad_request(e)


@router.delete("/{language}")
async def remove_langpack(language: str, keep_files: bool = False):
    """卸载语言包，可选择保留模型文件。"""
    try:
        from cli.core.langpacks import parse_lang_spec

        return _manager().remove(parse_lang_spec(language), delete_files=not keep_files)
    except Exception as e:
        raise _bad_request(e)
