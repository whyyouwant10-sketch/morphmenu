"""Public, serializable data types used by the planner and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class DetectionResult:
    extension_guess: str | None
    content_guess: str | None
    selected_format: str | None
    confidence: str
    bytes_inspected: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "extension_guess": self.extension_guess,
            "content_guess": self.content_guess,
            "selected_format": self.selected_format,
            "confidence": self.confidence,
            "bytes_inspected": self.bytes_inspected,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Capability:
    adapter: str
    executable: str | None
    version: str | None
    available: bool
    diagnostic: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "executable": self.executable,
            "version": self.version,
            "available": self.available,
            "diagnostic": self.diagnostic,
        }


@dataclass(frozen=True)
class ConversionEdge:
    source: str
    target: str
    adapter: str
    cost: int = 1
    lossy: bool = False
    metadata_policy: str = "strip"
    required_capability: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "adapter": self.adapter,
            "cost": self.cost,
            "lossy": self.lossy,
            "metadata_policy": self.metadata_policy,
            "required_capability": self.required_capability,
        }


@dataclass(frozen=True)
class ConversionPlan:
    input_path: Path
    source_format: str
    target_format: str
    output_path: Path
    route: tuple[ConversionEdge, ...]
    detection: DetectionResult
    metadata_policy: str
    input_size: int
    input_mtime_ns: int
    safety_checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, str], ...] = ()
    status: str = "ready"

    @property
    def adapter(self) -> str:
        return self.route[0].adapter if self.route else "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "input": {
                "path": str(self.input_path),
                "size": self.input_size,
                "mtime_ns": self.input_mtime_ns,
            },
            "detection": self.detection.to_dict(),
            "source_format": self.source_format,
            "target_format": self.target_format,
            "route": [edge.to_dict() for edge in self.route],
            "output_path": str(self.output_path),
            "metadata_policy": self.metadata_policy,
            "safety_checks": list(self.safety_checks),
            "warnings": list(self.warnings),
            "diagnostics": list(self.diagnostics),
            "status": self.status,
        }


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    output_path: Path | None
    duration_ms: int
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "output_path": str(self.output_path) if self.output_path else None,
            "duration_ms": self.duration_ms,
            "diagnostics": list(self.diagnostics),
        }
