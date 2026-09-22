import hashlib
import unittest

from p10_lab.panorama import CameraAuthority, PanoramaSpec
from p10_lab.panorama_projection import build_projection_plan


def _camera():
    payload = {
        "valid": True,
        "scene_contract_id": "cgsc_observation_test",
        "schema": "ConceptGhost.CameraBundle.v0.8",
        "image_width": 800,
        "image_height": 600,
        "horizontal_fov_deg": 43.60281897270362,
        "intrinsics": {
            "fx_px": 1000.0,
            "fy_px": 1000.0,
            "cx_px": 400.0,
            "cy_px": 300.0,
            "lens_model": "pinhole",
            "distortion": {},
        },
        "extrinsics": {
            "camera_position": [0.0, 1.5, 0.0],
            "camera_world_matrix": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 1.5],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        },
    }
    return CameraAuthority.from_payload(
        payload,
        expected_scene_contract_id=payload["scene_contract_id"],
    )


class ObservationMapTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.observation_map import (
                SOURCE_LOCK_POLICY,
                build_observation_map,
            )
        except ImportError as error:
            self.fail(f"Gate 3.3 observation-map module is missing: {error}")
        return SOURCE_LOCK_POLICY, build_observation_map

    def test_source_center_is_observed_and_erp_seam_is_unknown(self):
        _, build_observation_map = self._api()
        spec = PanoramaSpec(width=512, height=256)
        observed = build_observation_map(build_projection_plan(_camera(), spec))

        self.assertTrue(observed.is_observed(256, 128))
        self.assertFalse(observed.is_unknown(256, 128))
        self.assertTrue(observed.is_unknown(0, 128))
        self.assertTrue(observed.is_unknown(511, 128))

    def test_source_lock_and_unknown_masks_are_exact_complements(self):
        _, build_observation_map = self._api()
        spec = PanoramaSpec(width=512, height=256)
        observed = build_observation_map(build_projection_plan(_camera(), spec))

        lock = observed.source_lock_bytes()
        unknown = observed.unknown_mask_bytes()

        self.assertEqual(len(lock), 512 * 256)
        self.assertEqual(len(unknown), len(lock))
        for left, right in zip(lock, unknown):
            self.assertIn(left, (0, 255))
            self.assertEqual(left + right, 255)

    def test_observed_rows_are_contiguous_and_bounded_away_from_seam(self):
        _, build_observation_map = self._api()
        observed = build_observation_map(
            build_projection_plan(_camera(), PanoramaSpec(width=1024, height=512))
        )

        nonempty = [span for span in observed.row_spans if span is not None]
        self.assertGreater(len(nonempty), 1)
        self.assertTrue(all(span.start_x > 0 for span in nonempty))
        self.assertTrue(all(span.end_x < 1024 for span in nonempty))
        self.assertTrue(all(span.start_x < span.end_x for span in nonempty))

    def test_manifest_makes_source_authority_and_counts_explicit(self):
        SOURCE_LOCK_POLICY, build_observation_map = self._api()
        observed = build_observation_map(
            build_projection_plan(_camera(), PanoramaSpec(width=512, height=256))
        )
        manifest = observed.manifest()

        self.assertEqual(manifest["policy"], SOURCE_LOCK_POLICY)
        self.assertEqual(manifest["observed_value"], 255)
        self.assertEqual(manifest["unknown_value"], 0)
        self.assertEqual(
            manifest["observed_pixel_count"] + manifest["unknown_pixel_count"],
            512 * 256,
        )
        self.assertGreater(manifest["observed_pixel_count"], 0)
        self.assertLess(manifest["observed_fraction"], 0.10)

    def test_map_is_deterministic_for_same_camera_and_erp_spec(self):
        _, build_observation_map = self._api()
        plan = build_projection_plan(_camera(), PanoramaSpec(width=512, height=256))

        first = build_observation_map(plan)
        second = build_observation_map(plan)

        self.assertEqual(first.source_lock_bytes(), second.source_lock_bytes())
        self.assertEqual(
            hashlib.sha256(first.source_lock_bytes()).hexdigest(),
            first.sha256,
        )

    def test_out_of_bounds_pixel_query_is_rejected(self):
        _, build_observation_map = self._api()
        observed = build_observation_map(
            build_projection_plan(_camera(), PanoramaSpec(width=512, height=256))
        )

        with self.assertRaises(ValueError):
            observed.is_observed(-1, 0)
        with self.assertRaises(ValueError):
            observed.is_unknown(512, 0)


if __name__ == "__main__":
    unittest.main()
