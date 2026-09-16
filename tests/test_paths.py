from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.cg_paths import PathContract, load_path_contract, validate_path_contract


class PathContractTests(unittest.TestCase):
    def test_defaults_match_approved_stage4s_roots(self):
        c = load_path_contract(None)
        self.assertEqual(c.project_root, Path(r"G:\My Drive\ConceptGhost"))
        self.assertEqual(c.runtime_root, Path(r"C:\ConceptGhostRuntime"))
        self.assertEqual(c.workflows, c.project_root / "Workflows")
        self.assertEqual(c.manifests, c.project_root / "Manifests")
        self.assertEqual(c.cache, c.runtime_root / "cache")

    def test_config_override_keeps_project_and_runtime_separate(self):
        with TemporaryDirectory() as td:
            cfg = Path(td) / "config.yml"
            cfg.write_text(
                'paths:\n  project_root: "G:\\\\My Drive\\\\ConceptGhost"\n'
                '  runtime_root: "C:\\\\ConceptGhostRuntime"\n',
                encoding="utf-8",
            )
            c = load_path_contract(cfg)
            self.assertNotEqual(c.project_root, c.runtime_root)
            self.assertEqual(c.project_root, Path(r"G:\My Drive\ConceptGhost"))
            self.assertEqual(c.runtime_root, Path(r"C:\ConceptGhostRuntime"))

    def test_environment_overrides_are_available_for_tests(self):
        with patch.dict(
            "os.environ",
            {
                "CONCEPTGHOST_PROJECT_ROOT": r"D:\Project",
                "CONCEPTGHOST_RUNTIME_ROOT": r"E:\Runtime",
            },
            clear=False,
        ):
            c = load_path_contract(None)
        self.assertEqual(c.project_root, Path(r"D:\Project"))
        self.assertEqual(c.runtime_root, Path(r"E:\Runtime"))
        self.assertEqual(c.workflows, c.project_root / "Workflows")
        self.assertEqual(c.cache, c.runtime_root / "cache")

    def test_validation_blocks_missing_drive_when_required(self):
        c = PathContract.from_roots(Path(r"Z:\missing\ConceptGhost"), Path(r"C:\Runtime"))
        errors = validate_path_contract(c, require_drive=True)
        self.assertTrue(any("project root" in e.lower() for e in errors))

    def test_validation_rejects_identical_roots(self):
        root = Path(r"C:\Same")
        c = PathContract.from_roots(root, root)
        errors = validate_path_contract(c, require_drive=False)
        self.assertTrue(any("identical" in e.lower() for e in errors))

    def test_validation_rejects_nested_roots(self):
        c = PathContract.from_roots(Path(r"C:\Parent"), Path(r"C:\Parent\runtime"))
        errors = validate_path_contract(c, require_drive=False)
        self.assertTrue(any("nested" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
