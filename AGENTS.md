# vibe-printing modeling guidelines

- Use Python 3.11+ and CadQuery. All dimensions are in millimeters (mm).
- Keep repository documentation, comments, docstrings, and script messages in English.
- Store each model in `models/<name>/model.py`. Use lowercase directory names with hyphens.
- Define dimensions at the top of the file and provide `build_model() -> cq.Workplane` with no required arguments.
- Return one connected solid by default, with its bottom at Z=0 and the XY plane as its print base.
- Importing a model file must not export files, open windows, or trigger other side effects.
- Generate STEP and STL files in each model's `exports/` directory with `scripts/build.py`. Do not edit exports manually.
- After modifying a model, run `python scripts/validate.py <name>` and `python scripts/build.py <name>`.
- Validate parameter ranges. Avoid zero thickness, negative dimensions, self-intersections, and disconnected solids. Choose wall thickness and clearances for the intended printing process.
- Geometry validation does not replace slicing checks. Do not claim production readiness without physical print validation.
- Keep the project simple. Do not add web services, databases, or complex build frameworks unless requested.

## Task notifications

- Send a notification only when the user explicitly requests one for the current task. Use Bark by default; use email only when explicitly requested.
- Send once at task completion with an accurate outcome. Do not send progress or test notifications.
- If configuration is missing, explain what is missing rather than switching channels. Never include secrets or private customer information.
