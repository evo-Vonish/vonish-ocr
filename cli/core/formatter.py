import json


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def table(rows, columns):
    rows = list(rows or [])
    widths = []
    for key, title in columns:
        values = [str(row.get(key, "")) for row in rows]
        widths.append(max(len(str(title)), *(len(v) for v in values)) if values else len(str(title)))
    header = "  ".join(str(title).ljust(widths[i]) for i, (_, title) in enumerate(columns))
    sep = "  ".join("-" * width for width in widths)
    lines = [header, sep]
    for row in rows:
        lines.append("  ".join(str(row.get(key, "")).ljust(widths[i]) for i, (key, _) in enumerate(columns)))
    return "\n".join(lines)


def print_table(rows, columns):
    print(table(rows, columns))


def as_text_result(result, fmt="md"):
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    ai = result.get("ai") or {}
    if fmt == "txt":
        return ai.get("polished") or result.get("text") or ""
    return ai.get("polished") or result.get("text") or ""
