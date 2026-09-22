import math
import unittest

from p10_lab.path_planner import CameraPath, RelativeWaypoint


class ClearanceTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.clearance import (
                ClearanceConfig,
                adapt_path_for_clearance,
                sample_path_waypoints,
            )
        except ImportError as error:
            self.fail(f"Gate 4.2 clearance module is missing: {error}")
        return ClearanceConfig, adapt_path_for_clearance, sample_path_waypoints

    def test_safe_path_is_preserved_exactly(self):
        Config, adapt, _ = self._api()
        path = CameraPath(
            "safe",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(1.0, 0.2, 0.5),
                RelativeWaypoint(2.0, 0.3, 1.0),
            ),
        )
        result = adapt(
            path,
            lambda point: 10.0,
            Config(min_clearance=1.0, samples_per_segment=4),
        )
        self.assertFalse(result.adapted)
        self.assertFalse(result.blocked)
        self.assertEqual(result.path, path)
        self.assertGreaterEqual(result.minimum_clearance, 10.0)

    def test_unsafe_path_shrinks_until_clearance_passes(self):
        Config, adapt, _ = self._api()
        path = CameraPath(
            "needs_shrink",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(4.0, 0.0, 0.0),
            ),
        )

        def clearance(point):
            return 5.0 - abs(point.right)

        result = adapt(
            path,
            clearance,
            Config(
                min_clearance=2.0,
                samples_per_segment=8,
                shrink_factor=0.75,
                max_shrink_attempts=6,
            ),
        )

        self.assertTrue(result.adapted)
        self.assertFalse(result.blocked)
        self.assertGreaterEqual(result.minimum_clearance, 2.0)
        self.assertLess(result.path.waypoints[-1].right, 4.0)
        self.assertGreater(result.path.waypoints[-1].right, 0.0)

    def test_origin_collision_blocks_path_fail_closed(self):
        Config, adapt, _ = self._api()
        path = CameraPath(
            "origin_bad",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(1.0, 0.0, 0.0),
            ),
        )
        result = adapt(
            path,
            lambda point: 0.2 if point.right == 0.0 else 10.0,
            Config(min_clearance=1.0),
        )
        self.assertTrue(result.blocked)
        self.assertFalse(result.adapted)
        self.assertIn("origin", result.reason.lower())

    def test_nonfinite_clearance_blocks_instead_of_passing(self):
        Config, adapt, _ = self._api()
        path = CameraPath(
            "nan",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(1.0, 0.0, 0.0),
            ),
        )
        result = adapt(path, lambda point: float("nan"), Config(min_clearance=1.0))
        self.assertTrue(result.blocked)

    def test_sampling_covers_segment_endpoints_and_interior(self):
        _, _, sample = self._api()
        path = CameraPath(
            "sample",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(2.0, 0.0, 1.0),
            ),
        )
        points = sample(path, 4)
        self.assertEqual(points[0], path.waypoints[0])
        self.assertEqual(points[-1], path.waypoints[-1])
        self.assertEqual(len(points), 5)
        self.assertAlmostEqual(points[2].right, 1.0)
        self.assertAlmostEqual(points[2].forward, 0.5)

    def test_invalid_config_is_rejected(self):
        Config, _, _ = self._api()
        with self.assertRaises(ValueError):
            Config(min_clearance=0.0)
        with self.assertRaises(ValueError):
            Config(samples_per_segment=0)
        with self.assertRaises(ValueError):
            Config(shrink_factor=1.0)
        with self.assertRaises(ValueError):
            Config(min_clearance=float("nan"))


if __name__ == "__main__":
    unittest.main()
