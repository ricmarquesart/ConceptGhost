import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "references" / "SOURCE_LOCK.json"
README_PATH = ROOT / "references" / "README.md"
COLLECTOR_PATH = ROOT / "tools" / "DOWNLOAD_REFERENCE_CODE.bat"
VERIFIER_PATH = ROOT / "tools" / "VERIFY_REFERENCE_CODE.bat"


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

    def test_collector_pins_every_repository_from_source_lock(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        collector = COLLECTOR_PATH.read_text(encoding="utf-8", errors="ignore")
        for item in lock["sources"]:
            if item["kind"] == "git":
                self.assertIn(item["url"], collector, item["id"])
                self.assertIn(item["commit"], collector, item["id"])
        self.assertIn('call :clone_exact "ComfyUI-workflow-templates"', collector)
        self.assertNotIn('call :clone_sparse "ComfyUI-workflow-templates"', collector)

    def test_verifier_is_read_only_and_checks_locked_commits(self):
        self.assertTrue(VERIFIER_PATH.is_file(), "tools/VERIFY_REFERENCE_CODE.bat must exist")
        text = VERIFIER_PATH.read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("source_lock.json", text)
        self.assertIn("git -c safe.directory=* -c advice.detachedhead=false -c core.quotepath=false -c color.ui=false -c pager.branch=false -c pager.log=false -c pager.show=false -c pager.status=false -c pager.diff=false -c pager.blame=false -c pager.tag=false -c pager.grep=false -c pager.reflog=false -c pager.whitespace=false -c pager.help=false -c pager.push=false -c pager.commit=false -c pager.merge=false -c pager.rebase=false -c pager.cherry=false -c pager.bisect=false -c pager.clean=false -c pager.add=false -c pager.restore=false -c pager.switch=false -c pager.checkout=false -c pager.worktree=false -c pager.config=false -c pager.remote=false -c pager.fetch=false -c pager.pull=false -c pager.push=false -c pager.showbranch=false -c pager.shortlog=false -c pager.describe=false -c pager.name-rev=false -c pager.for-each-ref=false -c pager.ls-files=false -c pager.ls-tree=false -c pager.rev-list=false -c pager.rev-parse=false -c pager.status=false -c pager.diff=false -c pager.log=false -c pager.show=false -c pager.branch=false -c pager.tag=false -c pager.grep=false -c pager.blame=false -c pager.reflog=false -c pager.help=false rev-parse head", text)
        for forbidden in ["git checkout", "git fetch", "git pull", "git reset", "git clean", "git clone", "pip install"]:
            self.assertNotIn(forbidden, text)
        self.assertIn(r"references\audit_and_videos\reference_verification", text)

    def test_reference_readme_declares_baseline_first_rule(self):
        self.assertTrue(README_PATH.is_file(), "references/README.md must exist")
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("Baseline-first rule", text)
        self.assertIn("SOURCE_LOCK.json", text)
        self.assertIn("Google Drive", text)
        self.assertIn("Do not vendor", text)


if __name__ == "__main__":
    unittest.main()
