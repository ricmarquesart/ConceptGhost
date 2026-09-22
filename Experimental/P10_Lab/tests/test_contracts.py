import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from p10_lab.contracts import CompletionBundle, CONTRACT_VERSION
from p10_lab.path_planner import default_paths
from p10_lab.contracts import SceneScale


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_bundle(root: Path, source_stage: str, run_id: str) -> None:
    scene_id = "cgsc_unit_test"
    branch_mode = "Refined / P9 Clone" if source_stage == "p9" else "Baseline / P9"
    (root / "source.png").write_bytes(b"source")
    (root / "mesh.npz").write_bytes(b"mesh")
    camera = {
        "valid": True,
        "scene_contract_id": scene_id,
        "image_width": 100,
        "image_height": 80,
        "intrinsics": {"fx_px": 100.0},
        "extrinsics": {"camera_world_matrix": [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]},
    }
    (root / "camera.json").write_text(json.dumps(camera), encoding="utf-8")
    metadata = {
        "source_stage": source_stage,
        "source_equivalent_to": "baseline",
        "source_run_id": run_id,
        "scene_contract_id": scene_id,
        "source_branch_mode": branch_mode,
    }
    (root / "run.json").write_text(json.dumps(metadata), encoding="utf-8")
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "source_stage": source_stage,
        "source_equivalent_to": "baseline",
        "source_run_id": run_id,
        "scene_contract_id": scene_id,
        "source_branch_mode": branch_mode,
        "source_manifest_schema": "ConceptGhost.Manifest.v0.31",
        "identity_status": "PASS",
        "source_image": "source.png",
        "camera": "camera.json",
        "primary_mesh": "mesh.npz",
        "run_metadata": "run.json",
        "optional": {},
        "file_sha256": {
            "source_image": _digest(root / "source.png"),
            "camera": _digest(root / "camera.json"),
            "primary_mesh": _digest(root / "mesh.npz"),
            "run_metadata": _digest(root / "run.json"),
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class CompletionBundleTests(unittest.TestCase):
    def test_p9_bundle_and_default_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root, "p9", "unit-test")

            bundle = CompletionBundle.from_directory(root)

            self.assertEqual(bundle.source_stage, "p9")
            self.assertEqual(bundle.source_run_id, "unit-test")
            self.assertEqual(bundle.scene_contract_id, "cgsc_unit_test")
            paths = default_paths(SceneScale(10.0))
            self.assertEqual(
                [path.name for path in paths],
                ["left_arc", "right_arc", "forward_probe"],
            )
            self.assertTrue(all(len(path.waypoints) >= 4 for path in paths))

    def test_baseline_equivalent_bundle_is_accepted_for_lab_compatibility(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root, "baseline", "baseline-compat-test")

            bundle = CompletionBundle.from_directory(root)

            self.assertEqual(bundle.source_stage, "baseline")
            self.assertEqual(bundle.source_equivalent_to, "baseline")


if __name__ == "__main__":
    unittest.main()
