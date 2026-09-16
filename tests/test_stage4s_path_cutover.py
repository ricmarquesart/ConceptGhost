import json
import tempfile
import unittest
from pathlib import Path

from scripts.cg_paths import (
    PathContract,
    resolve_da3_runtime_layout,
    resolve_stage4s_contract,
)


class Stage4SPathCutoverTests(unittest.TestCase):
    def test_legacy_default_resolves_to_dual_root_contract(self):
        contract = resolve_stage4s_contract(Path(r"C:\ConceptGhost"), config_path=None)
        self.assertEqual(contract.project_root, Path(r"G:\My Drive\ConceptGhost"))
        self.assertEqual(contract.runtime_root, Path(r"C:\ConceptGhostRuntime"))
        self.assertEqual(contract.workflows / "DA3", Path(r"G:\My Drive\ConceptGhost") / "Workflows" / "DA3")
        self.assertEqual(contract.manifests, Path(r"G:\My Drive\ConceptGhost") / "Manifests")
        self.assertEqual(contract.cache, Path(r"C:\ConceptGhostRuntime") / "cache")

    def test_explicit_nonlegacy_root_stays_testable_and_separate(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            contract = resolve_stage4s_contract(project, config_path=None)
            self.assertEqual(contract.project_root, project)
            self.assertEqual(contract.runtime_root, project / "_runtime")
            self.assertNotEqual(contract.project_root, contract.runtime_root)

    def test_existing_da3_manifest_grandfathers_legacy_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "project"
            runtime = base / "runtime"
            contract = PathContract.from_roots(project, runtime)
            legacy_workspace = base / "legacy" / "cache" / "da3-comfy-env"
            legacy_env = legacy_workspace / ".pixi" / "envs" / "depthanythingv3-nodes"
            legacy_pixi = base / "legacy" / "cache" / "pixi"
            legacy_shadow = base / "legacy" / "cache" / "da3-shadow-comfyui"
            legacy_env.mkdir(parents=True)
            legacy_pixi.mkdir(parents=True)
            legacy_shadow.mkdir(parents=True)
            contract.manifests.mkdir(parents=True)
            manifest = {
                "project_comfy_env_workspace": str(legacy_workspace),
                "project_isolated_env": str(legacy_env),
                "project_pixi_cache": str(legacy_pixi),
                "shadow_comfyui": str(legacy_shadow),
            }
            (contract.manifests / "da3_baseline_install.json").write_text(json.dumps(manifest), encoding="utf-8")
            layout = resolve_da3_runtime_layout(contract)
            self.assertTrue(layout["grandfathered_runtime"])
            self.assertEqual(Path(layout["workspace"]), legacy_workspace)
            self.assertEqual(Path(layout["isolated_env"]), legacy_env)
            self.assertEqual(Path(layout["pixi_cache"]), legacy_pixi)
            self.assertEqual(Path(layout["shadow_comfyui"]), legacy_shadow)

    def test_new_da3_runtime_uses_runtime_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            contract = PathContract.from_roots(base / "project", base / "runtime")
            layout = resolve_da3_runtime_layout(contract)
            self.assertFalse(layout["grandfathered_runtime"])
            self.assertEqual(Path(layout["workspace"]), contract.cache / "da3-comfy-env")
            self.assertEqual(Path(layout["isolated_env"]), contract.cache / "da3-comfy-env" / ".pixi" / "envs" / "depthanythingv3-nodes")
            self.assertEqual(Path(layout["pixi_cache"]), contract.cache / "pixi")
            self.assertEqual(Path(layout["shadow_comfyui"]), contract.cache / "da3-shadow-comfyui")


if __name__ == "__main__":
    unittest.main()
