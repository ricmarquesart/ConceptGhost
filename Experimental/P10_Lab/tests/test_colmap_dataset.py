import json
import tempfile
import unittest
from pathlib import Path


class KnownCameraColmapDatasetTests(unittest.TestCase):
    def _stub_inputs(self, root: Path, *, frame_count=2):
        comp = root / "composite" / "00_a"
        comp.mkdir(parents=True, exist_ok=True)
        for i in range(frame_count):
            (comp / f"frame_{i:04d}.png").write_bytes(b"png" + bytes([i]))

        wan = {
            "run_id": "run1",
            "effective_dimensions": {"width": 832, "height": 480, "mode": "UNCHANGED"},
            "windows": [{
                "window_index": 0,
                "name": "a",
                "source_start": 0,
                "source_end": frame_count,
                "decoded_frame_count": frame_count,
                "composite_dir": str(comp),
            }],
        }
        frames = []
        for i in range(frame_count):
            frames.append({
                "global_frame_index": i,
                "path_name": "a",
                "path_frame_index": i,
                "camera": {
                    "model": "PINHOLE",
                    "width": 640,
                    "height": 360,
                    "fx": 700.0,
                    "fy": 701.0,
                    "cx": 320.0,
                    "cy": 180.0,
                    "world_matrix": [
                        [1.0, 0.0, 0.0, float(i)],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                },
            })
        cameras = {
            "scene_contract_id": "scene1",
            "frames": frames,
        }
        wp = root / "wan.json"
        cp = root / "cameras.json"
        wp.write_text(json.dumps(wan), encoding="utf-8")
        cp.write_text(json.dumps(cameras), encoding="utf-8")
        return wp, cp

    def test_identity_maya_camera_converts_to_colmap_forward_positive_z(self):
        from p10_lab.colmap_dataset import world_matrix_to_colmap_pose

        qvec, tvec = world_matrix_to_colmap_pose([
            [1.0,0.0,0.0,0.0],
            [0.0,1.0,0.0,0.0],
            [0.0,0.0,1.0,0.0],
            [0.0,0.0,0.0,1.0],
        ])
        self.assertAlmostEqual(tvec[0], 0.0)
        self.assertAlmostEqual(tvec[1], 0.0)
        self.assertAlmostEqual(tvec[2], 0.0)
        self.assertAlmostEqual(abs(qvec[0]), 0.0, places=6)
        self.assertAlmostEqual(abs(qvec[1]), 1.0, places=6)
        self.assertAlmostEqual(abs(qvec[2]), 0.0, places=6)
        self.assertAlmostEqual(abs(qvec[3]), 0.0, places=6)

    def test_translation_is_converted_to_world_to_camera_tvec(self):
        from p10_lab.colmap_dataset import world_matrix_to_colmap_pose

        _, tvec = world_matrix_to_colmap_pose([
            [1.0,0.0,0.0,2.0],
            [0.0,1.0,0.0,3.0],
            [0.0,0.0,1.0,4.0],
            [0.0,0.0,0.0,1.0],
        ])
        self.assertAlmostEqual(tvec[0], -2.0, places=6)
        self.assertAlmostEqual(tvec[1], 3.0, places=6)
        self.assertAlmostEqual(tvec[2], 4.0, places=6)

    def test_materializes_known_camera_colmap_dataset(self):
        from p10_lab.colmap_dataset import prepare_known_camera_colmap_dataset

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wp, cp = self._stub_inputs(root)
            out = root / "dataset"
            result = prepare_known_camera_colmap_dataset(wp, cp, out)

            self.assertEqual(result["frame_count"], 2)
            self.assertEqual(result["camera_count"], 1)
            self.assertEqual(result["scene_contract_id"], "scene1")
            self.assertEqual(result["reconstruction_strategy"], "KNOWN_CAMERA_COLMAP_PRIMARY")
            self.assertEqual(
                result["spheresfm_role"],
                "OPTIONAL_ERP_VALIDATION_NOT_PRIMARY_POSE_SOLVER",
            )

            self.assertTrue((out / "images" / "frame_000000.png").is_file())
            self.assertTrue((out / "images" / "frame_000001.png").is_file())
            self.assertTrue((out / "sparse" / "known" / "cameras.txt").is_file())
            self.assertTrue((out / "sparse" / "known" / "images.txt").is_file())
            self.assertTrue((out / "sparse" / "known" / "points3D.txt").is_file())
            self.assertTrue((out / "dataset_manifest.json").is_file())
            self.assertTrue((out / "reconstruction_inputs.json").is_file())

            cameras_txt = (out / "sparse" / "known" / "cameras.txt").read_text(encoding="utf-8")
            self.assertIn("1 PINHOLE 832 480", cameras_txt)
            self.assertEqual(
                result["camera_image_mapping_policy"],
                "COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
            )
            self.assertEqual(result["schema"], "ConceptGhost.P10KnownCameraColmapDataset.v0.2")
            self.assertEqual(result["composite_dimensions"], {"width": 832, "height": 480})
            self.assertIn("wan_manifest_sha256", result["source_inputs"])
            self.assertIn("camera_manifest_sha256", result["source_inputs"])

            images_txt = (out / "sparse" / "known" / "images.txt").read_text(encoding="utf-8")
            self.assertIn("frame_000000.png", images_txt)
            self.assertIn("frame_000001.png", images_txt)

    def test_existing_nonempty_dataset_fails_closed_without_overwrite(self):
        from p10_lab.colmap_dataset import prepare_known_camera_colmap_dataset

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wp, cp = self._stub_inputs(root, frame_count=1)
            out = root / "dataset"
            out.mkdir()
            (out / "keep.txt").write_text("do not delete", encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare_known_camera_colmap_dataset(wp, cp, out)


if __name__ == "__main__":
    unittest.main()
