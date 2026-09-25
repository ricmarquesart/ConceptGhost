import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


def _write_mesh(path: Path):
    vertices = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),  # face 0 supported
        (2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, 1.0, 0.0),  # face 1 free
        (3.0, 1.0, 0.0),                                      # face 2 shares 4,5
        (5.0, 0.0, 0.0), (6.0, 0.0, 0.0), (5.0, 1.0, 0.0),  # face 3 conflict
        (8.0, 0.0, 0.0), (9.0, 0.0, 0.0), (8.0, 1.0, 0.0),  # face 4 low
        (11.0, 0.0, 0.0), (12.0, 0.0, 0.0), (11.0, 1.0, 0.0), # face 5 protected overlap
    ]
    faces = [
        (0, 1, 2),
        (3, 4, 5),
        (4, 6, 5),
        (7, 8, 9),
        (10, 11, 12),
        (13, 14, 15),
    ]
    lines = [
        "ply", "format ascii 1.0",
        f"element vertex {len(vertices)}",
        "property float x", "property float y", "property float z",
        f"element face {len(faces)}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    lines.extend(f"{x} {y} {z}" for x, y, z in vertices)
    lines.extend(f"3 {a} {b} {c}" for a, b, c in faces)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


@unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
class Gate8DefectAnalysisTests(unittest.TestCase):
    def _fixture(self, root: Path):
        mesh = root / "prefusion.ply"
        _write_mesh(mesh)

        reason_codes = {
            "ACCEPTED_P10_MULTIVIEW": 0,
            "CONFIRMED_FREE_VETO": 1,
            "FREE_SPACE_CONFLICT": 2,
            "P9_SOURCE_PROTECTED_OVERLAP": 3,
            "INSUFFICIENT_PROVENANCE": 4,
            "LOW_CONFIDENCE": 5,
            "SUPPORT_DISTANCE": 6,
            "DELAUNAY_DISAGREEMENT": 7,
        }
        fusion_npz = root / "fusion_faces.npz"
        np.savez_compressed(
            fusion_npz,
            p10_face_accept_mask=np.asarray([1, 0, 0, 0, 0, 0], dtype=np.uint8),
            p10_face_reason_code=np.asarray([0, 1, 1, 2, 5, 3], dtype=np.uint8),
            p10_face_confidence=np.asarray([0.9, 0.5, 0.5, 0.2, 0.1, 0.8], dtype=np.float32),
        )
        fusion = root / "fusion.json"
        fusion.write_text(json.dumps({
            "schema": "ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1",
            "status": "PASS",
            "scene_contract_id": "scene-1",
            "p9_run_id": "p9-run",
            "p10_attempt_id": "attempt-1",
            "coordinate_space": "P9_CANONICAL_WORLD_METERS",
            "official_geometry_changed": False,
            "p9_authority_changed": False,
            "candidate_is_official_geometry": False,
            "destructive_cleanup_performed": False,
            "face_provenance_npz_path": str(fusion_npz.resolve()),
            "reason_codes": reason_codes,
            "inputs": {"p10_prefusion_mesh_path": str(mesh.resolve())},
        }), encoding="utf-8")

        free_npz = root / "free.npz"
        np.savez_compressed(
            free_npz,
            voxel_keys=np.asarray([[20, 0, 0], [5, 0, 0]], dtype=np.int32),
            state=np.asarray([2, 3], dtype=np.uint8),
        )
        free = root / "free.json"
        free.write_text(json.dumps({
            "schema": "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1",
            "status": "PASS",
            "scene_contract_id": "scene-1",
            "p9_run_id": "p9-run",
            "p10_attempt_id": "attempt-1",
            "official_geometry_changed": False,
            "p9_authority_changed": False,
            "voxel": {"voxel_size_m": 1.0},
            "constraints_npz_path": str(free_npz.resolve()),
        }), encoding="utf-8")

        confidence_npz = root / "confidence.npz"
        np.savez_compressed(
            confidence_npz,
            p10_points=np.asarray([
                [10.25, 0.25, 0.25],  # UNKNOWN because no key exists -> missing candidate
                [20.25, 0.25, 0.25],  # CONFIRMED_FREE -> must NOT become missing surface
                [30.25, 0.25, 0.25],  # not virtual
            ], dtype=np.float32),
            p10_confidence_virtual_hole_candidate=np.asarray([1, 1, 0], dtype=np.uint8),
        )
        confidence = root / "confidence.json"
        confidence.write_text(json.dumps({
            "schema": "ConceptGhost.P10Gate7GeometryConfidence.v0.1",
            "status": "PASS",
            "scene_contract_id": "scene-1",
            "p9_run_id": "p9-run",
            "p10_attempt_id": "attempt-1",
            "official_geometry_changed": False,
            "p9_authority_changed": False,
            "evidence_npz_path": str(confidence_npz.resolve()),
        }), encoding="utf-8")
        return fusion, free, confidence

    def test_g8_1_classifies_bounded_regions_without_geometry_mutation(self):
        from p10_lab.gate8_defect_analysis import analyze_gate8_defects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fusion, free, confidence = self._fixture(root)
            result = analyze_gate8_defects(fusion, free, confidence, root / "out")

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["subgate"], "8.1")
            self.assertFalse(result["official_geometry_changed"])
            self.assertFalse(result["p9_authority_changed"])
            self.assertFalse(result["destructive_cleanup_performed"])
            self.assertFalse(result["automatic_geometry_edit_allowed"])
            self.assertTrue(result["ready_for_gate8_2"])

            counts = result["class_counts"]
            self.assertEqual(counts["SUPPORTED_SURFACE"]["face_count"], 2)
            self.assertEqual(counts["FALSE_SURFACE_IN_CONFIRMED_FREE"]["face_count"], 2)
            self.assertEqual(counts["FALSE_SURFACE_IN_CONFIRMED_FREE"]["region_count"], 1)
            self.assertEqual(counts["VALID_OPENING"]["region_count"], 1)
            self.assertEqual(counts["CONFLICT_REGION"]["face_count"], 1)
            self.assertEqual(counts["LOW_CONFIDENCE_SURFACE"]["face_count"], 1)
            self.assertEqual(counts["MISSING_SURFACE_UNKNOWN"]["region_count"], 1)

            classes = [item["class"] for item in result["regions"]]
            self.assertIn("VALID_OPENING", classes)
            self.assertIn("MISSING_SURFACE_UNKNOWN", classes)
            self.assertIn("FALSE_SURFACE_IN_CONFIRMED_FREE", classes)
            self.assertIn("CONFLICT_REGION", classes)
            self.assertIn("LOW_CONFIDENCE_SURFACE", classes)

            with np.load(result["evidence_npz_path"], allow_pickle=False) as evidence:
                defect = evidence["p10_face_defect_class"].tolist()
                missing = evidence["missing_surface_unknown_voxel_keys"].tolist()
            self.assertEqual(defect, [0, 2, 2, 5, 4, 0])
            self.assertEqual(missing, [[10, 0, 0]])

    def test_g8_1_fails_closed_on_identity_mismatch(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate8_defect_analysis import analyze_gate8_defects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fusion, free, confidence = self._fixture(root)
            payload = json.loads(confidence.read_text(encoding="utf-8"))
            payload["p10_attempt_id"] = "wrong-attempt"
            confidence.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ContractError):
                analyze_gate8_defects(fusion, free, confidence, root / "out")

    def test_source_contract_keeps_g8_1_diagnostic_only(self):
        import p10_lab.gate8_defect_analysis as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        for token in (
            '"official_geometry_changed": False',
            '"destructive_cleanup_performed": False',
            '"automatic_geometry_edit_allowed": False',
            '"confirmed_free": "NEVER_FILL_AUTOMATICALLY"',
            '"unknown": "NOT_FREE_NOT_A_DELETION_AUTHORITY"',
            '"ready_for_gate8_2": True',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
