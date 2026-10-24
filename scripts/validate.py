"""Validate source model solids. Run from any working directory."""

import argparse
import importlib.util
from pathlib import Path

import cadquery as cq

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def select_models(names: list[str]) -> list[Path]:
    available = {path.parent.name: path for path in sorted(MODELS_DIR.glob("*/model.py"))}
    unknown = set(names) - available.keys()
    if unknown:
        raise ValueError(f"Unknown models: {', '.join(sorted(unknown))}")
    paths = [available[name] for name in dict.fromkeys(names)] if names else list(available.values())
    if not paths:
        raise ValueError("No model.py files found under models/")
    return paths


def load_model(path: Path) -> cq.Workplane:
    spec = importlib.util.spec_from_file_location(f"model_{path.parent.name.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # Read source directly so rapid saves never reuse timestamp-based bytecode.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module.build_model()


def validate_model(model: cq.Workplane) -> str:
    if not isinstance(model, cq.Workplane):
        raise ValueError("build_model() must return cq.Workplane")
    shapes = model.vals()
    if len(shapes) != 1 or not isinstance(shapes[0], cq.Shape):
        raise ValueError("The model must contain exactly one shape")
    shape = shapes[0]
    solids = shape.Solids()
    if not shape.isValid() or len(solids) != 1:
        raise ValueError("The model must be a valid single solid")
    if not solids[0].isValid() or solids[0].Volume() <= 0:
        raise ValueError("The solid is invalid or its volume is not positive")
    box = shape.BoundingBox()
    return (
        f"Dimensions: {box.xlen:.2f} × {box.ylen:.2f} × {box.zlen:.2f} mm, "
        f"volume: {shape.Volume():.2f} mm³"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CadQuery source models; check all models by default")
    parser.add_argument("models", nargs="*", help="Model directory names, for example phone-stand")
    args = parser.parse_args()
    try:
        paths = select_models(args.models)
    except ValueError as exc:
        parser.error(str(exc))
    failed = False
    for path in paths:
        try:
            print(f"[PASS] {path.parent.name}: {validate_model(load_model(path))}")
        except Exception as exc:
            failed = True
            print(f"[FAIL] {path.parent.name}: {exc}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
