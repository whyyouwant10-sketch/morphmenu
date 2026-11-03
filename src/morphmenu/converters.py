"""Safe, local conversions that do not need external executables."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any


try:  # PyYAML is useful when present, but intentionally not required.
    import yaml as _pyyaml  # type: ignore
except ImportError:  # pragma: no cover - depends on the user's environment
    _pyyaml = None


def parse_yaml(text: str) -> Any:
    if _pyyaml is not None:
        return _pyyaml.safe_load(text)
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    lines = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    value, index = _parse_yaml_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("unsupported or malformed YAML")
    return value


def _parse_yaml_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    is_list = lines[index][1].startswith("-")
    result: Any = [] if is_list else {}
    while index < len(lines) and lines[index][0] == indent:
        _, content = lines[index]
        if is_list:
            if not content.startswith("-"):
                break
            remainder = content[1:].strip()
            if not remainder:
                if index + 1 < len(lines) and lines[index + 1][0] > indent:
                    item, index = _parse_yaml_block(lines, index + 1, lines[index + 1][0])
                else:
                    item, index = None, index + 1
            elif ":" in remainder and not remainder.startswith(("'", '"')):
                key, raw = remainder.split(":", 1)
                item = {key.strip(): _yaml_scalar(raw.strip()) if raw.strip() else None}
                index += 1
                if index < len(lines) and lines[index][0] > indent:
                    child, index = _parse_yaml_block(lines, index, lines[index][0])
                    if isinstance(child, dict):
                        item.update(child)
            else:
                item, index = _yaml_scalar(remainder), index + 1
            result.append(item)
        else:
            if content.startswith("-") or ":" not in content:
                break
            key, raw = content.split(":", 1)
            key = key.strip().strip("'\"")
            if raw.strip():
                result[key] = _yaml_scalar(raw.strip())
                index += 1
            elif index + 1 < len(lines) and lines[index + 1][0] > indent:
                result[key], index = _parse_yaml_block(lines, index + 1, lines[index + 1][0])
            else:
                result[key], index = None, index + 1
    return result, index


def _yaml_scalar(value: str) -> Any:
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value.split(" #", 1)[0].rstrip()


def dump_yaml(value: Any, indent: int = 0) -> str:
    if _pyyaml is not None:
        return _pyyaml.safe_dump(value, allow_unicode=True, sort_keys=False)
    lines: list[str] = []
    _dump_yaml(value, lines, indent)
    return "\n".join(lines) + "\n"


def _dump_yaml(value: Any, lines: list[str], indent: int) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key) if re.fullmatch(r"[A-Za-z_][\w.-]*", str(key)) else json.dumps(str(key), ensure_ascii=False)
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key_text}:")
                _dump_yaml(item, lines, indent + 2)
            else:
                lines.append(f"{prefix}{key_text}: {_yaml_dump_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                _dump_yaml(item, lines, indent + 2)
            else:
                lines.append(f"{prefix}- {_yaml_dump_scalar(item)}")
    else:
        lines.append(f"{prefix}{_yaml_dump_scalar(value)}")


def _yaml_dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def parse_csv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV input has no header row")
    return [dict(row) for row in reader]


def object_to_csv(value: Any) -> str:
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        fields: list[str] = []
        for item in value:
            for key in item:
                if str(key) not in fields:
                    fields.append(str(key))
        rows = [{field: item.get(field, "") for field in fields} for item in value]
    elif isinstance(value, list):
        fields, rows = ["value"], [{"value": item} for item in value]
    elif isinstance(value, dict):
        if value and all(isinstance(item, list) for item in value.values()):
            fields = [str(key) for key in value]
            rows = [dict(zip(fields, row)) for row in zip(*value.values())]
        else:
            fields, rows = ["key", "value"], [{"key": key, "value": item} for key, item in value.items()]
    else:
        fields, rows = ["value"], [{"value": value}]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def markdown_to_text(text: str) -> str:
    text = re.sub(r"```(?:[^\n]*)\n(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"^\s*[-*>+]\s+", "", text, flags=re.MULTILINE)
    return text


def convert_text(source: str, target: str, text: str) -> str:
    if source == target:
        return text
    if source == "markdown" and target == "text":
        return markdown_to_text(text)
    if source == "text" and target == "markdown":
        return text
    if source == "text":
        value = text
    elif source == "markdown":
        value = markdown_to_text(text)
    elif source == "json":
        value = json.loads(text)
    elif source == "yaml":
        value = parse_yaml(text)
    elif source == "csv":
        value = parse_csv(text)
    else:
        raise ValueError(f"no built-in converter from {source} to {target}")
    if target == "text":
        if source == "csv":
            return text
        return json.dumps(value, ensure_ascii=False, indent=2) + "\n" if source == "json" else dump_yaml(value)
    if target == "markdown":
        if isinstance(value, str):
            return value
        return dump_yaml(value)
    if target == "json":
        return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if target == "yaml":
        return dump_yaml(value)
    if target == "csv":
        return object_to_csv(value)
    raise ValueError(f"no built-in converter from {source} to {target}")
