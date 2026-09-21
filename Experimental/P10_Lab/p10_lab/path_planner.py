from __future__ import annotations

from dataclasses import dataclass
from .contracts import SceneScale


@dataclass(frozen=True)
class RelativeWaypoint:
    right: float
    up: float
    forward: float
    look_right: float = 0.0
    look_up: float = 0.0
    look_forward: float = 1.0


@dataclass(frozen=True)
class CameraPath:
    name: str
    waypoints: tuple[RelativeWaypoint, ...]


def default_paths(scale: SceneScale) -> tuple[CameraPath, ...]:
    """Return scene-relative paths.

    Values are expressed as fractions of scene radius, not fixed world meters.
    Collision testing is intentionally a later gate so planning stays pure and
    deterministic.
    """
    r = scale.radius
    left = CameraPath(
        "left_arc",
        (
            RelativeWaypoint(0.0, 0.0, 0.0),
            RelativeWaypoint(-0.10*r, 0.02*r, 0.05*r),
            RelativeWaypoint(-0.20*r, 0.03*r, 0.10*r),
            RelativeWaypoint(-0.28*r, 0.04*r, 0.12*r),
        ),
    )
    right = CameraPath(
        "right_arc",
        (
            RelativeWaypoint(0.0, 0.0, 0.0),
            RelativeWaypoint(0.10*r, 0.02*r, 0.05*r),
            RelativeWaypoint(0.20*r, 0.03*r, 0.10*r),
            RelativeWaypoint(0.28*r, 0.04*r, 0.12*r),
        ),
    )
    forward = CameraPath(
        "forward_probe",
        (
            RelativeWaypoint(0.0, 0.0, 0.0),
            RelativeWaypoint(-0.04*r, 0.02*r, 0.10*r),
            RelativeWaypoint(0.04*r, 0.04*r, 0.20*r),
            RelativeWaypoint(0.0, 0.05*r, 0.28*r),
        ),
    )
    return left, right, forward
