import tempfile
import unittest
from pathlib import Path

from scripts.cg_atlas_camera_deps import (
    GEOCALIB_PINNED_COMMIT,
    OPENCV_PYTHON_VERSION,
    build_install_plan_from_probe,
    compare_custom_node_snapshots,
    compare_freeze_maps,
    snapshot_custom_nodes,
)


class AtlasCameraDepsTests(unittest.TestCase):
    def _healthy_probe(self):
        return {
            "python": "3.13.12",
            "packages": {
                "torch": "2.12.1+cu130",
                "torchvision": "0.27.1+cu130",
                "numpy": "2.5.2",
                "kornia": "0.8.3",
                "transformers": "5.16.1",
                "geocalib": None,
                "opencv-python": None,
                "opencv-contrib-python": None,
                "opencv-python-headless": None,
            },
            "modules": {"geocalib": False, "cv2": False},
        }

    def test_plan_adds_only_missing_geocalib_and_opencv_without_touching_protected_stack(self):
        plan = build_install_plan_from_probe(self._healthy_probe())
        self.assertEqual(plan["blockers"], [])
        self.assertEqual([x["package"] for x in plan["installs"]], ["geocalib", "opencv-python"])
        self.assertIn("--no-deps", plan["installs"][0]["pip_args"])
        self.assertIn(GEOCALIB_PINNED_COMMIT, " ".join(plan["installs"][0]["pip_args"]))
        self.assertIn("--no-deps", plan["installs"][1]["pip_args"])
        self.assertIn("--only-binary=:all:", plan["installs"][1]["pip_args"])
        self.assertIn(f"opencv-python=={OPENCV_PYTHON_VERSION}", plan["installs"][1]["pip_args"])
        self.assertEqual(plan["protected_changes_planned"], [])
        self.assertIn("torch", plan["protected_packages"])
        self.assertIn("kornia", plan["protected_packages"])

    def test_plan_reuses_existing_geocalib_and_cv2(self):
        probe = self._healthy_probe()
        probe["packages"]["geocalib"] = "1.0"
        probe["packages"]["opencv-python"] = "4.14.0.94"
        probe["modules"]["geocalib"] = True
        probe["modules"]["cv2"] = True
        plan = build_install_plan_from_probe(probe)
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["installs"], [])
        self.assertEqual(sorted(x["component"] for x in plan["reuse"]), ["cv2", "geocalib"])

    def test_plan_blocks_broken_existing_geocalib_instead_of_overwriting(self):
        probe = self._healthy_probe()
        probe["packages"]["geocalib"] = "1.0"
        probe["modules"]["geocalib"] = False
        plan = build_install_plan_from_probe(probe)
        self.assertTrue(any("geocalib" in x.lower() and "overwrite" in x.lower() for x in plan["blockers"]))
        self.assertNotIn("geocalib", [x["package"] for x in plan["installs"]])

    def test_plan_blocks_broken_existing_opencv_distribution_instead_of_overwriting(self):
        probe = self._healthy_probe()
        probe["packages"]["opencv-python"] = "4.12.0.88"
        probe["modules"]["cv2"] = False
        plan = build_install_plan_from_probe(probe)
        self.assertTrue(any("opencv" in x.lower() and "overwrite" in x.lower() for x in plan["blockers"]))
        self.assertNotIn("opencv-python", [x["package"] for x in plan["installs"]])

    def test_plan_blocks_if_required_protected_dependency_is_missing_instead_of_installing_it(self):
        probe = self._healthy_probe()
        probe["packages"]["kornia"] = None
        plan = build_install_plan_from_probe(probe)
        self.assertTrue(any("kornia" in x.lower() for x in plan["blockers"]))
        self.assertNotIn("kornia", [x["package"] for x in plan["installs"]])

    def test_freeze_delta_allows_only_new_stage3_packages(self):
        before = {
            "torch": "torch==2.12.1+cu130",
            "numpy": "numpy==2.5.2",
            "kornia": "kornia==0.8.3",
        }
        after = {
            **before,
            "geocalib": "geocalib==1.0",
            "opencv-python": "opencv-python==4.14.0.94",
        }
        delta = compare_freeze_maps(before, after)
        self.assertTrue(delta["safe"])
        self.assertEqual(delta["changed"], {})
        self.assertEqual(delta["removed"], {})
        self.assertEqual(sorted(delta["allowed_added"]), ["geocalib", "opencv-python"])
        self.assertEqual(delta["unexpected_added"], {})

    def test_freeze_delta_rejects_any_existing_package_change(self):
        before = {"torch": "torch==2.12.1+cu130", "numpy": "numpy==2.5.2"}
        after = {"torch": "torch==2.11.0", "numpy": "numpy==2.5.2", "geocalib": "geocalib==1.0"}
        delta = compare_freeze_maps(before, after)
        self.assertFalse(delta["safe"])
        self.assertIn("torch", delta["changed"])

    def test_custom_node_snapshot_detects_changes_outside_atlas(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "custom_nodes"
            atlas = root / "atlas-camera"
            protected = root / "ComfyUI-Trellis2"
            atlas.mkdir(parents=True)
            protected.mkdir(parents=True)
            (atlas / "a.py").write_text("atlas", encoding="utf-8")
            target = protected / "node.py"
            target.write_text("before", encoding="utf-8")
            before = snapshot_custom_nodes(root)
            target.write_text("after-change", encoding="utf-8")
            after = snapshot_custom_nodes(root)
            diff = compare_custom_node_snapshots(before, after)
            self.assertFalse(diff["safe"])
            self.assertIn("ComfyUI-Trellis2", diff["changed"])
            self.assertNotIn("atlas-camera", diff["changed"])


if __name__ == "__main__":
    unittest.main()
