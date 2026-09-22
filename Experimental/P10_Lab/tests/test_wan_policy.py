import unittest


class WanRuntimePolicyTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.wan_policy import WanRuntimeProfile
        except ImportError as error:
            self.fail(f"Gate 5.1 WAN policy module is missing: {error}")
        return WanRuntimeProfile

    def test_default_profile_targets_2080ti_11gb_conservatively(self):
        Profile = self._api()
        profile = Profile.default_11gb()
        self.assertEqual(profile.width, 832)
        self.assertEqual(profile.height, 480)
        self.assertEqual(profile.length, 33)
        self.assertEqual(profile.steps, 4)
        self.assertEqual(profile.cfg, 1.0)
        self.assertEqual(profile.max_parallel_windows, 1)
        self.assertTrue(profile.offload_between_windows)
        self.assertTrue(profile.use_fp8_unet)

    def test_wan_dimensions_are_multiple_of_16(self):
        Profile = self._api()
        profile = Profile.default_11gb()
        self.assertEqual(profile.width % 16, 0)
        self.assertEqual(profile.height % 16, 0)

    def test_invalid_memory_heavy_parallelism_is_rejected(self):
        Profile = self._api()
        with self.assertRaises(ValueError):
            Profile(
                width=832,
                height=480,
                length=33,
                steps=4,
                cfg=1.0,
                max_parallel_windows=2,
                offload_between_windows=True,
                use_fp8_unet=True,
            )

    def test_manifest_records_hardware_target_and_sequence_policy(self):
        Profile = self._api()
        payload = Profile.default_11gb().manifest()
        self.assertEqual(payload["hardware_target"], "RTX_2080_TI_11GB")
        self.assertEqual(payload["window_policy"], "SEQUENTIAL_ONLY")
        self.assertEqual(payload["hole_fill"], "black")


if __name__ == "__main__":
    unittest.main()
