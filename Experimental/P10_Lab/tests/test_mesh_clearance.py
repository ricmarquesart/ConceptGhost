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
        self.assertEqual(manifest["method"], "P9_PRIMARYMESH_VERTEX_CLEARANCE")
        self.assertTrue(manifest["approximate"])
        self.assertEqual(manifest["retained_point_count"], 1)


if __name__ == "__main__":
    unittest.main()
