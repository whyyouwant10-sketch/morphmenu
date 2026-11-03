# MorphMenu test report

**Date:** 2026-11-04
**Environment:** Debian Linux container, CPython 3.11.2
**Scope:** release-asset and clean-install verification for the existing v0.1 implementation

## Full test suite from the source checkout

Command:

```console
PYTHONPATH=src python -m unittest discover -s tests -v
```

Result: **PASS** — 11 tests ran and all passed in 0.199 seconds.

The suite covers detection, naming, dry-run filesystem behavior, structured
text conversion, optional capability reporting, and CLI JSON output.

## Clean-install smoke

Commands:

```console
rm -rf /tmp/opencode/morphmenu-clean-install
python -m venv /tmp/opencode/morphmenu-clean-install
/tmp/opencode/morphmenu-clean-install/bin/python -m pip install --no-deps .
mkdir -p /tmp/opencode/morphmenu-smoke
printf '{"name": "Ada"}\n' >/tmp/opencode/morphmenu-smoke/data.json
/tmp/opencode/morphmenu-clean-install/bin/morphmenu convert /tmp/opencode/morphmenu-smoke/data.json --to yaml --out-dir /tmp/opencode/morphmenu-smoke/out
/tmp/opencode/morphmenu-clean-install/bin/morphmenu convert /tmp/opencode/morphmenu-smoke/data.json --to yaml --out-dir /tmp/opencode/morphmenu-smoke/out --execute
/tmp/opencode/morphmenu-clean-install/bin/morphmenu --help
/tmp/opencode/morphmenu-clean-install/bin/morphmenu formats --available
```

Result: **PASS**.

- The package installed into a fresh virtual environment with `--no-deps`.
- The installed CLI printed its help successfully.
- The dry run left the output directory absent until the explicit execute
  command.
- Explicit execution created `data.yaml` containing `name: "Ada"`.
- The installed CLI reported ImageMagick and FFmpeg as unavailable in this
  environment, which is expected for optional external capabilities.
- The package build emitted setuptools' existing deprecation warning for the
  table form of `project.license`; it did not affect installation or execution.

The same installed environment was also used for the full test command:

```console
/tmp/opencode/morphmenu-clean-install/bin/python -m unittest discover -s tests -v
```

Result: **PASS** — 11 tests ran and all passed in 0.101 seconds.

## Not run

- Windows CI was not run locally; `.github/workflows/ci.yml` covers Windows
  and Ubuntu with Python 3.11, 3.12, and 3.13.
- ImageMagick and FFmpeg integration conversion was not run because neither
  optional executable was available in the test environment.
