"""Optional executable discovery; it never runs a converter during planning."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .model import Capability


def discover_capabilities() -> dict[str, Capability]:
    image_executable = shutil.which("magick") or shutil.which("convert")
    ffmpeg_executable = shutil.which("ffmpeg")
    return {
        "imagemagick": Capability(
            adapter="ImageMagick",
            executable=image_executable,
            version=None,
            available=bool(image_executable),
            diagnostic="available" if image_executable else "ImageMagick is not installed (looked for magick/convert)",
        ),
        "ffmpeg": Capability(
            adapter="FFmpeg",
            executable=ffmpeg_executable,
            version=None,
            available=bool(ffmpeg_executable),
            diagnostic="available" if ffmpeg_executable else "FFmpeg is not installed (looked for ffmpeg)",
        ),
    }


def capability_for(name: str, snapshot: dict[str, Capability] | None = None) -> Capability:
    values = snapshot or discover_capabilities()
    return values[name]
