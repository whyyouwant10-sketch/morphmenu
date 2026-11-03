# MorphMenu v0.1 Specification

**Status:** first implementation design  
**Audience:** contributors implementing the core, CLI, and later desktop integrations  
**Primary promise:** convert local files predictably, with an inspectable plan and no filesystem mutation unless the user explicitly opts in.

## 1. Product definition

MorphMenu is a local, cross-platform file-conversion utility. It detects the likely format of an input from both its content and its extension, finds a route through a registry of format-conversion capabilities, presents a deterministic output plan, and can execute that plan through approved local tools.

The product is intentionally split into:

1. **Core planning** — pure or read-only Python code for format definitions, detection, graph search, capability evaluation, output naming, and plan serialization.
2. **Execution** — a small, explicit boundary that runs an adapter only after the caller has selected execution mode.
3. **Optional external-tool adapters** — isolated command builders for tools such as ImageMagick and FFmpeg. A missing tool makes a capability unavailable; it does not make MorphMenu unusable or trigger an installation.
4. **Interfaces** — the v0.1 CLI, followed later by a Qt GUI and operating-system context-menu integrations. All interfaces use the same core plan and execution APIs.

MorphMenu does not upload files, invoke a shell, install codecs, or silently replace an input file.

## 2. User flows

### 2.1 Inspect a file

```text
$ morphmenu detect ./photo.wepb
Path:             /work/photo.wepb
Extension guess:  webp (low confidence because the extension is unusual)
Content guess:    webp (high confidence)
Selected format:  webp
Warning:          extension does not match the canonical spelling; no content change is needed
```

`detect` is read-only. It reads a bounded prefix and, when needed, a bounded amount of structural metadata. It does not invoke a converter.

### 2.2 Create a conversion plan (the default)

```text
$ morphmenu convert ./photo.png --to jpeg --out-dir ./converted
DRY RUN — no files will be written
Input:       ./photo.png (png, content confirmed)
Route:       png -> jpeg via ImageMagick
Output:      ./converted/photo.jpg
Policy:      create-only; existing outputs are blocked
Run with:    morphmenu convert ./photo.png --to jpeg --out-dir ./converted --execute
```

`convert` always produces a plan. Without `--execute`, it is a read-only operation and is safe to use in scripts for previewing work.

The equivalent explicit command is:

```text
morphmenu plan ./photo.png --to jpeg --out-dir ./converted --json
```

### 2.3 Execute an approved plan

Execution requires the explicit `--execute` flag. The CLI revalidates the input, tool capability, destination, and collision policy immediately before running. A plan generated earlier is informational; it is not an authorization token and is never executed automatically.

```text
morphmenu convert ./photo.png --to jpeg --out-dir ./converted --execute
```

The first v0.1 implementation never overwrites an existing destination. A future, separately reviewed overwrite mode may require both `--overwrite` and a confirmation; it is not part of the v0.1 contract.

### 2.4 Convert several files

The CLI accepts repeated paths. Each item gets an independent plan and result:

```text
morphmenu convert ./a.png ./b.webp --to jpeg --out-dir ./converted
```

The default is still dry-run. One unsupported or unsafe item does not cause another item to be executed. In execute mode, only items whose individual checks pass are run; the process exits non-zero if any item fails.

Shell glob expansion is allowed because the shell supplies ordinary paths. MorphMenu does not interpret a path as a command or glob internally in v0.1.

### 2.5 Future GUI flow

The GUI will use the same sequence:

1. Drop or select files.
2. Show detected content/extension formats and mismatches.
3. Select a target format and destination directory.
4. Show the complete route, tool, warnings, filenames, and collision results.
5. Let the user press **Convert** explicitly.
6. Display per-file progress, logs, and an output-folder action.

The GUI must not duplicate detection, graph search, naming, or command construction. It will call the core library, probably through an in-process Python API in the first desktop build.

### 2.6 Future right-click flow

OS integrations will pass selected paths to the CLI or a small local GUI launcher. They will open a preview plan first; a context-menu action named **Convert with MorphMenu…** must not silently convert. Platform packaging is planned as follows:

- **Windows:** an optional Explorer context-menu registration (MSIX or a documented per-user registry installer).
- **macOS:** an optional Finder Quick Action/Service that launches MorphMenu with selected paths.
- **Linux:** an optional `.desktop` action for file managers that support `Actions`, plus a documented manual command for file managers that do not.

Installers will be per-user, reversible, and separate from the converter core. No integration will require administrator/root privileges for normal conversion.

## 3. Architecture choice

### 3.1 Python core and CLI

The first implementation should use **Python 3.11 or newer**:

- `pathlib`, `dataclasses`, `subprocess`, and `typing` provide the needed portable primitives.
- A standard-library CLI based on `argparse` keeps the command usable without a GUI or a large runtime dependency.
- Python is a practical boundary for subprocess-based media tools and for later PySide6 integration.
- The core can be unit-tested without installing ImageMagick, FFmpeg, Qt, or codecs.

The GUI is an optional future package using **PySide6**. PySide6 is not a dependency of the CLI/core v0.1. A Tauri shell is possible later, but it would add a second language/runtime boundary without a current product requirement; it is not the first implementation choice.

### 3.2 Core invariants

- Planning is deterministic for a fixed input observation, format registry, and capability snapshot.
- Core planning does not spawn processes and does not write files.
- Execution receives a typed plan, never an arbitrary command string.
- External commands are passed as an argument vector with `shell=False`.
- A conversion writes to a temporary file and atomically publishes a new destination only after success.
- Inputs are never modified, removed, or renamed by v0.1.
- Dry-run is the default for every command that could lead to a write.

## 4. Module layout

The intended package layout is:

```text
morphmenu/
  __init__.py
  cli.py                    # argparse commands, output formatting, exit codes
  model.py                  # FormatId, DetectionResult, Edge, Plan, Result
  formats.py                # canonical format registry and aliases
  detect.py                 # extension hints and bounded content sniffers
  graph.py                  # immutable conversion graph and route search
  capabilities.py           # tool discovery, version/probe results, cache
  naming.py                 # safe destination-name and collision policy
  planner.py                # combines detection, graph, capability, naming
  execute.py                # explicit execution boundary and atomic publish
  adapters/
    __init__.py
    base.py                 # adapter protocol and typed command description
    imagemagick.py          # image command builder
    ffmpeg.py               # audio/video command builder
  resources/
    formats.json            # reviewable format aliases/signatures/defaults
tests/
  fixtures/
  ...
```

The adapters package is deliberately below the execution boundary. `planner.py` can ask an adapter for declared edges and a command description, but it must not run the command. The adapter protocol should return an argv list, expected output semantics, and warnings; it must never return a shell pipeline.

### 4.1 Core data model

The first implementation should make these concepts explicit:

- `FormatId`: canonical lowercase identifier such as `png`, `jpeg`, or `mp4`.
- `DetectionResult`: extension guess, content guess, selected format, confidence, bytes inspected, and mismatch/ambiguity warnings.
- `Capability`: adapter name, executable path, version, supported source/target formats, and diagnostic state.
- `ConversionEdge`: source, target, adapter, cost, lossiness, metadata policy, and prerequisites.
- `ConversionPlan`: input identity, selected route, target, output path, safety checks, warnings, and a stable JSON representation.
- `ExecutionResult`: status, output path, duration, tool diagnostics, and cleanup status.

Paths should remain `pathlib.Path` objects inside the core and be serialized only at interface boundaries. Plans should include enough information to explain a decision, but not embed file contents or secret environment variables.

## 5. Format detection

Detection uses both signals, with content taking precedence when it is conclusive:

1. Normalize the final extension as a hint using the alias table (`.jpg` and `.jpeg` both map to `jpeg`).
2. Read only the minimum bounded prefix needed by registered sniffers; do not read an entire file merely to identify it.
3. Select a content format when a signature is conclusive.
4. Report extension/content mismatch instead of hiding it.
5. Require an explicit `--from FORMAT` for unknown or ambiguous content. An extension alone is not sufficient to turn arbitrary bytes into a conversion input.

The v0.1 sniffers cover:

- PNG, JPEG, WebP, GIF, and BMP image signatures;
- WAV/RIFF, MP3 (ID3 and frame signatures), FLAC, and Ogg audio signatures;
- MP4/MOV (`ftyp`) and WebM/Matroska (EBML) container signatures;
- PDF and ZIP as recognizable but unsupported document/archive formats;
- conservative UTF-8 text detection for Markdown/HTML hints, without pretending that every text file is Markdown or HTML.

Detection must not load an image library or media decoder just to identify a file. Full decoder validation is an adapter capability and execution concern.

If content and extension disagree, the plan uses the content result when it is conclusive and emits a warning. If a user explicitly supplies `--from`, it must agree with the selected content result; the flag is for unknown/ambiguous files, not for bypassing a signature mismatch.

## 6. Format graph and route planning

The registry is a directed graph. Nodes are canonical formats; edges are conversion capabilities. An edge contains:

```text
source format(s), target format, adapter, cost, lossy flag,
metadata behavior, quality defaults, required capability, and safety notes
```

The planner filters edges by detected source, requested target, and the current capability snapshot, then chooses the lowest-cost deterministic route. Tie-breaking is stable: fewer steps, lower lossiness, adapter name, then target spelling. A plan explains every edge and why alternatives were unavailable.

The graph supports multi-step routes in its model, which allows later plugins and GUI explanations. v0.1 should execute only routes whose adapters declare safe temporary intermediates; the initial built-in routes are direct conversions. A route that requires an undeclared intermediate or an unavailable tool is rejected rather than guessed.

A plan is invalidated if the source identity changes between planning and execution. At minimum, identity includes absolute path, file size, and modification time; a content hash may be added for large-file policy or high-assurance workflows.

## 7. v0.1 supported formats and capabilities

“Recognized” means detection is available. “Convertible” means a route is available when the named optional tool is installed and passes capability checks.

| Family | Recognized | v0.1 conversion routes | Adapter | Notes |
| --- | --- | --- | --- | --- |
| Images | PNG, JPEG/JPG, WebP, GIF, BMP | PNG/JPEG/WebP between each other | ImageMagick (`magick`, with a narrowly checked legacy `convert` fallback if supported) | GIF/BMP are detection-only initially; image metadata/animation policy is explicit in the plan |
| Audio | WAV, MP3, FLAC, Ogg | WAV, MP3, and FLAC between each other | FFmpeg | Ogg is detection-only initially unless an edge is added and tested |
| Video | MP4/MOV, WebM/Matroska | MP4 and WebM between each other | FFmpeg | Encoding defaults are conservative and documented by the adapter |
| Documents | PDF, UTF-8 text/Markdown, HTML hint | none in v0.1 | none | Recognition prevents misleading “unsupported format” messages; Pandoc is a post-v0.1 adapter candidate |
| Archives | ZIP | none | none | Never unpacked automatically |

The registry must not claim that every extension pair is supported. Tool-specific codec availability, ImageMagick policy files, and FFmpeg build options can reduce the actual capability set; the CLI must show that reason.

### 7.1 External tool boundary

ImageMagick and FFmpeg are optional system capabilities, not Python package dependencies. MorphMenu:

- discovers an executable with `shutil.which` or an explicit user configuration path;
- checks its version using a fixed `--version`/`-version` argv, with no input file;
- records the executable path, version, and adapter diagnostics;
- builds an argv vector with fixed flags and validated user values;
- runs with `shell=False`, a closed stdin, a bounded stderr capture, and a configurable timeout;
- treats non-zero exit, timeout, missing output, or an output-format mismatch as failure;
- never downloads, installs, or updates a tool.

Capability detection is safe to perform during a dry-run because version probing does not touch user files. An optional cache may live in the platform user-cache directory, but stale or missing cache entries must not be treated as proof that a tool exists.

## 8. Safe output naming and filesystem policy

The default output directory is not the input directory unless the user explicitly supplies it. A future GUI may offer a clearly labeled “same folder” choice, but v0.1 still refuses an output path equal to the input path.

Given `Vacation photo (1).PNG` and target `jpeg`, the default name is:

```text
Vacation photo (1).jpg
```

The naming algorithm:

1. Starts with the source basename without its final suffix.
2. Normalizes Unicode to NFC and removes control characters.
3. Replaces path separators, NUL, trailing dots/spaces, and other platform-invalid characters with `_`.
4. Handles Windows reserved basenames (`CON`, `PRN`, `AUX`, `NUL`, `COM1`…`LPT9`) even when running on another platform.
5. Bounds the stem length while retaining a stable suffix when truncating.
6. Adds the canonical target extension.
7. Refuses an existing destination by default; a future explicit overwrite mode must be separate from normal conversion.

If the name is empty after sanitization, use `converted.<ext>`. For a collision in a create-only batch, use a deterministic suffix such as `name (1).jpg` only when that candidate is not already present; otherwise report the collision and require a user-selected policy. A collision must never cause an existing file to be replaced.

Before execution, MorphMenu verifies that:

- the input is a regular readable file;
- the output directory is the requested directory and is not created during dry-run;
- the destination is not the input, an existing symlink, or a path that escapes the requested output directory;
- the destination does not exist under create-only policy;
- enough temporary space is available when the adapter can estimate it.

To avoid time-of-check/time-of-use races, execution writes a uniquely named temporary file in the destination directory, validates it, and uses an atomic no-replace publish operation where the platform supports it. Temporary files are removed on failure or cancellation.

## 9. CLI contract

The v0.1 command set is:

```text
morphmenu detect PATH [--json]
morphmenu formats [--available] [--json]
morphmenu plan PATH... --to FORMAT [--from FORMAT] [--out-dir DIR] [--json]
morphmenu convert PATH... --to FORMAT [--from FORMAT] [--out-dir DIR]
                     [--execute] [--metadata strip|preserve] [--json]
```

Important behavior:

- `convert` without `--execute` is a dry-run, including when several inputs are supplied.
- `--json` emits a versioned machine-readable envelope containing plans/results and diagnostics; it must not mix human progress text into stdout.
- Human-readable diagnostics go to stderr when JSON is selected.
- `--from` only resolves an unknown/ambiguous input; it cannot override a conclusive conflicting signature.
- Unsupported formats, unavailable tools, unsafe paths, and collisions have distinct diagnostic codes.
- Exit code `0` means all requested operations succeeded or a dry-run produced valid plans. Non-zero means at least one requested item could not be planned or executed. The exact code table should be frozen with the CLI tests.

There is no `--shell`, arbitrary command template, automatic overwrite, delete, in-place conversion, network URL input, or recursive directory traversal in v0.1.

## 10. Security and safety

### 10.1 Default behavior

All write-capable operations are dry-run by default. MorphMenu does not delete, overwrite, rename, or modify inputs. A user must explicitly provide `--execute` for each invocation. Dry-run must not create an output directory, temporary file, or stateful lock.

### 10.2 Process isolation boundary

External programs are treated as untrusted converters:

- use argv arrays and `shell=False`; never concatenate a command line;
- pass only a minimal environment and do not forward secrets unnecessarily;
- set `cwd` to a controlled temporary directory;
- close stdin, set timeouts, limit captured log size, and clean up children on cancellation;
- run with the invoking user's privileges, never as root/Administrator;
- never ask a converter to execute metadata, scripts, macros, or embedded commands;
- cap input size and temporary disk use with configurable limits;
- do not follow output symlinks and do not write outside the selected destination directory.

Image and media files are treated as hostile inputs. Parser crashes or tool failures must become ordinary conversion errors with cleanup, not a reason to retry with looser flags. Archive files are not unpacked in v0.1.

### 10.3 Privacy

The default metadata policy is `strip` where the adapter can implement it reliably. The plan states the policy and any adapter-specific exception. `--metadata preserve` is explicit and may be unavailable for a given route. No telemetry or network access is part of the product.

## 11. Acceptance criteria for v0.1

The implementation is ready for a v0.1 release when all of the following are true:

1. A clean Python environment can run `detect`, `formats`, and dry-run `convert` without ImageMagick, FFmpeg, Qt, or network access.
2. Detection reports extension and content independently, handles common aliases, and surfaces a deliberate mismatch.
3. The planner represents conversion routes as graph edges and produces a stable, explainable route or a specific unavailable-capability error.
4. A dry-run leaves a temporary test directory byte-for-byte unchanged, including when the output directory does not exist yet.
5. Safe naming handles Unicode, control characters, separators, Windows reserved names, long names, collisions, and an input/output path collision on Linux, macOS, and Windows path semantics.
6. With a supported ImageMagick or FFmpeg installation, an explicit `--execute` creates the expected output through a temporary file and leaves the input unchanged.
7. Existing outputs, symlinks, tool timeouts, non-zero tool exits, missing outputs, and cancellation produce cleanup and actionable diagnostics.
8. JSON output is versioned and stable enough for a future GUI and shell integration.
9. The same core plan API can be called without importing PySide6 or starting a GUI.
10. The test suite can run entirely without external tools; adapter integration tests are separately marked and report skipped capability requirements honestly.

## 12. Fixture and test strategy

Fixtures should be small, deterministic, and checked into `tests/fixtures/` only when their licensing is clear. Prefer generated fixtures with a manifest over large media files:

- minimal valid PNG, JPEG, WebP, WAV, FLAC, MP3-header, MP4-container, and WebM-container samples where practical;
- representative extension aliases and mismatches, including a valid PNG named `.jpg`;
- unknown bytes, ambiguous UTF-8 text, truncated signatures, and zero-byte input;
- filenames containing Unicode, control characters, separators, trailing dots/spaces, Windows reserved names, long stems, and collisions;
- a symlink fixture where the platform supports it, with a platform-conditional test;
- capability snapshots for missing tools, acceptable versions, malformed version output, and incompatible tool builds.

Each binary fixture should have a size and SHA-256 manifest entry. Generated fixtures must use fixed bytes and be validated by a format-aware parser, not merely by an extension.

Tests should be layered:

1. Pure unit tests for aliases, sniffers, graph ordering, naming, and plan serialization.
2. Filesystem tests in a fresh temporary directory for dry-run and atomic publish behavior.
3. Mocked adapter tests that assert exact argv arrays and reject shell metacharacters in paths.
4. Optional external-tool tests, gated by a clearly documented marker such as `MORPHMENU_RUN_EXTERNAL=1`, recording tool versions and never serving as the only coverage.
5. CLI subprocess tests for exit codes, human output, JSON output, and batch isolation.

Tests must not write into the repository's source tree, require network access, or depend on a user's installed GUI.

## 13. Honest v0.1 scope

### Included

- Python core library and a CLI.
- Content-plus-extension detection for the listed common formats.
- A reviewable directed format graph and deterministic route planning.
- Optional ImageMagick image routes and FFmpeg audio/video routes.
- Safe create-only output naming, collision handling, atomic publication, and dry-run-by-default behavior.
- Versioned human and JSON plan output.
- Unit, filesystem, CLI, and mocked-adapter tests, with optional external integration tests.

### Explicitly deferred

- GUI implementation, drag-and-drop, progress windows, and system notifications.
- Windows/macOS/Linux context-menu installers and packaging.
- Automatic tool installation, codec downloads, cloud providers, URLs, watch folders, and background services.
- Recursive directory conversion and archive unpacking.
- In-place conversion, deletion, overwrite mode, and destructive batch cleanup.
- OCR, document rendering, PDF generation, subtitles, animation-preserving image conversion, and advanced codec/quality UI.
- A general plugin marketplace or arbitrary user-provided command templates.

These boundaries keep the first implementation useful while preserving a stable core for the future GUI and right-click integrations.

## 14. Implementation order

1. Freeze the format aliases, signatures, model types, and JSON schema version.
2. Implement read-only detection and safe naming with tests.
3. Implement the graph and planner against synthetic capabilities; verify deterministic plans without external tools.
4. Implement capability discovery and mocked ImageMagick/FFmpeg command builders.
5. Implement the explicit execution boundary, temporary output, atomic publish, cleanup, and CLI.
6. Add optional external-tool integration tests and package the CLI for the three target desktop platforms.
7. Build the GUI and OS integrations as thin consumers of the same plan/execution API only after the CLI contract is stable.
