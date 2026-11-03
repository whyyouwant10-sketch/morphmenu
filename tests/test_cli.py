from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
        return subprocess.run(
            [sys.executable, "-m", "morphmenu", *arguments],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_json_plan_is_machine_readable_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data.json"
            out = root / "out"
            source.write_text('{"ok": true}\n', encoding="utf-8")
            completed = self.run_cli("convert", str(source), "--to", "yaml", "--out-dir", str(out), "--json")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["plans"][0]["status"], "ready")
            self.assertFalse(out.exists())

    def test_missing_capability_does_not_run_converter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "picture.png"
            out = root / "out"
            source.write_bytes(b"\x89PNG\r\n\x1a\n")
            completed = self.run_cli("convert", str(source), "--to", "jpeg", "--out-dir", str(out), "--json")
            payload = json.loads(completed.stdout)
            # This environment intentionally has no ImageMagick. If a runner has
            # it installed, the plan is still a dry run and no output is written.
            self.assertFalse(out.exists())
            if payload["plans"][0]["status"] == "unavailable_capability":
                self.assertEqual(payload["errors"][0]["code"], "UNAVAILABLE_CAPABILITY")


if __name__ == "__main__":
    unittest.main()
