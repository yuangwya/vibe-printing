"""Build and validate models, then export STEP and STL files."""

import argparse

import cadquery as cq

from validate import load_model, select_models, validate_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Export STEP and STL files; build all models by default")
    parser.add_argument("models", nargs="*", help="Model directory names, for example phone-stand")
    args = parser.parse_args()
    try:
        paths = select_models(args.models)
    except ValueError as exc:
        parser.error(str(exc))
    failed = False
    for path in paths:
        try:
            model = load_model(path)
            summary = validate_model(model)
            output = path.parent / "exports"
            output.mkdir(exist_ok=True)
            cq.exporters.export(model, str(output / "model.step"))
            cq.exporters.export(
                model, str(output / "model.stl"),
                tolerance=0.1, angularTolerance=0.1,
            )
            print(f"[DONE] {path.parent.name}: {summary}\n       {output}")
        except Exception as exc:
            failed = True
            print(f"[FAIL] {path.parent.name}: {exc}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
