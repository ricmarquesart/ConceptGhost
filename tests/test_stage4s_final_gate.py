import unittest


class Stage4SFinalGateTests(unittest.TestCase):
    def test_cleanup_plan_lists_only_verified_duplicates_and_never_deletes(self):
        from scripts.cg_storage_migration import build_cleanup_plan

        copy_report = {
            "status": "verified",
            "all_verified": True,
            "items": [
                {
                    "relative_path": "workflows/reference/da3/advanced_3d.json",
                    "source": r"C:\ConceptGhost\workflows\reference\da3\advanced_3d.json",
                    "destination": r"G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json",
                    "source_sha256": "a" * 64,
                    "destination_sha256": "a" * 64,
                    "verified": True,
                },
                {
                    "relative_path": "logs/not_verified.json",
                    "source": r"C:\ConceptGhost\logs\not_verified.json",
                    "destination": r"G:\My Drive\ConceptGhost\Logs\Legacy_C_ConceptGhost\not_verified.json",
                    "source_sha256": "b" * 64,
                    "destination_sha256": "c" * 64,
                    "verified": False,
                },
            ],
        }
        cutover_report = {
            "safe": True,
            "status": "ready",
            "verified": [
                {
                    "relative_path": "workflows/reference/da3/advanced_3d.json",
                    "source_sha256": "a" * 64,
                    "destination_sha256": "a" * 64,
                    "verified": True,
                }
            ],
            "legacy_sources_deleted": False,
        }

        plan = build_cleanup_plan(copy_report, cutover_report)

        self.assertTrue(plan["requires_explicit_user_approval"])
        self.assertFalse(plan["deletion_performed"])
        self.assertEqual(len(plan["verified_duplicates"]), 1)
        duplicate = plan["verified_duplicates"][0]
        self.assertEqual(duplicate["source_sha256"], duplicate["destination_sha256"])
        self.assertTrue(duplicate["verified"])
        self.assertEqual(plan["excluded_unverified_count"], 1)

    def test_cleanup_plan_blocks_when_cutover_is_not_safe(self):
        from scripts.cg_storage_migration import build_cleanup_plan

        plan = build_cleanup_plan(
            {"status": "verified", "all_verified": True, "items": []},
            {"safe": False, "status": "blocked", "blockers": ["hash mismatch"]},
        )
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["verified_duplicates"], [])
        self.assertFalse(plan["deletion_performed"])

    def test_final_cutover_report_exposes_safety_contract(self):
        from scripts.cg_storage_migration import build_stage4s_cutover_report

        inventory = {
            "project_root": r"G:\My Drive\ConceptGhost",
            "runtime_root": r"C:\ConceptGhostRuntime",
            "counts": {"UNKNOWN": 0},
            "items": [
                {
                    "relative_path": "cache/da3-comfy-env/pixi.lock",
                    "source": r"C:\ConceptGhost\cache\da3-comfy-env\pixi.lock",
                    "classification": "RUNTIME_GRANDFATHERED",
                }
            ],
        }
        cutover = {
            "safe": True,
            "status": "ready",
            "blockers": [],
            "canonical_workflows_verified": True,
            "canonical_workflows": [{"relative_path": "x.json", "verified": True}],
            "reference_provenance": {
                "source_lock_exists": True,
                "upstream_code_exists": True,
            },
            "verified": [],
            "legacy_sources_deleted": False,
        }

        report = build_stage4s_cutover_report(inventory, cutover)

        self.assertTrue(report["safe"])
        self.assertEqual(report["g_project_root"], r"G:\My Drive\ConceptGhost")
        self.assertEqual(report["c_runtime_root"], r"C:\ConceptGhostRuntime")
        self.assertTrue(report["canonical_workflows_verified"])
        self.assertFalse(report["legacy_sources_deleted"])
        self.assertEqual(report["unknown_paths"], [])
        self.assertEqual(report["hash_mismatches"], [])
        self.assertEqual(report["destination_conflicts"], [])
        self.assertEqual(len(report["grandfathered_runtime"]), 1)

    def test_stage4s_cli_has_no_delete_action(self):
        from scripts.cg_storage_migration import build_arg_parser

        parser = build_arg_parser()
        options = {opt for action in parser._actions for opt in action.option_strings}
        self.assertNotIn("--delete", options)
        self.assertNotIn("--cleanup", options)
        self.assertNotIn("--remove", options)


if __name__ == "__main__":
    unittest.main()
