"""Canonical format names, aliases, and filename extensions."""

from __future__ import annotations


ALIASES = {
    "txt": "text",
    "text": "text",
    "md": "markdown",
    "markdown": "markdown",
    "mkd": "markdown",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "csv": "csv",
    "htm": "html",
    "html": "html",
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "jpe": "jpeg",
    "png": "png",
    "webp": "webp",
    "gif": "gif",
    "bmp": "bmp",
    "wav": "wav",
    "mp3": "mp3",
    "flac": "flac",
    "ogg": "ogg",
    "oga": "ogg",
    "mp4": "mp4",
    "m4v": "mp4",
    "mov": "mov",
    "webm": "webm",
    "mkv": "matroska",
    "mka": "matroska",
    "pdf": "pdf",
    "zip": "zip",
}

EXTENSIONS = {
    "text": ".txt",
    "markdown": ".md",
    "json": ".json",
    "yaml": ".yaml",
    "csv": ".csv",
    "html": ".html",
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "gif": ".gif",
    "bmp": ".bmp",
    "wav": ".wav",
    "mp3": ".mp3",
    "flac": ".flac",
    "ogg": ".ogg",
    "mp4": ".mp4",
    "mov": ".mov",
    "webm": ".webm",
    "matroska": ".mkv",
    "pdf": ".pdf",
    "zip": ".zip",
}

CANONICAL_FORMATS = tuple(EXTENSIONS)


def canonicalize(value: str) -> str | None:
    return ALIASES.get(value.lower().lstrip("."))


def extension_format(suffix: str) -> str | None:
    return canonicalize(suffix)


def extension_for(format_id: str) -> str:
    try:
        return EXTENSIONS[canonicalize(format_id) or format_id]
    except KeyError as exc:
        raise ValueError(f"unknown target format: {format_id}") from exc
