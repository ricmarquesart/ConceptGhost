import math
import unittest

from p10_lab.path_planner import CameraPath, RelativeWaypoint


class RefinedEvidenceInterpolationTests(unittest.TestCase):
    def _interpolator(self):
        from p10_lab.refined_evidence import _interpolated_waypoints
        return _interpolated_waypoints

    def test_antipodal_turnaround_never_creates_zero_look_vector(self):
        interpolate = self._interpolator()
        path = CameraPath(
            "turnaround",
            (
                RelativeWaypoint(
                    right=0.0,
                    up=0.0,
                    forward=10.0,
                    look_right=0.0,
                    look_up=0.0,
                    look_forward=1.0,
                ),
                RelativeWaypoint(
                    right=0.0,
                    up=0.0,
                    forward=10.0,
                    look_right=0.0,
                    look_up=0.0,
                    look_forward=-1.0,
                ),
            ),
        )

        points = interpolate(path, 2)

        self.assertEqual(len(points), 3)
        for point in points:
            norm = math.sqrt(
                point.look_right ** 2
                + point.look_up ** 2
                + point.look_forward ** 2
            )
            self.assertGreater(norm, 0.999999)
            self.assertLess(norm, 1.000001)

        midpoint = points[1]
        self.assertGreater(abs(midpoint.look_right), 0.999)
        self.assertAlmostEqual(midpoint.look_forward, 0.0, places=8)

    def test_current_three_mission_plan_interpolates_without_zero_look_vectors(self):
        from p10_lab.scene_coverage import SceneFootprint, plan_geometry_aware_flights

        interpolate = self._interpolator()
        footprint = SceneFootprint(
            right_min=-3.1,
            right_max=9.6,
            up_min=-4.2,
            up_max=7.5,
            forward_near=7.5,
            forward_far=69.3,
            median_depth=11.1,
            true_forward_far=144.6,
        )
        plan = plan_geometry_aware_flights(footprint)

        self.assertEqual(len(plan.paths), 3)
        for path in plan.paths:
            points = interpolate(path, 2)
            for point in points:
                norm = math.sqrt(
                    point.look_right ** 2
                    + point.look_up ** 2
                    + point.look_forward ** 2
                )
                self.assertGreater(norm, 0.999999)

    def test_interpolation_preserves_position_lerp(self):
        interpolate = self._interpolator()
        path = CameraPath(
            "simple",
            (
                RelativeWaypoint(0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
                RelativeWaypoint(2.0, 4.0, 6.0, 1.0, 0.0, 0.0),
            ),
        )

        points = interpolate(path, 2)
        midpoint = points[1]

        self.assertAlmostEqual(midpoint.right, 1.0)
        self.assertAlmostEqual(midpoint.up, 2.0)
        self.assertAlmostEqual(midpoint.forward, 3.0)


if __name__ == "__main__":
    unittest.main()
