from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi, sin
from .contracts import SceneScale
from .contracts import ContractError


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


@dataclass(frozen=True)
class FlightPlanConfig:
    initial_path_count: int = 3
    adaptive_path_budget: int = 1
    lateral_limit_fraction: float = 0.30
    forward_limit_fraction: float = 0.30
    elevation_limit_fraction: float = 0.10

    def __post_init__(self) -> None:
        if type(self.initial_path_count) is not int or self.initial_path_count < 1:
            raise ContractError("initial_path_count must be at least 1")
        if type(self.adaptive_path_budget) is not int or self.adaptive_path_budget < 0:
            raise ContractError("adaptive_path_budget cannot be negative")
        for name in (
            "lateral_limit_fraction",
            "forward_limit_fraction",
            "elevation_limit_fraction",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or not 0.0 < value <= 1.0
            ):
                raise ContractError(f"{name} must be in the range (0, 1]")


@dataclass(frozen=True)
class FlightPlan:
    initial_paths: tuple[CameraPath, ...]
    adaptive_path_budget: int

    @property
    def maximum_flights(self) -> int:
        return len(self.initial_paths) + self.adaptive_path_budget


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


def _coverage_probe(
    scale: SceneScale,
    ordinal: int,
    extra_count: int,
    config: FlightPlanConfig,
) -> CameraPath:
    """Create another bounded local probe without expanding to a 360 orbit."""

    r = scale.radius
    phase = ordinal / max(1, extra_count)
    lateral_sign = -1.0 if ordinal % 2 else 1.0
    lateral = lateral_sign * config.lateral_limit_fraction * r * (0.55 + 0.45 * phase)
    forward = config.forward_limit_fraction * r * (0.45 + 0.55 * phase)
    elevation_wave = abs(sin(ordinal * pi * 0.61803398875))
    up = config.elevation_limit_fraction * r * (0.35 + 0.65 * elevation_wave)

    return CameraPath(
        name=f"coverage_probe_{ordinal + 3:02d}",
        waypoints=tuple(
            RelativeWaypoint(
                right=lateral * amount,
                up=up * amount,
                forward=forward * amount,
            )
            for amount in (0.0, 0.34, 0.67, 1.0)
        ),
    )


def _bounded_seed_path(
    path: CameraPath,
    scale: SceneScale,
    config: FlightPlanConfig,
) -> CameraPath:
    limits = (
        config.lateral_limit_fraction * scale.radius,
        config.elevation_limit_fraction * scale.radius,
        config.forward_limit_fraction * scale.radius,
    )

    def clamp(value: float, limit: float) -> float:
        return max(-limit, min(limit, value))

    return CameraPath(
        path.name,
        tuple(
            RelativeWaypoint(
                right=clamp(point.right, limits[0]),
                up=clamp(point.up, limits[1]),
                forward=clamp(point.forward, limits[2]),
                look_right=point.look_right,
                look_up=point.look_up,
                look_forward=point.look_forward,
            )
            for point in path.waypoints
        ),
    )


def plan_flights(
    scale: SceneScale,
    config: FlightPlanConfig | None = None,
) -> FlightPlan:
    """Build a data-driven local flight plan.

    The first three routes retain the reviewed left/right/forward behavior.
    Further routes are bounded coverage probes, not copies of hard-coded nodes.
    Adaptive routes are only a budget here; a later evidence analyzer decides
    whether and where to spend them.
    """

    config = config or FlightPlanConfig()
    paths = [
        _bounded_seed_path(path, scale, config)
        for path in default_paths(scale)[: config.initial_path_count]
    ]
    extra_count = max(0, config.initial_path_count - len(paths))
    for ordinal in range(1, extra_count + 1):
        paths.append(_coverage_probe(scale, ordinal, extra_count, config))
    return FlightPlan(tuple(paths), config.adaptive_path_budget)
