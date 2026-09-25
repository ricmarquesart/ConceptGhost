import json
import tempfile
import unittest
from pathlib import Path


PLY = """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
1 1 0
0 1 0
3 0 1 2
3 0 2 3
"""


class GateOutputContractTests(unittest.TestCase):
    def _base(self, root: Path):
        p9 = root / "p9run"
        attempt = root / "attempt123"
        p9.mkdir()
        attempt.mkdir()
        (p9 / "maya").mkdir()
        (p9 / "maya" / "ConceptGhost_P9.ma").write_text(
            "//Maya ASCII 2024 scene\nrequires maya \"2020\";\n",
            encoding="utf-8",
        )
        (p9 / "manifest.json").write_text("{}", encoding="utf-8")
        (p9 / "output_index.json").write_text("{}", encoding="utf-8")
        (p9 / "RUN_PARAMETERS.txt").write_text("test\n", encoding="utf-8")
        (attempt / "attempt_manifest.json").write_text(
            json.dumps({"p10_attempt_id": "attempt123"}),
            encoding="utf-8",
        )
        return p9, attempt

    def _gate4(self, attempt: Path):
        source = attempt / "gate4"
        control = source / "control_sequence"
        frames = control / "frames"
        masks = control / "masks"
        frames.mkdir(parents=True)
        masks.mkdir(parents=True)
        for index in range(2):
            (frames / f"frame_{index:04d}.png").write_bytes(b"png")
            (masks / f"mask_{index:04d}.png").write_bytes(b"png")
        (control / "route_plan.json").write_text(
            json.dumps({"schema": "route"}),
            encoding="utf-8",
        )
        (control / "manifest.json").write_text(
            json.dumps({"frame_count": 2}),
            encoding="utf-8",
        )
        (control / "camera_manifest.json").write_text(
            json.dumps({
                "frame_count": 2,
                "frames": [
                    {
                        "camera": {
                            "width": 832,
                            "height": 480,
                            "fx": 700.0,
                            "fy": 700.0,
                            "cx": 416.0,
                            "cy": 240.0,
                            "world_matrix": [
                                [1, 0, 0, 0],
                                [0, 1, 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1],
                            ],
                        }
                    },
                    {
                        "camera": {
                            "width": 832,
                            "height": 480,
                            "fx": 700.0,
                            "fy": 700.0,
                            "cx": 416.0,
                            "cy": 240.0,
                            "world_matrix": [
                                [1, 0, 0, 1],
                                [0, 1, 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1],
                            ],
                        }
                    },
                ],
            }),
            encoding="utf-8",
        )
        (source / "P10_drone_flights_P9_holes.gif").write_bytes(b"gif")
        for name in (
            "drone_flight_views_contact_sheet.png",
            "raw_holes_contact_sheet.png",
            "camera_paths_topdown.png",
            "p9_3d_partial_erp.png",
            "source_authority_partial_erp.png",
            "source_lock_known_unknown.png",
        ):
            (source / name).write_bytes(b"png")

    def _gate5(self, attempt: Path):
        source = attempt / "gate5"
        raw = source / "wan_raw" / "00_drone"
        comp = source / "composite" / "00_drone"
        previews = source / "drone_previews"
        raw.mkdir(parents=True)
        comp.mkdir(parents=True)
        previews.mkdir(parents=True)
        for index in range(2):
            (raw / f"frame_{index:04d}.png").write_bytes(b"raw")
            (comp / f"frame_{index:04d}.png").write_bytes(b"composite")
        (previews / "drone.gif").write_bytes(b"gif")
        (source / "wan_manifest.json").write_text(
            json.dumps({
                "missions": [{"name": "Drone 1", "frame_count": 2}],
                "known_pixel_policy": "CONTROL_VIDEO_PRESERVED_WHERE_HOLE_MASK_IS_BLACK",
            }),
            encoding="utf-8",
        )

    def _gate6(self, attempt: Path):
        source = attempt / "gate6"
        explicit = source / "gate6_output"
        dense = source / "dataset" / "dense"
        sparse = source / "dataset" / "sparse" / "triangulated_txt"
        logs = source / "dataset" / "logs" / "gate6_3"
        diagnostics = source / "diagnostics"
        for folder in (explicit, dense, sparse, logs, diagnostics):
            folder.mkdir(parents=True, exist_ok=True)
        for name in (
            "GATE6_RAW_P10_GEOMETRY.ply",
            "GATE6_DENSE_POINTS.ply",
        ):
            (explicit / name).write_text(PLY, encoding="ascii")
        (explicit / "GATE6_RAW_P10_GEOMETRY.obj").write_text(
            "v 0 0 0\nv 1 0 0\nv 1 1 0\nf 1 2 3\n",
            encoding="utf-8",
        )
        (explicit / "GATE6_OUTPUT_MANIFEST.json").write_text(
            json.dumps({"status": "PASS", "vertex_count": 4, "face_count": 2}),
            encoding="utf-8",
        )
        (sparse / "points3D.txt").write_text(
            "# points\n1 0 0 0 255 0 0 0\n2 1 0 0 0 255 0 0\n",
            encoding="utf-8",
        )
        (logs / "sparse.log").write_text("PASS\n", encoding="utf-8")
        (diagnostics / "p9_p10_metric_overlay.png").write_bytes(b"png")
        (diagnostics / "gate6_geometry_quality.json").write_text(
            json.dumps({"status": "WARN", "alerts": ["TEST_WARN"]}),
            encoding="utf-8",
        )
        (source / "reconstruction_runtime_manifest.json").write_text(
            json.dumps({"runtime_status": "PASS", "geometry_quality_status": "WARN"}),
            encoding="utf-8",
        )

    def _gate7(self, attempt: Path, accepted_faces: int):
        try:
            import numpy as np
        except ImportError as error:
            self.skipTest(str(error))
        source = attempt / "gate7"
        g74 = source / "g7_4"
        g72 = source / "g7_2c"
        g73 = source / "g7_3" / "constraints"
        g75 = source / "g7_5"
        for folder in (g74, g72, g73, g75):
            folder.mkdir(parents=True, exist_ok=True)
        (g74 / "protected_fusion_candidate.ply").write_text(PLY, encoding="ascii")
        np.savez_compressed(
            g74 / "protected_fusion_face_provenance.npz",
            p10_accepted_face_indices=np.asarray(
                [0] if accepted_faces else [], dtype=np.int64
            ),
            p10_rejected_face_indices=np.asarray(
                [1] if accepted_faces else [0, 1], dtype=np.int64
            ),
        )
        (g74 / "protected_fusion_candidate_manifest.json").write_text(
            json.dumps({
                "status": "PASS",
                "counts": {
                    "p10_input_faces": 2,
                    "p10_accepted_faces": accepted_faces,
                    "p10_rejected_faces": 2 - accepted_faces,
                },
                "reason_counts": {
                    "P9_SOURCE_PROTECTED_OVERLAP": 2 - accepted_faces,
                },
            }),
            encoding="utf-8",
        )
        (g72 / "geometry_confidence_manifest.json").write_text("{}", encoding="utf-8")
        np.savez_compressed(
            g73 / "free_space_constraints.npz",
            voxel_keys=np.zeros((1, 3), dtype=np.int32),
            state=np.zeros(1, dtype=np.uint8),
        )
        (g73 / "free_space_constraints_manifest.json").write_text("{}", encoding="utf-8")
        (g75 / "gate7_registration_provenance_review.png").write_bytes(b"png")
        (source / "gate7_runtime_manifest.json").write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )

    def test_gate4_and_gate5_publish_all_png_products(self):
        from p10_lab.gate_output_contract import publish_gate4_output, publish_gate5_output

        with tempfile.TemporaryDirectory() as tmp:
            p9, attempt = self._base(Path(tmp))
            self._gate4(attempt)
            self._gate5(attempt)

            g4 = publish_gate4_output(p9, attempt)
            g5 = publish_gate5_output(p9, attempt)

            self.assertEqual(g4["functional_status"], "PASS")
            self.assertEqual(g5["functional_status"], "PASS")
            root = p9 / "GATE_OUTPUTS" / "attempt123"
            self.assertEqual(
                len(list((root / "GATE_04_DRONES_CAMERAS" / "OUTPUTS" / "CONTROL_FRAMES").glob("*.png"))),
                2,
            )
            self.assertEqual(
                len(list((root / "GATE_05_NEW_VIEWS" / "OUTPUTS" / "FINAL_SOURCE_PRESERVED_VIEWS").rglob("*.png"))),
                2,
            )
            self.assertTrue((p9 / "GATE_OUTPUT_INDEX.json").is_file())

    def test_gate6_requires_inspectable_geometry_and_diagnostic_maya(self):
        from p10_lab.gate_output_contract import publish_gate6_output_tree

        with tempfile.TemporaryDirectory() as tmp:
            p9, attempt = self._base(Path(tmp))
            self._gate4(attempt)
            self._gate6(attempt)

            result = publish_gate6_output_tree(p9, attempt)
            self.assertEqual(result["runtime_status"], "PASS")
            self.assertEqual(result["functional_status"], "PASS")
            self.assertEqual(result["quality_status"], "WARN")
            root = p9 / "GATE_OUTPUTS" / "attempt123" / "GATE_06_RECONSTRUCTION_3D"
            self.assertTrue((root / "OUTPUTS" / "sparse_points.ply").is_file())
            self.assertTrue((root / "OUTPUTS" / "dense_points.ply").is_file())
            self.assertTrue((root / "OUTPUTS" / "reconstructed_mesh.ply").is_file())
            self.assertTrue((root / "OUTPUTS" / "reconstructed_mesh.obj").is_file())
            ma = root / "OUTPUTS" / "Gate06_Reconstruction_Diagnostic.ma"
            self.assertTrue(ma.is_file())
            text = ma.read_text(encoding="utf-8")
            self.assertIn("P10_RECONSTRUCTED_RAW", text)
            self.assertIn("CAMERAS_GATE06", text)

    def test_gate7_zero_p10_contribution_is_functional_fail_but_outputs_exist(self):
        from p10_lab.gate_output_contract import (
            publish_gate6_output_tree,
            publish_gate7_output_tree,
        )

        with tempfile.TemporaryDirectory() as tmp:
            p9, attempt = self._base(Path(tmp))
            self._gate4(attempt)
            self._gate6(attempt)
            publish_gate6_output_tree(p9, attempt)
            self._gate7(attempt, accepted_faces=0)

            result = publish_gate7_output_tree(p9, attempt)
            self.assertEqual(result["runtime_status"], "PASS")
            self.assertEqual(result["functional_status"], "FAIL")
            self.assertEqual(result["quality_status"], "FAIL")
            root = p9 / "GATE_OUTPUTS" / "attempt123" / "GATE_07_P9_P10_FUSION"
            self.assertTrue((root / "OUTPUTS" / "P10_reconstructed_mesh.ply").is_file())
            self.assertTrue((root / "OUTPUTS" / "fused_candidate_mesh.ply").is_file())
            self.assertTrue((root / "OUTPUTS" / "P10_REJECTED.obj").is_file())
            ma = root / "OUTPUTS" / "Gate07_Fusion_Diagnostic.ma"
            text = ma.read_text(encoding="utf-8")
            self.assertIn('namespace "P9_ORIGINAL"', text)
            self.assertIn("P10_RECONSTRUCTION", text)
            self.assertIn("P10_REJECTED", text)
            self.assertNotIn('namespace "P10_ACCEPTED"', text)

    def test_gate3_is_not_silently_closed_without_explicit_free_conflict_outputs(self):
        from p10_lab.gate_output_contract import publish_gate1_to_gate3_snapshots

        with tempfile.TemporaryDirectory() as tmp:
            p9, attempt = self._base(Path(tmp))
            self._gate4(attempt)
            rows = publish_gate1_to_gate3_snapshots(p9, attempt)
            gate3 = next(row for row in rows if row["gate"] == 3)
            self.assertEqual(gate3["functional_status"], "FAIL")
            self.assertFalse(gate3["next_gate_authorized"])
            self.assertIn("explicit_free_space_mask", gate3["missing_required_outputs"])
            self.assertIn("explicit_conflict_mask", gate3["missing_required_outputs"])


if __name__ == "__main__":
    unittest.main()
