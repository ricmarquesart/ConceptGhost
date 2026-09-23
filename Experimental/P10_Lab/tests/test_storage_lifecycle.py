import tempfile
import unittest
from pathlib import Path


class P10StorageLifecycleTests(unittest.TestCase):
    def test_report_lists_explicit_p10_roots(self):
        from p10_lab.storage_lifecycle import build_storage_report
        with tempfile.TemporaryDirectory() as tmp:
            report=build_storage_report(tmp)
            self.assertEqual(Path(report["roots"]["route_setup_root"]).parts[-2:],("conceptghost","p10_route_setup"))
            self.assertEqual(Path(report["roots"]["attempts_root"]).parts[-2:],("conceptghost","p10_attempts"))
            self.assertEqual(report["retention_policy"]["p9_run"],"NEVER_DELETE_FROM_P10_CLEANUP")

    def test_cleanup_deletes_only_p10_attempt(self):
        from p10_lab.storage_lifecycle import cleanup_p10_owned_cache
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"concept_scene"/"p9_run"; p9.mkdir(parents=True)
            p9_file=p9/"manifest.json"; p9_file.write_text("keep",encoding="utf-8")
            attempt=root/"conceptghost"/"p10_attempts"/"run1"/"attempt1"
            attempt.mkdir(parents=True); (attempt/"x.bin").write_bytes(b"123")
            result=cleanup_p10_owned_cache(root,delete_attempt_paths=[attempt])
            self.assertFalse(attempt.exists())
            self.assertTrue(p9_file.is_file())
            self.assertFalse(result["p9_deleted"])

    def test_cleanup_refuses_path_outside_p10_roots(self):
        from p10_lab.storage_lifecycle import cleanup_p10_owned_cache
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"concept_scene"/"p9_run"; p9.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,"Refusing cleanup outside"):
                cleanup_p10_owned_cache(root,delete_attempt_paths=[p9])


    def test_route_handoff_can_be_cleaned_without_touching_p9_or_attempts(self):
        from p10_lab.storage_lifecycle import cleanup_p10_owned_cache,storage_roots
        with tempfile.TemporaryDirectory() as tmp:
            roots=storage_roots(tmp)
            roots.route_setup_root.mkdir(parents=True)
            (roots.route_setup_root/"LATEST_PRODUCTION_ENTRY.json").write_text("{}",encoding="utf-8")
            attempt=roots.attempts_root/"p9"/"attempt1"
            attempt.mkdir(parents=True)
            (attempt/"attempt_manifest.json").write_text('{"status":"ACTIVE"}',encoding="utf-8")
            p9=Path(tmp)/"p9_authority"; p9.mkdir()
            (p9/"keep.txt").write_text("keep",encoding="utf-8")
            result=cleanup_p10_owned_cache(tmp,delete_route_setup_state=True)
            self.assertFalse(roots.route_setup_root.exists())
            self.assertTrue(attempt.exists())
            self.assertTrue((p9/"keep.txt").exists())
            self.assertFalse(result["p9_deleted"])

if __name__=="__main__":
    unittest.main()
