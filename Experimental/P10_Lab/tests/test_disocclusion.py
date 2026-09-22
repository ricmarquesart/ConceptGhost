import unittest


class DisocclusionContractTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.disocclusion import (
                DISOCCLUSION_POLICY,
                build_disocclusion_mask,
            )
        except ImportError as error:
            self.fail(f"Gate 4.5 disocclusion module is missing: {error}")
        return DISOCCLUSION_POLICY, build_disocclusion_mask

    def test_gate4_disocclusion_is_exact_raw_unsupported_region(self):
        policy, build = self._api()
        raw = bytes([0, 255, 255, 0])
        result = build(2, 2, raw)
        self.assertEqual(result.mask, raw)
        self.assertEqual(result.policy, policy)
        self.assertFalse(result.feathered)
        self.assertFalse(result.dilated)

    def test_disocclusion_manifest_is_explicit_about_no_fill(self):
        _, build = self._api()
        result = build(2, 2, bytes([0, 255, 255, 0]))
        manifest = result.manifest()
        self.assertEqual(manifest["candidate_pixel_count"], 2)
        self.assertEqual(manifest["candidate_fraction"], 0.5)
        self.assertFalse(manifest["geometry_fill_applied"])


if __name__ == "__main__":
    unittest.main()
