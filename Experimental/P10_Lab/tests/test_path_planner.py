import unittest

from p10_lab.contracts import ContractError, SceneScale
from p10_lab.path_planner import FlightPlanConfig, plan_flights


class FlightPlannerTests(unittest.TestCase):
    def test_default_plan_has_three_initial_flights_and_one_adaptive_slot(self):
        plan = plan_flights(SceneScale(10.0), FlightPlanConfig())

        self.assertEqual(
            [path.name for path in plan.initial_paths],
            ["left_arc", "right_arc", "forward_probe"],
        )
        self.assertEqual(plan.adaptive_path_budget, 1)
        self.assertEqual(plan.maximum_flights, 4)

    def test_ten_initial_flights_use_one_reusable_data_driven_plan(self):
        plan = plan_flights(
            SceneScale(10.0),
            FlightPlanConfig(initial_path_count=10, adaptive_path_budget=2),
        )

        self.assertEqual(len(plan.initial_paths), 10)
        self.assertEqual(plan.initial_paths[3].name, "coverage_probe_04")
        self.assertEqual(plan.initial_paths[-1].name, "coverage_probe_10")
        self.assertEqual(len({path.name for path in plan.initial_paths}), 10)
        self.assertEqual(plan.maximum_flights, 12)
        self.assertLessEqual(
            max(abs(point.right) for path in plan.initial_paths for point in path.waypoints),
            3.0,
        )

    def test_negative_or_empty_flight_configuration_is_rejected(self):
        with self.assertRaises(ContractError):
            FlightPlanConfig(initial_path_count=0)
        with self.assertRaises(ContractError):
            FlightPlanConfig(adaptive_path_budget=-1)

    def test_scene_scale_and_envelope_limits_must_be_finite(self):
        for radius in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(radius=radius), self.assertRaises(ContractError):
                SceneScale(radius)
        with self.assertRaises(ContractError):
            FlightPlanConfig(lateral_limit_fraction=float("nan"))

    def test_tight_envelope_bounds_apply_to_original_three_paths_too(self):
        scale = SceneScale(10.0)
        config = FlightPlanConfig(
            lateral_limit_fraction=0.01,
            forward_limit_fraction=0.02,
            elevation_limit_fraction=0.005,
        )

        plan = plan_flights(scale, config)

        for path in plan.initial_paths:
            for point in path.waypoints:
                self.assertLessEqual(abs(point.right), 0.1)
                self.assertLessEqual(abs(point.forward), 0.2)
                self.assertLessEqual(abs(point.up), 0.05)


if __name__ == "__main__":
    unittest.main()
