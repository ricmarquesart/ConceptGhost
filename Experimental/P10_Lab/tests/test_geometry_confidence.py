import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


class GeometryConfidenceTests(unittest.TestCase):
    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_confidence_field_is_diagnostic_only_and_preserves_source_authority(self):
        from p10_lab.gate7_provenance import Gate7ProvenanceClass
        from p10_lab.geometry_confidence import (
            GeometryConfidenceClass,
            build_geometry_confidence,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "gate7_provenance_evidence.npz"
            np.savez_compressed(
                evidence,
                p9_points=np.asarray([[0, 0, 0], [1, 0, 0]], dtype=np.float32),
                p9_labels=np.asarray(
                    [
                        int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED),
                        int(Gate7ProvenanceClass.P9_RETAINED),
                    ],
                    dtype=np.uint8,
                ),
                p10_points=np.asarray(
                    [[0, 0, 0], [2, 0, 0], [3, 0, 0], [4, 0, 0], [5, 0, 0]],
                    dtype=np.float32,
                ),
                p10_labels=np.asarray(
                    [
                        int(Gate7ProvenanceClass.P9_RETAINED),
                        int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED),
                        int(Gate7ProvenanceClass.P10_GENERATED_ONLY),
                        int(Gate7ProvenanceClass.CONFLICT),
                        int(Gate7ProvenanceClass.UNKNOWN),
                    ],
                    dtype=np.uint8,
                ),
                p10_nearest_sparse_distance_m=np.asarray(
                    [0.1, 0.01, 1.0, 0.01, 1.0], dtype=np.float32
                ),
                p10_sparse_track_support=np.asarray([0, 4, 0, 3, 0], dtype=np.int32),
                p10_sparse_independent_mission_support=np.asarray(
                    [0, 2, 0, 2, 0], dtype=np.int16
                ),
            )
            manifest = root / "gate7_provenance.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "ConceptGhost.P10Gate7Provenance.v0.1",
                        "status": "PASS",
                        "p9_authority_changed": False,
                        "official_geometry_changed": False,
                        "ready_for_destructive_fusion": False,
                        "ready_for_gate7_2c": True,
                        "scene_contract_id": "scene-abc",
                        "p9_run_id": "p9_run",
                        "p10_attempt_id": "attempt-001",
                        "coordinate_space": "P9_CANONICAL_WORLD_METERS",
                        "evidence_npz_path": str(evidence.resolve()),
                        "thresholds": {"sparse_support_m": 0.2},
                    }
                ),
                encoding="utf-8",
            )

            result = build_geometry_confidence(manifest, root / "confidence")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["subgate"], "7.2C")
            self.assertTrue(result["geometry_confidence_analysis"])
            self.assertTrue(result["show_geometry_confidence"])
            self.assertFalse(result["geometry_confidence_refine"])
            self.assertFalse(result["official_geometry_changed"])
            self.assertFalse(result["p9_authority_changed"])
            self.assertFalse(result["ready_for_destructive_fusion"])
            self.assertTrue(result["ready_for_gate7_3"])
            self.assertEqual(result["scoring_policy"]["free_space_penalty"], "NOT_APPLIED_G7_3_PENDING")
            self.assertEqual(result["scoring_policy"]["unknown_free_space_penalty"], 0.0)

            with np.load(result["evidence_npz_path"], allow_pickle=False) as payload:
                p9_class = payload["p9_confidence_class"].tolist()
                p10_class = payload["p10_confidence_class"].tolist()
                virtual = payload["p10_confidence_virtual_hole_candidate"].tolist()

            self.assertEqual(
                p9_class[0],
                int(GeometryConfidenceClass.HIGH),
            )
            self.assertEqual(
                p9_class[1],
                int(GeometryConfidenceClass.NEUTRAL),
            )
            self.assertEqual(
                p10_class[1],
                int(GeometryConfidenceClass.HIGH),
            )
            self.assertEqual(
                p10_class[2],
                int(GeometryConfidenceClass.LOW),
            )
            self.assertEqual(
                p10_class[3],
                int(GeometryConfidenceClass.VERY_LOW),
            )
            self.assertEqual(
                p10_class[4],
                int(GeometryConfidenceClass.NEUTRAL),
            )
            self.assertEqual(virtual[3], 1)
            self.assertEqual(virtual[2], 0)
            self.assertTrue(Path(result["confidence_proxy_ply_path"]).is_file())

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_provenance_that_already_allows_destructive_fusion_is_rejected(self):
        from p10_lab.contracts import ContractError
        from p10_lab.geometry_confidence import build_geometry_confidence

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence.npz"
            np.savez_compressed(
                evidence,
                p9_points=np.asarray([[0, 0, 0]], dtype=np.float32),
                p9_labels=np.asarray([1], dtype=np.uint8),
                p10_points=np.asarray([[1, 0, 0]], dtype=np.float32),
                p10_labels=np.asarray([5], dtype=np.uint8),
                p10_nearest_sparse_distance_m=np.asarray([1.0], dtype=np.float32),
                p10_sparse_track_support=np.asarray([0], dtype=np.int32),
                p10_sparse_independent_mission_support=np.asarray([0], dtype=np.int16),
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "ConceptGhost.P10Gate7Provenance.v0.1",
                        "status": "PASS",
                        "p9_authority_changed": False,
                        "official_geometry_changed": False,
                        "ready_for_destructive_fusion": True,
                        "ready_for_gate7_2c": True,
                        "evidence_npz_path": str(evidence.resolve()),
                        "thresholds": {"sparse_support_m": 0.2},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ContractError):
                build_geometry_confidence(manifest, root / "out")

    def test_source_contract_keeps_confidence_refinement_off(self):
        import p10_lab.geometry_confidence as confidence

        source = Path(confidence.__file__).read_text(encoding="utf-8")
        self.assertIn('"geometry_confidence_refine": False', source)
        self.assertIn('"official_geometry_changed": False', source)
        self.assertIn('"p9_authority_changed": False', source)
        self.assertIn('"ready_for_destructive_fusion": False', source)
        self.assertIn("NOT_APPLIED_G7_3_PENDING", source)
        self.assertIn("COMFYUI_DIAGNOSTIC_ONLY_NEVER_MAYA_EXPORT", source)


if __name__ == "__main__":
    unittest.main()
