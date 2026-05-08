import os
from pathlib import Path

import click

from cli.core.client import VonishOCRClient
from cli.core.daemon import ensure_service, service_url


class RootGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        aliases = {"ls": "list"}
        return super().get_command(ctx, aliases.get(cmd_name, cmd_name))


@click.group(cls=RootGroup)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--api-key", envvar="VONISH_API_KEY", default=None)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="vonishocr")
def cli(ctx, host, port, api_key):
    """VonishOCR - local OCR infrastructure."""
    ctx.ensure_object(dict)
    base_url = f"http://{host}:{port}"
    ctx.obj["port"] = port
    ctx.obj["base_url"] = base_url
    ctx.obj["api_key"] = api_key
    ctx.obj["client"] = VonishOCRClient(base_url=base_url, api_key=api_key)


def _client(ctx, autostart=True):
    if autostart:
        ensure_service(ctx.obj["port"])
    return VonishOCRClient(base_url=service_url(ctx.obj["port"]), api_key=ctx.obj.get("api_key"))


from cli.commands.serve import serve, stop, status
from cli.commands.model import list_cmd, pull, rm, load
from cli.commands.ocr import ocr, batch
from cli.commands.queue import queue
from cli.commands.vault import vault
from cli.commands.config import config
from cli.commands.metrics import metrics, logs
from cli.commands.system import version, doctor, update, gui

cli.add_command(serve)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(list_cmd, "list")
cli.add_command(pull)
cli.add_command(rm)
cli.add_command(load)
cli.add_command(ocr)
cli.add_command(batch)
cli.add_command(queue)
cli.add_command(vault)
cli.add_command(config)
cli.add_command(metrics)
cli.add_command(logs)
cli.add_command(version)
cli.add_command(doctor)
cli.add_command(update)
cli.add_command(gui)


if __name__ == "__main__":
    cli()
