import platform
import subprocess

import click

from cli.core.context import get_client
from cli.core.formatter import print_json


@click.command()
def version():
    """Show version information."""
    click.echo("VonishOCR 0.1.0")


@click.command()
@click.pass_context
def doctor(ctx):
    """Run diagnostics."""
    client = get_client(ctx)
    data = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "health": client.health(),
        "ready": client.get("/v1/system/ready"),
        "models": client.local_models(),
    }
    print_json(data)


@click.command()
def update():
    """Check for updates."""
    click.echo("Update check is not wired yet.")


@click.command()
def gui():
    """Launch desktop GUI."""
    subprocess.call(["npm", "run", "tauri-dev"])
