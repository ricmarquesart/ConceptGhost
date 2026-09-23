import json
import tempfile
import unittest
from pathlib import Path


class Gate6GeometryQualityTests(unittest.TestCase):
    def _write(self, root: Path, *, sparse_points=500, selected=20, dropped=0,
               contributes=True, dense_points=2000, depth_maps=20,
               mesh_vertices=1500, mesh_faces=2600, components=2,
               invalid_faces=0, degenerate=0.01):
        sparse={
            "status":"PASS",
            "quality_status":"PASS" if contributes and sparse_points>0 else "FAIL",
            "sparse_point_count":sparse_points,
            "verified_component_count":1 if contributes else 0,
            "mission_contribution":[{
                "mission_name":"drone_1",
                "dataset_frame_count":selected+dropped,
                "selected_frame_count":selected,
                "dropped_frame_count":dropped,
                "component_indices":[0] if contributes else [],
                "contributes_to_sparse":contributes,
            }],
        }
        dense={
            "status":"PASS",
            "depth_map_file_count":depth_maps,
            "normal_map_file_count":depth_maps,
            "fused_cloud":{"vertex_count":dense_points},
        }
        mesh={
            "status":"PASS",
            "mesh_health":{
                "vertex_count":mesh_vertices,
                "face_count":mesh_faces,
                "invalid_face_index_count":invalid_faces,
                "degenerate_face_sample_fraction":degenerate,
                "sampled_connected_component_count":components,
                "sampled_connected_component_count_is_approximate":False,
                "flattened_axes_warning":[],
                "health_status":"PASS",
            },
        }
        (root/"sparse_triangulation_manifest.json").write_text(json.dumps(sparse),encoding="utf-8")
        (root/"dense_reconstruction_manifest.json").write_text(json.dumps(dense),encoding="utf-8")
        (root/"prefusion_mesh_manifest.json").write_text(json.dumps(mesh),encoding="utf-8")

    def test_healthy_reconstruction_is_pass(self):
        from p10_lab.geometry_quality import evaluate_gate6_geometry_quality
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._write(root)
            result=evaluate_gate6_geometry_quality(
                root,
                expected_missions=["drone_1"],
                p9_roundtrip={"quality_status":"PASS"},
                metric_overlay={
                    "status":"PASS",
                    "p10_dense_to_p9_distance":{"available":True,"median_m":25.0},
                    "p9":{"bounds":{"span":[10,20,145]}},
                    "p10_dense":{"bounds":{"span":[12,21,150]}},
                    "p10_sparse":{"bounds":{"span":[12,21,150]}},
                    "p10_prefusion_mesh":{"bounds":{"span":[12,21,150]}},
                    "cameras":{"bounds":{"span":[20,25,155]}},
                },
            )
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["mission_count_contributing"],1)
            self.assertEqual(result["p10_dense_to_p9_distance"]["median_m"],25.0)
            self.assertEqual(result["distance_policy"],"DESCRIPTIVE_ONLY_FOR_GENERATED_UNSEEN_SURFACES")

    def test_missing_one_mission_is_warn_not_silent(self):
        from p10_lab.geometry_quality import evaluate_gate6_geometry_quality
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._write(root)
            result=evaluate_gate6_geometry_quality(
                root,
                expected_missions=["drone_1","drone_2"],
                p9_roundtrip={"quality_status":"PASS"},
            )
            self.assertEqual(result["status"],"WARN")
            self.assertIn("AUTHORED_MISSION_MISSING_FROM_SPARSE",result["alerts"])

    def test_empty_core_geometry_is_fail(self):
        from p10_lab.geometry_quality import evaluate_gate6_geometry_quality
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._write(
                root,
                sparse_points=0,
                selected=0,
                contributes=False,
                dense_points=0,
                depth_maps=0,
                mesh_vertices=0,
                mesh_faces=0,
                components=0,
            )
            result=evaluate_gate6_geometry_quality(root,expected_missions=["drone_1"])
            self.assertEqual(result["status"],"FAIL")
            self.assertIn("SPARSE_POINT_CLOUD_EMPTY",result["alerts"])
            self.assertIn("DENSE_FUSED_CLOUD_EMPTY",result["alerts"])
            self.assertIn("PREFUSION_MESH_EMPTY",result["alerts"])

    def test_p9_roundtrip_failure_warns_but_does_not_redefine_p9(self):
        from p10_lab.geometry_quality import evaluate_gate6_geometry_quality
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._write(root)
            result=evaluate_gate6_geometry_quality(
                root,
                expected_missions=["drone_1"],
                p9_roundtrip={"quality_status":"FAIL"},
            )
            self.assertEqual(result["status"],"WARN")
            self.assertFalse(result["p9_authority_changed"])
            self.assertIn("P9_ONLY_ROUNDTRIP_AUDIT_FAILED",result["alerts"])


if __name__=="__main__":
    unittest.main()
