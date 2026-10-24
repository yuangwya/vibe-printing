"""Regression checks for configurable slicing and failed-job handling."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bambu


class BambuWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        for kind in bambu.KINDS:
            (self.directory / kind).mkdir()

    def preset(self, kind, name, data):
        (self.directory / kind / f"{name}.json").write_text(json.dumps(data))

    def config(self):
        config = json.loads((ROOT / "configs/printer.json").read_text())
        (self.directory / "slicer").touch()
        config["bambu_studio"].update({
            "executable": "slicer", "profiles_directory": ".",
            "open_command": ["viewer", "{file}"],
        })
        path = self.directory / "printer.json"
        path.write_text(json.dumps(config))
        return path

    def test_inheritance_and_include_precedence(self):
        self.preset("machine", "base", {"speed": "100", "gcode": "base"})
        self.preset("machine", "template", {"gcode": "template", "temperature": "200"})
        self.preset("machine", "custom", {"inherits": "base", "include": ["template"], "speed": "200"})
        result = bambu.resolve_preset(self.directory, "machine", "custom")
        self.assertEqual(result, {"speed": "200", "gcode": "template", "temperature": "200"})

    def test_cycle_fails_with_a_useful_error(self):
        self.preset("process", "a", {"inherits": "b"})
        self.preset("process", "b", {"inherits": "a"})
        with self.assertRaisesRegex(ValueError, "inheritance cycle"):
            bambu.resolve_preset(self.directory, "process", "a")

    def test_missing_preset_does_not_fall_back_to_another_machine(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            bambu.resolve_preset(self.directory, "machine", "unknown")

    def test_config_paths_are_relative_to_config_not_working_directory(self):
        config = bambu.load_config(self.config())
        self.assertEqual(config["bambu_studio"]["executable"], str((self.directory / "slicer").resolve()))
        self.assertEqual(config["bambu_studio"]["profiles_directory"], str(self.directory.resolve()))

    def test_invalid_price_and_override_types_are_rejected(self):
        for changes in [
            {"material_cost": {"price_per_kg": -1, "currency": "CNY"}},
            {"overrides": {"machine": {}, "process": {"layer_height": 0.2}, "filament": {}}},
        ]:
            path = self.config()
            data = json.loads(path.read_text())
            data.update(changes)
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                bambu.load_config(path)

    def test_incompatible_presets_are_rejected(self):
        config = bambu.load_config(self.config())
        config["presets"] = {kind: kind for kind in bambu.KINDS}
        for kind in bambu.KINDS:
            self.preset(kind, kind, {"compatible_printers": ["a different printer"]})
        with self.assertRaisesRegex(ValueError, "not compatible"):
            bambu.prepare_presets(config)

    def project(self, outside="false", toolpaths=True):
        project = self.directory / "test.3mf"
        with ZipFile(project, "w") as archive:
            if toolpaths:
                archive.writestr("Metadata/plate_1.gcode", "G1 X0 Y0\n")
            archive.writestr("Metadata/slice_info.config", f'''<config><plate>
                <metadata key="prediction" value="120"/>
                <metadata key="weight" value="12.5"/>
                <metadata key="outside" value="{outside}"/>
                <metadata key="support_used" value="false"/>
            </plate></config>''')
        return project

    def test_summary_requires_cached_toolpaths_and_an_in_bounds_plate(self):
        with self.assertRaisesRegex(ValueError, "no sliced toolpaths"):
            bambu.summarize(self.project(toolpaths=False))
        with self.assertRaisesRegex(ValueError, "outside"):
            bambu.summarize(self.project(outside="true"))
        self.assertEqual(bambu.summarize(self.project())["filament_g"], 12.5)

    def test_failed_slice_does_not_replace_an_existing_project(self):
        output = self.directory / "exports"
        output.mkdir()
        old_project = output / "model.3mf"
        old_project.write_bytes(b"previous project")
        config = bambu.load_config(self.config())
        with patch.object(bambu.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["slicer"])):
            with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                bambu.slice_model(output, config, {kind: {} for kind in bambu.KINDS})
        self.assertEqual(old_project.read_bytes(), b"previous project")

    def test_open_command_preserves_paths_with_spaces_as_one_argument(self):
        config = bambu.load_config(self.config())
        project = self.directory / "a model.3mf"
        with patch.object(bambu.subprocess, "run") as run:
            bambu.open_project(project, config)
        run.assert_called_once_with(["viewer", str(project)], check=True)


if __name__ == "__main__":
    unittest.main()
