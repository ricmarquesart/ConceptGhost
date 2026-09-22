from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from pathlib import Path
from typing import Iterable

from .contracts import ContractError
from .panorama import CameraAuthority
from .path_planner import CameraPath, RelativeWaypoint
from .clearance import ClearanceConfig, ClearanceResult, adapt_path_for_clearance


@dataclass(frozen=True)
class ClearanceCloud:
    """Deterministic camera-local point cloud for bounded path clearance checks.

    Coordinates use the same convention as P10 flight waypoints:
    +right, +up, +forward. The cloud is intentionally approximate in Gate 4.2:
    it samples authoritative PrimaryMesh vertices rather than performing exact
    triangle-distance queries. This is sufficient to prevent obvious path
    intersections while keeping the first end-to-end implementation portable.
    """

    points: tuple[tuple[float, float, float], ...]
    source_point_count: int
    retained_point_count: int
    sampling_stride: int

    def __post_init__(self) -> None:
        if not self.points:
            raise ContractError("ClearanceCloud requires at least one point")
        if self.source_point_count < self.retained_point_count:
            raise ContractError("source_point_count cannot be smaller than retained_point_count")
        if self.retained_point_count != len(self.points):
            raise ContractError("retained_point_count must match points")
        if self.sampling_stride < 1:
            raise ContractError("sampling_stride must be >= 1")
        for point in self.points:
            if len(point) != 3:
                raise ContractError("ClearanceCloud points must contain three values")
            for value in point:
                if not isfinite(float(value)):
                    raise ContractError("ClearanceCloud points must be finite")

    @classmethod
    def from_local_points(
        cls,
        points: Iterable[tuple[float, float, float]],
        *,
        max_points: int = 50000,
    ) -> "ClearanceCloud":
        if type(max_points) is not int or max_points < 1:
            raise ContractError("max_points must be a positive integer")
        source = tuple(
            (float(right), float(up), float(forward))
            for right, up, forward in points
            if all(isfinite(float(value)) for value in (right, up, forward))
        )
        if not source:
            raise ContractError("No finite points available for clearance cloud")
        stride = max(1, (len(source) + max_points - 1) // max_points)
        retained = source[::stride]
        if len(retained) > max_points:
            retained = retained[:max_points]
        return cls(
            points=retained,
            source_point_count=len(source),
            retained_point_count=len(retained),
            sampling_stride=stride,
        )

    def query_components(self, right: float, up: float, forward: float) -> float:
        right = float(right)
        up = float(up)
        forward = float(forward)
        if not all(isfinite(value) for value in (right, up, forward)):
            return float("nan")
        best_sq = float("inf")
        for point_right, point_up, point_forward in self.points:
            dr = right - point_right
            du = up - point_up
            df = forward - point_forward
            distance_sq = dr * dr + du * du + df * df
            if distance_sq < best_sq:
                best_sq = distance_sq
                if best_sq <= 0.0:
                    return 0.0
        return sqrt(best_sq)

    def query(self, waypoint: RelativeWaypoint) -> float:
        return self.query_components(
            waypoint.right,
            waypoint.up,
            waypoint.forward,
        )

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10ClearanceCloud.v0.1",
            "method": "P9_PRIMARYMESH_VERTEX_CLEARANCE",
            "approximate": True,
            "source_point_count": self.source_point_count,
            "retained_point_count": self.retained_point_count,
            "sampling_stride": self.sampling_stride,
        }


def build_clearance_cloud(
    primary_mesh: str | Path,
    camera: CameraAuthority,
    *,
    max_points: int = 50000,
) -> ClearanceCloud:
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required for Gate 4.2 mesh clearance") from error

    path = Path(primary_mesh)
    if not path.is_file() or path.suffix.lower() != ".npz":
        raise ContractError(f"Clearance requires authoritative PrimaryMesh NPZ: {path}")

    try:
        with np.load(path, allow_pickle=False) as payload:
            if "vertices" not in payload.files:
                raise ContractError("PrimaryMesh NPZ is missing vertices")
            vertices = np.asarray(payload["vertices"], dtype=np.float64)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh for clearance: {path}: {error}") from error

    if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.shape[0] < 1:
        raise ContractError("PrimaryMesh vertices must have shape [N,3]")
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

    points = zip(right.tolist(), up.tolist(), forward.tolist())
    return ClearanceCloud.from_local_points(points, max_points=max_points)



@dataclass(frozen=True)
class FlightClearanceBatch:
    paths: tuple[CameraPath, ...]
    results: tuple[ClearanceResult, ...]

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10FlightClearanceBatch.v0.1",
            "mission_count_input": len(self.results),
            "mission_count_output": len(self.paths),
            "blocked_mission_count": sum(1 for result in self.results if result.blocked),
            "adapted_mission_count": sum(1 for result in self.results if result.adapted),
            "missions": [
                {
                    "name": result.path.name,
                    "blocked": result.blocked,
                    "adapted": result.adapted,
                    "minimum_clearance": result.minimum_clearance,
                    "shrink_scale": result.shrink_scale,
                    "reason": result.reason,
                    "sample_count": result.sample_count,
                }
                for result in self.results
            ],
        }


def adapt_paths_for_clearance(
    paths: tuple[CameraPath, ...],
    cloud: ClearanceCloud,
    *,
    min_clearance: float,
    samples_per_segment: int = 3,
    shrink_factor: float = 0.85,
    max_shrink_attempts: int = 4,
) -> FlightClearanceBatch:
    """Apply bounded clearance adaptation to each planned mission.

    Blocked missions are omitted from the returned active path list rather than
    failing the entire Refined pipeline. This keeps Gate 4.2 fail-safe while
    allowing the end-to-end implementation to continue with remaining missions.
    """

    if not paths:
        raise ContractError("At least one flight path is required for clearance")
    config = ClearanceConfig(
        min_clearance=min_clearance,
        samples_per_segment=samples_per_segment,
        shrink_factor=shrink_factor,
        max_shrink_attempts=max_shrink_attempts,
    )
    results = tuple(
        adapt_path_for_clearance(path, cloud.query, config)
        for path in paths
    )
    active = tuple(result.path for result in results if not result.blocked)
    return FlightClearanceBatch(paths=active, results=results)
