import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "references" / "SOURCE_LOCK.json"
README_PATH = ROOT / "references" / "README.md"
COLLECTOR_PATH = ROOT / "tools" / "DOWNLOAD_REFERENCE_CODE.bat"
VERIFIER_BAT = ROOT / "tools" / "VERIFY_REFERENCE_CODE.bat"
VERIFIER_PY = ROOT / "scripts" / "cg_verify_references.py"


class ReferenceSourceTests(unittest.TestCase):
    def test_source_lock_exists_and_covers_required_references(self):
        self.assertTrue(LOCK_PATH.is_file(), "references/SOURCE_LOCK.json must exist")
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        sources = {item["id"]: item for item in lock["sources"]}
        required = {
            "atlas-camera",
            "geocalib",
            "comfyui-depthanythingv3",
            "depth-anything-3",
            "da3-blender",
            "moge",
            "comfyui-workflow-templates",
            "fspy",
            "fspy-blender",
            "maya-usd-reference",
            "openusd-ply-to-usd",
        }
        self.assertTrue(required.issubset(sources.keys()))
        for source_id in required:
            item = sources[source_id]
            self.assertRegex(item["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(item["drive_path"].startswith(r"G:\My Drive\ConceptGhost\References\Upstream_Code"))
            self.assertTrue(item["stages"], source_id)
            self.assertTrue(item["evidence"], source_id)

    def test_collector_pins_every_git_repository_from_source_lock(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        collector = COLLECTOR_PATH.read_text(encoding="utf-8", errors="ignore")
        for item in lock["sources"]:
            if item["kind"] == "git":
                self.assertIn(item["url"], collector, item["id"])
                self.assertIn(item["commit"], collector, item["id"])
        self.assertIn('call :clone_exact "ComfyUI-workflow-templates"', collector)
        self.assertNotIn('call :clone_sparse "ComfyUI-workflow-templates"', collector)

    def test_collector_repairs_only_safe_stale_git_locks(self):
        collector = COLLECTOR_PATH.read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("index.lock", collector)
        self.assertIn("tasklist", collector)
        self.assertIn("lastwritetime", collector)
        self.assertIn("120", collector)
        self.assertIn("rev-parse head", collector)
        self.assertIn("lock is recent", collector)
        self.assertIn("git.exe is active", collector)

    def test_verifier_is_read_only_and_checks_locked_commits(self):
        self.assertTrue(VERIFIER_BAT.is_file(), "tools/VERIFY_REFERENCE_CODE.bat must exist")
        self.assertTrue(VERIFIER_PY.is_file(), "scripts/cg_verify_references.py must exist")
        bat = VERIFIER_BAT.read_text(encoding="utf-8", errors="ignore").lower()
        py = VERIFIER_PY.read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("cg_verify_references.py", bat)
        self.assertIn("source_lock.json", bat)
        self.assertIn('"--lock"', py)
        self.assertIn("rev-parse", py)
        for forbidden in ["checkout", "fetch", "pull", "reset --hard", "clean -", "clone", "pip install"]:
            self.assertNotIn(forbidden, py)
        self.assertIn(r"references\audit_and_videos\reference_verification", bat)

    def test_reference_readme_declares_baseline_first_rule(self):
        self.assertTrue(README_PATH.is_file(), "references/README.md must exist")
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("Baseline-first rule", text)
        self.assertIn("SOURCE_LOCK.json", text)
        self.assertIn("Google Drive", text)
        self.assertIn("Do not vendor", text)


if __name__ == "__main__":
    unittest.main()
