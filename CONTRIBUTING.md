# Contributing to MorphMenu

MorphMenu is in early development. Contributions should preserve the existing
dry-run-first behavior, the create-only output policy, and the small standard-
library-first core.

## Development setup

MorphMenu requires Python 3.11 or newer. A virtual environment keeps local
tools isolated:

```console
python -m venv .venv
```

Activate it using the command for your shell, then install the package:

```console
python -m pip install --upgrade pip
python -m pip install -e .
```

ImageMagick and FFmpeg are optional system capabilities for image, audio, and
video routes. They are not Python dependencies and are not installed by
MorphMenu.

## Checks

Run the full test suite from the repository root:

```console
python -m unittest discover -s tests -v
```

The tests do not require external media tools. The CI workflow exercises
Python 3.11, 3.12, and 3.13 on Ubuntu and Windows.

For a quick installed-command check:

```console
morphmenu --help
morphmenu formats --available
```

## Change guidelines

- Keep planning read-only; writes require explicit `--execute`.
- Do not overwrite, delete, or modify input files.
- Keep external commands as argument lists with `shell=False`.
- Add or update tests for behavior changes.
- Update the README or `docs/` when user-visible behavior or supported routes
  change.
- Use focused commits with a conventional prefix such as `fix:`, `feat:`,
  `docs:`, or `test:`.

Please describe the behavior you changed, the checks you ran, and any
optional-tool assumptions in pull requests.
