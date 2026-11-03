"""The explicit execution boundary for a previously planned conversion."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from .capabilities import discover_capabilities
from .converters import convert_text
from .model import ConversionPlan, ExecutionResult


def execute_plan(plan: ConversionPlan, *, timeout: float = 120.0) -> ExecutionResult:
    started = time.monotonic()
    if plan.status != "ready":
        return _failure(plan, "plan is not executable: " + plan.status, started)
    try:
        current = plan.input_path.stat()
    except OSError as exc:
        return _failure(plan, f"input disappeared: {exc}", started)
    if (current.st_size, current.st_mtime_ns) != (plan.input_size, plan.input_mtime_ns):
        return _failure(plan, "input changed since planning (identity mismatch)", started)
    output_dir = plan.output_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if plan.output_path.is_symlink() or plan.output_path.exists():
            return _failure(plan, "destination exists or is a symlink", started)
        temp_fd, temp_name = tempfile.mkstemp(prefix=".morphmenu-", suffix=plan.output_path.suffix, dir=output_dir)
        os.close(temp_fd)
        temp_path = Path(temp_name)
        try:
            if plan.adapter == "builtin":
                source = plan.input_path.read_text(encoding="utf-8")
                result = convert_text(plan.source_format, plan.target_format, source)
                temp_path.write_text(result, encoding="utf-8", newline="")
            else:
                _run_external(plan, temp_path, timeout)
            if not temp_path.is_file() or temp_path.stat().st_size == 0:
                raise RuntimeError("converter did not produce a non-empty output")
            _publish_no_replace(temp_path, plan.output_path)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return _failure(plan, str(exc), started)
    return ExecutionResult("success", plan.output_path, _duration(started))


def _run_external(plan: ConversionPlan, temp_path: Path, timeout: float) -> None:
    capabilities = discover_capabilities()
    required = plan.route[0].required_capability
    if not required or not capabilities[required].available:
        raise RuntimeError("required optional converter is unavailable")
    executable = capabilities[required].executable
    assert executable is not None
    if required == "imagemagick":
        argv = [executable, str(plan.input_path), "-strip", str(temp_path)]
    else:
        argv = [executable, "-hide_banner", "-loglevel", "error", "-i", str(plan.input_path), str(temp_path)]
    completed = subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=str(temp_path.parent),
        timeout=timeout,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    if completed.returncode:
        diagnostic = completed.stderr[:2000].decode("utf-8", "replace").strip()
        raise RuntimeError(f"optional converter failed ({completed.returncode}): {diagnostic}")


def _publish_no_replace(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError as exc:
        raise RuntimeError("destination appeared during conversion; nothing was overwritten") from exc
    source.unlink()


def _duration(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _failure(plan: ConversionPlan, message: str, started: float) -> ExecutionResult:
    return ExecutionResult("failed", None, _duration(started), (message,))
