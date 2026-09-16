import tempfile
import unittest
from pathlib import Path

from scripts.cg_paths import PathContract
from scripts.cg_storage_migration import (
    build_migration_inventory,
    copy_project_items,
    cutover_check,
    sha256_file,
)


class Stage4SWorkflowCanonicalizationTests(unittest.TestCase):
    def _fixture(self):
        legacy_td = tempfile.TemporaryDirectory()
        project_td = tempfile.TemporaryDirectory()
        legacy = Path(legacy_td.name)
        project = Path(project_td.name)
        contract = PathContract.from_roots(project, project.parent / "runtime")
        refs = project / "References"
        (refs / "Upstream_Code").mkdir(parents=True)
        (refs / "SOURCE_LOCK.json").write_text("{}\n", encoding="utf-8")
        src = legacy / "workflows" / "reference" / "da3" / "advanced_3d.json"
        src.parent.mkdir(parents=True)
        src.write_bytes(b'{"workflow":"upstream"}\n')
        return legacy_td, project_td, legacy, project, contract, src

    def test_cutover_report_lists_required_workflow_hash_and_reference_provenance(self):
        legacy_td, project_td, legacy, project, contract, src = self._fixture()
        try:
            inventory = build_migration_inventory(legacy, contract)
            copied = copy_project_items(inventory)
            self.assertTrue(copied["all_verified"])

            report = cutover_check(
                inventory,
                required_workflows=("workflows/reference/da3/advanced_3d.json",),
                require_reference_provenance=True,
            )

            self.assertTrue(report["safe"])
            self.assertTrue(report["canonical_workflows_verified"])
            self.assertEqual(len(report["canonical_workflows"]), 1)
            workflow = report["canonical_workflows"][0]
            self.assertEqual(workflow["sha256"], sha256_file(src))
            self.assertTrue(workflow["verified"])
            self.assertTrue(report["reference_provenance"]["source_lock_exists"])
            self.assertTrue(report["reference_provenance"]["upstream_code_exists"])
        finally:
            legacy_td.cleanup()
            project_td.cleanup()

    def test_missing_reference_provenance_blocks_required_cutover(self):
        legacy_td, project_td, legacy, project, contract, src = self._fixture()
        try:
            (project / "References" / "SOURCE_LOCK.json").unlink()
            inventory = build_migration_inventory(legacy, contract)
            copy_project_items(inventory)
            report = cutover_check(
                inventory,
                required_workflows=("workflows/reference/da3/advanced_3d.json",),
                require_reference_provenance=True,
            )
            self.assertFalse(report["safe"])
            self.assertTrue(any("SOURCE_LOCK.json" in x for x in report["blockers"]))
        finally:
            legacy_td.cleanup()
            project_td.cleanup()


if __name__ == "__main__":
    unittest.main()
