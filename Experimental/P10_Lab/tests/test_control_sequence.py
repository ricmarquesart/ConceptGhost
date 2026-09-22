import unittest


class ControlSequenceContractTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.control_sequence import (
                ControlFrameRecord,
                ControlSequenceManifest,
            )
        except ImportError as error:
            self.fail(f"Gate 4.4 control-sequence module is missing: {error}")
        return ControlFrameRecord, ControlSequenceManifest

    def test_manifest_preserves_frame_order_and_path_identity(self):
        Frame, Manifest = self._api()
        frames = (
            Frame(0, "entry_micro_orbit_360", 0, 0.25, "frame_0000.png", "mask_0000.png"),
            Frame(1, "entry_micro_orbit_360", 1, 0.50, "frame_0001.png", "mask_0001.png"),
            Frame(2, "scene_round_trip", 0, 0.75, "frame_0002.png", "mask_0002.png"),
        )
        manifest = Manifest(frames=frames, width=640, height=480)
        payload = manifest.to_dict()
        self.assertEqual(payload["frame_count"], 3)
        self.assertEqual(payload["frames"][2]["path_name"], "scene_round_trip")
        self.assertEqual(payload["frames"][0]["global_frame_index"], 0)

    def test_control_sequence_requires_monotonic_global_indexes(self):
        Frame, Manifest = self._api()
        frames = (
            Frame(0, "a", 0, 0.2, "a.png", "a_mask.png"),
            Frame(2, "a", 1, 0.3, "b.png", "b_mask.png"),
        )
        with self.assertRaises(ValueError):
            Manifest(frames=frames, width=640, height=480)

    def test_hole_fraction_is_bounded(self):
        Frame, _ = self._api()
        with self.assertRaises(ValueError):
            Frame(0, "a", 0, 1.1, "a.png", "m.png")


if __name__ == "__main__":
    unittest.main()
