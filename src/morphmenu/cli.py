"""Argparse CLI for detection, planning, and explicit conversion."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .capabilities import discover_capabilities
from .detect import detect_file
from .execute import execute_plan
from .formats import CANONICAL_FORMATS
from .model import SCHEMA_VERSION
from .planner import PlanningError, plan_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="morphmenu", description="Safe local file conversion planning")
    subparsers = parser.add_subparsers(dest="command", required=True)
    detect_parser = subparsers.add_parser("detect", help="detect a file format")
    detect_parser.add_argument("path")
    detect_parser.add_argument("--json", action="store_true")
    formats_parser = subparsers.add_parser("formats", help="list recognized formats and capabilities")
    formats_parser.add_argument("--available", action="store_true")
    formats_parser.add_argument("--json", action="store_true")
    for name in ("plan", "convert"):
        command = subparsers.add_parser(name, help="create a conversion plan")
        command.add_argument("paths", nargs="+")
        command.add_argument("--to", required=True, dest="target")
        command.add_argument("--from", dest="from_format")
        command.add_argument("--out-dir")
        command.add_argument("--metadata", choices=("strip", "preserve"), default="strip")
        command.add_argument("--execute", action="store_true", help="write outputs (convert only)")
        command.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "detect":
        return _detect(args)
    if args.command == "formats":
        return _formats(args)
    if args.command == "plan" and args.execute:
        print("error: plan does not support --execute", file=sys.stderr)
        return 2
    return _plans(args)


def _detect(args: argparse.Namespace) -> int:
    try:
        result = detect_file(args.path)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "detection": result.to_dict()}, indent=2, sort_keys=True))
    else:
        print(f"Path:             {args.path}")
        print(f"Extension guess:  {result.extension_guess or 'unknown'}")
        print(f"Content guess:    {result.content_guess or 'unknown'}")
        print(f"Selected format:  {result.selected_format or 'unknown'} ({result.confidence} confidence)")
        for warning in result.warnings:
            print(f"Warning:          {warning}")
    return 0 if result.selected_format else 1


def _formats(args: argparse.Namespace) -> int:
    capabilities = discover_capabilities()
    payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "formats": list(CANONICAL_FORMATS)}
    if args.available:
        payload["capabilities"] = {name: capability.to_dict() for name, capability in capabilities.items()}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Recognized formats: " + ", ".join(CANONICAL_FORMATS))
        if args.available:
            for capability in capabilities.values():
                state = "available" if capability.available else "unavailable"
                print(f"{capability.adapter}: {state} — {capability.diagnostic}")
    return 0


def _plans(args: argparse.Namespace) -> int:
    plans = []
    errors = []
    for path in args.paths:
        try:
            plan = plan_file(path, args.target, from_format=args.from_format, out_dir=args.out_dir, metadata=args.metadata)
        except PlanningError as exc:
            errors.append({"path": path, "code": exc.code, "message": exc.message})
            continue
        plans.append(plan)
        if plan.status != "ready":
            errors.extend({"path": path, **diagnostic} for diagnostic in plan.diagnostics)
    execution_results = []
    if args.execute:
        for plan in plans:
            execution_results.append(execute_plan(plan) if plan.status == "ready" else None)
    results = [result.to_dict() for result in execution_results if result is not None]
    if args.execute:
        errors.extend(
            {"path": str(plan.input_path), "code": "EXECUTION_FAILED", "message": result.diagnostics[0]}
            for plan, result in zip(plans, execution_results)
            if result is not None and result.status != "success"
        )
    if args.json:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "dry_run": not args.execute,
            "plans": [plan.to_dict() for plan in plans],
            "results": results,
            "errors": errors,
        }
        print(json.dumps(envelope, indent=2, sort_keys=True))
    else:
        if not args.execute:
            print("DRY RUN — no files will be written")
        for index, plan in enumerate(plans):
            print(f"Input:  {plan.input_path} ({plan.source_format})")
            route = " -> ".join([plan.source_format] + [edge.target for edge in plan.route])
            print(f"Route:  {route} via {plan.adapter}")
            print(f"Output: {plan.output_path}")
            print("Policy: create-only; existing outputs are never overwritten")
            for warning in plan.warnings:
                print(f"Warning: {warning}")
            if args.execute:
                result = execution_results[index] if index < len(execution_results) else None
                if result:
                    output = str(result.output_path) if result.output_path else "; ".join(result.diagnostics)
                    print(f"Result: {result.status} ({output})")
        for error in errors:
            print(f"Error [{error.get('code', 'ERROR')}] {error.get('path', '')}: {error['message']}", file=sys.stderr)
    if args.execute and not args.json:
        if any(result is not None and result.status != "success" for result in execution_results):
            return 1
    return 1 if errors else 0
