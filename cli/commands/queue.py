import os
import time

import click

from cli.core.context import get_client
from cli.core.formatter import print_json, print_table
from cli.core.paths import log_file


@click.group()
def queue():
    """Queue operations."""


@queue.command("ls")
@click.option("--watch", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def ls(ctx, watch, as_json):
    client = get_client(ctx)
    while True:
        data = client.tasks()
        rows = data.get("tasks", [])
        if as_json:
            print_json(data)
        else:
            if watch:
                click.clear()
            print_table(rows, [("id", "ID"), ("filename", "FILE"), ("model_tier", "MODEL"), ("status", "STATUS"), ("elapsed_ms", "MS")])
        if not watch:
            return
        time.sleep(1)


@queue.command()
@click.argument("task_id")
@click.pass_context
def cancel(ctx, task_id):
    print_json(get_client(ctx).cancel_task(task_id))


@queue.command()
@click.argument("task_id")
@click.pass_context
def logs(ctx, task_id):
    # Per-task logs are not yet stored separately; show matching backend log lines.
    path = log_file().parent / "backend.log"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if task_id in line:
            click.echo(line)


@queue.command()
@click.pass_context
def clear(ctx):
    data = get_client(ctx).tasks(limit=500)
    for task in data.get("tasks", []):
        if task.get("status") in ("queued", "processing"):
            get_client(ctx).cancel_task(task["id"])
    click.echo("queued/processing tasks cancelled")
