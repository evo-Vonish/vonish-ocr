import click

from cli.core.formatter import print_json, print_table
from cli.core.langpacks import LangPackError, LangPackManager, parse_lang_spec


@click.group()
def lang():
    """Manage OCR language packs."""


@lang.command("list")
@click.option("--installed", is_flag=True, help="Only show installed language packs.")
@click.option("--json", "as_json", is_flag=True)
def list_langs(installed, as_json):
    """List installed and available language packs."""
    rows = LangPackManager().list(include_remote=not installed)
    if as_json:
        print_json(rows)
    else:
        print_table(
            rows,
            [
                ("name", "NAME"),
                ("version", "VERSION"),
                ("installed", "INSTALLED"),
                ("size_mb", "SIZE_MB"),
                ("quality", "QUALITY"),
                ("language", "LANGUAGE"),
            ],
        )


@lang.command()
@click.argument("language")
@click.option("--mirror", default=None, help="Prefer a mirror name or URL fragment.")
@click.option("--yes", "-y", is_flag=True, help="Skip download confirmation.")
@click.option("--offline", is_flag=True, help="Do not access the network.")
@click.option("--json", "as_json", is_flag=True)
def pull(language, mirror, yes, offline, as_json):
    """Install a language pack, e.g. `vocr lang pull ch`."""
    try:
        result = LangPackManager().install(parse_lang_spec(language), mirror=mirror, yes=yes, offline=offline)
    except LangPackError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        print_json(result)
    else:
        click.echo(f"[OK] {result['language']} {result['status']} from {result['source']}: {result['path']}")


@lang.command()
@click.argument("language")
@click.option("--json", "as_json", is_flag=True)
def show(language, as_json):
    """Show manifest and install status for a language pack."""
    try:
        result = LangPackManager().show(parse_lang_spec(language))
    except LangPackError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        print_json(result)
    else:
        manifest = result["manifest"]
        installed = result["installed"]
        rows = [
            {"key": "language", "value": f"{manifest['language']['code']} / {manifest['language'].get('name', '')}"},
            {"key": "model_family", "value": manifest["model_family"]},
            {"key": "pack_version", "value": manifest["pack_version"]},
            {"key": "quality", "value": manifest.get("quality_tier", "standard")},
            {"key": "installed", "value": "yes" if installed else "no"},
            {"key": "license", "value": (manifest.get("metadata") or {}).get("license", "")},
        ]
        print_table(rows, [("key", "FIELD"), ("value", "VALUE")])


@lang.command("rm")
@click.argument("language")
@click.option("--keep-files", is_flag=True, help="Only unregister the language pack.")
@click.option("--json", "as_json", is_flag=True)
def remove(language, keep_files, as_json):
    """Uninstall a language pack."""
    try:
        result = LangPackManager().remove(parse_lang_spec(language), delete_files=not keep_files)
    except LangPackError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        print_json(result)
    else:
        click.echo(f"[OK] removed {result['language']}: {result['path']}")


@lang.command()
@click.argument("language", required=False)
@click.option("--repair", is_flag=True, help="Delete corrupt local files so they can be pulled again.")
@click.option("--json", "as_json", is_flag=True)
def verify(language, repair, as_json):
    """Verify installed language pack files with SHA256."""
    try:
        result = LangPackManager().verify(parse_lang_spec(language) if language else None, repair=repair)
    except LangPackError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        print_json(result)
    else:
        rows = result if isinstance(result, list) else [result]
        print_table(rows, [("language", "NAME"), ("model_family", "MODEL"), ("ok", "OK"), ("path", "PATH")])


@lang.command()
@click.option("--json", "as_json", is_flag=True)
def update(as_json):
    """Check installed language packs. Network upgrades are not automatic yet."""
    rows = LangPackManager().list(include_remote=False)
    result = {"checked": len(rows), "updates": [], "message": "remote update resolution is not enabled yet"}
    if as_json:
        print_json(result)
    else:
        click.echo(f"checked {result['checked']} installed language pack(s); no automatic update source is enabled yet")
