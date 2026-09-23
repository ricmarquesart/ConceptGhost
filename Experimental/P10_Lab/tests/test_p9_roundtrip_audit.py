import json
import tempfile
import unittest
from pathlib import Path


class P9RoundtripAuditTests(unittest.TestCase):
    def test_builds_known_camera_dataset_from_p9_control_frames_without_wan(self):
        from p10_lab.camera_sequence import CameraFrameRecord, CameraSequenceManifest
        from p10_lab.control_sequence import ControlFrameRecord, ControlSequenceManifest
        from p10_lab.p9_roundtrip_audit import prepare_p9_roundtrip_colmap_dataset

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            control_root=root/"control_sequence"
            frame_root=control_root/"frames"
            frame_root.mkdir(parents=True)
            for index in range(2):
                (frame_root/f"frame_{index:04d}.png").write_bytes(
                    b"not-decoded-by-dataset-builder-"+bytes([index])
                )

            control=ControlSequenceManifest(
                frames=(
                    ControlFrameRecord(0,"drone_1",0,0.25,"frames/frame_0000.png","masks/mask_0000.png"),
                    ControlFrameRecord(1,"drone_1",1,0.30,"frames/frame_0001.png","masks/mask_0001.png"),
                ),
                width=640,
                height=360,
                route_authority="ARTIST_AUTHORED",
                scene_contract_id="scene",
                source_run_id="run",
                mission_modes=(("drone_1","PATH"),),
            )
            control_path=control_root/"manifest.json"
            control_path.write_text(json.dumps(control.to_dict()),encoding="utf-8")

            frames=[]
            for index,x in enumerate((0.0,1.0)):
                frames.append(
                    CameraFrameRecord(
                        global_frame_index=index,
                        path_name="drone_1",
                        path_frame_index=index,
                        width=640,
                        height=360,
                        fx=500.0,
                        fy=500.0,
                        cx=320.0,
                        cy=180.0,
                        world_matrix=(
                            (1.0,0.0,0.0,x),
                            (0.0,1.0,0.0,0.0),
                            (0.0,0.0,1.0,0.0),
                            (0.0,0.0,0.0,1.0),
                        ),
                    )
                )
            camera=CameraSequenceManifest(
                frames=tuple(frames),
                scene_contract_id="scene",
                route_authority="ARTIST_AUTHORED",
                source_run_id="run",
                mission_modes=(("drone_1","PATH"),),
            )
            camera_path=control_root/"camera_manifest.json"
            camera_path.write_text(json.dumps(camera.to_dict()),encoding="utf-8")

            dataset_root=root/"audit_dataset"
            manifest=prepare_p9_roundtrip_colmap_dataset(
                control_path,camera_path,dataset_root
            )

            self.assertEqual(manifest["schema"],"ConceptGhost.P10P9RoundtripDataset.v0.1")
            self.assertEqual(manifest["frame_count"],2)
            self.assertEqual(manifest["camera_count"],1)
            self.assertFalse(manifest["wan_pixels_present"])
            self.assertEqual(manifest["image_authority"],"P9_ONLY_GATE4_CONTROL_FRAME_NO_WAN")
            self.assertEqual(manifest["mission_order"],["drone_1"])
            self.assertTrue((dataset_root/"images"/"frame_000000.png").is_file())
            self.assertTrue((dataset_root/"images"/"frame_000001.png").is_file())
            self.assertTrue((dataset_root/"sparse"/"known"/"cameras.txt").is_file())
            self.assertTrue((dataset_root/"sparse"/"known"/"images.txt").is_file())
            self.assertEqual(len(manifest["frames"][0]["qvec"]),4)
            self.assertEqual(len(manifest["frames"][0]["tvec"]),3)

    def test_rejects_camera_control_identity_mismatch(self):
        from p10_lab.camera_sequence import CameraFrameRecord, CameraSequenceManifest
        from p10_lab.control_sequence import ControlFrameRecord, ControlSequenceManifest
        from p10_lab.p9_roundtrip_audit import prepare_p9_roundtrip_colmap_dataset

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            control_root=root/"control_sequence"
            frame_root=control_root/"frames"
            frame_root.mkdir(parents=True)
            (frame_root/"frame_0000.png").write_bytes(b"x")
            (frame_root/"frame_0001.png").write_bytes(b"y")

            control=ControlSequenceManifest(
                frames=(
                    ControlFrameRecord(0,"drone_1",0,0.1,"frames/frame_0000.png","masks/a.png"),
                    ControlFrameRecord(1,"drone_1",1,0.1,"frames/frame_0001.png","masks/b.png"),
                ),
                width=640,height=360,
                route_authority="ARTIST_AUTHORED",
                scene_contract_id="sceneA",source_run_id="run",
                mission_modes=(("drone_1","PATH"),),
            )
            control_path=control_root/"manifest.json"
            control_path.write_text(json.dumps(control.to_dict()),encoding="utf-8")

            frames=tuple(
                CameraFrameRecord(
                    global_frame_index=i,path_name="drone_1",path_frame_index=i,
                    width=640,height=360,fx=500,fy=500,cx=320,cy=180,
                    world_matrix=(
                        (1,0,0,float(i)),(0,1,0,0),(0,0,1,0),(0,0,0,1)
                    ),
                )
                for i in range(2)
            )
            cameras=CameraSequenceManifest(
                frames=frames,scene_contract_id="sceneB",
                route_authority="ARTIST_AUTHORED",source_run_id="run",
                mission_modes=(("drone_1","PATH"),),
            )
            camera_path=control_root/"camera_manifest.json"
            camera_path.write_text(json.dumps(cameras.to_dict()),encoding="utf-8")

            with self.assertRaises(ValueError):
                prepare_p9_roundtrip_colmap_dataset(
                    control_path,camera_path,root/"audit"
                )


if __name__=="__main__":
    unittest.main()
