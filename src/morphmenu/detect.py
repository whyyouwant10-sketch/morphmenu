"""Bounded content-plus-extension format detection."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .formats import canonicalize, extension_format
from .model import DetectionResult


MAX_SNIFF_BYTES = 64 * 1024


def _text_guess(data: bytes) -> str | None:
    if not data or b"\x00" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    stripped = text.strip()
    if not stripped:
        return "text"
    if stripped.lower().startswith(("<!doctype html", "<html", "<head", "<body")):
        return "html"
    try:
        json.loads(stripped)
    except (ValueError, TypeError):
        pass
    else:
        return "json"
    lines = text.splitlines()
    markdown_markers = ("# ", "## ", "### ", "```", "- ", "* ", "> ", "[", "---")
    if any(line.lstrip().startswith(markdown_markers) for line in lines):
        return "markdown"
    if any(":" in line and line.split(":", 1)[0].strip() for line in lines[:20]):
        return "yaml"
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        rows = []
    if len(rows) >= 2 and len({len(row) for row in rows[:10]}) == 1 and len(rows[0]) > 1:
        return "csv"
    return "text"


def sniff_content(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if len(data) >= 2 and data[:2] == b"BM":
        return "bmp"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    if data.startswith(b"ID3") or _looks_like_mp3_frame(data):
        return "mp3"
    if data.startswith(b"fLaC"):
        return "flac"
    if data.startswith(b"OggS"):
        return "ogg"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12].lower()
        return "mov" if brand in {b"qt  ", b"m4v ", b"m4a ", b"m4b "} else "mp4"
    if data.startswith(b"\x1aE\xdf\xa3"):
        return "webm"
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06"):
        return "zip"
    return _text_guess(data)


def _looks_like_mp3_frame(data: bytes) -> bool:
    if len(data) < 2:
        return False
    return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0 and (data[1] & 0x06) != 0


def detect_file(path: str | Path, *, max_bytes: int = MAX_SNIFF_BYTES) -> DetectionResult:
    file_path = Path(path)
    extension_guess = extension_format(file_path.suffix)
    with file_path.open("rb") as handle:
        data = handle.read(max_bytes)
    content_guess = sniff_content(data)
    warnings: list[str] = []
    if content_guess and extension_guess and content_guess != extension_guess:
        warnings.append("EXTENSION_CONTENT_MISMATCH")
    if content_guess:
        selected = content_guess
        confidence = "high" if content_guess not in {"text", "markdown", "yaml", "csv"} else "medium"
    else:
        selected = extension_guess
        confidence = "low" if selected else "unknown"
        if selected:
            warnings.append("CONTENT_UNCONFIRMED_EXTENSION_ONLY")
        else:
            warnings.append("UNKNOWN_CONTENT")
    return DetectionResult(
        extension_guess=extension_guess,
        content_guess=content_guess,
        selected_format=selected,
        confidence=confidence,
        bytes_inspected=len(data),
        warnings=tuple(warnings),
    )
