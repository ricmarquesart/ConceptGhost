from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

from scripts.cg_paths import PathContract
from scripts.cg_storage_migration import (
    build_migration_inventory,
    classify_legacy_path,
    destination_for_project_path,
)


class MigrationClassificationTests(unittest.TestCase):
    def test_known_durable_paths_are_project(self):
        self.assertEqual(classify_legacy_path(Path("workflows/reference/da3/advanced_3d.json")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("manifests/da3_baseline_install.json")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("docs/STAGE4_DA3_BASELINE.md")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("config.yml")), "PROJECT")

    def test_active_da3_cache_is_grandfathered(self):
        self.assertEqual(classify_legacy_path(Path("cache/da3-comfy-env/.pixi/pixi.lock")), "RUNTIME_GRANDFATHERED")
        self.assertEqual(classify_legacy_path(Path("cache/pixi/archive.bin")), "RUNTIME_GRANDFATHERED")

    def test_bootstrap_and_temp_are_explicit(self):
        self.assertEqual(classify_legacy_path(Path("scripts/cg_bootstrap.py")), "BOOTSTRAP_STATE")
        self.assertEqual(classify_legacy_path(Path("temp/probe.txt")), "TEMP")
        self.assertEqual(classify_legacy_path(Path("cache/downloads/file.bin")), "TEMP")

    def test_unrecognized_path_blocks_inventory(self):
        self.assertEqual(classify_legacy_path(Path("mystery/data.bin")), "UNKNOWN")

    def test_classification_is_case_insensitive_for_windows_legacy_paths(self):
        self.assertEqual(classify_legacy_path(Path("WorkFlows/Reference/DA3/advanced_3d.json")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("CACHE/PIXI/archive.bin")), "RUNTIME_GRANDFATHERED")


class MigrationDestinationTests(unittest.TestCase):
    def setUp(self):
        self.contract = PathContract.from_roots(Path(r"G:\My Drive\ConceptGhost"), Path(r"C:\ConceptGhostRuntime"))

    def test_required_project_destination_mappings(self):
        cases = {
            "workflows/reference/atlas/a.json": self.contract.workflows / "Atlas" / "a.json",
            "workflows/reference/da3/a.json": self.contract.workflows / "DA3" / "a.json",
            "workflows/reference/moge/a.json": self.contract.workflows / "MoGe" / "a.json",
            "workflows/project/a.json": self.contract.workflows / "Project" / "a.json",
            "config.yml": self.contract.project_root / "Config" / "config.yml",
            "manifests/a.json": self.contract.manifests / "a.json",
            "logs/a.log": self.contract.logs / "Legacy_C_ConceptGhost" / "a.log",
            "docs/a.md": self.contract.project_root / "Documentation" / "Legacy_C_ConceptGhost" / "a.md",
            "output/a.ply": self.contract.outputs / "Legacy_C_ConceptGhost" / "a.ply",
            "maya/a.ma": self.contract.outputs / "Maya" / "Legacy_C_ConceptGhost" / "a.ma",
        }
        for rel, expected in cases.items():
            with self.subTest(rel=rel):
                self.assertEqual(destination_for_project_path(Path(rel), self.contract), expected)

    def test_destination_rejects_non_project_paths(self):
        with self.assertRaises(ValueError):
            destination_for_project_path(Path("cache/pixi/x.bin"), self.contract)


class MigrationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.contract = PathContract.from_roots(Path(r"G:\My Drive\ConceptGhost"), Path(r"C:\ConceptGhostRuntime"))

    def test_project_files_have_sha_size_source_and_destination(self):
        with TemporaryDirectory() as td:
            legacy = Path(td)
            src = legacy / "workflows" / "reference" / "da3" / "advanced_3d.json"
            src.parent.mkdir(parents=True)
            src.write_bytes(b"upstream-workflow")
            inventory = build_migration_inventory(legacy, self.contract)
            self.assertEqual(inventory["status"], "ready")
            record = next(x for x in inventory["items"] if x["relative_path"] == "workflows/reference/da3/advanced_3d.json")
            self.assertEqual(record["classification"], "PROJECT")
            self.assertEqual(record["size_bytes"], len(b"upstream-workflow"))
            self.assertEqual(len(record["sha256"]), 64)
            self.assertEqual(Path(record["source"]), src)
            self.assertEqual(Path(record["destination"]), self.contract.workflows / "DA3" / "advanced_3d.json")

    def test_unknown_files_make_inventory_blocked_but_scan_completes(self):
        with TemporaryDirectory() as td:
            legacy = Path(td)
            known = legacy / "docs" / "known.md"
            unknown = legacy / "mystery" / "data.bin"
            known.parent.mkdir(parents=True)
            unknown.parent.mkdir(parents=True)
            known.write_text("known", encoding="utf-8")
            unknown.write_bytes(b"unknown")
            inventory = build_migration_inventory(legacy, self.contract)
            self.assertEqual(inventory["status"], "blocked")
            self.assertTrue(any("mystery/data.bin" in b for b in inventory["blockers"]))
            self.assertTrue(any(x["relative_path"] == "docs/known.md" for x in inventory["items"]))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_symlink_is_recorded_and_not_recursively_followed(self):
        with TemporaryDirectory() as td, TemporaryDirectory() as outside_td:
            legacy = Path(td)
            outside = Path(outside_td)
            (outside / "secret.bin").write_bytes(b"do-not-follow")
            link = legacy / "docs" / "external_link"
            link.parent.mkdir(parents=True)
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted")
            inventory = build_migration_inventory(legacy, self.contract)
            link_record = next(x for x in inventory["items"] if x["relative_path"] == "docs/external_link")
            self.assertEqual(link_record["kind"], "link")
            self.assertFalse(any(x["relative_path"].endswith("secret.bin") for x in inventory["items"]))


class CopyVerificationTests(unittest.TestCase):
    def test_existing_identical_destination_is_reused(self):
        from scripts.cg_storage_migration import copy_one_verified
        with TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src.bin"
            dst = root / "dest" / "dst.bin"
            src.write_bytes(b"same")
            dst.parent.mkdir(parents=True)
            dst.write_bytes(b"same")
            result = copy_one_verified(src, dst)
            self.assertEqual(result["action"], "reuse-identical")
            self.assertTrue(src.exists())

    def test_existing_different_destination_blocks(self):
        from scripts.cg_storage_migration import MigrationBlocked, copy_one_verified
        with TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src.bin"
            dst = root / "dst.bin"
            src.write_bytes(b"source")
            dst.write_bytes(b"different")
            with self.assertRaises(MigrationBlocked):
                copy_one_verified(src, dst)
            self.assertTrue(src.exists())
            self.assertEqual(dst.read_bytes(), b"different")

    def test_copy_never_deletes_source_and_hashes_match(self):
        from scripts.cg_storage_migration import copy_one_verified, sha256_file
        with TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src.bin"
            dst = root / "nested" / "dst.bin"
            src.write_bytes(b"project-data")
            result = copy_one_verified(src, dst)
            self.assertEqual(result["action"], "copied")
            self.assertTrue(src.exists())
            self.assertEqual(sha256_file(src), sha256_file(dst))

    def test_whole_inventory_report_verifies_all_project_sources_remain(self):
        from scripts.cg_storage_migration import copy_project_items
        with TemporaryDirectory() as legacy_td, TemporaryDirectory() as project_td:
            legacy = Path(legacy_td)
            contract = PathContract.from_roots(Path(project_td), Path(project_td).parent / "runtime")
            for rel, payload in [
                ("docs/a.md", b"doc"),
                ("manifests/a.json", b"manifest"),
            ]:
                path = legacy / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            inventory = build_migration_inventory(legacy, contract)
            result = copy_project_items(inventory)
            self.assertEqual(result["copied"], 2)
            self.assertEqual(result["reused_identical"], 0)
            self.assertEqual(result["blocked"], [])
            self.assertEqual(len(result["source_files_remaining"]), 2)
            self.assertTrue(result["all_verified"])
            self.assertTrue(all(Path(p).exists() for p in result["source_files_remaining"]))

    def test_blocked_inventory_performs_no_copy(self):
        from scripts.cg_storage_migration import copy_project_items
        with TemporaryDirectory() as legacy_td, TemporaryDirectory() as project_td:
            legacy = Path(legacy_td)
            contract = PathContract.from_roots(Path(project_td), Path(project_td).parent / "runtime")
            known = legacy / "docs" / "a.md"
            unknown = legacy / "mystery" / "x.bin"
            known.parent.mkdir(parents=True)
            unknown.parent.mkdir(parents=True)
            known.write_bytes(b"doc")
            unknown.write_bytes(b"unknown")
            inventory = build_migration_inventory(legacy, contract)
            result = copy_project_items(inventory)
            self.assertFalse(result["all_verified"])
            self.assertTrue(result["blocked"])
            self.assertFalse((contract.project_root / "Documentation" / "Legacy_C_ConceptGhost" / "a.md").exists())


if __name__ == "__main__":
    unittest.main()
