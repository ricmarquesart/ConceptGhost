from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys
import unittest

from scripts.cg_paths import PathContract
from scripts.cg_storage_migration import (
    build_arg_parser,
    build_migration_inventory,
    copy_project_items,
    cutover_check,
)


class StorageMigrationCliTests(unittest.TestCase):
    def test_cli_defaults_to_inventory_dry_run_and_has_no_delete_option(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertFalse(args.copy)
        self.assertFalse(args.cutover_check)
        options = {opt for action in parser._actions for opt in action.option_strings}
        self.assertNotIn("--delete", options)

    def test_cutover_check_requires_verified_destinations_but_never_removes_sources(self):
        with TemporaryDirectory() as legacy_td, TemporaryDirectory() as project_td:
            legacy = Path(legacy_td)
            contract = PathContract.from_roots(Path(project_td), Path(project_td).parent / "runtime")
            src = legacy / "docs" / "a.md"
            src.parent.mkdir(parents=True)
            src.write_bytes(b"doc")
            inventory = build_migration_inventory(legacy, contract)
            self.assertFalse(cutover_check(inventory)["safe"])
            copied = copy_project_items(inventory)
            self.assertTrue(copied["all_verified"])
            after = cutover_check(inventory)
            self.assertTrue(after["safe"])
            self.assertTrue(src.exists())
            self.assertFalse(after["legacy_sources_deleted"])

    def test_script_can_run_help_directly_from_package_root(self):
        root = Path(__file__).resolve().parents[1]
        cp = subprocess.run(
            [sys.executable, str(root / "scripts" / "cg_storage_migration.py"), "--help"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("--copy", cp.stdout)
        self.assertIn("--cutover-check", cp.stdout)
        self.assertNotIn("--delete", cp.stdout)


if __name__ == "__main__":
    unittest.main()
