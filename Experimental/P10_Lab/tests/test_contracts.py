import json
import tempfile
import unittest
from pathlib import Path

from p10_lab.contracts import CompletionBundle, CONTRACT_VERSION
from p10_lab.path_planner import default_paths
from p10_lab.contracts import SceneScale


def _write_bundle(root: Path, source_stage: str, run_id: str) -> None:
    for name in ["source.png", "camera.json", "mesh.ply", "run.json"]:
        (root / name).write_text("x", encoding="utf-8")
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "source_stage": source_stage,
        "source_equivalent_to": "baseline",
        "source_run_id": run_id,
        "source_image": "source.png",
        "camera": "camera.json",
        "primary_mesh": "mesh.ply",
        "run_metadata": "run.json",
        "optional": {},
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


if __name__ == "__main__":
    unittest.main()
