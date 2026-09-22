from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Sequence

from .contracts import ContractError
from .panorama import CameraAuthority
from .path_planner import CameraPath, RelativeWaypoint


_EPSILON = 1.0e-10


def _finite(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a finite number")
    value = float(value)
    if not isfinite(value):
        raise ContractError(f"{label} must be finite")
    return value


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(left * right for left, right in zip(a, b))


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(vector: Sequence[float], label: str) -> tuple[float, float, float]:
    values = tuple(_finite(value, label) for value in vector)
    length = sqrt(_dot(values, values))
    if length <= _EPSILON:
        raise ContractError(f"{label} cannot have zero length")
    return tuple(value / length for value in values)


def _column(matrix: Sequence[Sequence[float]], index: int) -> tuple[float, float, float]:
    return tuple(float(matrix[row][index]) for row in range(3))


@dataclass(frozen=True)
class WorldCameraPose:
    scene_contract_id: str
    frame_index: int
    position: tuple[float, float, float]
    world_matrix: tuple[tuple[float, float, float, float], ...]
    relative_waypoint: RelativeWaypoint

    @property
    def right_axis(self) -> tuple[float, float, float]:
        return _column(self.world_matrix, 0)

    @property
    def up_axis(self) -> tuple[float, float, float]:
        return _column(self.world_matrix, 1)

    @property
    def forward_axis(self) -> tuple[float, float, float]:
        local_z = _column(self.world_matrix, 2)
        return tuple(-value for value in local_z)


@dataclass(frozen=True)
class WorldCameraPath:
    name: str
    scene_contract_id: str
    poses: tuple[WorldCameraPose, ...]


def _translated_position(
    camera: CameraAuthority,
    waypoint: RelativeWaypoint,
) -> tuple[float, float, float]:
    right = _column(camera.world_matrix, 0)
    up = _column(camera.world_matrix, 1)
    local_z = _column(camera.world_matrix, 2)
    forward = tuple(-value for value in local_z)
    base = tuple(camera.world_matrix[row][3] for row in range(3))

    amount_right = _finite(waypoint.right, "waypoint.right")
    amount_up = _finite(waypoint.up, "waypoint.up")
    amount_forward = _finite(waypoint.forward, "waypoint.forward")
    return tuple(
        base[index]
        + amount_right * right[index]
        + amount_up * up[index]
        + amount_forward * forward[index]
        for index in range(3)
    )


def _resolved_rotation(
    camera: CameraAuthority,
    waypoint: RelativeWaypoint,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    look = (
        _finite(waypoint.look_right, "waypoint.look_right"),
        _finite(waypoint.look_up, "waypoint.look_up"),
        _finite(waypoint.look_forward, "waypoint.look_forward"),
    )
    if sqrt(_dot(look, look)) <= _EPSILON:
        raise ContractError("Waypoint look vector cannot have zero length")

    base_right = _column(camera.world_matrix, 0)
    base_up = _column(camera.world_matrix, 1)
    base_local_z = _column(camera.world_matrix, 2)
    base_forward = tuple(-value for value in base_local_z)

    # The default planner look vector means "keep the canonical P9 orientation".
    # Returning the original basis exactly avoids needless floating-point drift.
    if look == (0.0, 0.0, 1.0):
        return base_right, base_up, base_local_z

    desired_forward = _normalize(
        tuple(
            look[0] * base_right[index]
            + look[1] * base_up[index]
            + look[2] * base_forward[index]
            for index in range(3)
        ),
        "resolved look direction",
    )

    right_candidate = _cross(desired_forward, base_up)
    if sqrt(_dot(right_candidate, right_candidate)) <= _EPSILON:
        # If the requested view is almost parallel to canonical up, project the
        # canonical right axis onto the plane normal to the desired forward.
        projection = _dot(base_right, desired_forward)
        right_candidate = tuple(
            base_right[index] - projection * desired_forward[index]
            for index in range(3)
        )

    resolved_right = _normalize(right_candidate, "resolved camera right axis")
    resolved_up = _normalize(
        _cross(resolved_right, desired_forward),
        "resolved camera up axis",
    )
    resolved_local_z = tuple(-value for value in desired_forward)
    return resolved_right, resolved_up, resolved_local_z


def resolve_world_camera(
    camera: CameraAuthority,
    waypoint: RelativeWaypoint,
    *,
    frame_index: int = 0,
) -> WorldCameraPose:
    if type(frame_index) is not int or frame_index < 0:
        raise ContractError("frame_index must be a nonnegative integer")

    position = _translated_position(camera, waypoint)
    right, up, local_z = _resolved_rotation(camera, waypoint)
    world_matrix = tuple(
        (
            right[row],
            up[row],
            local_z[row],
            position[row],
        )
        for row in range(3)
    ) + ((0.0, 0.0, 0.0, 1.0),)

    return WorldCameraPose(
        scene_contract_id=camera.scene_contract_id,
        frame_index=frame_index,
        position=position,
        world_matrix=world_matrix,
        relative_waypoint=waypoint,
    )


def resolve_camera_path(
    camera: CameraAuthority,
    path: CameraPath,
) -> WorldCameraPath:
    if not path.name:
        raise ContractError("CameraPath name cannot be empty")
    if not path.waypoints:
        raise ContractError("CameraPath must contain at least one waypoint")

    poses = tuple(
        resolve_world_camera(camera, waypoint, frame_index=index)
        for index, waypoint in enumerate(path.waypoints)
    )
    return WorldCameraPath(
        name=path.name,
        scene_contract_id=camera.scene_contract_id,
        poses=poses,
    )
