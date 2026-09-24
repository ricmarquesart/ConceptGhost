import hashlib
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
        route_meta={"scene_contract_id":"scene1","source_run_id":"run1","route_authority":"ARTIST_AUTHORED","route_plan_sha256":"routehash","mission_order":["a"]}
        wan.write_text(json.dumps({"run_id":"run1",**route_meta,"mission_modes":{"a":"PATH"},"effective_dimensions":{"width":832,"height":480,"mode":"UNCHANGED"},"windows":[{"window_index":0,"name":"a","mission_name":"a","source_start":0,"source_end":1,"decoded_frame_count":1,"composite_dir":str(root/"comp")}]}),encoding="utf-8")
        cam.write_text(json.dumps({"scene_contract_id":"scene1",**route_meta,"frames":[{"global_frame_index":0,"path_name":"a","path_frame_index":0,"camera":{"model":"PINHOLE","width":640,"height":360,"fx":700,"fy":700,"cx":320,"cy":180,"world_matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}}]}),encoding="utf-8")
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
            source_image=root/"comp"/"frame_0000.png"
            source_image.parent.mkdir(parents=True,exist_ok=True)
            source_image.write_bytes(b"png")
            source_image_sha=hashlib.sha256(source_image.read_bytes()).hexdigest()
            image_set=hashlib.sha256(
                b"0\x00a\x00"+source_image_sha.encode("ascii")+b"\n"
            ).hexdigest()
            dataset_manifest={
                "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                "frame_count":1,
                "camera_image_mapping_policy":"COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
                "frames":[{
                    "global_frame_index":0,
                    "path_name":"a",
                    "source_image_path":str(source_image),
                    "source_image_sha256":source_image_sha,
                }],
                "source_inputs":{
                    "wan_manifest_sha256":hashlib.sha256(wan.read_bytes()).hexdigest(),
                    "camera_manifest_sha256":hashlib.sha256(cam.read_bytes()).hexdigest(),
                    "source_image_set_sha256":image_set,
                },
            }
            (dataset/"dataset_manifest.json").write_text(json.dumps(dataset_manifest),encoding="utf-8")
            (dataset/"sparse_triangulation_manifest.json").write_text(json.dumps({"status":"PASS"}),encoding="utf-8")
            (dataset/"dense_reconstruction_manifest.json").write_text(json.dumps({
                "schema":"ConceptGhost.P10DenseReconstructionResult.v0.3",
                "status":"PASS",
                "gate7_geometric_evidence_ready":True,
                "geometric_depth_map_file_count":1,
                "geometric_consistency_graph_file_count":1,
            }),encoding="utf-8")
            (dataset/"prefusion_mesh_manifest.json").write_text(json.dumps({"status":"PASS"}),encoding="utf-8")
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

    def test_resume_rebuilds_when_source_composite_bytes_change(self):
        from p10_lab.reconstruction_runtime import run_reconstruction_pipeline
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            wan,cam=self._manifests(root)
            source_image=root/"comp"/"frame_0000.png"
            source_image.parent.mkdir(parents=True,exist_ok=True)
            source_image.write_bytes(b"old")
            source_image_sha=hashlib.sha256(source_image.read_bytes()).hexdigest()
            image_set=hashlib.sha256(
                b"0\x00a\x00"+source_image_sha.encode("ascii")+b"\n"
            ).hexdigest()
            out=root/"gate6"
            dataset=out/"dataset"
            dataset.mkdir(parents=True)
            dataset_manifest={
                "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                "frame_count":1,
                "camera_image_mapping_policy":"COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
                "frames":[{
                    "global_frame_index":0,"path_name":"a",
                    "source_image_path":str(source_image),
                    "source_image_sha256":source_image_sha,
                }],
                "source_inputs":{
                    "wan_manifest_sha256":hashlib.sha256(wan.read_bytes()).hexdigest(),
                    "camera_manifest_sha256":hashlib.sha256(cam.read_bytes()).hexdigest(),
                    "source_image_set_sha256":image_set,
                },
            }
            (dataset/"dataset_manifest.json").write_text(json.dumps(dataset_manifest),encoding="utf-8")
            source_image.write_bytes(b"changed")
            with patch("p10_lab.reconstruction_runtime.prepare_known_camera_colmap_dataset") as prepare, \
                 patch("p10_lab.reconstruction_runtime.resolve_colmap_executable", return_value="colmap"), \
                 patch("p10_lab.reconstruction_runtime.run_sparse_triangulation") as sparse:
                prepare.side_effect=RuntimeError("stale image rebuild requested")
                with self.assertRaisesRegex(RuntimeError,"stale image rebuild requested"):
                    run_reconstruction_pipeline(wan,cam,out,colmap_executable="colmap",resume=True)
            self.assertTrue(prepare.called)
            self.assertFalse(sparse.called)

    def test_resume_rebuilds_stale_dataset_context(self):
        from p10_lab.reconstruction_runtime import run_reconstruction_pipeline
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            wan,cam=self._manifests(root)
            out=root/"gate6"
            dataset=out/"dataset"
            dataset.mkdir(parents=True)
            (dataset/"dataset_manifest.json").write_text(
                json.dumps({"schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.1","frame_count":1}),
                encoding="utf-8",
            )
            (dataset/"database.db").write_bytes(b"stale")
            with patch("p10_lab.reconstruction_runtime.prepare_known_camera_colmap_dataset") as prepare, \
                 patch("p10_lab.reconstruction_runtime.resolve_colmap_executable", return_value="colmap"), \
                 patch("p10_lab.reconstruction_runtime.run_sparse_triangulation") as sparse, \
                 patch("p10_lab.reconstruction_runtime.run_dense_reconstruction") as dense, \
                 patch("p10_lab.reconstruction_runtime.run_prefusion_meshing") as mesh:
                def rebuild(_wan,_cam,target,overwrite=False):
                    self.assertTrue(overwrite)
                    target=Path(target)
                    for child in list(target.iterdir()):
                        if child.is_file():
                            child.unlink()
                    payload={
                        "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                        "frame_count":1,
                        "camera_image_mapping_policy":"COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
                        "source_inputs":{
                            "wan_manifest_sha256":hashlib.sha256(Path(_wan).read_bytes()).hexdigest(),
                            "camera_manifest_sha256":hashlib.sha256(Path(_cam).read_bytes()).hexdigest(),
                        },
                    }
                    (target/"dataset_manifest.json").write_text(json.dumps(payload),encoding="utf-8")
                    return payload
                prepare.side_effect=rebuild
                sparse.side_effect=RuntimeError("stop after dataset rebuild")
                with self.assertRaises(RuntimeError):
                    run_reconstruction_pipeline(wan,cam,out,colmap_executable="colmap",resume=True)
            self.assertTrue(prepare.called)
            self.assertTrue(sparse.called)
            self.assertFalse((dataset/"database.db").exists())

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
