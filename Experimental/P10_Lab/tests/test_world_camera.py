import math
import unittest

from p10_lab.panorama import CameraAuthority
from p10_lab.path_planner import CameraPath, RelativeWaypoint


def _camera():
    payload = {
        "valid": True,
        "scene_contract_id": "cgsc_world_camera_test",
        "schema": "ConceptGhost.CameraBundle.v0.8",
        "image_width": 1000,
        "image_height": 800,
        "horizontal_fov_deg": 53.13010235415598,
        "intrinsics": {
            "fx_px": 1000.0,
            "fy_px": 1000.0,
            "cx_px": 500.0,
            "cy_px": 400.0,
            "lens_model": "pinhole",
            "distortion": {},
        },
        "extrinsics": {
            "camera_position": [10.0, 20.0, 30.0],
            "camera_world_matrix": [
                [1.0, 0.0, 0.0, 10.0],
                [0.0, 1.0, 0.0, 20.0],
                [0.0, 0.0, 1.0, 30.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        },
    }
    return CameraAuthority.from_payload(
        payload,
        expected_scene_contract_id=payload["scene_contract_id"],
    )


class WorldCameraTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.world_camera import (
                resolve_camera_path,
                resolve_world_camera,
            )
        except ImportError as error:
            self.fail(f"Gate 4.1 world-camera module is missing: {error}")
        return resolve_camera_path, resolve_world_camera

    def test_zero_waypoint_reproduces_authoritative_camera_pose(self):
        _, resolve_world_camera = self._api()
        camera = _camera()

        pose = resolve_world_camera(camera, RelativeWaypoint(0.0, 0.0, 0.0))

        self.assertEqual(pose.scene_contract_id, camera.scene_contract_id)
        self.assertEqual(pose.position, (10.0, 20.0, 30.0))
        for actual, expected in zip(pose.world_matrix, camera.world_matrix):
            for a, e in zip(actual, expected):
                self.assertAlmostEqual(a, e, places=10)

    def test_right_up_forward_offsets_follow_camera_local_basis(self):
        _, resolve_world_camera = self._api()
        camera = _camera()

        pose = resolve_world_camera(
            camera,
            RelativeWaypoint(right=2.0, up=3.0, forward=4.0),
        )

        self.assertAlmostEqual(pose.position[0], 12.0)
        self.assertAlmostEqual(pose.position[1], 23.0)
        self.assertAlmostEqual(pose.position[2], 26.0)

    def test_default_look_vector_preserves_original_rotation(self):
        _, resolve_world_camera = self._api()
        camera = _camera()

        pose = resolve_world_camera(
            camera,
            RelativeWaypoint(right=5.0, up=1.0, forward=2.0),
        )

        for row in range(3):
            for col in range(3):
                self.assertAlmostEqual(
                    pose.world_matrix[row][col],
                    camera.world_matrix[row][col],
                    places=10,
                )

    def test_custom_look_direction_builds_rigid_right_handed_camera(self):
        _, resolve_world_camera = self._api()
        camera = _camera()
        waypoint = RelativeWaypoint(
            right=-2.0,
            up=1.0,
            forward=3.0,
            look_right=0.5,
            look_up=0.1,
            look_forward=1.0,
        )

        pose = resolve_world_camera(camera, waypoint)
        right = tuple(pose.world_matrix[row][0] for row in range(3))
        up = tuple(pose.world_matrix[row][1] for row in range(3))
        local_z = tuple(pose.world_matrix[row][2] for row in range(3))
        forward = tuple(-value for value in local_z)

        self.assertAlmostEqual(sum(value * value for value in right), 1.0, places=9)
        self.assertAlmostEqual(sum(value * value for value in up), 1.0, places=9)
        self.assertAlmostEqual(sum(value * value for value in forward), 1.0, places=9)
        self.assertAlmostEqual(sum(a * b for a, b in zip(right, up)), 0.0, places=9)
        self.assertGreater(forward[0], 0.0)
        self.assertGreater(forward[2] * -1.0, 0.0)

    def test_zero_look_vector_is_rejected(self):
        _, resolve_world_camera = self._api()
        with self.assertRaises(ValueError):
            resolve_world_camera(
                _camera(),
                RelativeWaypoint(
                    0.0,
                    0.0,
                    0.0,
                    look_right=0.0,
                    look_up=0.0,
                    look_forward=0.0,
                ),
            )

    def test_path_resolution_preserves_order_and_identity(self):
        resolve_camera_path, _ = self._api()
        path = CameraPath(
            "test_path",
            (
                RelativeWaypoint(0.0, 0.0, 0.0),
                RelativeWaypoint(1.0, 0.0, 1.0),
                RelativeWaypoint(2.0, 1.0, 2.0),
            ),
        )

        resolved = resolve_camera_path(_camera(), path)

        self.assertEqual(resolved.name, "test_path")
        self.assertEqual(len(resolved.poses), 3)
        self.assertEqual([pose.frame_index for pose in resolved.poses], [0, 1, 2])
        self.assertTrue(
            all(
                pose.scene_contract_id == "cgsc_world_camera_test"
                for pose in resolved.poses
            )
        )


if __name__ == "__main__":
    unittest.main()
