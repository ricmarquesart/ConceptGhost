import unittest


class CameraSequenceTests(unittest.TestCase):
    def test_camera_frame_manifest_preserves_pose_and_intrinsics(self):
        from p10_lab.camera_sequence import CameraFrameRecord, CameraSequenceManifest

        frame = CameraFrameRecord(
            global_frame_index=0,
            path_name="entry_micro_orbit_360",
            path_frame_index=0,
            width=640,
            height=360,
            fx=700.0,
            fy=701.0,
            cx=320.0,
            cy=180.0,
            world_matrix=(
                (1.0,0.0,0.0,1.0),
                (0.0,1.0,0.0,2.0),
                (0.0,0.0,1.0,3.0),
                (0.0,0.0,0.0,1.0),
            ),
        )
        payload=CameraSequenceManifest(frames=(frame,)).to_dict()
        self.assertEqual(payload["frame_count"],1)
        self.assertEqual(payload["frames"][0]["path_name"],"entry_micro_orbit_360")
        self.assertEqual(payload["frames"][0]["camera"]["model"],"PINHOLE")
        self.assertEqual(payload["frames"][0]["camera"]["world_matrix"][2][3],3.0)

    def test_global_indexes_must_be_contiguous(self):
        from p10_lab.camera_sequence import CameraFrameRecord, CameraSequenceManifest
        def frame(i):
            return CameraFrameRecord(
                global_frame_index=i,path_name="a",path_frame_index=i,
                width=640,height=360,fx=700,fy=700,cx=320,cy=180,
                world_matrix=((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)),
            )
        with self.assertRaises(ValueError):
            CameraSequenceManifest(frames=(frame(0),frame(2)))

    def test_nonfinite_pose_is_rejected(self):
        from p10_lab.camera_sequence import CameraFrameRecord
        with self.assertRaises(ValueError):
            CameraFrameRecord(
                global_frame_index=0,path_name="a",path_frame_index=0,
                width=640,height=360,fx=700,fy=700,cx=320,cy=180,
                world_matrix=((1,0,0,float("nan")),(0,1,0,0),(0,0,1,0),(0,0,0,1)),
            )


if __name__=="__main__":
    unittest.main()
