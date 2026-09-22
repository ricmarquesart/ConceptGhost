from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from .contracts import ContractError
from .path_planner import CameraPath, RelativeWaypoint


@dataclass(frozen=True)
class ClearanceConfig:
    min_clearance: float
    samples_per_segment: int = 8
    shrink_factor: float = 0.80
    max_shrink_attempts: int = 8

    def __post_init__(self) -> None:
        if (
            isinstance(self.min_clearance, bool)
            or not isinstance(self.min_clearance, (int, float))
            or not isfinite(float(self.min_clearance))
            or float(self.min_clearance) <= 0.0
        ):
            raise ContractError("min_clearance must be finite and positive")
        if type(self.samples_per_segment) is not int or self.samples_per_segment < 1:
            raise ContractError("samples_per_segment must be an integer >= 1")
        if (
            isinstance(self.shrink_factor, bool)
            or not isinstance(self.shrink_factor, (int, float))
            or not isfinite(float(self.shrink_factor))
            or not 0.0 < float(self.shrink_factor) < 1.0
        ):
            raise ContractError("shrink_factor must be finite and in (0,1)")
        if type(self.max_shrink_attempts) is not int or self.max_shrink_attempts < 0:
            raise ContractError("max_shrink_attempts must be a nonnegative integer")


@dataclass(frozen=True)
class ClearanceResult:
    path: CameraPath
    adapted: bool
    blocked: bool
    minimum_clearance: float
    shrink_scale: float
    reason: str
    sample_count: int


def _lerp(left: float, right: float, amount: float) -> float:
    return left * (1.0 - amount) + right * amount


def _lerp_waypoint(
    left: RelativeWaypoint,
    right: RelativeWaypoint,
    amount: float,
) -> RelativeWaypoint:
    return RelativeWaypoint(
        right=_lerp(left.right, right.right, amount),
        up=_lerp(left.up, right.up, amount),
        forward=_lerp(left.forward, right.forward, amount),
        look_right=_lerp(left.look_right, right.look_right, amount),
        look_up=_lerp(left.look_up, right.look_up, amount),
        look_forward=_lerp(left.look_forward, right.look_forward, amount),
    )


def sample_path_waypoints(
    path: CameraPath,
    samples_per_segment: int,
) -> tuple[RelativeWaypoint, ...]:
    if type(samples_per_segment) is not int or samples_per_segment < 1:
        raise ContractError("samples_per_segment must be an integer >= 1")
    if not path.waypoints:
        raise ContractError("CameraPath must contain at least one waypoint")
    if len(path.waypoints) == 1:
        return path.waypoints

    sampled: list[RelativeWaypoint] = []
    for index in range(len(path.waypoints) - 1):
        left = path.waypoints[index]
        right = path.waypoints[index + 1]
        for step in range(samples_per_segment):
            amount = step / float(samples_per_segment)
            sampled.append(_lerp_waypoint(left, right, amount))
    sampled.append(path.waypoints[-1])
    return tuple(sampled)


def _scaled_path(path: CameraPath, scale: float) -> CameraPath:
    return CameraPath(
        path.name,
        tuple(
            RelativeWaypoint(
                right=point.right * scale,
                up=point.up * scale,
                forward=point.forward * scale,
                look_right=point.look_right,
                look_up=point.look_up,
                look_forward=point.look_forward,
            )
            for point in path.waypoints
        ),
    )


def _minimum_clearance(
    path: CameraPath,
    query: Callable[[RelativeWaypoint], float],
    samples_per_segment: int,
) -> tuple[float, int, bool]:
    values = []
    for point in sample_path_waypoints(path, samples_per_segment):
        value = query(point)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
        ):
            return 0.0, len(values) + 1, False
        values.append(float(value))
    return min(values), len(values), True


def adapt_path_for_clearance(
    path: CameraPath,
    clearance_query: Callable[[RelativeWaypoint], float],
    config: ClearanceConfig,
) -> ClearanceResult:
    """Shrink a local flight around the authoritative origin until safe.

    The origin is never moved. If the origin itself is unsafe, or if the path
    cannot pass within the bounded retry budget, the flight is blocked instead
    of silently accepting collision risk.
    """

    if not path.waypoints:
        raise ContractError("CameraPath must contain at least one waypoint")

    origin_clearance = clearance_query(path.waypoints[0])
    if (
        isinstance(origin_clearance, bool)
        or not isinstance(origin_clearance, (int, float))
        or not isfinite(float(origin_clearance))
    ):
        return ClearanceResult(
            path=path,
            adapted=False,
            blocked=True,
            minimum_clearance=0.0,
            shrink_scale=1.0,
            reason="Origin clearance query returned a non-finite value",
            sample_count=1,
        )
    if float(origin_clearance) < config.min_clearance:
        return ClearanceResult(
            path=path,
            adapted=False,
            blocked=True,
            minimum_clearance=float(origin_clearance),
            shrink_scale=1.0,
            reason="Authoritative origin is below minimum clearance",
            sample_count=1,
        )

    scale = 1.0
    for attempt in range(config.max_shrink_attempts + 1):
        candidate = path if attempt == 0 else _scaled_path(path, scale)
        minimum, count, valid = _minimum_clearance(
            candidate,
            clearance_query,
            config.samples_per_segment,
        )
        if valid and minimum >= config.min_clearance:
            return ClearanceResult(
                path=candidate,
                adapted=attempt > 0,
                blocked=False,
                minimum_clearance=minimum,
                shrink_scale=scale,
                reason="PASS" if attempt == 0 else "PASS_AFTER_BOUNDED_SHRINK",
                sample_count=count,
            )
        scale *= config.shrink_factor

    return ClearanceResult(
        path=path,
        adapted=False,
        blocked=True,
        minimum_clearance=minimum if 'minimum' in locals() else 0.0,
        shrink_scale=scale,
        reason="No safe path found within bounded shrink budget",
        sample_count=count if 'count' in locals() else 0,
    )
