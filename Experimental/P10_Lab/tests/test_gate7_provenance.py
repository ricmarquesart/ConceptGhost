import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy as np
except ImportError:
    np = None


def _write_ascii_ply(path: Path, points):
    rows = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(points)}",
        "property float x",
        "property float y",
        "property float z",
        "end_header",
    ]
    rows.extend(f"{x} {y} {z}" for x, y, z in points)
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


class Gate7ProvenanceTests(unittest.TestCase):
    def _fixture(self, root: Path):
        p9 = root / "p9_run"
        p9.mkdir()
        primary = p9 / "primary_mesh.npz"
        p9_vertices = np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
        grid = np.asarray([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.int64)
        np.savez(primary, vertices=p9_vertices, grid_xy=grid)

        dataset = root / "dataset"
        sparse = dataset / "sparse" / "triangulated_txt"
        sparse.mkdir(parents=True)
        mesh = dataset / "dense" / "pre_fusion_mesh.ply"
        mesh.parent.mkdir()
        _write_ascii_ply(
            mesh,
            [
                (0.02, 0.0, 0.0),  # source match -> P9_RETAINED
                (0.20, 0.0, 0.0),  # supported + near P9 -> CONFLICT
                (2.00, 0.0, 0.0),  # supported + far -> P10_MULTIVIEW_SUPPORTED
                (3.00, 0.0, 0.0),  # far unsupported -> P10_GENERATED_ONLY
                (0.20, 1.0, 0.0),  # near but unsupported -> UNKNOWN
            ],
        )
        (dataset / "dataset_manifest.json").write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                    "run_id": "p9_run",
                    "scene_contract_id": "scene-abc",
                    "camera_authority": "P9_BASELINE_WORLD_DERIVED",
                    "frames": [
                        {"image_id": 1, "path_name": "drone_a"},
                        {"image_id": 2, "path_name": "drone_b"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (sparse / "points3D.txt").write_text(
            "\n".join(
                [
                    "# POINT3D_ID X Y Z R G B ERROR TRACK[]",
                    "1 0.20 0 0 255 255 255 0.1 1 0 2 1",
                    "2 2.00 0 0 255 255 255 0.1 1 2 2 3",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        registration = root / "gate7_registration.json"
        registration.write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10Gate7Registration.v0.1",
                    "status": "PASS",
                    "registration_policy": "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
                    "p9_authority_changed": False,
                    "sim3_refit_allowed": False,
                    "ready_for_gate7_2": True,
                    "transform_p10_to_p9": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    "scale": 1.0,
                    "p9_run_dir": str(p9.resolve()),
                    "p9_run_id": "p9_run",
                    "scene_contract_id": "scene-abc",
                    "p10_attempt_id": "attempt-001",
                    "dataset_manifest_path": str((dataset / "dataset_manifest.json").resolve()),
                    "pre_fusion_mesh_path": str(mesh.resolve()),
                }
            ),
            encoding="utf-8",
        )
        boundary = SimpleNamespace(
            root=p9.resolve(),
            run_id="p9_run",
            scene_contract_id="scene-abc",
            primary_mesh=primary.resolve(),
        )
        return p9, registration, boundary

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_diagnostic_provenance_classifies_authority_without_geometry_mutation(self):
        from p10_lab.gate7_provenance import (
            Gate7ProvenanceClass,
            build_gate7_provenance,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9, registration, boundary = self._fixture(root)
            output = root / "g7_2"
            with patch(
                "p10_lab.gate7_provenance.validate_official_run",
                return_value=boundary,
            ):
                result = build_gate7_provenance(
                    p9,
                    registration,
                    output,
                    max_p9_points=100,
                    max_p10_points=100,
                    max_sparse_points=100,
                    source_match_fraction=0.05,
                    conflict_band_fraction=0.25,
                    sparse_support_fraction=0.10,
                )

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["subgate"], "7.2")
            self.assertEqual(result["mode"], "DIAGNOSTIC_ONLY_NO_GEOMETRY_MUTATION")
            self.assertFalse(result["p9_authority_changed"])
            self.assertFalse(result["official_geometry_changed"])
            self.assertFalse(result["ready_for_destructive_fusion"])
            self.assertTrue(result["ready_for_gate7_2c"])

            with np.load(result["evidence_npz_path"], allow_pickle=False) as evidence:
                labels = evidence["p10_labels"].tolist()
                self.assertEqual(
                    labels,
                    [
                        int(Gate7ProvenanceClass.P9_RETAINED),
                        int(Gate7ProvenanceClass.CONFLICT),
                        int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED),
                        int(Gate7ProvenanceClass.P10_GENERATED_ONLY),
                        int(Gate7ProvenanceClass.UNKNOWN),
                    ],
                )
                self.assertTrue(
                    np.all(
                        evidence["p9_labels"]
                        == int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED)
                    )
                )

            self.assertEqual(
                result["p10_summary"]["P10_MULTIVIEW_SUPPORTED"]["count"],
                1,
            )
            self.assertEqual(result["p10_summary"]["CONFLICT"]["count"], 1)
            self.assertEqual(result["p10_summary"]["P10_GENERATED_ONLY"]["count"], 1)
            self.assertEqual(result["p10_summary"]["UNKNOWN"]["count"], 1)

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_non_identity_registration_is_rejected(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_provenance import build_gate7_provenance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9, registration, boundary = self._fixture(root)
            payload = json.loads(registration.read_text(encoding="utf-8"))
            payload["transform_p10_to_p9"][0][3] = 0.25
            registration.write_text(json.dumps(payload), encoding="utf-8")
            with patch(
                "p10_lab.gate7_provenance.validate_official_run",
                return_value=boundary,
            ):
                with self.assertRaises(ContractError):
                    build_gate7_provenance(p9, registration, root / "out")

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_wrong_scene_contract_is_rejected(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_provenance import build_gate7_provenance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9, registration, boundary = self._fixture(root)
            payload = json.loads(registration.read_text(encoding="utf-8"))
            payload["scene_contract_id"] = "wrong-scene"
            registration.write_text(json.dumps(payload), encoding="utf-8")
            with patch(
                "p10_lab.gate7_provenance.validate_official_run",
                return_value=boundary,
            ):
                with self.assertRaises(ContractError):
                    build_gate7_provenance(p9, registration, root / "out")

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_generated_only_label_cannot_promote_destructive_fusion(self):
        from p10_lab.gate7_provenance import build_gate7_provenance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9, registration, boundary = self._fixture(root)
            with patch(
                "p10_lab.gate7_provenance.validate_official_run",
                return_value=boundary,
            ):
                result = build_gate7_provenance(
                    p9,
                    registration,
                    root / "out",
                    source_match_fraction=0.05,
                    conflict_band_fraction=0.25,
                    sparse_support_fraction=0.10,
                )
            self.assertFalse(result["ready_for_destructive_fusion"])
            self.assertIn(
                "CONSERVATIVE_CANDIDATE",
                result["classification_policy"]["p10_generated_only"],
            )


    def test_source_contract_keeps_g7_2_diagnostic_only(self):
        import p10_lab.gate7_provenance as provenance

        source = Path(provenance.__file__).read_text(encoding="utf-8")
        self.assertIn("DIAGNOSTIC_ONLY_NO_GEOMETRY_MUTATION", source)
        self.assertIn('"ready_for_destructive_fusion": False', source)
        self.assertIn("P9_ACCEPTED_IMMUTABLE_UPSTREAM", source)
        self.assertIn("sim3_refit_allowed", source)
        self.assertIn("P10_GENERATED_ONLY", source)
        self.assertIn("P10_MULTIVIEW_SUPPORTED", source)
        self.assertIn("CONFLICT", source)



if __name__ == "__main__":
    unittest.main()
