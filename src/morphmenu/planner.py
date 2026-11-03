"""Detection, route selection, capability evaluation, and safe naming."""

from __future__ import annotations

from pathlib import Path

from .capabilities import discover_capabilities
from .detect import detect_file
from .formats import CANONICAL_FORMATS, canonicalize
from .graph import find_route
from .model import Capability, ConversionPlan
from .naming import destination_path


class PlanningError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def plan_file(
    input_path: str | Path,
    target: str,
    *,
    from_format: str | None = None,
    out_dir: str | Path | None = None,
    metadata: str = "strip",
    capabilities: dict[str, Capability] | None = None,
) -> ConversionPlan:
    source_path = Path(input_path).expanduser().absolute()
    if not source_path.exists() or not source_path.is_file():
        raise PlanningError("INPUT_NOT_REGULAR_FILE", f"input is not a regular file: {input_path}")
    if not source_path.stat().st_mode & 0o444:
        raise PlanningError("INPUT_NOT_READABLE", f"input is not readable: {input_path}")
    target_id = canonicalize(target)
    if target_id not in CANONICAL_FORMATS:
        raise PlanningError("UNKNOWN_TARGET_FORMAT", f"unknown target format: {target}")
    try:
        detection = detect_file(source_path)
    except OSError as exc:
        raise PlanningError("INPUT_READ_ERROR", f"could not read input: {exc}") from exc
    explicit_source = canonicalize(from_format) if from_format else None
    if from_format and explicit_source is None:
        raise PlanningError("UNKNOWN_SOURCE_FORMAT", f"unknown source format: {from_format}")
    if detection.content_guess and explicit_source and detection.content_guess not in {"text", "markdown", "yaml", "csv"} and explicit_source != detection.content_guess:
        raise PlanningError(
            "FROM_MISMATCH",
            f"--from {explicit_source} conflicts with conclusive content format {detection.content_guess}",
        )
    if explicit_source:
        source_format = explicit_source
    elif detection.content_guess:
        source_format = detection.selected_format
    else:
        raise PlanningError("UNKNOWN_CONTENT", "content is not recognized; provide --from FORMAT")
    if source_format is None:
        raise PlanningError("UNKNOWN_CONTENT", "content is not recognized; provide --from FORMAT")
    if source_format == target_id:
        raise PlanningError("NO_OP_CONVERSION", "source and target formats are the same")
    route = find_route(source_format, target_id)
    if route is None:
        raise PlanningError("UNSUPPORTED_ROUTE", f"no v0.1 conversion route from {source_format} to {target_id}")
    output_directory = Path(out_dir).expanduser().absolute() if out_dir else Path.cwd().absolute() / "converted"
    try:
        output_path, naming_warnings = destination_path(source_path, output_directory, target_id)
    except ValueError as exc:
        raise PlanningError("OUTPUT_COLLISION", str(exc)) from exc
    if output_path.absolute() == source_path:
        raise PlanningError("INPUT_OUTPUT_COLLISION", "output path would replace the input")
    stat = source_path.stat()
    snapshot = capabilities or discover_capabilities()
    diagnostics: list[dict[str, str]] = []
    status = "ready"
    for edge in route:
        if edge.required_capability:
            capability = snapshot[edge.required_capability]
            if not capability.available:
                status = "unavailable_capability"
                diagnostics.append({"code": "UNAVAILABLE_CAPABILITY", "message": capability.diagnostic})
    warnings = list(detection.warnings) + list(naming_warnings)
    if metadata not in {"strip", "preserve"}:
        raise PlanningError("INVALID_METADATA_POLICY", "metadata must be strip or preserve")
    return ConversionPlan(
        input_path=source_path,
        source_format=source_format,
        target_format=target_id,
        output_path=output_path,
        route=route,
        detection=detection,
        metadata_policy=metadata,
        input_size=stat.st_size,
        input_mtime_ns=stat.st_mtime_ns,
        safety_checks=("create-only", "output-directory-not-created-during-plan", "input-identity-captured"),
        warnings=tuple(warnings),
        diagnostics=tuple(diagnostics),
        status=status,
    )
