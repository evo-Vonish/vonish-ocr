import shutil
from pathlib import Path

import click

from cli.core.context import get_client
from cli.core.daemon import project_root
from cli.core.formatter import print_json, print_table


@click.command("list")
@click.option("--remote", is_flag=True, help="List remote manifest models instead of local models.")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def list_cmd(ctx, remote, as_json):
    """List models."""
    client = get_client(ctx)
    data = client.models() if remote else client.local_models()
    rows = data.get("available" if remote else "models", [])
    if as_json:
        print_json(rows)
    else:
        print_table(rows, [("id", "ID"), ("tier", "TIER"), ("size_mb", "SIZE_MB"), ("version", "VERSION"), ("name", "NAME")])


@click.command()
@click.argument("name")
@click.option("--url", default=None, help="Custom model URL.")
@click.option("--sha256", default=None, help="Expected SHA256.")
@click.pass_context
def pull(ctx, name, url, sha256):
    """Download model."""
    result = get_client(ctx).pull_model(name, url=url, sha256=sha256)
    print_json(result)


@click.command()
@click.argument("name")
def rm(name):
    """Remove local model directory."""
    path = project_root() / "models" / name
    resolved = path.resolve()
    models_root = (project_root() / "models").resolve()
    if models_root not in [resolved, *resolved.parents]:
        raise click.ClickException(f"refusing to remove outside model directory: {resolved}")
    if not path.exists():
        raise click.ClickException(f"model not found: {name}")
    shutil.rmtree(path)
    click.echo(f"removed {path}")


@click.command()
@click.argument("name")
@click.pass_context
def load(ctx, name):
    """Hot-load model by switching console model."""
    aliases = {"rapidocr-mobile": "rapid", "rapidocr-mobile-cn": "rapid", "cnocr-standard": "cnocr"}
    model_id = aliases.get(name, name)
    result = get_client(ctx).post("/v1/console/model/switch", json_body={"model_id": model_id})
    print_json(result)
