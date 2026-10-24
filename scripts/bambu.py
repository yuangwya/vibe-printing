"""Build, slice, and open a model using a configurable Bambu Studio profile."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from build import build_one
from validate import select_models

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("machine", "process", "filament")


def read_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def load_config(path):
    config = read_json(path)
    app = config["bambu_studio"]
    for key in ("executable", "profiles_directory"):
        value = Path(app[key]).expanduser()
        app[key] = str((value if value.is_absolute() else path.parent / value).resolve())
    if not Path(app["executable"]).is_file():
        raise ValueError("Bambu Studio executable not found; update bambu_studio.executable in the config")
    if not Path(app["profiles_directory"]).is_dir():
        raise ValueError("Preset directory not found; update bambu_studio.profiles_directory in the config")
    command = app["open_command"]
    if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
        raise ValueError("open_command must be a nonempty array of command arguments")
    if sum(arg.count("{file}") for arg in command) != 1:
        raise ValueError("open_command must contain exactly one {file} placeholder")
    if type(config["open_after_slice"]) is not bool:
        raise ValueError("open_after_slice must be true or false")
    timeout = config["slice_timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("slice_timeout_seconds must be a finite positive number")
    if not isinstance(config["bed_type"], str) or not config["bed_type"]:
        raise ValueError("bed_type must be a nonempty string")
    cost = config["material_cost"]
    price = cost["price_per_kg"]
    if price is not None and (type(price) not in (int, float) or not math.isfinite(price) or price < 0):
        raise ValueError("price_per_kg must be null or a finite nonnegative number")
    if not isinstance(cost["currency"], str) or not cost["currency"]:
        raise ValueError("currency must be a nonempty string")
    for kind in KINDS:
        if not isinstance(config["presets"][kind], str) or not config["presets"][kind]:
            raise ValueError(f"presets.{kind} must be a nonempty name")
        overrides = config["overrides"][kind]
        if not isinstance(overrides, dict) or {"inherits", "include", "type", "name"} & overrides.keys():
            raise ValueError(f"Invalid overrides.{kind}; preset metadata cannot be overridden")
        for value in overrides.values():
            if not (isinstance(value, str) or isinstance(value, list) and value and all(isinstance(v, str) for v in value)):
                raise ValueError(f"overrides.{kind} values must be strings or arrays of strings")
    return config


def resolve_preset(directory, kind, name, stack=()):
    """Expand installed preset inheritance and include templates for the CLI."""
    if name in stack:
        raise ValueError(f"Preset inheritance cycle: {' -> '.join((*stack, name))}")
    # Match stems rather than treating preset names as arbitrary file paths.
    matches = [p for p in (directory / kind).rglob("*.json") if p.stem == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind} preset named {name!r}; found {len(matches)} in {directory}")
    data = read_json(matches[0])
    result = {}
    if data.get("inherits"):
        result.update(resolve_preset(directory, kind, data["inherits"], (*stack, name)))
    for include in data.get("include", []):
        result.update(resolve_preset(directory, kind, include, (*stack, name)))
    result.update({key: value for key, value in data.items() if key not in ("inherits", "include")})
    return result


def prepare_presets(config):
    directory = Path(config["bambu_studio"]["profiles_directory"])
    resolved = {}
    for kind in KINDS:
        resolved[kind] = resolve_preset(directory, kind, config["presets"][kind])
        resolved[kind].update(config["overrides"][kind])
    machine_name = config["presets"]["machine"]
    for kind in ("process", "filament"):
        compatible = resolved[kind].get("compatible_printers", [])
        if compatible and machine_name not in compatible:
            raise ValueError(f"The {kind} preset is not compatible with {machine_name}")
    return resolved


def summarize(project):
    with ZipFile(project) as archive:
        # Require both cached toolpaths and a real positive estimate.
        gcode = [name for name in archive.namelist() if name.endswith(".gcode")]
        if not gcode or not all(archive.getinfo(name).file_size > 0 for name in gcode):
            raise ValueError("The exported project contains no sliced toolpaths")
        plate = ET.fromstring(archive.read("Metadata/slice_info.config")).find("plate")
        if plate is None:
            raise ValueError("No plate found in the sliced project")
        metadata = {item.get("key"): item.get("value") for item in plate.findall("metadata")}
        seconds, grams = int(metadata["prediction"]), float(metadata["weight"])
        if seconds <= 0 or not math.isfinite(grams) or grams <= 0 or metadata.get("outside") != "false":
            raise ValueError("The sliced model has invalid estimates or is outside the build area")
        return {"estimated_total_seconds": seconds, "filament_g": grams,
                "support_used": metadata.get("support_used") == "true"}


def slice_model(output, config, presets):
    log_path = output / "slice.log"
    # Run in a staging directory: a failed slice never opens an older project.
    with tempfile.TemporaryDirectory(prefix=".bambu-", dir=output) as temporary:
        stage = Path(temporary)
        for kind, data in presets.items():
            (stage / f"{kind}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        project = stage / "model.3mf"
        command = [
            config["bambu_studio"]["executable"], "--datadir", str(stage / "settings"),
            "--load-settings", f"{stage / 'machine.json'};{stage / 'process.json'}",
            "--load-filaments", str(stage / "filament.json"),
            "--curr-bed-type", config["bed_type"], "--arrange", "1",
            "--slice", "0", "--debug", "2", "--outputdir", str(stage),
            "--export-3mf", project.name, str(output / "model.stl"),
        ]
        print("[SLICE] Running Bambu Studio with the configured presets...", flush=True)
        with log_path.open("w", encoding="utf-8") as log:
            try:
                subprocess.run(command, cwd=stage, stdout=log, stderr=subprocess.STDOUT,
                               timeout=config["slice_timeout_seconds"], check=True)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"Bambu Studio failed with exit code {exc.returncode}; see {log_path}") from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"Bambu Studio exceeded the configured timeout; see {log_path}") from exc
        summary = summarize(project)
        log = log_path.read_text(encoding="utf-8", errors="replace")
        summary["cli_diagnostics"] = [line for line in log.splitlines() if "[error]" in line or "[warning]" in line]
        summary["presets"] = config["presets"]
        summary["bed_type"] = config["bed_type"]
        summary["overrides"] = config["overrides"]
        summary["stl_sha256"] = hashlib.sha256((output / "model.stl").read_bytes()).hexdigest()
        price = config["material_cost"]["price_per_kg"]
        if price is not None:
            summary["estimated_material_cost"] = summary["filament_g"] / 1000 * price
            summary["currency"] = config["material_cost"]["currency"]
        (stage / "slice-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        # Keep expanded presets alongside the project for reproducibility.
        profile_dir = output / "slicer-profiles"
        profile_dir.mkdir(exist_ok=True)
        for kind in KINDS:
            shutil.copyfile(stage / f"{kind}.json", profile_dir / f"{kind}.json")
        project.replace(output / "model.3mf")
        (stage / "slice-summary.json").replace(output / "slice-summary.json")
    minutes, seconds = divmod(summary["estimated_total_seconds"], 60)
    print(f"[SLICED] {summary['filament_g']:.2f} g; estimated total time {minutes}m {seconds}s", flush=True)
    if price is not None:
        print(f"[COST] Material only: {summary['estimated_material_cost']:.2f} {summary['currency']}", flush=True)
    if summary["cli_diagnostics"]:
        print(f"[NOTE] CLI diagnostics were saved to {log_path}. Review the project before printing.", flush=True)
    return output / "model.3mf"


def open_project(path, config):
    command = [part.replace("{file}", str(path)) for part in config["bambu_studio"]["open_command"]]
    subprocess.run(command, check=True)
    print(f"[OPEN] Sent to Bambu Studio: {path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Build, slice, and open a model in Bambu Studio")
    parser.add_argument("model", help="Model directory name, for example phone-stand")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/printer.json", help="Printer configuration JSON")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--slice-only", action="store_true", help="Build and slice without opening the GUI")
    mode.add_argument("--import-only", action="store_true", help="Build and open the STL for slicing in the GUI")
    args = parser.parse_args()
    try:
        config = load_config(args.config.expanduser().resolve())
        path = select_models([args.model])[0]
        presets = None if args.import_only else prepare_presets(config)
        output = build_one(path)
        if args.import_only:
            open_project(output / "model.stl", config)
        else:
            project = slice_model(output, config, presets)
            if not args.slice_only and config["open_after_slice"]:
                open_project(project, config)
    except Exception as exc:
        parser.exit(1, f"[FAIL] {exc}\nCheck the printer config and the model's exports/slice.log if present.\n")
    except KeyboardInterrupt:
        parser.exit(130, "\n[STOP] Workflow interrupted.\n")


if __name__ == "__main__":
    main()
