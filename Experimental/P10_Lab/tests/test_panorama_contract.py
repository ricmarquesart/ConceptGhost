import json
import math
import tempfile
import unittest
from pathlib import Path


class PanoramaContractTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.panorama import (
                CameraAuthority,
                PanoramaSpec,
                camera_ray_to_source_pixel,
                erp_pixel_to_camera_ray,
                source_pixel_to_erp,
            )
        except ImportError as error:
            self.fail(f"Gate 3.1 panorama contract module is missing: {error}")
        return (
            CameraAuthority,
            PanoramaSpec,
            camera_ray_to_source_pixel,
            erp_pixel_to_camera_ray,
            source_pixel_to_erp,
        )

    @staticmethod
    def _real_v153_camera_payload():
        return {
            "valid": True,
            "scene_contract_id": "cgsc_legacy_8f72c73ab923f5801558",
            "schema": "ConceptGhost.CameraBundle.v0.8",
            "image_width": 1448,
            "image_height": 1086,
            "horizontal_fov_deg": 36.83175195590167,
            "intrinsics": {
                "fx_px": 2174.4124890692074,
                "fy_px": 2174.4124890692074,
                "cx_px": 724.0,
                "cy_px": 543.0,
                "lens_model": "pinhole",
                "distortion": {},
            },
            "extrinsics": {
                "camera_position": [0.0, 1.7325509134129196, 0.0],
                "camera_world_matrix": [
                    [0.9999498562934125, 0.010009220431606377, -0.00031686769398751267, 0.0],
                    [-0.010014234807711445, 0.9994491565632839, -0.031640141373841864, 1.7325509134129196],
                    [5.421010862427522e-20, 0.03164172800736699, 0.999499275161672, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
            },
        }

    def test_real_v153_camera_contract_parses_and_recomputes_fov(self):
        CameraAuthority, _, _, _, _ = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "camera.json"
            path.write_text(json.dumps(self._real_v153_camera_payload()), encoding="utf-8")
            camera = CameraAuthority.from_json(
                path,
                expected_scene_contract_id="cgsc_legacy_8f72c73ab923f5801558",
            )

        self.assertEqual(camera.width, 1448)
        self.assertEqual(camera.height, 1086)
        self.assertEqual(camera.lens_model, "pinhole")
        self.assertAlmostEqual(camera.horizontal_fov_deg, 36.83175195590167, places=8)
        self.assertAlmostEqual(camera.vertical_fov_deg, 28.042570114135742, places=6)

    def test_source_center_maps_to_erp_center(self):
        CameraAuthority, PanoramaSpec, _, _, source_pixel_to_erp = self._api()
        payload = self._real_v153_camera_payload()
        camera = CameraAuthority.from_payload(
            payload,
            expected_scene_contract_id=payload["scene_contract_id"],
        )
        spec = PanoramaSpec(width=2048, height=1024)

        u, v = source_pixel_to_erp(camera, spec, camera.cx, camera.cy)

        self.assertAlmostEqual(u, 1024.0, places=9)
        self.assertAlmostEqual(v, 512.0, places=9)

    def test_source_edges_land_symmetrically_around_erp_center_for_centered_principal_point(self):
        CameraAuthority, PanoramaSpec, _, _, source_pixel_to_erp = self._api()
        payload = self._real_v153_camera_payload()
        camera = CameraAuthority.from_payload(
            payload,
            expected_scene_contract_id=payload["scene_contract_id"],
        )
        spec = PanoramaSpec(width=4096, height=2048)

        left_u, _ = source_pixel_to_erp(camera, spec, 0.0, camera.cy)
        right_u, _ = source_pixel_to_erp(camera, spec, float(camera.width), camera.cy)

        self.assertAlmostEqual(2048.0 - left_u, right_u - 2048.0, places=8)

    def test_erp_ray_round_trip_recovers_source_pixel_inside_source_fov(self):
        CameraAuthority, PanoramaSpec, camera_ray_to_source_pixel, erp_pixel_to_camera_ray, source_pixel_to_erp = self._api()
        payload = self._real_v153_camera_payload()
        camera = CameraAuthority.from_payload(
            payload,
            expected_scene_contract_id=payload["scene_contract_id"],
        )
        spec = PanoramaSpec(width=4096, height=2048)

        source = (403.25, 721.75)
        erp = source_pixel_to_erp(camera, spec, *source)
        ray = erp_pixel_to_camera_ray(spec, *erp)
        recovered = camera_ray_to_source_pixel(camera, ray)

        self.assertAlmostEqual(recovered[0], source[0], places=7)
        self.assertAlmostEqual(recovered[1], source[1], places=7)

    def test_non_pinhole_or_distorted_camera_is_rejected_fail_closed(self):
        CameraAuthority, _, _, _, _ = self._api()
        payload = self._real_v153_camera_payload()

        bad_lens = json.loads(json.dumps(payload))
        bad_lens["intrinsics"]["lens_model"] = "fisheye"
        with self.assertRaises(ValueError):
            CameraAuthority.from_payload(
                bad_lens,
                expected_scene_contract_id=payload["scene_contract_id"],
            )

        distorted = json.loads(json.dumps(payload))
        distorted["intrinsics"]["distortion"] = {"k1": 0.1}
        with self.assertRaises(ValueError):
            CameraAuthority.from_payload(
                distorted,
                expected_scene_contract_id=payload["scene_contract_id"],
            )

    def test_world_matrix_must_be_finite_rigid_and_affine(self):
        CameraAuthority, _, _, _, _ = self._api()
        payload = self._real_v153_camera_payload()

        malformed = json.loads(json.dumps(payload))
        malformed["extrinsics"]["camera_world_matrix"][3] = [0.0, 0.0, 1.0, 1.0]
        with self.assertRaises(ValueError):
            CameraAuthority.from_payload(
                malformed,
                expected_scene_contract_id=payload["scene_contract_id"],
            )

        scaled = json.loads(json.dumps(payload))
        scaled["extrinsics"]["camera_world_matrix"][0][0] = 2.0
        with self.assertRaises(ValueError):
            CameraAuthority.from_payload(
                scaled,
                expected_scene_contract_id=payload["scene_contract_id"],
            )

    def test_panorama_spec_is_strictly_two_to_one(self):
        _, PanoramaSpec, _, _, _ = self._api()

        valid = PanoramaSpec(width=2048, height=1024)
        self.assertEqual(valid.aspect_ratio, 2.0)

        with self.assertRaises(ValueError):
            PanoramaSpec(width=2048, height=1000)
        with self.assertRaises(ValueError):
            PanoramaSpec(width=0, height=0)


if __name__ == "__main__":
    unittest.main()
