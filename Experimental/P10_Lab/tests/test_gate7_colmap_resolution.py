import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class Gate7ColmapResolutionTests(unittest.TestCase):
    def test_prefers_exact_colmap_recorded_by_gate6_dense_manifest(self):
        from p10_lab.gate7_runtime import _resolve_gate7_repair_colmap

        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "dataset"
            dataset.mkdir()
            executable = Path(tmp) / "COLMAP" / "COLMAP.bat"
            executable.parent.mkdir(parents=True)
            executable.write_text("@echo off\n", encoding="utf-8")
            (dataset / "dense_reconstruction_manifest.json").write_text(
                json.dumps({"colmap_executable": str(executable)}),
                encoding="utf-8",
            )

            resolved = _resolve_gate7_repair_colmap(dataset, "colmap")
            self.assertTrue(os.path.samefile(Path(resolved), executable.resolve()))

    def test_default_colmap_token_reuses_conceptghost_private_runtime(self):
        from p10_lab.gate7_runtime import _resolve_gate7_repair_colmap

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            dataset.mkdir()
            localappdata = root / "LocalAppData"
            executable = (
                localappdata
                / "ConceptGhost"
                / "ThirdParty"
                / "COLMAP-4.2.0"
                / "COLMAP.bat"
            )
            executable.parent.mkdir(parents=True)
            executable.write_text("@echo off\n", encoding="utf-8")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(localappdata)}, clear=False):
                with patch("p10_lab.reconstruction_runtime.shutil.which", return_value=None):
                    resolved = _resolve_gate7_repair_colmap(dataset, "colmap")

            self.assertTrue(os.path.samefile(Path(resolved), executable.resolve()))

    def test_blank_colmap_input_uses_same_auto_discovery_contract(self):
        from p10_lab.gate7_runtime import _resolve_gate7_repair_colmap

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            dataset.mkdir()
            localappdata = root / "LocalAppData"
            executable = (
                localappdata
                / "ConceptGhost"
                / "ThirdParty"
                / "COLMAP-4.2.0"
                / "bin"
                / "colmap.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"MZ")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(localappdata)}, clear=False):
                with patch("p10_lab.reconstruction_runtime.shutil.which", return_value=None):
                    resolved = _resolve_gate7_repair_colmap(dataset, "")

            self.assertTrue(os.path.samefile(Path(resolved), executable.resolve()))

    def test_gate7_delaunay_resolves_before_native_runner(self):
        import inspect
        from p10_lab.gate7_runtime import run_gate7_pipeline

        source = inspect.getsource(run_gate7_pipeline)
        self.assertIn(
            "delaunay_executable = _resolve_gate7_repair_colmap(",
            source,
        )
        self.assertIn(
            "colmap_executable=delaunay_executable",
            source,
        )


if __name__ == "__main__":
    unittest.main()
