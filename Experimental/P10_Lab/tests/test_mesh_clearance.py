import tempfile
import unittest
from pathlib import Path


class MeshClearanceRuntimeTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.mesh_clearance import (
                ClearanceCloud,
                build_clearance_cloud,
            )
        except ImportError as error:
            self.fail(f"Gate 4.2 mesh clearance module is missing: {error}")
        return ClearanceCloud, build_clearance_cloud

    def test_local_clearance_query_uses_camera_relative_right_up_forward_axes(self):
        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((0.0, 0.0, 5.0), (2.0, 0.0, 5.0)),
            source_point_count=2,
            retained_point_count=2,
            sampling_stride=1,
        )
        self.assertAlmostEqual(cloud.query_components(0.0, 0.0, 5.0), 0.0)
        self.assertAlmostEqual(cloud.query_components(1.0, 0.0, 5.0), 1.0)
        self.assertAlmostEqual(cloud.query_components(0.0, 3.0, 5.0), 3.0)

    def test_query_accepts_relative_waypoint(self):
        from p10_lab.path_planner import RelativeWaypoint
        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((0.0, 0.0, 5.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
        )
        point = RelativeWaypoint(0.0, 0.0, 4.0)
        self.assertAlmostEqual(cloud.query(point), 1.0)

    def test_cloud_is_deterministically_downsampled_to_budget(self):
        ClearanceCloud, _ = self._api()
        points = tuple((float(i), 0.0, 10.0) for i in range(100))
        cloud = ClearanceCloud.from_local_points(points, max_points=20)
        self.assertLessEqual(cloud.retained_point_count, 20)
        self.assertGreater(cloud.sampling_stride, 1)
        second = ClearanceCloud.from_local_points(points, max_points=20)
        self.assertEqual(cloud.points, second.points)

    def test_runtime_path_clearance_reports_pass_or_bounded_adaptation(self):
        from p10_lab.mesh_clearance import adapt_paths_for_clearance
        from p10_lab.path_planner import CameraPath, RelativeWaypoint

        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((3.0, 0.0, 0.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
        )
        safe = CameraPath(
            "safe",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(0.5, 0.0, 0.0),
            ),
        )
        result = adapt_paths_for_clearance(
            (safe,),
            cloud,
            min_clearance=1.0,
            samples_per_segment=2,
        )
        self.assertEqual(len(result.paths), 1)
        self.assertFalse(result.results[0].blocked)
        self.assertEqual(result.results[0].reason, "PASS")
        self.assertEqual(result.manifest()["blocked_mission_count"], 0)

    def test_runtime_path_clearance_blocks_mission_if_anchor_is_inside_geometry(self):
        from p10_lab.mesh_clearance import adapt_paths_for_clearance
        from p10_lab.path_planner import CameraPath, RelativeWaypoint

        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((0.0, 0.0, 0.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
        )
        bad = CameraPath(
            "bad",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(1.0, 0.0, 0.0),
            ),
        )
        result = adapt_paths_for_clearance(
            (bad,),
            cloud,
            min_clearance=0.5,
            samples_per_segment=2,
        )
        self.assertEqual(len(result.paths), 0)
        self.assertTrue(result.results[0].blocked)
        self.assertEqual(result.manifest()["blocked_mission_count"], 1)

    def test_segment_clearance_detects_surface_between_safe_endpoints(self):
        from p10_lab.path_planner import RelativeWaypoint
        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((0.0, 0.0, 0.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
            grid_cell_size=0.25,
        )
        start=RelativeWaypoint(-1.0,0.0,0.0)
        end=RelativeWaypoint(1.0,0.0,0.0)
        self.assertGreaterEqual(cloud.query(start),0.9)
        self.assertGreaterEqual(cloud.query(end),0.9)
        self.assertTrue(
            cloud.segment_is_blocked(
                start,end,0.20,sample_step=0.05
            )
        )

    def test_threshold_query_uses_spatial_buckets(self):
        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((5.0, 2.0, 3.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
            grid_cell_size=0.25,
        )
        self.assertIsNone(cloud.clearance_below(0.0,0.0,0.0,0.2))
        self.assertIsNotNone(cloud.clearance_below(5.1,2.0,3.0,0.2))

    def test_empty_cloud_fails_closed(self):
        ClearanceCloud, _ = self._api()
        with self.assertRaises(ValueError):
            ClearanceCloud.from_local_points((), max_points=20)

    def test_manifest_reports_approximation_explicitly(self):
        ClearanceCloud, _ = self._api()
        cloud = ClearanceCloud(
            points=((0.0, 0.0, 1.0),),
            source_point_count=10,
            retained_point_count=1,
            sampling_stride=10,
        )
        manifest = cloud.manifest()
        self.assertEqual(manifest["method"], "P9_PRIMARYMESH_VERTEX_PLUS_FACE_CENTROID_CLEARANCE")
        self.assertTrue(manifest["approximate"])
        self.assertEqual(manifest["retained_point_count"], 1)


if __name__ == "__main__":
    unittest.main()
