import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.cg_paths import PathContract
from scripts.cg_storage_migration import REQUIRED_CANONICAL_WORKFLOWS, build_migration_inventory, copy_project_items


ROOT = Path(__file__).resolve().parents[1]


class Stage4SFinalizeTests(unittest.TestCase):
    def test_finalizer_writes_two_read_only_reports_and_preserves_sources(self):
        from scripts.cg_stage4s_finalize import write_stage4s_final_evidence

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            legacy = base / "legacy"
            project = base / "project"
            runtime = base / "runtime"
            evidence = base / "evidence"
            contract = PathContract.from_roots(project, runtime)

            (project / "References" / "Upstream_Code").mkdir(parents=True)
            (project / "References" / "SOURCE_LOCK.json").write_text("{}\n", encoding="utf-8")

            for rel in REQUIRED_CANONICAL_WORKFLOWS:
                src = legacy / Path(rel)
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_text(json.dumps({"path": rel}) + "\n", encoding="utf-8")

            inventory = build_migration_inventory(legacy, contract)
            copied = copy_project_items(inventory)
            self.assertTrue(copied["all_verified"])
            source_paths = [Path(item["source"]) for item in copied["items"]]

            result = write_stage4s_final_evidence(
                legacy_root=legacy,
                contract=contract,
                evidence_dir=evidence,
            )

            self.assertEqual(result["status"], "ready")
            cutover_path = evidence / "stage4s_cutover_report.json"
            cleanup_path = evidence / "stage4s_cleanup_plan.json"
            self.assertTrue(cutover_path.is_file())
            self.assertTrue(cleanup_path.is_file())
            cutover = json.loads(cutover_path.read_text(encoding="utf-8"))
            cleanup = json.loads(cleanup_path.read_text(encoding="utf-8"))
            self.assertTrue(cutover["safe"])
            self.assertTrue(cutover["canonical_workflows_verified"])
            self.assertFalse(cutover["legacy_sources_deleted"])
            self.assertTrue(cleanup["requires_explicit_user_approval"])
            self.assertFalse(cleanup["deletion_performed"])
            self.assertEqual(cleanup["verified_duplicate_count"], len(REQUIRED_CANONICAL_WORKFLOWS))
            self.assertTrue(all(path.exists() for path in source_paths))

    def test_finalizer_bat_is_read_only_reports_to_drive_and_has_crlf(self):
        bat = ROOT / "STAGE4S_FINALIZE.bat"
        self.assertTrue(bat.is_file())
        data = bat.read_bytes()
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        text = data.decode("utf-8")
        self.assertIn("cg_stage4s_finalize.py", text)
        self.assertIn("G:\\My Drive\\ConceptGhost\\Reports\\StorageMigration", text)
        self.assertIn("--evidence-dir", text)
        self.assertIn("scripts\\cg_find_python.ps1", text)
        self.assertNotIn("--delete", text.lower())
        self.assertNotIn("--remove", text.lower())
        self.assertIn("pause >nul", text.lower())

    def test_python_locator_has_manifest_and_comfy_desktop_fallbacks(self):
        locator = ROOT / "scripts" / "cg_find_python.ps1"
        self.assertTrue(locator.is_file())
        text = locator.read_text(encoding="utf-8")
        for token in (
            "da3_baseline_install.json",
            "atlas_camera_deps_install.json",
            "preinstall_inventory.json",
            "Comfy Desktop",
            "installations.json",
            ".venv",
            "python.exe",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    @unittest.skipUnless(os.name == "nt", "PowerShell locator integration test is Windows-only")
    def test_python_locator_prefers_project_da3_manifest(self):
        locator = ROOT / "scripts" / "cg_find_python.ps1"
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "project"
            legacy = base / "legacy"
            appdata = base / "appdata"
            fake_python = base / "Comfy Python" / "python.exe"
            fake_python.parent.mkdir(parents=True)
            fake_python.write_bytes(b"fake")
            manifests = project / "Manifests"
            manifests.mkdir(parents=True)
            (manifests / "da3_baseline_install.json").write_text(
                json.dumps({"python_executable": str(fake_python)}), encoding="utf-8"
            )

            cp = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(locator),
                    "-ProjectRoot",
                    str(project),
                    "-LegacyRoot",
                    str(legacy),
                    "-AppDataRoot",
                    str(appdata),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertEqual(Path(cp.stdout.strip()), fake_python.resolve())


if __name__ == "__main__":
    unittest.main()
