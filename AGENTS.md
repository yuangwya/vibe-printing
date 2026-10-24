# vibe-printing modeling guidelines

- Use Python 3.11+ and CadQuery. All dimensions are in millimeters (mm).
- Keep repository documentation, comments, docstrings, and script messages in English.
- Store each model in `models/<name>/model.py`. Use lowercase directory names with hyphens.
- Define dimensions at the top of the file and provide `build_model() -> cq.Workplane` with no required arguments.
- Return one connected solid by default, with its bottom at Z=0 and the XY plane as its print base.
- Importing a model file must not export files, open windows, or trigger other side effects.
- Generate STEP and STL files in each model's `exports/` directory with `scripts/build.py`. Do not edit exports manually.
- After modifying a model, validate its geometry and update the existing live preview. Export files only when requested or when entering an explicitly authorized print-preparation stage.
- Validate parameter ranges. Avoid zero thickness, negative dimensions, self-intersections, and disconnected solids. Choose wall thickness and clearances for the intended printing process.
- Geometry validation does not replace slicing checks. Do not claim production readiness without physical print validation.
- Keep the project simple. Do not add web services, databases, or complex build frameworks unless requested.

## Design and print-preparation workflow

- Default to the design stage. Requests to change dimensions, structure, lettering, fillets, or appearance remain design work unless the user explicitly authorizes print preparation.
- During design, edit the source, perform the geometry checks relevant to the change, and use `python scripts/preview.py <name> --watch`. Reuse the existing preview process and viewer instead of starting duplicate servers or opening more windows. Let the watcher refresh the model after saves.
- A successful live preview already validates the model. Do not repeat equivalent validation runs, exports, or tests without a new change, failure, or unresolved concern that warrants them.
- Do not run `scripts/build.py`, slice models, run `scripts/bambu.py`, or import/open models in Bambu Studio as a routine part of design iteration. Do not repeatedly slice solely to verify visual changes.
- Enter print preparation only after an explicit user instruction, such as approving the design for printing or directly requesting export, slicing, or import into Bambu Studio. A request to add or configure workflow commands does not by itself authorize running them on a model.
- A narrow request authorizes only the requested operation: an export request does not authorize slicing or opening Bambu Studio; a slicing request does not authorize opening the application or sending a print job. Use `--slice-only` when only slicing is requested. Do not treat earlier print-preparation work as blanket authorization for later design revisions.
- Once print preparation is authorized for the current revision, use `configs/printer.json` or the user's selected configuration. Build once, slice once if requested, and open Bambu Studio only if requested. Reuse current artifacts when their source and configuration have not changed; rebuild only stale outputs.
- Sending a job to a physical printer requires a separate explicit user instruction. Design approval, export, slicing, and opening a project do not authorize starting a print.
- Keep design updates focused on what changed and the preview. Do not claim STEP/STL exports or slicing estimates are current when they belong to an earlier revision.

## Task notifications

- Send a notification only when the user explicitly requests one for the current task. Use Bark by default; use email only when explicitly requested.
- Send once at task completion with an accurate outcome. Do not send progress or test notifications.
- If configuration is missing, explain what is missing rather than switching channels. Never include secrets or private customer information.
