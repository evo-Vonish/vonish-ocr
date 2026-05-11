import json
import re
from pathlib import Path

import click

from cli.core.daemon import project_root
from cli.core.formatter import print_json

THEME_FILE = "appearance.json"
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def theme_path() -> Path:
    root = project_root() / ".vocr"
    root.mkdir(parents=True, exist_ok=True)
    return root / THEME_FILE


def load_theme():
    path = theme_path()
    if not path.exists():
        return {
            "appearance": "professional",
            "themeMode": "system",
            "resolvedTheme": "dark",
            "customTokens": {
                "accent": "#8FF6D2",
                "warn": "#D7B95A",
                "error": "#B85A50",
                "success": "#56F28C",
                "sizeOffset": 0,
                "fontWeight": "normal",
                "borderWidth": 1,
                "decorationLevel": 1,
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_theme(data):
    theme_path().write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_hex(value, token_name):
    if not HEX_RE.match(value or ""):
        raise click.ClickException(f"{token_name} must be a 6-digit HEX color, for example #8FF6D2")
    return value.upper()


@click.group()
def theme():
    """Appearance configuration."""


@theme.command("get")
@click.argument("key", required=False)
def get_cmd(key):
    data = load_theme()
    if key:
        value = data
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        print_json(value)
    else:
        print_json(data)


@theme.group("set")
def set_group():
    """Set appearance tokens."""


@set_group.command("appearance")
@click.argument("value", type=click.Choice(["evidence", "professional"]))
def set_appearance(value):
    data = load_theme()
    data["appearance"] = value
    save_theme(data)
    print_json(data)


@set_group.command("mode")
@click.argument("value", type=click.Choice(["dark", "light", "system"]))
def set_mode(value):
    data = load_theme()
    data["themeMode"] = value
    save_theme(data)
    print_json(data)


@set_group.command("accent")
@click.argument("value")
def set_accent(value):
    _set_custom_color("accent", value)


@set_group.command("warn")
@click.argument("value")
def set_warn(value):
    _set_custom_color("warn", value)


@set_group.command("error")
@click.argument("value")
def set_error(value):
    _set_custom_color("error", value)


@set_group.command("success")
@click.argument("value")
def set_success(value):
    _set_custom_color("success", value)


@theme.command("reset")
def reset():
    path = theme_path()
    if path.exists():
        path.unlink()
    print_json(load_theme())


def _set_custom_color(key, value):
    data = load_theme()
    custom = data.setdefault("customTokens", {})
    custom[key] = assert_hex(value, key)
    save_theme(data)
    print_json(data)
