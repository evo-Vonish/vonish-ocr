import time
import json
from pathlib import Path

import click

from cli.core.context import get_client
from cli.core.paths import log_file


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Reserved for future JSON metrics.")
@click.pass_context
def metrics(ctx, as_json):
    """Print Prometheus metrics."""
    text = get_client(ctx).metrics()
    if not as_json:
        click.echo(text)
        return
    rows = []
    for line in str(text).splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition(" ")
        rows.append({"metric": name, "value": value})
    click.echo(json.dumps(rows, ensure_ascii=False, indent=2))


@click.command()
@click.option("--follow", is_flag=True)
@click.option("--since", default=None, help="Reserved; currently tails raw log.")
def logs(follow, since):
    """Show service logs."""
    path = log_file().parent / "backend.log"
    if not path.exists():
        return
    if not follow:
        click.echo(path.read_text(encoding="utf-8", errors="ignore"))
        return
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                click.echo(line, nl=False)
            else:
                time.sleep(0.5)
