import json
import tempfile
import unittest
from pathlib import Path


class ReconstructionInputManifestTests(unittest.TestCase):
    def _write_png_stub(self,path):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b"png")

    def test_pairs_gate5_composite_frames_with_authoritative_cameras(self):
        from p10_lab.reconstruction_inputs import build_reconstruction_input_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            comp=root/"composite"/"00_a"
            self._write_png_stub(comp/"frame_0000.png")
            self._write_png_stub(comp/"frame_0001.png")

            wan={
                "run_id":"run1",
                "windows":[{
                    "window_index":0,"name":"a","source_start":0,"source_end":2,
                    "decoded_frame_count":2,"composite_dir":str(comp),
                }],
            }
            cameras={
                "scene_contract_id":"scene1",
                "frames":[
                    {"global_frame_index":0,"path_name":"a","path_frame_index":0,
                     "camera":{"model":"PINHOLE","width":640,"height":360,"fx":700,"fy":700,
                               "cx":320,"cy":180,"world_matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}},
                    {"global_frame_index":1,"path_name":"a","path_frame_index":1,
                     "camera":{"model":"PINHOLE","width":640,"height":360,"fx":700,"fy":700,
                               "cx":320,"cy":180,"world_matrix":[[1,0,0,1],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}},
                ],
            }
            wp=root/"wan.json"; cp=root/"cameras.json"
            wp.write_text(json.dumps(wan),encoding="utf-8")
            cp.write_text(json.dumps(cameras),encoding="utf-8")

            out=build_reconstruction_input_manifest(wp,cp)
            self.assertEqual(out["frame_count"],2)
            self.assertEqual(out["frames"][1]["global_frame_index"],1)
            self.assertEqual(out["frames"][1]["path_name"],"a")
            self.assertEqual(out["frames"][1]["image_provenance"],"P10_WAN_SOURCE_PRESERVED_COMPOSITE")
            self.assertEqual(out["frames"][1]["camera_authority"],"P9_PLANNED_WORLD_CAMERA")

    def test_missing_camera_fails_closed(self):
        from p10_lab.reconstruction_inputs import build_reconstruction_input_manifest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            comp=root/"composite"/"00_a"
            self._write_png_stub(comp/"frame_0000.png")
            (root/"wan.json").write_text(json.dumps({"run_id":"r","windows":[{
                "window_index":0,"name":"a","source_start":0,"source_end":1,
                "decoded_frame_count":1,"composite_dir":str(comp)}]}),encoding="utf-8")
            (root/"cameras.json").write_text(json.dumps({"frames":[]}),encoding="utf-8")
            with self.assertRaises(ValueError):
                build_reconstruction_input_manifest(root/"wan.json",root/"cameras.json")


if __name__=="__main__":
    unittest.main()
