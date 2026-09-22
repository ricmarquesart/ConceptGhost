import unittest


class FlightScaleTests(unittest.TestCase):
    def _selector(self):
        try:
            from p10_lab.flight_scale import select_local_flight_radius
        except ImportError as error:
            self.fail(f"Gate 4.1 robust flight-scale module is missing: {error}")
        return select_local_flight_radius

    def test_uses_median_camera_depth_not_far_outlier_radius(self):
        select = self._selector()

        radius, evidence = select([10.0, 11.0, 12.0, 999.0])

        self.assertAlmostEqual(radius, 11.5, places=6)
        self.assertEqual(evidence["sample_count"], 4)
        self.assertGreater(evidence["max_depth"], 900.0)
        self.assertLess(radius, evidence["max_depth"] / 50.0)

    def test_ignores_invalid_depth_samples_when_enough_valid_values_remain(self):
        select = self._selector()

        radius, evidence = select([0.0, -1.0, float("nan"), float("inf"), 9.0, 10.0, 11.0])

        self.assertAlmostEqual(radius, 10.0, places=6)
        self.assertEqual(evidence["sample_count"], 3)

    def test_rejects_too_few_positive_finite_depths(self):
        select = self._selector()

        with self.assertRaises(ValueError):
            select([0.0, -1.0, float("nan"), 10.0, 11.0])


if __name__ == "__main__":
    unittest.main()
