import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ReconstructionRuntimeTests(unittest.TestCase):
    def _manifests(self, root: Path):
        wan=root/"p10_gate5"/"run1"/"wan_manifest.json"
        cam=root/"p10_gate4"/"run1"/"control_sequence"/"camera_manifest.json"
        wan.parent.mkdir(parents=True)
        cam.parent.mkdir(parents=True)
        wan.write_text(json.dumps({"run_id":"run1","windows":[{"window_index":0,"name":"a","source_start":0,"source_end":1,"decoded_frame_count":1,"composite_dir":str(root/"comp")}]}),encoding="utf-8")
        cam.write_text(json.dumps({"scene_contract_id":"scene1","frames":[{"global_frame_index":0,"path_name":"a","path_frame_index":0,"camera":{"model":"PINHOLE","width":640,"height":360,"fx":700,"fy":700,"cx":320,"cy":180,"world_matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}}]}),encoding="utf-8")
        return wan,cam

    def test_standard_colmap_candidates_include_conceptghost_runtime(self):
        from p10_lab.reconstruction_runtime import standard_colmap_candidates
        candidates=standard_colmap_candidates(localappdata=r"C:\Users\x\AppData\Local")
        text="\n".join(str(p) for p in candidates).lower()
        self.assertIn("conceptghost",text)
        self.assertIn("colmap-4.2.0",text)

    def test_resume_reuses_complete_stage_manifests(self):
        from p10_lab.reconstruction_runtime import run_reconstruction_pipeline
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            wan,cam=self._manifests(root)
            out=root/"gate6"
            out.mkdir()
            dataset=out/"dataset"
            dataset.mkdir()
            (dataset/"dataset_manifest.json").write_text(json.dumps({"frame_count":1}),encoding="utf-8")
            for name in ("sparse_triangulation_manifest.json","dense_reconstruction_manifest.json","prefusion_mesh_manifest.json"):
                (dataset/name).write_text(json.dumps({"status":"PASS"}),encoding="utf-8")
            sparse=dataset/"sparse"/"triangulated"
            sparse.mkdir(parents=True)
            for name in ("cameras.bin","images.bin","points3D.bin"):
                (sparse/name).write_bytes(b"x")
            mesh=dataset/"dense"/"pre_fusion_mesh.ply"
            mesh.parent.mkdir()
            (dataset/"dense"/"fused.ply").write_bytes(b"ply")
            mesh.write_text("mesh",encoding="utf-8")
            with patch("p10_lab.reconstruction_runtime.prepare_known_camera_colmap_dataset") as a, \
                 patch("p10_lab.reconstruction_runtime.run_sparse_triangulation") as b, \
                 patch("p10_lab.reconstruction_runtime.run_dense_reconstruction") as c, \
                 patch("p10_lab.reconstruction_runtime.run_prefusion_meshing") as d:
                result=run_reconstruction_pipeline(wan,cam,out,colmap_executable="colmap",resume=True)
            self.assertFalse(a.called)
            self.assertFalse(b.called)
            self.assertFalse(c.called)
            self.assertFalse(d.called)
            self.assertEqual(result["stages"]["dataset"]["state"],"REUSED")
            self.assertEqual(result["stages"]["mesh"]["state"],"REUSED")

    def test_nonresume_refuses_existing_output(self):
        from p10_lab.reconstruction_runtime import run_reconstruction_pipeline
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            wan,cam=self._manifests(root)
            out=root/"gate6"
            out.mkdir()
            (out/"keep.txt").write_text("x",encoding="utf-8")
            with self.assertRaises(ValueError):
                run_reconstruction_pipeline(wan,cam,out,colmap_executable="colmap",resume=False)


if __name__=="__main__":
    unittest.main()
