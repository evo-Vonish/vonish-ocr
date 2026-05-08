from .client import VonishOCRClient
from .daemon import ensure_service, service_url


def get_client(ctx, autostart=True):
    if autostart:
        ensure_service(ctx.obj.get("port", 8000))
    return VonishOCRClient(
        base_url=service_url(ctx.obj.get("port", 8000)),
        api_key=ctx.obj.get("api_key"),
    )
