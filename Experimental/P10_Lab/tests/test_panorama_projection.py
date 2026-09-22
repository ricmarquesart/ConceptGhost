import json
import unittest

from p10_lab.panorama import CameraAuthority, PanoramaSpec


def _camera():
    payload = {
        "valid": True,
        "scene_contract_id": "cgsc_projection_test",
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
            "camera_position": [0.0, 1.7, 0.0],
            "camera_world_matrix": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 1.7],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        },
    }
    return CameraAuthority.from_payload(
        payload,
        expected_scene_contract_id=payload["scene_contract_id"],
    )


class PanoramaProjectionTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.panorama_projection import (
                ProjectionPlan,
                build_projection_plan,
            )
        except ImportError as error:
            self.fail(f"Gate 3.2 projection module is missing: {error}")
        return ProjectionPlan, build_projection_plan

    def test_projection_plan_centers_authoritative_source_in_camera_local_erp(self):
        _, build_projection_plan = self._api()
        camera = _camera()
        spec = PanoramaSpec(width=4096, height=2048)

        plan = build_projection_plan(camera, spec)
        sample = plan.sample_continuous(2048.0, 1024.0)

        self.assertIsNotNone(sample)
        self.assertAlmostEqual(sample.source_x, camera.cx, places=8)
        self.assertAlmostEqual(sample.source_y, camera.cy, places=8)

    def test_projection_footprint_is_local_and_does_not_touch_erp_seam(self):
        _, build_projection_plan = self._api()
        plan = build_projection_plan(_camera(), PanoramaSpec(width=4096, height=2048))

        footprint = plan.footprint
        self.assertGreater(footprint.min_u, 0.0)
        self.assertLess(footprint.max_u, 4096.0)
        self.assertGreater(footprint.min_v, 0.0)
        self.assertLess(footprint.max_v, 2048.0)
        self.assertLess(footprint.width, 4096.0 / 2.0)
        self.assertLess(footprint.height, 2048.0 / 2.0)

    def test_projection_rejects_erp_pixels_outside_source_camera_fov(self):
        _, build_projection_plan = self._api()
        plan = build_projection_plan(_camera(), PanoramaSpec(width=2048, height=1024))

        self.assertIsNone(plan.sample_continuous(0.0, 512.0))
        self.assertIsNone(plan.sample_continuous(1024.0, 0.0))
        self.assertIsNone(plan.sample_continuous(2048.0, 512.0))

    def test_pixel_center_sampling_uses_half_pixel_convention(self):
        _, build_projection_plan = self._api()
        plan = build_projection_plan(_camera(), PanoramaSpec(width=2048, height=1024))

        a = plan.sample_pixel(1023, 511)
        b = plan.sample_continuous(1023.5, 511.5)

        self.assertEqual(a, b)

    def test_source_orientation_is_not_mirrored_or_flipped(self):
        _, build_projection_plan = self._api()
        camera = _camera()
        plan = build_projection_plan(camera, PanoramaSpec(width=4096, height=2048))

        left = plan.project_source(camera.cx - 200.0, camera.cy)
        right = plan.project_source(camera.cx + 200.0, camera.cy)
        top = plan.project_source(camera.cx, camera.cy - 150.0)
        bottom = plan.project_source(camera.cx, camera.cy + 150.0)

        self.assertLess(left.erp_u, 2048.0)
        self.assertGreater(right.erp_u, 2048.0)
        self.assertLess(top.erp_v, 1024.0)
        self.assertGreater(bottom.erp_v, 1024.0)

    def test_footprint_tracks_source_boundary_not_entire_panorama(self):
        _, build_projection_plan = self._api()
        plan = build_projection_plan(_camera(), PanoramaSpec(width=4096, height=2048))

        center_span = 4096.0 * (_camera().horizontal_fov_deg / 360.0)
        self.assertAlmostEqual(plan.footprint.width, center_span, delta=3.0)
        self.assertGreater(plan.footprint.boundary_samples, 8)

    def test_projection_plan_is_resolution_independent_in_angular_space(self):
        _, build_projection_plan = self._api()
        camera = _camera()
        low = build_projection_plan(camera, PanoramaSpec(width=2048, height=1024))
        high = build_projection_plan(camera, PanoramaSpec(width=4096, height=2048))

        low_center = low.project_source(200.0, 300.0)
        high_center = high.project_source(200.0, 300.0)

        self.assertAlmostEqual(high_center.erp_u, low_center.erp_u * 2.0, places=8)
        self.assertAlmostEqual(high_center.erp_v, low_center.erp_v * 2.0, places=8)


if __name__ == "__main__":
    unittest.main()
