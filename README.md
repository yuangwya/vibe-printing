# Vibe Printing

A lightweight Python + CadQuery workspace for designing parametric 3D prints,
previewing changes live, and preparing approved models in Bambu Studio.
All dimensions are in millimeters. Repository content is maintained in English.

## Setup

Use Python 3.11+ (3.12 recommended):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-preview.txt
```

On Windows, activate with `.venv\Scripts\activate.bat` (Command Prompt) or
`.venv\Scripts\Activate.ps1` (PowerShell). `requirements.txt` alone is sufficient
for modeling and exports without the optional preview tools.

## Design: preview first

```bash
python scripts/preview.py phone-stand --watch
```

The command opens a local viewer at `http://127.0.0.1:3939`. Edit
`models/phone-stand/model.py` and save to refresh it. Invalid edits are reported
in the terminal while the last valid model remains visible. The watcher monitors
the selected `model.py`; restart after changing imported helper files.

Reuse the existing viewer during design. Previewing validates geometry without
exporting or slicing. Enter print preparation only after explicit user approval;
see [AGENTS.md](AGENTS.md) for the full workflow rules.

For an existing VS Code OCP CAD Viewer, add `--vscode`. Other preview options
include `--port 3940` and `--no-browser`. Press Ctrl+C to stop.

## Print preparation: when requested

Bambu Studio must be installed and [configs/printer.json](configs/printer.json)
configured for your machine. Run only the operation the user requested:

| Task | Command |
| --- | --- |
| Validate geometry only | `python scripts/validate.py phone-stand` |
| Export STEP and STL | `python scripts/build.py phone-stand` |
| Build and slice without opening Studio | `python scripts/bambu.py phone-stand --slice-only` |
| Build and import STL for manual slicing | `python scripts/bambu.py phone-stand --import-only` |
| Build, slice, and open the 3MF project | `python scripts/bambu.py phone-stand` |

The workflow never starts a physical print. Open the 3MF as a project to retain
its settings. Generated files live in `models/<name>/exports/` and are ignored
by Git: STEP, STL, sliced 3MF, `slice-summary.json`, `slice.log`, and expanded
presets in `slicer-profiles/`. Failed slices do not open an older project.

### Printer configuration

Machine choices are configured in JSON, not hardcoded in the scripts. The
included configuration uses **X2D / 0.4 mm nozzle / PLA Basic / 0.20 mm layers /
15% infill / two walls / Textured PEI Plate**, with supports disabled.

Edit `configs/printer.json` to set application paths and the opening command,
compatible machine/process/filament preset names, bed type, overrides, slicing
timeout, and whether to open Studio after slicing. Set
`material_cost.price_per_kg` and `currency` to include a material-cost estimate;
leave the price `null` to omit it.

Override values use Bambu's preset format: strings such as
`"layer_height": "0.2"` and `"enable_support": "1"`, or arrays of strings for
filament/extruder settings. The included application paths target macOS; update
them for your installation. Relative executable and preset-directory paths
resolve from the configuration file's directory. `open_command` is an argument
array containing one `{file}` placeholder.

Copy the configuration for another setup and select it with:

```bash
python scripts/bambu.py phone-stand --config configs/another-printer.json
```

## Included model

The phone stand is a lightweight frame with a 65° backrest, rear brace, rounded
contact edges, an integrated front lip, and **Made by WYA** lettering. It supports
centered portrait and landscape placement, with 16 mm phone/case clearance.
Overall dimensions are approximately **90 × 100.6 × 84.2 mm**.

The recorded X2D standard-preset estimate is **38.96 g** and **1 h 10 min 15 s**,
including preparation. These are estimates, not measured print results or a
strength guarantee. Settings and comparison details are in
[print-estimate.json](models/phone-stand/print-estimate.json).
Review slicing diagnostics and the layer preview, then test the physical fit,
stability, and strength. The bundled start/end sequence has emitted CLI
`Invalid T command` diagnostics; retain and review `exports/slice.log`.

## Repository layout and extension

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Modeling conventions and design/print workflow rules |
| `configs/printer.json` | Machine, material, slicing, and application configuration |
| `models/<name>/model.py` | Parametric model source |
| `models/<name>/exports/` | Regenerable geometry and slicing outputs |
| `scripts/preview.py` | Browser or VS Code preview with optional live reload |
| `scripts/validate.py` | Valid single-solid and positive-volume checks |
| `scripts/build.py` | STEP/STL export |
| `scripts/bambu.py` | Configurable build, slice, and Studio import workflow |
| `tests/` | Workflow regression checks |

Add `models/<lowercase-name>/model.py` with a parameterized
`build_model() -> cq.Workplane` function requiring no arguments. Return one
connected solid with its bottom at Z=0. Importing the file must have no side
effects. Models are discovered automatically; `build.py` and `validate.py`
accept multiple names or process all models when none are given.

```bash
python -m unittest discover -s tests -v
```
