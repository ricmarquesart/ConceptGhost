import unittest
from pathlib import Path

from scripts.cg_storage_migration import classify_legacy_path


class Stage4SRealInventoryRegressionTests(unittest.TestCase):
    def test_da3_shadow_comfyui_is_grandfathered_runtime(self):
        paths = [
            Path("cache/da3-shadow-comfyui/requirements.txt"),
            Path("cache/da3-shadow-comfyui/main.py"),
            Path("cache/da3-shadow-comfyui/custom_nodes/ComfyUI-DepthAnythingV3/nodes/comfy-env.toml"),
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(classify_legacy_path(path), "RUNTIME_GRANDFATHERED")

    def test_da3_host_paths_is_grandfathered_runtime_state(self):
        self.assertEqual(
            classify_legacy_path(Path("config/da3_host_paths.json")),
            "RUNTIME_GRANDFATHERED",
        )

    def test_unrelated_config_remains_unknown_fail_closed(self):
        self.assertEqual(classify_legacy_path(Path("config/mystery.json")), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
