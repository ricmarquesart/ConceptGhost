import unittest


class RawHoleContractTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.raw_holes import (
                RAW_HOLE_POLICY,
                coverage_to_hole_bytes,
                RawHoleFrame,
            )
        except ImportError as error:
            self.fail(f"Gate 4.3 raw-hole module is missing: {error}")
        return RAW_HOLE_POLICY, coverage_to_hole_bytes, RawHoleFrame

    def test_hole_mask_is_exact_complement_of_geometry_coverage(self):
        policy, convert, _ = self._api()
        coverage = [True, False, True, False]
        holes = convert(2, 2, coverage)
        self.assertEqual(holes, bytes([0, 255, 0, 255]))
        self.assertEqual(policy, "RAW_UNSUPPORTED_P9_GEOMETRY_NO_FILL")

    def test_frame_manifest_declares_no_compensation(self):
        _, _, RawHoleFrame = self._api()
        frame = RawHoleFrame(
            width=2,
            height=2,
            mask=bytes([0, 255, 0, 255]),
            observed_pixel_count=2,
            hole_pixel_count=2,
        )
        manifest = frame.manifest()
        self.assertFalse(manifest["geometry_fill_applied"])
        self.assertFalse(manifest["morphological_close_applied"])
        self.assertEqual(manifest["hole_fraction"], 0.5)

    def test_invalid_mask_size_fails_closed(self):
        _, _, RawHoleFrame = self._api()
        with self.assertRaises(ValueError):
            RawHoleFrame(
                width=2,
                height=2,
                mask=bytes([0, 255]),
                observed_pixel_count=1,
                hole_pixel_count=1,
            )

    def test_mask_values_are_binary(self):
        _, _, RawHoleFrame = self._api()
        with self.assertRaises(ValueError):
            RawHoleFrame(
                width=1,
                height=1,
                mask=bytes([127]),
                observed_pixel_count=0,
                hole_pixel_count=1,
            )


if __name__ == "__main__":
    unittest.main()
