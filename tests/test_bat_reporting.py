import unittest
from pathlib import Path


class BatReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def _text(self, name):
        return (self.root / name).read_text(encoding="utf-8", errors="ignore").lower()

    def test_inventory_keeps_window_open_and_reports_to_drive(self):
        bat = self._text("INVENTORY.bat")
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertIn(r"g:\my drive\conceptghost", bat)
        self.assertIn(r"reports\inventory", bat)
        self.assertIn("command_output.log", bat)

    def test_setup_captures_console_output_and_reports_to_drive(self):
        bat = self._text("SETUP.bat")
        self.assertIn(r"g:\my drive\conceptghost", bat)
        self.assertIn(r"reports\setup", bat)
        self.assertIn("command_output.log", bat)
        self.assertIn("%temp%", bat)

    def test_all_operational_bats_refresh_storage_tracker(self):
        for name in ["INVENTORY.bat", "SETUP.bat", "UNINSTALL.bat", "ATLAS_CORE.bat", "ATLAS_CAMERA_DEPS.bat", "TEST.bat"]:
            bat = self._text(name)
            self.assertIn("cg_storage.py\"", bat, name)
            self.assertIn(r"g:\my drive\conceptghost", bat, name)

    def test_storage_bat_updates_single_drive_txt(self):
        bat = self._text("STORAGE.bat")
        self.assertIn("cg_storage.py\"", bat)
        self.assertIn("conceptghost_disk_usage.txt", bat)
        self.assertIn("press any key to close", bat)

    def test_uninstall_keeps_window_open_and_reports_to_drive(self):
        bat = self._text("UNINSTALL.bat")
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertIn(r"g:\my drive\conceptghost", bat)
        self.assertIn(r"reports\uninstall", bat)
        self.assertIn("command_output.log", bat)


class Stage2BatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_atlas_core_bat_is_dry_run_by_default_and_reports_to_drive(self):
        bat = (self.root / "ATLAS_CORE.bat").read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("cg_atlas_core.py", bat)
        self.assertIn(r"reports\atlascore", bat)
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertIn("--apply", bat)

    def test_test_bat_reports_to_google_drive_tests_local(self):
        bat = (self.root / "TEST.bat").read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn(r"tests\local", bat)
        self.assertIn("unittest discover", bat)
        self.assertIn("test_output.log", bat)
        self.assertIn("press any key to close", bat)


class Stage3BatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_atlas_camera_deps_bat_is_protected_dry_run_and_reports_to_drive(self):
        bat = (self.root / "ATLAS_CAMERA_DEPS.bat").read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("cg_atlas_camera_deps.py", bat)
        self.assertIn(r"reports\atlascameradeps", bat)
        self.assertIn(r"tests\compatibility", bat)
        self.assertIn("does not upgrade", bat)
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertIn("--apply", bat)


if __name__ == "__main__":
    unittest.main()
