import json
import tempfile
import unittest
from pathlib import Path


class WanSequentialSamplerTests(unittest.TestCase):
    def test_sampler_body_does_not_load_removed_seed_parameter(self):
        from p10_lab.wan_sequence import ConceptGhostP10WanSequentialSampler

        sample_code = ConceptGhostP10WanSequentialSampler.sample.__code__
        self.assertIn("wan_seed", sample_code.co_varnames)
        self.assertNotIn(
            "seed",
            sample_code.co_names,
            "sample() still loads the removed legacy seed parameter",
        )

    def test_decoded_video_batch_is_flattened_before_frame_save(self):
        from p10_lab.wan_sequence import normalize_decoded_wan_images

        class TensorLike:
            def __init__(self, shape):
                self.shape = tuple(shape)

            def reshape(self, *shape):
                if shape.count(-1) > 1:
                    raise ValueError("only one inferred dimension is supported")
                if -1 in shape:
                    source_size = 1
                    for value in self.shape:
                        source_size *= value
                    known_size = 1
                    for value in shape:
                        if value != -1:
                            known_size *= value
                    shape = tuple(
                        source_size // known_size if value == -1 else value
                        for value in shape
                    )
                return TensorLike(shape)

        decoded = TensorLike((2, 3, 480, 832, 3))
        normalized = normalize_decoded_wan_images(decoded)
        self.assertEqual(normalized.shape, (6, 480, 832, 3))

    def test_decoded_image_batch_is_left_unchanged(self):
        from p10_lab.wan_sequence import normalize_decoded_wan_images

        class TensorLike:
            def __init__(self, shape):
                self.shape = tuple(shape)

            def reshape(self, *shape):
                raise AssertionError("4D IMAGE batch must not be reshaped")

        decoded = TensorLike((4, 480, 832, 3))
        normalized = normalize_decoded_wan_images(decoded)
        self.assertIs(normalized, decoded)

    def test_invalid_decoded_rank_fails_closed(self):
        from p10_lab.wan_sequence import normalize_decoded_wan_images

        class TensorLike:
            def __init__(self, shape):
                self.shape = tuple(shape)

        with self.assertRaises(ValueError):
            normalize_decoded_wan_images(TensorLike((480, 832, 3)))

    def test_node_is_registered(self):
        import p10_lab
        self.assertIn(
            "ConceptGhostP10WanSequentialSampler",
            p10_lab.NODE_CLASS_MAPPINGS,
        )
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10WanSequentialSampler"]
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        self.assertTrue(cls.OUTPUT_NODE)

    def test_control_batch_contract_requires_exact_authored_frame_count(self):
        from p10_lab.wan_sequence import validate_control_batch_contract
        payload={"frame_count":30,"width":640,"height":360}
        validate_control_batch_contract(payload,(30,360,640,3),(30,360,640))
        with self.assertRaises(ValueError):
            validate_control_batch_contract(payload,(29,360,640,3),(30,360,640))

    def test_control_batch_contract_requires_exact_manifest_dimensions(self):
        from p10_lab.wan_sequence import validate_control_batch_contract
        payload={"frame_count":2,"width":640,"height":360}
        with self.assertRaises(ValueError):
            validate_control_batch_contract(payload,(2,480,832,3),(2,480,832))

    def test_read_control_manifest_verifies_persisted_bound_route(self):
        from p10_lab.drone_route_plan import (
            DroneMission,DroneRoutePlan,DroneWaypoint,bind_route_plan
        )
        from p10_lab.wan_sequence import read_control_manifest

        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,3)
            )),),
            frames_per_drone=2,
        )
        bound=bind_route_plan(
            plan,scene_contract_id="scene",source_run_id="run",
            route_authority="ARTIST_AUTHORED",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            route=root/"route_plan.json"
            route.write_text(json.dumps(bound),encoding="utf-8")
            manifest={
                "frame_count":2,"width":640,"height":360,
                "route_authority":"ARTIST_AUTHORED",
                "route_plan_sha256":bound["route_plan_sha256"],
                "route_plan_file":"route_plan.json",
                "scene_contract_id":"scene",
                "source_run_id":"run",
                "mission_order":["drone_1"],
                "missions":[{"name":"drone_1","mode":"PATH","frame_count":2}],
                "frames":[
                    {"global_frame_index":0,"path_name":"drone_1"},
                    {"global_frame_index":1,"path_name":"drone_1"},
                ],
            }
            path=root/"manifest.json"
            path.write_text(json.dumps(manifest),encoding="utf-8")
            _path,payload,ranges=read_control_manifest(path)
            self.assertEqual(payload["route_plan_sha256"],bound["route_plan_sha256"])
            self.assertEqual([r.mission_name for r in ranges],["drone_1"])

            tampered=dict(bound)
            tampered["frames_per_drone"]=3
            route.write_text(json.dumps(tampered),encoding="utf-8")
            with self.assertRaises(ValueError):
                read_control_manifest(path)

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
        self.assertEqual([r.mission_name for r in ranges],["a","b"])

    def test_window_parts_preserve_original_mission_identity(self):
        from p10_lab.wan_sequence import MissionRange,_window_ranges
        windows=_window_ranges(MissionRange("drone_1",0,70,"drone_1"),33)
        self.assertEqual([w.name for w in windows],[
            "drone_1__part00","drone_1__part01","drone_1__part02"
        ])
        self.assertTrue(all(w.mission_name=="drone_1" for w in windows))

    def test_wan_conditioning_length_pads_to_next_four_k_plus_one(self):
        from p10_lab.wan_sequence import padded_wan_length
        self.assertEqual(padded_wan_length(1), 1)
        self.assertEqual(padded_wan_length(25), 25)
        self.assertEqual(padded_wan_length(31), 33)
        self.assertEqual(padded_wan_length(33), 33)

    def test_invalid_small_or_corrupted_dimensions_fall_back_to_safe_profile(self):
        from p10_lab.wan_sequence import normalize_wan_dimensions
        result = normalize_wan_dimensions(630, 95)
        self.assertEqual((result.width, result.height), (832, 480))
        self.assertEqual(result.mode, "SAFE_PROFILE_FALLBACK")

    def test_normal_invalid_dimensions_snap_to_nearest_multiple_of_16(self):
        from p10_lab.wan_sequence import normalize_wan_dimensions
        result = normalize_wan_dimensions(1000, 562)
        self.assertEqual((result.width, result.height), (992, 560))
        self.assertEqual(result.mode, "ALIGN_TO_16")

    def test_valid_dimensions_are_unchanged(self):
        from p10_lab.wan_sequence import normalize_wan_dimensions
        result = normalize_wan_dimensions(832, 480)
        self.assertEqual((result.width, result.height), (832, 480))
        self.assertEqual(result.mode, "UNCHANGED")

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
