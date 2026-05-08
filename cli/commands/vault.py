from pathlib import Path

import click

from cli.core.context import get_client
from cli.core.formatter import print_json, print_table


@click.group()
def vault():
    """Case vault operations."""


@vault.command("ls")
@click.option("--scene", default=None)
@click.option("--limit", default=50, type=int)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def ls(ctx, scene, limit, as_json):
    data = get_client(ctx).vault_list(limit=limit, scene=scene)
    rows = data.get("items", [])
    if as_json:
        print_json(data)
    else:
        print_table(rows, [("id", "ID"), ("filename", "FILE"), ("scene_type", "SCENE"), ("status", "STATUS"), ("created_at", "CREATED")])


@vault.command()
@click.argument("query")
@click.pass_context
def search(ctx, query):
    data = get_client(ctx).vault_list(search=query)
    print_table(data.get("items", []), [("id", "ID"), ("filename", "FILE"), ("scene_type", "SCENE"), ("status", "STATUS")])


@vault.command()
@click.argument("evidence_id")
@click.option("--format", "fmt", default="md", type=click.Choice(["txt", "md", "json", "docx"]))
@click.pass_context
def export(ctx, evidence_id, fmt):
    ev = get_client(ctx).vault_get(evidence_id)
    if fmt == "json":
        print_json(ev)
        return
    text = ev.get("refined_text") or ev.get("raw_text") or ""
    suffix = ".md" if fmt == "md" else ".txt"
    path = Path(f"{evidence_id}{suffix}")
    path.write_text(text, encoding="utf-8")
    click.echo(f"exported {path}")


@vault.command("rm")
@click.argument("evidence_id")
@click.option("--purge", is_flag=True, help="Reserved; current API deletes record.")
@click.pass_context
def rm_cmd(ctx, evidence_id, purge):
    print_json(get_client(ctx).vault_delete(evidence_id))
