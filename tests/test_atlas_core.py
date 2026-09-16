import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.cg_atlas_core import (
    ATLAS_PINNED_COMMIT,
    REFERENCE_WORKFLOWS,
    apply_atlas_core,
    plan_atlas_core,
)


class AtlasCoreTests(unittest.TestCase):
    def _make_project_and_comfy(self, base: Path):
        project = base / "ConceptGhost"
        comfy = base / "ComfyUI"
        (project / "manifests").mkdir(parents=True)
        (project / "workflows" / "reference" / "atlas").mkdir(parents=True)
        (comfy / "custom_nodes").mkdir(parents=True)
        (comfy / "main.py").write_text("# marker\n", encoding="utf-8")
        inventory = {
            "comfyui": {
                "selected": {
                    "root": str(comfy),
                    "mode": "desktop",
                    "python_executable": str(comfy / ".venv" / "Scripts" / "python.exe"),
                    "preexisting": True,
                }
            }
        }
        (project / "manifests" / "preinstall_inventory.json").write_text(
            json.dumps(inventory), encoding="utf-8"
        )
        return project, comfy

    def _make_local_atlas_repo(self, base: Path):
        repo = base / "atlas-source"
        (repo / "examples").mkdir(parents=True)
        for name in REFERENCE_WORKFLOWS:
            (repo / "examples" / name).write_text('{"workflow":"%s"}' % name, encoding="utf-8")
        (repo / "__init__.py").write_text("# atlas marker\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        return repo, commit

    def test_dry_run_plans_clone_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project, comfy = self._make_project_and_comfy(base)
            result = plan_atlas_core(project_root=project)
            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["action"], "clone")
            self.assertEqual(Path(result["target"]), comfy / "custom_nodes" / "atlas-camera")
            self.assertFalse((comfy / "custom_nodes" / "atlas-camera").exists())
            self.assertTrue(result["core_only"])
            self.assertFalse(result["pip_changes"])
            self.assertEqual(result["pinned_commit"], ATLAS_PINNED_COMMIT)

    def test_conflicting_existing_folder_blocks_install(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project, comfy = self._make_project_and_comfy(base)
            target = comfy / "custom_nodes" / "atlas-camera"
            target.mkdir(parents=True)
            (target / "user.txt").write_text("keep", encoding="utf-8")
            result = plan_atlas_core(project_root=project)
            self.assertEqual(result["action"], "blocked_conflict")
            self.assertTrue((target / "user.txt").exists())

    def test_apply_clones_pinned_repo_and_copies_reference_workflows(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project, comfy = self._make_project_and_comfy(base)
            repo, commit = self._make_local_atlas_repo(base)
            result = apply_atlas_core(
                project_root=project,
                repo_url=str(repo),
                pinned_commit=commit,
            )
            self.assertEqual(result["status"], "applied")
            target = comfy / "custom_nodes" / "atlas-camera"
            self.assertTrue((target / ".git").exists())
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
            self.assertEqual(head, commit)
            for name in REFERENCE_WORKFLOWS:
                self.assertTrue((project / "workflows" / "reference" / "atlas" / name).exists())
            manifest = json.loads((project / "manifests" / "atlas_core_install.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["atlas_commit"], commit)
            self.assertFalse(manifest["preexisting"])

    def test_apply_is_idempotent_and_does_not_update_existing_repo(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project, comfy = self._make_project_and_comfy(base)
            repo, commit = self._make_local_atlas_repo(base)
            first = apply_atlas_core(project_root=project, repo_url=str(repo), pinned_commit=commit)
            second = apply_atlas_core(project_root=project, repo_url=str(repo), pinned_commit=commit)
            self.assertEqual(first["status"], "applied")
            self.assertEqual(second["status"], "applied")
            self.assertEqual(second["action"], "reuse_existing")
            self.assertEqual(second["atlas_commit"], commit)


if __name__ == "__main__":
    unittest.main()
