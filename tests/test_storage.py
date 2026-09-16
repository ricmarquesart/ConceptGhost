import json
import tempfile
import unittest
from pathlib import Path

from scripts.cg_storage import build_storage_snapshot, write_storage_tracking


class StorageTests(unittest.TestCase):
    def test_storage_tracking_writes_local_and_drive_txt(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "ConceptGhost"
            drive = base / "Drive" / "ConceptGhost"
            (project / "output").mkdir(parents=True)
            (project / "cache" / "downloads").mkdir(parents=True)
            (project / "output" / "cloud.ply").write_bytes(b"x" * 25)
            (project / "cache" / "downloads" / "tmp.bin").write_bytes(b"y" * 10)
            (drive / "Reports").mkdir(parents=True)
            (drive / "Logs").mkdir(parents=True)
            (drive / "Tests" / "Local").mkdir(parents=True)
            (drive / "Reports" / "r.txt").write_bytes(b"r" * 7)
            (drive / "Logs" / "l.txt").write_bytes(b"l" * 5)

            result = write_storage_tracking(project_root=project, drive_root=drive, reason="unit-test")
            local_txt = project / "manifests" / "storage_usage.txt"
            drive_txt = drive / "Storage" / "ConceptGhost_Disk_Usage.txt"
            self.assertTrue(local_txt.is_file())
            self.assertTrue(drive_txt.is_file())
            text = drive_txt.read_text(encoding="utf-8")
            self.assertIn("ConceptGhost Storage Tracker", text)
            self.assertIn("Reason: unit-test", text)
            self.assertEqual(result["snapshot"]["components"]["project_root"]["size_bytes"], 35)
            self.assertGreaterEqual(result["snapshot"]["components"]["drive_root"]["size_bytes"], 12)

    def test_storage_history_appends_snapshots(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "ConceptGhost"
            drive = base / "Drive" / "ConceptGhost"
            project.mkdir(parents=True)
            drive.mkdir(parents=True)
            write_storage_tracking(project_root=project, drive_root=drive, reason="first")
            write_storage_tracking(project_root=project, drive_root=drive, reason="second")
            history = json.loads((project / "manifests" / "storage_history.json").read_text(encoding="utf-8"))
            self.assertEqual([x["reason"] for x in history["snapshots"][-2:]], ["first", "second"])

    def test_snapshot_tracks_drive_subfolders(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            project = base / "ConceptGhost"
            drive = base / "Drive" / "ConceptGhost"
            project.mkdir(parents=True)
            for name, n in [("Reports", 11), ("Logs", 13), ("Tests", 17)]:
                d = drive / name
                d.mkdir(parents=True)
                (d / "payload.bin").write_bytes(b"z" * n)
            snap = build_storage_snapshot(project_root=project, drive_root=drive, reason="scan")
            self.assertEqual(snap["components"]["drive_reports"]["size_bytes"], 11)
            self.assertEqual(snap["components"]["drive_logs"]["size_bytes"], 13)
            self.assertEqual(snap["components"]["drive_tests"]["size_bytes"], 17)


if __name__ == "__main__":
    unittest.main()
