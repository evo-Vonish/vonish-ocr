import json
import os
import subprocess
from pathlib import Path

import click

from cli.core.context import get_client
from cli.core.formatter import print_json


@click.group()
def config():
    """Configuration operations."""


@config.command("get")
@click.argument("key", required=False)
@click.pass_context
def get_cmd(ctx, key):
    data = get_client(ctx).config()
    if key:
        value = data
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        print_json(value)
    else:
        print_json(data)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def set_cmd(ctx, key, value):
    client = get_client(ctx)
    data = client.config()
    target = data
    parts = key.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = _coerce(value)
    print_json(client.save_config(data))


@config.command()
@click.pass_context
def reload(ctx):
    print_json(get_client(ctx).reload_config())


@config.command()
def edit():
    path = Path(os.environ.get("VONISH_CONFIG", "config.json"))
    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "vi")
    subprocess.call([editor, str(path)])


def _coerce(value):
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
