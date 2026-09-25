import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


@unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
class Gate8LocalRemeshCleanupTests(unittest.TestCase):
    def _fixture(self, root: Path):
        evidence = root / "gate8_defect_analysis_evidence.npz"
        np.savez_compressed(
            evidence,
            p10_face_defect_class=np.asarray([0, 2, 2, 5, 4, 0], dtype=np.uint8),
            p10_face_region_id=np.asarray([-1, 0, 0, 2, 3, -1], dtype=np.int32),
            p10_face_gate7_reason_code=np.asarray([0, 1, 1, 2, 5, 3], dtype=np.uint8),
            p10_face_gate7_confidence=np.asarray([0.9, 0.5, 0.5, 0.2, 0.1, 0.8], dtype=np.float32),
            missing_surface_unknown_voxel_keys=np.asarray([[10, 0, 0]], dtype=np.int32),
        )
        regions = [
            {
                "region_id": "G8R-000000",
                "region_index": 0,
                "class": "FALSE_SURFACE_IN_CONFIRMED_FREE",
                "automatic_geometry_edit_allowed": False,
            },
            {
                "region_id": "G8R-000001",
                "region_index": 1,
                "class": "VALID_OPENING",
                "automatic_geometry_edit_allowed": False,
            },
            {
                "region_id": "G8R-000002",
                "region_index": 2,
                "class": "CONFLICT_REGION",
                "automatic_geometry_edit_allowed": False,
            },
            {
                "region_id": "G8R-000003",
                "region_index": 3,
                "class": "LOW_CONFIDENCE_SURFACE",
                "automatic_geometry_edit_allowed": False,
            },
            {
                "region_id": "G8R-000004",
                "region_index": 4,
                "class": "MISSING_SURFACE_UNKNOWN",
                "automatic_geometry_edit_allowed": False,
            },
        ]
        manifest = root / "gate8_defect_analysis_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10Gate8DefectAnalysis.v0.1",
                    "status": "PASS",
                    "subgate": "8.1",
                    "scene_contract_id": "scene-1",
                    "p9_run_id": "p9-run",
                    "p10_attempt_id": "attempt-1",
                    "coordinate_space": "P9_CANONICAL_WORLD_METERS",
                    "regions": regions,
                    "class_counts": {},
                    "evidence_npz_path": str(evidence.resolve()),
                    "official_geometry_changed": False,
                    "p9_authority_changed": False,
                    "destructive_cleanup_performed": False,
                    "automatic_geometry_edit_allowed": False,
                    "ready_for_gate8_2": True,
                }
            ),
            encoding="utf-8",
        )
        return manifest

    def test_g8_2_builds_nondestructive_cleanup_preview_plan(self):
        from p10_lab.gate8_local_remesh import plan_gate8_local_remesh_cleanup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = plan_gate8_local_remesh_cleanup(
                self._fixture(root),
                root / "out",
            )

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["subgate"], "8.2")
            self.assertEqual(
                result["mode"],
                "STRUCTURAL_ANALYSIS_AND_NONDESTRUCTIVE_PREVIEW_PLAN",
            )
            self.assertTrue(result["structural_controls"]["structural_analysis"])
            self.assertTrue(result["structural_controls"]["structural_preview"])
            self.assertFalse(
                result["structural_controls"]["apply_structural_regularization"]
            )
            self.assertFalse(result["preview_candidate_is_official_geometry"])
            self.assertFalse(result["official_geometry_changed"])
            self.assertFalse(result["p9_authority_changed"])
            self.assertFalse(result["destructive_cleanup_performed"])
            self.assertFalse(result["automatic_geometry_edit_allowed"])
            self.assertTrue(result["ready_for_gate8_3_source_only"])
            self.assertFalse(result["ready_for_runtime_promotion"])

            counts = result["face_counts"]
            self.assertEqual(counts["total"], 6)
            self.assertEqual(counts["nominated_cleanup_preview_removal"], 2)
            self.assertEqual(counts["held_for_stronger_evidence"], 2)
            self.assertEqual(counts["supported_surface"], 2)

            with np.load(result["preview_evidence_npz_path"], allow_pickle=False) as data:
                self.assertEqual(
                    data["p10_face_cleanup_preview_remove_mask"].tolist(),
                    [0, 1, 1, 0, 0, 0],
                )
                self.assertEqual(
                    data["p10_face_preserve_mask"].tolist(),
                    [1, 0, 0, 1, 1, 1],
                )
                self.assertEqual(
                    data["p10_face_hold_mask"].tolist(),
                    [0, 0, 0, 1, 1, 0],
                )
                self.assertEqual(
                    data["missing_surface_unknown_voxel_keys"].tolist(),
                    [[10, 0, 0]],
                )

            decisions = {item["class"]: item for item in result["region_decisions"]}
            self.assertEqual(
                decisions["FALSE_SURFACE_IN_CONFIRMED_FREE"]["preview_action"],
                "REMOVE_FALSE_SURFACE_IN_NON_OFFICIAL_PREVIEW_ONLY",
            )
            self.assertEqual(
                decisions["VALID_OPENING"]["preview_action"],
                "PRESERVE_OPENING_NO_FILL",
            )
            self.assertTrue(
                decisions["MISSING_SURFACE_UNKNOWN"]["requires_new_support"]
            )
            self.assertFalse(
                decisions["MISSING_SURFACE_UNKNOWN"]["apply_in_this_subgate"]
            )

    def test_g8_2_refuses_apply_structural_regularization(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate8_local_remesh import plan_gate8_local_remesh_cleanup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ContractError):
                plan_gate8_local_remesh_cleanup(
                    self._fixture(root),
                    root / "out",
                    apply_structural_regularization=True,
                )

    def test_g8_2_fails_closed_on_gate8_1_mutation_or_region_mismatch(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate8_local_remesh import plan_gate8_local_remesh_cleanup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._fixture(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["official_geometry_changed"] = True
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ContractError):
                plan_gate8_local_remesh_cleanup(manifest, root / "out-a")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._fixture(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["regions"][0]["region_index"] = 99
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ContractError):
                plan_gate8_local_remesh_cleanup(manifest, root / "out-b")

    def test_source_contract_keeps_structural_apply_off(self):
        import p10_lab.gate8_local_remesh as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        for token in (
            '"structural_analysis": True',
            '"structural_preview": True',
            '"apply_structural_regularization": False',
            '"preview_candidate_is_official_geometry": False',
            '"official_geometry_changed": False',
            '"p9_authority_changed": False',
            '"automatic_geometry_edit_allowed": False',
            '"ready_for_runtime_promotion": False',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
