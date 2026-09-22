import math
import unittest


class GeometryAdaptiveFlightTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.scene_coverage import (
                SceneFootprint,
                GeometryFlightConfig,
                plan_geometry_aware_flights,
            )
        except ImportError as error:
            self.fail(f"Geometry-aware flight planner is missing: {error}")
        return SceneFootprint, GeometryFlightConfig, plan_geometry_aware_flights

    def _long_scene(self):
        SceneFootprint, _, _ = self._api()
        return SceneFootprint(
            right_min=-3.1,
            right_max=9.6,
            up_min=-4.2,
            up_max=7.5,
            forward_near=7.5,
            forward_far=69.3,
            median_depth=11.1,
            true_forward_far=144.6,
        )

    def test_long_scene_gets_entry_center_outbound_and_reverse_passes(self):
        _, _, plan = self._api()
        result = plan(self._long_scene())
        self.assertEqual(
            [path.name for path in result.paths],
            [
                "entry_micro_orbit_360",
                "center_micro_orbit_360",
                "outbound_scene_traverse",
                "return_scene_traverse",
            ],
        )

    def test_micro_orbits_cover_full_yaw_including_backward(self):
        _, _, plan = self._api()
        result = plan(self._long_scene())

        for path in result.paths[:2]:
            looks = [(p.look_right, p.look_forward) for p in path.waypoints]
            self.assertTrue(any(r > 0.95 and abs(f) < 0.2 for r, f in looks))
            self.assertTrue(any(r < -0.95 and abs(f) < 0.2 for r, f in looks))
            self.assertTrue(any(f < -0.95 and abs(r) < 0.2 for r, f in looks))
            self.assertTrue(any(f > 0.95 and abs(r) < 0.2 for r, f in looks))

    def test_center_orbit_anchor_tracks_mesh_center_not_camera_origin(self):
        _, _, plan = self._api()
        footprint = self._long_scene()
        result = plan(footprint)
        center = result.paths[1]
        average_forward = sum(p.forward for p in center.waypoints[:-1]) / (len(center.waypoints) - 1)
        self.assertAlmostEqual(average_forward, footprint.center_forward, delta=0.25)

    def test_outbound_crosses_most_of_scene_and_slightly_passes_robust_far_edge(self):
        _, _, plan = self._api()
        footprint = self._long_scene()
        result = plan(footprint)
        outbound = result.paths[2]
        self.assertAlmostEqual(outbound.waypoints[0].forward, 0.0, places=8)
        self.assertGreater(outbound.waypoints[-1].forward, footprint.forward_far)
        self.assertLess(outbound.waypoints[-1].forward, footprint.true_forward_far)
        self.assertGreater(len(outbound.waypoints), 5)

    def test_return_starts_far_and_finishes_near_camera_while_looking_back(self):
        _, _, plan = self._api()
        result = plan(self._long_scene())
        reverse = result.paths[3]

        self.assertGreater(reverse.waypoints[0].forward, 60.0)
        self.assertAlmostEqual(reverse.waypoints[-1].forward, 0.0, places=8)
        self.assertTrue(all(p.look_forward < 0.0 for p in reverse.waypoints))

    def test_orbit_radius_adapts_to_scene_size_and_is_small(self):
        SceneFootprint, _, plan = self._api()
        long_result = plan(self._long_scene())
        compact = SceneFootprint(
            right_min=-2.0, right_max=2.0,
            up_min=-1.5, up_max=2.0,
            forward_near=3.0, forward_far=10.0,
            median_depth=6.0, true_forward_far=11.0,
        )
        compact_result = plan(compact)

        self.assertGreater(long_result.orbit_radius, compact_result.orbit_radius)
        self.assertLess(long_result.orbit_radius, self._long_scene().lateral_span * 0.15)
        self.assertLess(compact_result.orbit_radius, compact.lateral_span * 0.15)

    def test_invalid_footprint_fails_closed(self):
        SceneFootprint, _, _ = self._api()
        with self.assertRaises(ValueError):
            SceneFootprint(
                right_min=1.0, right_max=-1.0,
                up_min=-1.0, up_max=1.0,
                forward_near=1.0, forward_far=10.0,
                median_depth=5.0, true_forward_far=11.0,
            )


if __name__ == "__main__":
    unittest.main()
