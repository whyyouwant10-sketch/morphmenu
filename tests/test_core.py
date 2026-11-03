from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from morphmenu.detect import detect_file
from morphmenu.execute import execute_plan
from morphmenu.model import Capability
from morphmenu.naming import destination_path, sanitize_stem
from morphmenu.planner import PlanningError, plan_file


class DetectionTests(unittest.TestCase):
    def test_content_wins_and_mismatch_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "picture.jpg"
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fixture")
            result = detect_file(path)
            self.assertEqual(result.extension_guess, "jpeg")
            self.assertEqual(result.content_guess, "png")
            self.assertEqual(result.selected_format, "png")
            self.assertIn("EXTENSION_CONTENT_MISMATCH", result.warnings)

    def test_json_and_csv_content_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.bin").write_text('{"ok": true}', encoding="utf-8")
            (root / "rows.data").write_text("name,age\nAda,36\n", encoding="utf-8")
            self.assertEqual(detect_file(root / "data.bin").content_guess, "json")
            self.assertEqual(detect_file(root / "rows.data").content_guess, "csv")


class NamingTests(unittest.TestCase):
    def test_sanitizes_reserved_and_control_characters(self) -> None:
        stem = sanitize_stem("CON\x00")
        self.assertTrue(stem.startswith("_CON"))
        self.assertNotIn("\x00", stem)
        self.assertNotIn(":", sanitize_stem("report:copy"))

    def test_collision_gets_new_name_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.json"
            source.write_text("{}", encoding="utf-8")
            out = root / "out"
            out.mkdir()
            (out / "report.yaml").write_text("existing", encoding="utf-8")
            candidate, warnings = destination_path(source, out, "yaml")
            self.assertEqual(candidate.name, "report (1).yaml")
            self.assertIn("OUTPUT_COLLISION_RENAMED", warnings)


class PlanningAndExecutionTests(unittest.TestCase):
    def test_dry_run_does_not_create_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data.json"
            source.write_text('{"name": "Ada"}\n', encoding="utf-8")
            out = root / "not-created"
            plan = plan_file(source, "yaml", out_dir=out)
            self.assertEqual(plan.status, "ready")
            self.assertFalse(out.exists())
            self.assertEqual(source.read_text(encoding="utf-8"), '{"name": "Ada"}\n')

    def test_execute_structured_conversion_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data.json"
            source.write_text('{"name": "Ada"}\n', encoding="utf-8")
            out = root / "out"
            plan = plan_file(source, "yaml", out_dir=out)
            result = execute_plan(plan)
            self.assertEqual(result.status, "success")
            self.assertIn('name:', result.output_path.read_text(encoding="utf-8"))
            second = plan_file(source, "yaml", out_dir=out)
            self.assertEqual(second.output_path.name, "data (1).yaml")

    def test_plain_text_can_become_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "note.txt"
            source.write_text("hello", encoding="utf-8")
            plan = plan_file(source, "json", out_dir=root / "out")
            result = execute_plan(plan)
            self.assertEqual(result.status, "success")
            self.assertEqual(json.loads(result.output_path.read_text(encoding="utf-8")), "hello")

    def test_missing_optional_tool_is_reported_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "picture.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\n")
            capabilities = {
                "imagemagick": Capability("ImageMagick", None, None, False, "ImageMagick missing for test"),
                "ffmpeg": Capability("FFmpeg", None, None, False, "FFmpeg missing for test"),
            }
            plan = plan_file(source, "jpeg", out_dir=Path(directory) / "out", capabilities=capabilities)
            self.assertEqual(plan.status, "unavailable_capability")
            self.assertEqual(plan.diagnostics[0]["code"], "UNAVAILABLE_CAPABILITY")
            self.assertFalse((Path(directory) / "out").exists())

    def test_unknown_content_requires_explicit_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "data.unknown"
            source.write_bytes(b"\x00\x01not text")
            with self.assertRaises(PlanningError) as raised:
                plan_file(source, "json", out_dir=Path(directory) / "out")
            self.assertEqual(raised.exception.code, "UNKNOWN_CONTENT")


if __name__ == "__main__":
    unittest.main()
