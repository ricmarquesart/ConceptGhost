import tempfile
import unittest
from pathlib import Path

from scripts.cg_da3_baseline import (
    COMFY_3D_VIEWERS_VERSION,
    COMFY_ENV_VERSION,
    DA3_PINNED_COMMIT,
    DA3_REPO_URL,
    REFERENCE_WORKFLOWS,
    assess_resolver_report,
    DA3_ENV_NAME,
    build_isolated_workspace_command,
    isolated_env_paths,
    make_safe_shadow_config,
    build_install_plan_from_probe,
    compute_storage_deltas,
    persist_stage4_plan,
    compare_freeze_maps,
    compare_protected_custom_node_snapshots,
    snapshot_protected_custom_nodes,
)


class DA3BaselineTests(unittest.TestCase):
    def _healthy_probe(self):
        return {
            "python": "3.13.12",
            "packages": {
                "torch": "2.12.1+cu130",
                "torchvision": "0.27.1+cu130",
                "numpy": "2.5.2",
                "kornia": "0.8.3",
                "transformers": "5.16.1",
                "geocalib": "1.0",
                "opencv-python": "4.14.0.94",
                "comfy-env": None,
                "comfy-3d-viewers": None,
            },
            "modules": {"comfy_env": False, "comfy_3d_viewers": False},
        }

    def _absent_repo(self):
        return {"exists": False, "target": r"C:\ComfyUI\custom_nodes\ComfyUI-DepthAnythingV3"}

    def test_plan_clones_pinned_da3_and_adds_only_missing_host_bridges(self):
        plan = build_install_plan_from_probe(self._healthy_probe(), self._absent_repo())
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["repo"]["action"], "clone")
        self.assertEqual(plan["repo"]["repo_url"], DA3_REPO_URL)
        self.assertEqual(plan["repo"]["pinned_commit"], DA3_PINNED_COMMIT)
        self.assertEqual(
            plan["bridge_requirements"],
            [f"comfy-env=={COMFY_ENV_VERSION}", f"comfy-3d-viewers=={COMFY_3D_VIEWERS_VERSION}"],
        )
        self.assertEqual(plan["protected_changes_planned"], [])
        self.assertTrue(plan["policy"]["targeted_comfy_env_only"])
        self.assertTrue(plan["policy"]["no_existing_package_replacement"])

    def test_plan_reuses_exact_bridge_versions(self):
        probe = self._healthy_probe()
        probe["packages"]["comfy-env"] = COMFY_ENV_VERSION
        probe["packages"]["comfy-3d-viewers"] = COMFY_3D_VIEWERS_VERSION
        probe["modules"]["comfy_env"] = True
        probe["modules"]["comfy_3d_viewers"] = True
        plan = build_install_plan_from_probe(probe, self._absent_repo())
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["bridge_requirements"], [])
        self.assertEqual(sorted(x["component"] for x in plan["reuse"]), ["comfy-3d-viewers", "comfy-env"])

    def test_plan_blocks_existing_different_bridge_version_instead_of_overwriting(self):
        probe = self._healthy_probe()
        probe["packages"]["comfy-env"] = "0.4.46"
        probe["modules"]["comfy_env"] = True
        plan = build_install_plan_from_probe(probe, self._absent_repo())
        self.assertTrue(any("comfy-env" in x.lower() and "overwrite" in x.lower() for x in plan["blockers"]))
        self.assertNotIn(f"comfy-env=={COMFY_ENV_VERSION}", plan["bridge_requirements"])

    def test_plan_preserves_existing_upstream_da3_checkout_without_checkout_or_update(self):
        repo = {
            "exists": True,
            "is_git": True,
            "target": r"C:\ComfyUI\custom_nodes\ComfyUI-DepthAnythingV3",
            "remote_url": DA3_REPO_URL,
            "commit": "1234567890abcdef",
            "workflows_present": list(REFERENCE_WORKFLOWS),
        }
        plan = build_install_plan_from_probe(self._healthy_probe(), repo)
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["repo"]["action"], "reuse_existing_untouched")
        self.assertEqual(plan["repo"]["actual_commit"], "1234567890abcdef")

    def test_plan_blocks_wrong_existing_da3_target_instead_of_replacing_it(self):
        repo = {
            "exists": True,
            "is_git": True,
            "target": r"C:\ComfyUI\custom_nodes\ComfyUI-DepthAnythingV3",
            "remote_url": "https://github.com/example/other.git",
            "commit": "abc",
            "workflows_present": list(REFERENCE_WORKFLOWS),
        }
        plan = build_install_plan_from_probe(self._healthy_probe(), repo)
        self.assertTrue(any("remote" in x.lower() and "replace" in x.lower() for x in plan["blockers"]))
        self.assertEqual(plan["repo"]["action"], "blocked")

    def test_resolver_report_allows_only_new_additions(self):
        installed = {
            "torch": "2.12.1+cu130",
            "numpy": "2.5.2",
            "pyyaml": "6.0.2",
        }
        report = {
            "install": [
                {"metadata": {"name": "comfy-env", "version": COMFY_ENV_VERSION}},
                {"metadata": {"name": "comfy-3d-viewers", "version": COMFY_3D_VIEWERS_VERSION}},
                {"metadata": {"name": "tomli-w", "version": "1.2.0"}},
                {"metadata": {"name": "uv", "version": "0.8.0"}},
            ]
        }
        result = assess_resolver_report(installed, report)
        self.assertTrue(result["safe"])
        self.assertEqual(result["existing_changes"], {})
        self.assertEqual(
            sorted(result["allowed_additions"]),
            ["comfy-3d-viewers", "comfy-env", "tomli-w", "uv"],
        )

    def test_resolver_report_blocks_any_existing_package_version_change(self):
        installed = {"numpy": "2.5.2", "torch": "2.12.1+cu130"}
        report = {
            "install": [
                {"metadata": {"name": "comfy-env", "version": COMFY_ENV_VERSION}},
                {"metadata": {"name": "numpy", "version": "1.26.4"}},
            ]
        }
        result = assess_resolver_report(installed, report)
        self.assertFalse(result["safe"])
        self.assertIn("numpy", result["existing_changes"])

    def test_freeze_delta_accepts_exact_resolver_additions_only(self):
        before = {"torch": "torch==2.12.1+cu130", "numpy": "numpy==2.5.2"}
        after = {
            **before,
            "comfy-env": f"comfy-env=={COMFY_ENV_VERSION}",
            "tomli-w": "tomli-w==1.2.0",
        }
        delta = compare_freeze_maps(before, after, allowed_additions={"comfy-env", "tomli-w"})
        self.assertTrue(delta["safe"])
        self.assertEqual(delta["changed"], {})
        self.assertEqual(delta["unexpected_added"], {})

    def test_freeze_delta_rejects_unplanned_addition(self):
        before = {"torch": "torch==2.12.1+cu130"}
        after = {**before, "mystery": "mystery==1.0"}
        delta = compare_freeze_maps(before, after, allowed_additions={"comfy-env"})
        self.assertFalse(delta["safe"])
        self.assertIn("mystery", delta["unexpected_added"])

    def test_custom_node_guard_excludes_only_atlas_and_da3_and_detects_other_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "custom_nodes"
            atlas = root / "atlas-camera"
            da3 = root / "ComfyUI-DepthAnythingV3"
            protected = root / "ComfyUI-Trellis2"
            for d in [atlas, da3, protected]:
                d.mkdir(parents=True)
                (d / "node.py").write_text("before", encoding="utf-8")
            before = snapshot_protected_custom_nodes(root)
            (atlas / "node.py").write_text("atlas changed", encoding="utf-8")
            (da3 / "node.py").write_text("da3 changed", encoding="utf-8")
            (protected / "node.py").write_text("protected changed", encoding="utf-8")
            after = snapshot_protected_custom_nodes(root)
            diff = compare_protected_custom_node_snapshots(before, after)
            self.assertFalse(diff["safe"])
            self.assertIn("ComfyUI-Trellis2", diff["changed"])
            self.assertNotIn("atlas-camera", diff["changed"])
            self.assertNotIn("ComfyUI-DepthAnythingV3", diff["changed"])

    def test_isolated_workspace_command_never_calls_global_plugin_install(self):
        cmd = build_isolated_workspace_command(
            Path(r"C:\ComfyUI\.venv\Scripts\python.exe"),
            Path(r"C:\ConceptGhost\cache\da3-shadow-comfyui"),
        )
        text = " ".join(str(x) for x in cmd).lower()
        self.assertIn("install_workspace", text)
        self.assertIn("da3-shadow-comfyui", text)
        self.assertNotIn("install.py", text)
        self.assertNotIn("main(['install'", text)

    def test_isolated_env_lives_inside_project_and_runtime_link_is_additive(self):
        project_env, runtime_link = isolated_env_paths(
            Path(r"C:\ConceptGhost"),
            Path(r"C:\Users\me\AppData\Local\Programs\comfy-env"),
        )
        self.assertEqual(DA3_ENV_NAME, "depthanythingv3-nodes")
        self.assertTrue(str(project_env).replace("\\", "/").endswith("ConceptGhost/cache/da3-comfy-env/.pixi/envs/depthanythingv3-nodes"))
        self.assertTrue(str(runtime_link).replace("\\", "/").endswith("Programs/comfy-env/.pixi/envs/depthanythingv3-nodes"))


    def test_storage_deltas_track_workspace_and_pixi_home_growth(self):
        result = compute_storage_deltas(
            workspace_before=100, workspace_after=145,
            pixi_home_before=40, pixi_home_after=52,
        )
        self.assertEqual(result["bytes_added_workspace"], 45)
        self.assertEqual(result["bytes_added_pixi_home"], 12)

    def test_storage_deltas_never_report_negative_growth(self):
        result = compute_storage_deltas(
            workspace_before=100, workspace_after=90,
            pixi_home_before=40, pixi_home_after=35,
        )
        self.assertEqual(result["bytes_added_workspace"], 0)
        self.assertEqual(result["bytes_added_pixi_home"], 0)

    def test_dry_run_plan_is_persisted_for_drive_reporting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ConceptGhost"
            plan = {"schema_version": 1, "status": "dry-run", "stage": 4, "component": "DA3 Baseline"}
            paths = persist_stage4_plan(plan, root)
            self.assertTrue((root / "manifests" / "stage4_plan.json").is_file())
            self.assertTrue((root / "logs" / "da3_baseline_plan.json").is_file())
            self.assertEqual(paths["manifest"], str(root / "manifests" / "stage4_plan.json"))
            self.assertIn('"stage": 4', (root / "manifests" / "stage4_plan.json").read_text(encoding="utf-8"))

    def test_shadow_config_removes_optional_cuda_backends_but_keeps_runtime_deps(self):
        source = """[dependencies]\nav = "*"\n[cuda]\npackages = ["flash_attn", "sageattention"]\n[pypi-dependencies]\neinops = ">=0.7.0,<1.0.0"\n"""
        out = make_safe_shadow_config(source)
        self.assertIn("[dependencies]", out)
        self.assertIn("[pypi-dependencies]", out)
        self.assertNotIn("[cuda]", out)
        self.assertNotIn("flash_attn", out)
        self.assertNotIn("sageattention", out)

    def test_reference_workflows_match_stage4_roadmap(self):
        self.assertEqual(list(REFERENCE_WORKFLOWS), ["advanced.json", "advanced_3d.json", "bas_relief.json"])


if __name__ == "__main__":
    unittest.main()
