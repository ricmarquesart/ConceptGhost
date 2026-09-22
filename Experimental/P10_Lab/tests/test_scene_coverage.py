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

    def test_stabilization_profile_uses_exactly_three_geometry_aware_missions(self):
        _, _, plan = self._api()
        result = plan(self._long_scene())
        self.assertEqual(
            [path.name for path in result.paths],
            [
                "entry_micro_orbit_360",
                "center_micro_orbit_360",
                "scene_round_trip",
            ],
        )
        self.assertEqual(len(result.paths), 3)

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
        average_forward = sum(
            p.forward for p in center.waypoints[:-1]
        ) / (len(center.waypoints) - 1)
        self.assertAlmostEqual(
            average_forward,
            footprint.center_forward,
            delta=0.25,
        )

    def test_round_trip_crosses_scene_and_returns_to_camera_region(self):
        _, _, plan = self._api()
        footprint = self._long_scene()
        result = plan(footprint)
        round_trip = result.paths[2]

        forwards = [p.forward for p in round_trip.waypoints]
        far_index = forwards.index(max(forwards))

        self.assertAlmostEqual(round_trip.waypoints[0].forward, 0.0, places=8)
        self.assertGreater(max(forwards), footprint.forward_far)
        self.assertLess(max(forwards), footprint.true_forward_far)
        self.assertAlmostEqual(round_trip.waypoints[-1].forward, 0.0, places=8)
        self.assertGreater(far_index, 0)
        self.assertLess(far_index, len(round_trip.waypoints) - 1)

    def test_round_trip_changes_view_direction_after_far_turnaround(self):
        _, _, plan = self._api()
        round_trip = plan(self._long_scene()).paths[2]
        forwards = [p.forward for p in round_trip.waypoints]
        far_index = forwards.index(max(forwards))

        outbound = round_trip.waypoints[:far_index]
        inbound = round_trip.waypoints[far_index + 1 :]

        self.assertTrue(outbound)
        self.assertTrue(inbound)
        self.assertTrue(all(p.look_forward > 0.0 for p in outbound))
        self.assertTrue(all(p.look_forward < 0.0 for p in inbound))

    def test_orbit_radius_adapts_to_scene_size_and_is_small(self):
        SceneFootprint, _, plan = self._api()
        long_result = plan(self._long_scene())
        compact = SceneFootprint(
            right_min=-2.0,
            right_max=2.0,
            up_min=-1.5,
            up_max=2.0,
            forward_near=3.0,
            forward_far=10.0,
            median_depth=6.0,
            true_forward_far=11.0,
        )
        compact_result = plan(compact)

        self.assertGreater(long_result.orbit_radius, compact_result.orbit_radius)
        self.assertLess(
            long_result.orbit_radius,
            self._long_scene().lateral_span * 0.15,
        )
        self.assertLess(
            compact_result.orbit_radius,
            compact.lateral_span * 0.15,
        )

    def test_planner_contract_remains_data_driven_for_future_larger_budgets(self):
        _, GeometryFlightConfig, _ = self._api()
        config = GeometryFlightConfig()
        self.assertEqual(config.stabilization_mission_count, 3)
        self.assertGreaterEqual(config.future_supported_mission_budget_max, 10)

    def test_invalid_footprint_fails_closed(self):
        SceneFootprint, _, _ = self._api()
        with self.assertRaises(ValueError):
            SceneFootprint(
                right_min=1.0,
                right_max=-1.0,
                up_min=-1.0,
                up_max=1.0,
                forward_near=1.0,
                forward_far=10.0,
                median_depth=5.0,
                true_forward_far=11.0,
            )


if __name__ == "__main__":
    unittest.main()
