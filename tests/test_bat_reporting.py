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

    def test_uninstall_keeps_window_open_and_reports_to_drive(self):
        bat = self._text("UNINSTALL.bat")
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertIn(r"g:\my drive\conceptghost", bat)
        self.assertIn(r"reports\uninstall", bat)
        self.assertIn("command_output.log", bat)


if __name__ == "__main__":
    unittest.main()
