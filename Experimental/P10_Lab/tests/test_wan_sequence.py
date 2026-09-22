import json
import tempfile
import unittest
from pathlib import Path


class WanSequentialSamplerTests(unittest.TestCase):
    def test_node_is_registered(self):
        import p10_lab
        self.assertIn(
            "ConceptGhostP10WanSequentialSampler",
            p10_lab.NODE_CLASS_MAPPINGS,
        )
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10WanSequentialSampler"]
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        self.assertTrue(cls.OUTPUT_NODE)

    def test_manifest_groups_contiguous_frames_by_mission(self):
        from p10_lab.wan_sequence import mission_ranges_from_manifest
        payload = {
            "frames": [
                {"global_frame_index": 0, "path_name": "a"},
                {"global_frame_index": 1, "path_name": "a"},
                {"global_frame_index": 2, "path_name": "b"},
                {"global_frame_index": 3, "path_name": "b"},
                {"global_frame_index": 4, "path_name": "b"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            ranges = mission_ranges_from_manifest(path)

        self.assertEqual(
            [(r.name, r.start, r.end) for r in ranges],
            [("a", 0, 2), ("b", 2, 5)],
        )

    def test_noncontiguous_repeated_mission_is_rejected(self):
        from p10_lab.wan_sequence import mission_ranges_from_payload
        payload = {
            "frames": [
                {"global_frame_index": 0, "path_name": "a"},
                {"global_frame_index": 1, "path_name": "b"},
                {"global_frame_index": 2, "path_name": "a"},
            ]
        }
        with self.assertRaises(ValueError):
            mission_ranges_from_payload(payload)

    def test_frame_indexes_must_be_contiguous(self):
        from p10_lab.wan_sequence import mission_ranges_from_payload
        payload = {
            "frames": [
                {"global_frame_index": 0, "path_name": "a"},
                {"global_frame_index": 2, "path_name": "a"},
            ]
        }
        with self.assertRaises(ValueError):
            mission_ranges_from_payload(payload)


if __name__ == "__main__":
    unittest.main()
