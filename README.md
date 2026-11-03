# MorphMenu

> **Early development — v0.1.** The command-line core is usable, but the
> format and adapter surface is intentionally small and may evolve.

MorphMenu is a local file-conversion planner with a safe, inspectable plan. It
detects files from content and extension, and `convert` is a dry run unless
`--execute` is explicitly supplied. Inputs are never overwritten or modified.

## Quick start

```console
python -m pip install .
morphmenu detect example.json
morphmenu convert example.json --to yaml --out-dir converted
morphmenu convert example.json --to yaml --out-dir converted --execute
```

The first `convert` command only prints a plan. The second explicitly writes a
new output file. The default output policy is create-only; an existing output
is never overwritten.

## Supported conversions

Recognition and conversion are separate. A recognized format can be detected
without having a conversion route. Optional routes are available only when the
named executable is installed and discoverable on `PATH`.

| Family | Recognized formats | Conversion routes in v0.1 | Adapter |
| --- | --- | --- | --- |
| Text and structured data | UTF-8 text, Markdown, JSON, YAML, CSV | Any pair among text, Markdown, JSON, YAML, and CSV | Built-in |
| Images | PNG, JPEG/JPG, WebP, GIF, BMP | PNG, JPEG, and WebP between each other; GIF/BMP are detection-only | ImageMagick (`magick` or `convert`) |
| Audio | WAV, MP3, FLAC, Ogg | WAV, MP3, and FLAC between each other; Ogg is detection-only | FFmpeg |
| Video | MP4/MOV, WebM/Matroska | MP4 and WebM between each other | FFmpeg |
| Documents | PDF and HTML hints | None | None |
| Archives | ZIP | None; archives are not unpacked | None |

Tool availability, codec support, and ImageMagick policy files can reduce the
routes available on a particular machine. Use `morphmenu formats --available`
to inspect the optional tool capabilities reported by the local installation.

## Example output

This is the output from a real dry-run of the built-in JSON-to-YAML route (the
destination directory is intentionally not created):

```console
$ printf '{"name": "Ada"}\n' > /tmp/opencode/morphmenu-example.json
$ morphmenu convert /tmp/opencode/morphmenu-example.json --to yaml --out-dir /tmp/opencode/morphmenu-output
DRY RUN — no files will be written
Input:  /tmp/opencode/morphmenu-example.json (json)
Route:  json -> yaml via builtin
Output: /tmp/opencode/morphmenu-output/morphmenu-example.yaml
Policy: create-only; existing outputs are never overwritten
```

## Current limitations

- There is no GUI, drag-and-drop flow, or operating-system right-click
  integration in v0.1.
- ImageMagick and FFmpeg are optional external tools; MorphMenu does not
  install codecs or tools for you.
- There is no overwrite mode, in-place conversion, deletion, recursive
  directory traversal, archive unpacking, network input, or cloud service.
- PDF, HTML, ZIP, GIF, BMP, Ogg, MOV, and Matroska recognition does not imply a
  conversion route.
- Text and structured-data conversion uses the small built-in parser/serializer;
  formatting, comments, and format-specific metadata are not preserved in
  general.

See [`docs/SPEC.md`](docs/SPEC.md) for the design contract and deferred scope.
Contributors can find the local setup and checks in
[`CONTRIBUTING.md`](CONTRIBUTING.md).
