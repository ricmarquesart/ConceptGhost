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


class Gate6GeometryOutputTests(unittest.TestCase):
    def test_publishes_raw_p10_geometry_obj_manifest_and_p9_sidecar(self):
        from p10_lab.gate6_geometry_output import publish_gate6_geometry_output

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dataset=root/"attempt"/"gate6"/"dataset"
            dense=dataset/"dense"
            dense.mkdir(parents=True)
            (dense/"pre_fusion_mesh.ply").write_text(PLY,encoding="ascii")
            (dense/"fused.ply").write_text(PLY,encoding="ascii")
            (dataset/"prefusion_mesh_manifest.json").write_text(
                json.dumps({"status":"PASS"}),
                encoding="utf-8",
            )
            p9=root/"p9run"
            p9.mkdir()
            overlay=root/"overlay.png"
            overlay.write_bytes(b"png")

            result=publish_gate6_geometry_output(
                dataset,
                root/"attempt"/"gate6",
                p9_run_dir=p9,
                p10_attempt_id="attempt123",
                geometry_quality={"status":"WARN","alerts":["TEST_WARNING"]},
                metric_overlay={
                    "preview_png_path":str(overlay),
                    "p10_dense_to_p9_distance":{"available":True,"median_m":0.25},
                },
            )

            self.assertEqual(result["status"],"PASS")
            self.assertTrue(result["geometry_generated"])
            self.assertEqual(result["vertex_count"],4)
            self.assertEqual(result["face_count"],2)
            self.assertTrue(Path(result["raw_p10_geometry_ply"]).is_file())
            self.assertTrue(Path(result["raw_p10_geometry_obj"]).is_file())
            self.assertTrue(Path(result["dense_points_ply"]).is_file())
            self.assertTrue(Path(result["manifest_path"]).is_file())
            self.assertTrue(Path(result["readme_path"]).is_file())

            obj=Path(result["raw_p10_geometry_obj"]).read_text(encoding="utf-8")
            self.assertEqual(sum(1 for line in obj.splitlines() if line.startswith("v ")),4)
            self.assertEqual(sum(1 for line in obj.splitlines() if line.startswith("f ")),2)

            sidecar=p9/"P10_GATE6_OUTPUT"/"attempt123"
            self.assertTrue((sidecar/"GATE6_RAW_P10_GEOMETRY.ply").is_file())
            self.assertTrue((sidecar/"GATE6_RAW_P10_GEOMETRY.obj").is_file())
            self.assertTrue((sidecar/"GATE6_OUTPUT_MANIFEST.json").is_file())
            pointer=Path(
                (p9/"LATEST_P10_GATE6_OUTPUT.txt").read_text(encoding="utf-8")
            ).resolve()
            self.assertEqual(pointer,sidecar.resolve())

    def test_refuses_to_close_gate6_without_mesh(self):
        from p10_lab.gate6_geometry_output import publish_gate6_geometry_output
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dataset=root/"dataset"
            (dataset/"dense").mkdir(parents=True)
            (dataset/"dense"/"fused.ply").write_text(PLY,encoding="ascii")
            (dataset/"prefusion_mesh_manifest.json").write_text(
                json.dumps({"status":"PASS"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError,"Gate 6 cannot close"):
                publish_gate6_geometry_output(dataset,root/"gate6")


if __name__=="__main__":
    unittest.main()
