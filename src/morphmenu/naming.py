"""Create-only, cross-platform-safe destination naming."""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path

from .formats import extension_for


_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def sanitize_stem(value: str, *, max_length: int = 120) -> str:
    value = unicodedata.normalize("NFC", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Cc")
    value = _INVALID.sub("_", value).strip().rstrip(". ")
    value = value or "converted"
    if value.upper().split(".", 1)[0] in _RESERVED:
        value = f"_{value}"
    if len(value) > max_length:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        value = f"{value[:max_length - 10].rstrip()}-{digest}"
    return value


def destination_path(input_path: Path, output_dir: Path, target: str) -> tuple[Path, tuple[str, ...]]:
    """Return an unused candidate without creating or modifying anything."""
    stem = sanitize_stem(input_path.stem)
    suffix = extension_for(target)
    output_dir = Path(output_dir)
    warnings: list[str] = []
    for number in range(0, 1001):
        candidate_stem = stem if number == 0 else f"{stem} ({number})"
        candidate = output_dir / f"{candidate_stem}{suffix}"
        # exists() misses broken symlinks; lstat is intentional for safety.
        if not os.path.lexists(candidate):
            if number:
                warnings.append("OUTPUT_COLLISION_RENAMED")
            return candidate, tuple(warnings)
    raise ValueError("OUTPUT_COLLISION: more than 1000 destination names are occupied")
