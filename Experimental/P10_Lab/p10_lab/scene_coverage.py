from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, pi, sin

from .contracts import ContractError
from .path_planner import CameraPath, RelativeWaypoint


def _finite(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a finite number")
    value = float(value)
    if not isfinite(value):
        raise ContractError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class SceneFootprint:
    right_min: float
    right_max: float
    up_min: float
    up_max: float
    forward_near: float
    forward_far: float
    median_depth: float
    true_forward_far: float

    def __post_init__(self) -> None:
        values = {
            name: _finite(getattr(self, name), name)
            for name in (
                "right_min",
                "right_max",
                "up_min",
                "up_max",
                "forward_near",
                "forward_far",
                "median_depth",
                "true_forward_far",
            )
        }
        if values["right_max"] <= values["right_min"]:
            raise ContractError("right_max must be greater than right_min")
        if values["up_max"] <= values["up_min"]:
            raise ContractError("up_max must be greater than up_min")
        if values["forward_near"] < 0.0:
            raise ContractError("forward_near cannot be negative")
        if values["forward_far"] <= values["forward_near"]:
            raise ContractError("forward_far must be greater than forward_near")
        if values["median_depth"] <= 0.0:
            raise ContractError("median_depth must be positive")
        if values["true_forward_far"] < values["forward_far"]:
            raise ContractError("true_forward_far cannot be smaller than forward_far")

    @property
    def lateral_span(self) -> float:
        return self.right_max - self.right_min

    @property
    def vertical_span(self) -> float:
        return self.up_max - self.up_min

    @property
    def longitudinal_span(self) -> float:
        return self.forward_far - self.forward_near

    @property
    def center_right(self) -> float:
        return 0.5 * (self.right_min + self.right_max)

    @property
    def center_forward(self) -> float:
        return 0.5 * (self.forward_near + self.forward_far)

    @property
    def aspect_ratio(self) -> float:
        return self.longitudinal_span / self.lateral_span

    def manifest(self) -> dict[str, float]:
        return {
            "right_min": self.right_min,
            "right_max": self.right_max,
            "up_min": self.up_min,
            "up_max": self.up_max,
            "forward_near": self.forward_near,
            "forward_far": self.forward_far,
            "true_forward_far": self.true_forward_far,
            "median_depth": self.median_depth,
            "lateral_span": self.lateral_span,
            "vertical_span": self.vertical_span,
            "longitudinal_span": self.longitudinal_span,
            "center_right": self.center_right,
            "center_forward": self.center_forward,
            "aspect_ratio": self.aspect_ratio,
        }


@dataclass(frozen=True)
class GeometryFlightConfig:
    # Stabilization preview intentionally uses three missions. The planner data
    # model remains list-based so the post-stabilization budget can grow to
    # 7-10 missions without adding/duplicating ComfyUI nodes.
    stabilization_mission_count: int = 3
    future_supported_mission_budget_max: int = 10
    orbit_steps: int = 12
    orbit_radius_lateral_fraction: float = 0.06
    orbit_radius_depth_fraction: float = 0.05
    far_overshoot_fraction: float = 0.06
    far_overshoot_depth_fraction: float = 0.25
    traverse_segments: int = 7
    traverse_lateral_fraction: float = 0.10
    return_lateral_fraction: float = 0.16

    def __post_init__(self) -> None:
        if self.stabilization_mission_count != 3:
            raise ContractError("Gate 4 stabilization profile currently requires exactly 3 missions")
        if (
            type(self.future_supported_mission_budget_max) is not int
            or self.future_supported_mission_budget_max < 10
        ):
            raise ContractError("future_supported_mission_budget_max must be at least 10")
        if type(self.orbit_steps) is not int or self.orbit_steps < 8 or self.orbit_steps > 48:
            raise ContractError("orbit_steps must be an integer in [8, 48]")
        if type(self.traverse_segments) is not int or self.traverse_segments < 5 or self.traverse_segments > 24:
            raise ContractError("traverse_segments must be an integer in [5, 24]")
        for name in (
            "orbit_radius_lateral_fraction",
            "orbit_radius_depth_fraction",
            "far_overshoot_fraction",
            "far_overshoot_depth_fraction",
            "traverse_lateral_fraction",
            "return_lateral_fraction",
        ):
            value = _finite(getattr(self, name), name)
            if value <= 0.0 or value > 0.5:
                raise ContractError(f"{name} must lie in (0, 0.5]")


@dataclass(frozen=True)
class GeometryAwareFlightPlan:
    paths: tuple[CameraPath, ...]
    orbit_radius: float
    far_target: float
    footprint: SceneFootprint

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10GeometryAwareFlightPlan.v0.2",
            "mission_count": len(self.paths),
            "orbit_radius": self.orbit_radius,
            "far_target": self.far_target,
            "scene_footprint": self.footprint.manifest(),
            "paths": [
                {
                    "name": path.name,
                    "waypoint_count": len(path.waypoints),
                    "start": {
                        "right": path.waypoints[0].right,
                        "up": path.waypoints[0].up,
                        "forward": path.waypoints[0].forward,
                    },
                    "end": {
                        "right": path.waypoints[-1].right,
                        "up": path.waypoints[-1].up,
                        "forward": path.waypoints[-1].forward,
                    },
                }
                for path in self.paths
            ],
        }


def _micro_orbit(
    name: str,
    *,
    center_right: float,
    center_forward: float,
    radius: float,
    steps: int,
) -> CameraPath:
    waypoints = []
    for index in range(steps + 1):
        angle = 2.0 * pi * index / steps
        # Position follows a small horizontal circle. Look direction is radial,
        # producing full yaw coverage from the local anchor instead of a fake
        # 360 equirectangular fill.
        look_right = sin(angle)
        look_forward = cos(angle)
        waypoints.append(
            RelativeWaypoint(
                right=center_right + radius * sin(angle),
                up=0.0,
                forward=center_forward + radius * cos(angle),
                look_right=look_right,
                look_up=0.0,
                look_forward=look_forward,
            )
        )
    return CameraPath(name, tuple(waypoints))


def _traverse(
    name: str,
    *,
    start_forward: float,
    end_forward: float,
    base_right: float,
    lateral_amplitude: float,
    segments: int,
    reverse_look: bool,
) -> CameraPath:
    points = []
    for index in range(segments + 1):
        amount = index / float(segments)
        forward = start_forward * (1.0 - amount) + end_forward * amount
        # A single gentle S-shaped lateral drift creates parallax along the
        # scene instead of repeating the exact optical axis.
        right = base_right + lateral_amplitude * sin(pi * amount)
        points.append(
            RelativeWaypoint(
                right=right,
                up=0.0,
                forward=forward,
                look_right=0.0,
                look_up=0.0,
                look_forward=-1.0 if reverse_look else 1.0,
            )
        )
    return CameraPath(name, tuple(points))


def _round_trip(
    *,
    far_target: float,
    footprint: SceneFootprint,
    config: GeometryFlightConfig,
) -> CameraPath:
    """One mission that traverses the useful scene and returns while looking back.

    Keeping outbound and inbound legs inside one CameraPath gives the current
    stabilization preview exactly three logical missions while preserving the
    two complementary viewing directions the user requested.
    """

    outbound = _traverse(
        "scene_round_trip_outbound",
        start_forward=0.0,
        end_forward=far_target,
        base_right=0.0,
        lateral_amplitude=footprint.lateral_span * config.traverse_lateral_fraction,
        segments=config.traverse_segments,
        reverse_look=False,
    )
    inbound = _traverse(
        "scene_round_trip_inbound",
        start_forward=far_target,
        end_forward=0.0,
        base_right=footprint.center_right * 0.25,
        lateral_amplitude=-footprint.lateral_span * config.return_lateral_fraction,
        segments=config.traverse_segments,
        reverse_look=True,
    )

    # Keep both far-end samples. The first still looks outward; the second
    # looks back toward the camera and may be later interpolated into a turn.
    # This makes the direction change explicit in evidence/GIF output.
    return CameraPath(
        "scene_round_trip",
        tuple(outbound.waypoints + inbound.waypoints),
    )


def plan_geometry_aware_flights(
    footprint: SceneFootprint,
    config: GeometryFlightConfig | None = None,
) -> GeometryAwareFlightPlan:
    config = config or GeometryFlightConfig()

    orbit_radius = min(
        footprint.lateral_span * config.orbit_radius_lateral_fraction,
        footprint.median_depth * config.orbit_radius_depth_fraction,
    )
    orbit_radius = max(orbit_radius, footprint.median_depth * 0.015)

    robust_overshoot = max(
        footprint.longitudinal_span * config.far_overshoot_fraction,
        footprint.median_depth * config.far_overshoot_depth_fraction,
    )
    # Never chase the extreme max vertex merely because one depth outlier
    # exists. Overshoot is bounded by the true observed far edge.
    far_target = min(
        footprint.true_forward_far,
        footprint.forward_far + robust_overshoot,
    )

    entry_orbit = _micro_orbit(
        "entry_micro_orbit_360",
        center_right=0.0,
        center_forward=0.0,
        radius=orbit_radius,
        steps=config.orbit_steps,
    )
    center_orbit = _micro_orbit(
        "center_micro_orbit_360",
        center_right=footprint.center_right,
        center_forward=footprint.center_forward,
        radius=orbit_radius,
        steps=config.orbit_steps,
    )

    round_trip = _round_trip(
        far_target=far_target,
        footprint=footprint,
        config=config,
    )

    return GeometryAwareFlightPlan(
        paths=(entry_orbit, center_orbit, round_trip),
        orbit_radius=orbit_radius,
        far_target=far_target,
        footprint=footprint,
    )



def derive_scene_footprint_from_primary_mesh(
    primary_mesh,
    camera,
    *,
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
):
    """Measure the P9 mesh footprint in canonical camera-local coordinates.

    Robust percentiles guide motion; true maxima are retained only as evidence
    and a hard upper bound. This makes long scenes traversable without allowing
    isolated far vertices to dominate the route.
    """

    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required to measure the P10 scene footprint") from error

    if not 0.0 <= lower_percentile < upper_percentile <= 100.0:
        raise ContractError("Scene footprint percentiles are invalid")

    from pathlib import Path
    path = Path(primary_mesh)
    if not path.is_file() or path.suffix.lower() != ".npz":
        raise ContractError(f"Scene footprint requires authoritative PrimaryMesh NPZ: {path}")

    try:
        with np.load(path, allow_pickle=False) as payload:
            if "vertices" not in payload.files:
                raise ContractError("PrimaryMesh NPZ is missing vertices")
            vertices = np.asarray(payload["vertices"], dtype=np.float64)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh for scene footprint: {path}: {error}") from error

    if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.shape[0] < 3:
        raise ContractError("PrimaryMesh vertices must have shape [N,3] with N >= 3")
    if not np.isfinite(vertices).all():
        raise ContractError("PrimaryMesh contains non-finite vertices")

    world = np.asarray(camera.world_matrix, dtype=np.float64)
    rotation = world[:3, :3]
    center = world[:3, 3]
    right_axis = rotation[:, 0]
    up_axis = rotation[:, 1]
    forward_axis = -rotation[:, 2]

    local = vertices - center[None, :]
    right = local @ right_axis
    up = local @ up_axis
    forward = local @ forward_axis
    valid = np.isfinite(right) & np.isfinite(up) & np.isfinite(forward) & (forward > 0.0)
    if int(valid.sum()) < 3:
        raise ContractError("PrimaryMesh has insufficient forward-facing vertices for path planning")

    right = right[valid]
    up = up[valid]
    forward = forward[valid]

    footprint = SceneFootprint(
        right_min=float(np.percentile(right, lower_percentile)),
        right_max=float(np.percentile(right, upper_percentile)),
        up_min=float(np.percentile(up, lower_percentile)),
        up_max=float(np.percentile(up, upper_percentile)),
        forward_near=float(np.percentile(forward, lower_percentile)),
        forward_far=float(np.percentile(forward, upper_percentile)),
        median_depth=float(np.median(forward)),
        true_forward_far=float(np.max(forward)),
    )
    evidence = {
        "schema": "ConceptGhost.P10SceneFootprintEvidence.v0.1",
        "vertex_count": int(vertices.shape[0]),
        "valid_forward_vertex_count": int(valid.sum()),
        "lower_percentile": float(lower_percentile),
        "upper_percentile": float(upper_percentile),
        "true_bounds": {
            "right_min": float(np.min(right)),
            "right_max": float(np.max(right)),
            "up_min": float(np.min(up)),
            "up_max": float(np.max(up)),
            "forward_near": float(np.min(forward)),
            "forward_far": float(np.max(forward)),
        },
        "robust_footprint": footprint.manifest(),
    }
    return footprint, evidence
