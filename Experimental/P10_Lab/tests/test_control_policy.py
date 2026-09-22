import unittest

from p10_lab.control_policy import RawHoleControlPolicy
from p10_lab.contracts import ContractError


class RawHoleControlPolicyTests(unittest.TestCase):
    def test_defaults_expose_missing_geometry_instead_of_compensating_for_it(self):
        policy = RawHoleControlPolicy()

        self.assertFalse(policy.fill_holes)
        self.assertFalse(policy.bridge_depth_discontinuities)
        self.assertFalse(policy.smooth_unknown_regions)
        self.assertFalse(policy.extrapolate_silhouettes)
        self.assertEqual(policy.unknown_pixel_mode, "black")
        self.assertTrue(policy.emit_binary_mask)
        self.assertTrue(policy.lock_observed_pixels)

    def test_policy_manifest_is_explicit_about_the_p10_only_derivative(self):
        manifest = RawHoleControlPolicy().to_manifest()

        self.assertEqual(manifest["scope"], "p10_control_derivative")
        self.assertEqual(manifest["baseline_mutated"], False)
        self.assertEqual(manifest["unknown_pixel_mode"], "black")

    def test_raw_hole_and_source_lock_safety_cannot_be_disabled(self):
        unsafe_options = (
            {"fill_holes": True},
            {"bridge_depth_discontinuities": True},
            {"smooth_unknown_regions": True},
            {"extrapolate_silhouettes": True},
            {"unknown_pixel_mode": "transparent"},
            {"emit_binary_mask": False},
            {"lock_observed_pixels": False},
        )
        for options in unsafe_options:
            with self.subTest(options=options), self.assertRaises(ContractError):
                RawHoleControlPolicy(**options)


if __name__ == "__main__":
    unittest.main()
