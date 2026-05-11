import time
from pathlib import Path

import click

from cli.core.context import get_client
from cli.core.formatter import as_text_result

IMAGE_PATTERNS = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.tif", "*.tiff", "*.pdf")


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--model", "-m", default="auto")
@click.option("--output", "-o", type=click.Path())
@click.option("--format", "fmt", type=click.Choice(["txt", "md", "json"]), default="md")
@click.option("--refine", is_flag=True, help="Reserved for AI refine queue option.")
@click.option("--priority", "-p", default=0, type=int)
@click.option("--timeout", default=600, type=int, help="Maximum seconds to wait for completion.")
@click.pass_context
def ocr(ctx, file, model, output, fmt, refine, priority, timeout):
    """Recognize one file."""
    client = get_client(ctx)
    submitted = client.submit_ocr(file, model_tier=model, priority=priority)
    task_id = submitted["task_id"]
    click.echo(f"Task submitted: {task_id}", err=True)
    deadline = time.time() + max(1, timeout)
    while True:
        if time.time() > deadline:
            raise click.ClickException(f"task timed out after {timeout}s: {task_id}")
        task = client.task(task_id)["task"]
        status = task.get("status")
        if status == "done":
            text = as_text_result(task.get("result") or {}, fmt)
            if output:
                Path(output).write_text(text, encoding="utf-8")
                click.echo(f"Result saved to {output}", err=True)
            else:
                click.echo(text)
            return
        if status in ("failed", "cancelled"):
            raise click.ClickException(task.get("error") or status)
        time.sleep(0.5)


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("--model", "-m", default="auto")
@click.option("--output", "-o", type=click.Path())
@click.option("--format", "fmt", type=click.Choice(["txt", "md", "json"]), default="md")
@click.option("--workers", "-w", default=4, type=int)
@click.option("--timeout", default=1800, type=int, help="Maximum seconds to wait for the batch.")
@click.pass_context
def batch(ctx, directory, model, output, fmt, workers, timeout):
    """Recognize all supported files in a directory."""
    client = get_client(ctx)
    root = Path(directory)
    files = []
    for pattern in IMAGE_PATTERNS:
        files.extend(root.glob(pattern))
    files = sorted(set(files))
    if not files:
        raise click.ClickException("no supported files found")
    out_dir = Path(output) if output else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    with click.progressbar(files, label="Submitting") as bar:
        for file in bar:
            tasks.append({"file": file, **client.submit_ocr(file, model_tier=model)})

    done = set()
    failed = []
    succeeded = 0
    with click.progressbar(length=len(tasks), label="Processing") as bar:
        deadline = time.time() + max(1, timeout)
        while len(done) < len(tasks):
            if time.time() > deadline:
                pending = [task["task_id"] for task in tasks if task["task_id"] not in done]
                raise click.ClickException(f"batch timed out after {timeout}s; pending={len(pending)}")
            for task in tasks:
                tid = task["task_id"]
                if tid in done:
                    continue
                row = client.task(tid)["task"]
                if row.get("status") in ("done", "failed", "cancelled"):
                    done.add(tid)
                    bar.update(1)
                    if row.get("status") == "done":
                        succeeded += 1
                    else:
                        failed.append({"file": str(task["file"]), "status": row.get("status"), "error": row.get("error")})
                    if out_dir and row.get("status") == "done":
                        text = as_text_result(row.get("result") or {}, fmt)
                        suffix = ".json" if fmt == "json" else ".md" if fmt == "md" else ".txt"
                        (out_dir / (task["file"].stem + suffix)).write_text(text, encoding="utf-8")
            time.sleep(0.5)
    click.echo(f"Processed {len(done)} tasks: done={succeeded} failed={len(failed)}", err=True)
    for item in failed:
        click.echo(f"FAILED {item['file']}: {item['error'] or item['status']}", err=True)
    if failed:
        raise click.ClickException(f"{len(failed)} task(s) failed")
