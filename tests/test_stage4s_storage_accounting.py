import json
import tempfile
import unittest
from pathlib import Path

from scripts.cg_paths import PathContract
from scripts.cg_storage import build_storage_snapshot, path_size


class Stage4SStorageAccountingTests(unittest.TestCase):
    def test_dual_root_totals_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "G" / "ConceptGhost"
            runtime = base / "C" / "ConceptGhostRuntime"
            contract = PathContract.from_roots(project, runtime)

            (project / "Workflows" / "DA3").mkdir(parents=True)
            (project / "Workflows" / "DA3" / "advanced_3d.json").write_bytes(b"durable")
            (runtime / "cache").mkdir(parents=True)
            (runtime / "cache" / "runtime.bin").write_bytes(b"runtime")

            snap = build_storage_snapshot(contract=contract, reason="stage4s-test", comfyui_root=None)

            self.assertEqual(snap["durable_project_root"], str(project))
            self.assertEqual(snap["runtime_root"], str(runtime))
            self.assertEqual(snap["durable_g_bytes"], path_size(project))
            self.assertEqual(snap["runtime_c_bytes"], path_size(runtime))
            self.assertIn("external_attributable_bytes", snap)
            self.assertEqual(
                snap["combined_tracked_bytes"],
                snap["durable_g_bytes"]
                + snap["runtime_c_bytes"]
                + snap["grandfathered_runtime_c_bytes"]
                + snap["external_attributable_bytes"],
            )

    def test_grandfathered_da3_runtime_is_reported_not_double_counted(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "G" / "ConceptGhost"
            runtime = base / "C" / "ConceptGhostRuntime"
            legacy = base / "C" / "ConceptGhost"
            contract = PathContract.from_roots(project, runtime)

            manifests = project / "Manifests"
            manifests.mkdir(parents=True)
            runtime.mkdir(parents=True)
            grandfathered = legacy / "cache" / "da3-comfy-env"
            grandfathered.mkdir(parents=True)
            (grandfathered / "payload.bin").write_bytes(b"grandfathered")
            (manifests / "da3_baseline_install.json").write_text(
                json.dumps({"project_comfy_env_workspace": str(grandfathered)}),
                encoding="utf-8",
            )

            snap = build_storage_snapshot(contract=contract, reason="stage4s-test", comfyui_root=None)

            self.assertEqual(
                snap["components"]["da3_grandfathered_runtime"]["classification"],
                "grandfathered-runtime",
            )
            self.assertEqual(
                snap["components"]["da3_grandfathered_runtime"]["size_bytes"],
                path_size(grandfathered),
            )
            self.assertEqual(snap["grandfathered_runtime_c_bytes"], path_size(grandfathered))
            self.assertEqual(snap["runtime_c_bytes"], path_size(runtime))


if __name__ == "__main__":
    unittest.main()
