import unittest

from p10_lab.contracts import SceneScale
from p10_lab.observation_map import build_observation_map
from p10_lab.panorama import CameraAuthority, PanoramaSpec
from p10_lab.panorama_projection import build_projection_plan
from p10_lab.path_planner import FlightPlanConfig, plan_flights


def _camera():
    payload = {
        "valid": True,
        "scene_contract_id": "cgsc_envelope_test",
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


class CompletionEnvelopeTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.completion_envelope import (
                CompletionEnvelopeConfig,
                build_completion_envelope,
                build_generation_candidate_map,
            )
        except ImportError as error:
            self.fail(f"Gate 3.4 completion-envelope module is missing: {error}")
        return CompletionEnvelopeConfig, build_completion_envelope, build_generation_candidate_map

    def test_default_envelope_contains_all_default_initial_flight_offsets(self):
        _, build_completion_envelope, _ = self._api()
        scale = SceneScale(10.0)
        envelope = build_completion_envelope(_camera(), scale)
        plan = plan_flights(scale, FlightPlanConfig())

        for path in plan.initial_paths:
            for point in path.waypoints:
                self.assertTrue(
                    envelope.contains_offset(point.right, point.up, point.forward),
                    msg=f"{path.name} point escaped default completion envelope",
                )

    def test_default_envelope_rejects_world_scale_exploration(self):
        _, build_completion_envelope, _ = self._api()
        envelope = build_completion_envelope(_camera(), SceneScale(10.0))

        self.assertFalse(envelope.contains_offset(5.0, 0.0, 0.0))
        self.assertFalse(envelope.contains_offset(0.0, 2.0, 0.0))
        self.assertFalse(envelope.contains_offset(0.0, 0.0, 5.0))
        self.assertFalse(envelope.contains_offset(0.0, 0.0, -1.0))

    def test_angular_envelope_excludes_rear_hemisphere_and_erp_poles(self):
        _, build_completion_envelope, _ = self._api()
        envelope = build_completion_envelope(_camera(), SceneScale(10.0))

        self.assertTrue(envelope.contains_camera_ray((0.0, 0.0, -1.0)))
        self.assertFalse(envelope.contains_camera_ray((0.0, 0.0, 1.0)))
        self.assertFalse(envelope.contains_camera_ray((0.0, 1.0, 0.0)))
        self.assertFalse(envelope.contains_camera_ray((0.0, -1.0, 0.0)))

    def test_generation_candidates_are_unknown_and_inside_local_angular_envelope_only(self):
        _, build_completion_envelope, build_generation_candidate_map = self._api()
        camera = _camera()
        spec = PanoramaSpec(width=512, height=256)
        projection = build_projection_plan(camera, spec)
        observed = build_observation_map(projection)
        envelope = build_completion_envelope(camera, SceneScale(10.0))

        candidates = build_generation_candidate_map(projection, observed, envelope)

        self.assertFalse(candidates.is_candidate(256, 128))
        self.assertFalse(candidates.is_candidate(0, 128))
        self.assertFalse(candidates.is_candidate(256, 0))
        self.assertGreater(candidates.candidate_pixel_count, 0)
        self.assertLess(candidates.candidate_fraction, 0.50)

        for y in range(spec.height):
            for x in range(spec.width):
                if candidates.is_candidate(x, y):
                    self.assertTrue(observed.is_unknown(x, y))

    def test_candidate_mask_uses_255_only_for_allowed_unknown_pixels(self):
        _, build_completion_envelope, build_generation_candidate_map = self._api()
        camera = _camera()
        spec = PanoramaSpec(width=256, height=128)
        projection = build_projection_plan(camera, spec)
        observed = build_observation_map(projection)
        candidates = build_generation_candidate_map(
            projection,
            observed,
            build_completion_envelope(camera, SceneScale(10.0)),
        )

        mask = candidates.mask_bytes()
        self.assertEqual(len(mask), 256 * 128)
        self.assertTrue(set(mask).issubset({0, 255}))
        self.assertEqual(mask[128 * 64 + 128], 0)

    def test_invalid_envelope_configuration_fails_closed(self):
        CompletionEnvelopeConfig, _, _ = self._api()

        with self.assertRaises(ValueError):
            CompletionEnvelopeConfig(lateral_limit_fraction=0.0)
        with self.assertRaises(ValueError):
            CompletionEnvelopeConfig(max_yaw_deg=180.0)
        with self.assertRaises(ValueError):
            CompletionEnvelopeConfig(pitch_margin_deg=float("nan"))


if __name__ == "__main__":
    unittest.main()
