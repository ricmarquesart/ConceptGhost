from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from math import ceil, floor, isfinite, sqrt
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
    source_face_count: int = 0
    retained_vertex_count: int = 0
    retained_surface_sample_count: int = 0
    grid_cell_size: float = 0.50

    def __post_init__(self) -> None:
        if not self.points:
            raise ContractError("ClearanceCloud requires at least one point")
        if self.source_point_count < self.retained_point_count:
            raise ContractError("source_point_count cannot be smaller than retained_point_count")
        if self.retained_point_count != len(self.points):
            raise ContractError("retained_point_count must match points")
        if self.sampling_stride < 1:
            raise ContractError("sampling_stride must be >= 1")
        if self.source_face_count < 0:
            raise ContractError("source_face_count cannot be negative")
        if self.retained_vertex_count < 0 or self.retained_surface_sample_count < 0:
            raise ContractError("retained clearance sample counts cannot be negative")
        if self.grid_cell_size <= 0.0 or not isfinite(float(self.grid_cell_size)):
            raise ContractError("grid_cell_size must be finite and positive")
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
            retained_vertex_count=len(retained),
            retained_surface_sample_count=0,
        )

    @cached_property
    def _grid(self) -> dict[tuple[int, int, int], tuple[tuple[float, float, float], ...]]:
        """Spatial buckets used by dense authored-route collision preflight."""

        buckets: dict[tuple[int, int, int], list[tuple[float, float, float]]] = {}
        size=float(self.grid_cell_size)
        for point in self.points:
            key=(
                floor(point[0]/size),
                floor(point[1]/size),
                floor(point[2]/size),
            )
            buckets.setdefault(key,[]).append(point)
        return {key:tuple(values) for key,values in buckets.items()}

    def clearance_below(
        self,
        right: float,
        up: float,
        forward: float,
        threshold: float,
    ) -> float | None:
        """Return nearest sampled-surface distance only when it is below threshold.

        This threshold query is intentionally much cheaper than an exact global
        nearest-neighbour search and is the primitive used by authored-route
        collision checks.
        """

        right=float(right)
        up=float(up)
        forward=float(forward)
        threshold=float(threshold)
        if threshold < 0.0 or not all(isfinite(v) for v in (right,up,forward,threshold)):
            return None
        size=float(self.grid_cell_size)
        radius=max(0,ceil(threshold/size))
        base=(floor(right/size),floor(up/size),floor(forward/size))
        best_sq=threshold*threshold
        found=False
        grid=self._grid
        for dx in range(-radius,radius+1):
            for dy in range(-radius,radius+1):
                for dz in range(-radius,radius+1):
                    for pr,pu,pf in grid.get((base[0]+dx,base[1]+dy,base[2]+dz),()):
                        dr=right-pr
                        du=up-pu
                        df=forward-pf
                        distance_sq=dr*dr+du*du+df*df
                        if distance_sq < best_sq:
                            best_sq=distance_sq
                            found=True
                            if best_sq <= 0.0:
                                return 0.0
        return sqrt(best_sq) if found else None

    def waypoint_is_blocked(self, waypoint: RelativeWaypoint, min_clearance: float) -> bool:
        return self.clearance_below(
            waypoint.right,
            waypoint.up,
            waypoint.forward,
            min_clearance,
        ) is not None

    def segment_is_blocked(
        self,
        start: RelativeWaypoint,
        end: RelativeWaypoint,
        min_clearance: float,
        *,
        sample_step: float | None = None,
        max_samples: int = 4096,
    ) -> bool:
        """Sample the complete camera translation, not only emitted frame endpoints."""

        threshold=float(min_clearance)
        if threshold < 0.0 or not isfinite(threshold):
            raise ContractError("min_clearance must be finite and non-negative")
        if type(max_samples) is not int or max_samples < 2:
            raise ContractError("max_samples must be an integer >= 2")
        dr=float(end.right)-float(start.right)
        du=float(end.up)-float(start.up)
        df=float(end.forward)-float(start.forward)
        length=sqrt(dr*dr+du*du+df*df)
        if sample_step is None:
            sample_step=max(0.025,threshold*0.50)
        sample_step=float(sample_step)
        if sample_step <= 0.0 or not isfinite(sample_step):
            raise ContractError("sample_step must be finite and positive")
        count=max(2,min(max_samples,ceil(length/sample_step)+1))
        denominator=float(max(1,count-1))
        for index in range(count):
            t=index/denominator
            if self.clearance_below(
                float(start.right)+dr*t,
                float(start.up)+du*t,
                float(start.forward)+df*t,
                threshold,
            ) is not None:
                return True
        return False

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
            "method": "P9_PRIMARYMESH_VERTEX_PLUS_FACE_CENTROID_CLEARANCE",
            "approximate": True,
            "source_point_count": self.source_point_count,
            "source_face_count": self.source_face_count,
            "retained_point_count": self.retained_point_count,
            "retained_vertex_count": self.retained_vertex_count,
            "retained_surface_sample_count": self.retained_surface_sample_count,
            "sampling_stride": self.sampling_stride,
            "grid_cell_size": self.grid_cell_size,
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

    faces=None
    try:
        with np.load(path, allow_pickle=False) as payload:
            if "faces" in payload.files:
                candidate=np.asarray(payload["faces"],dtype=np.int64)
                if candidate.ndim==2 and candidate.shape[1]>=3:
                    faces=candidate[:,:3]
    except Exception:
        faces=None

    world = np.asarray(camera.world_matrix, dtype=np.float64)
    rotation = world[:3, :3]
    center = world[:3, 3]
    right_axis = rotation[:, 0]
    up_axis = rotation[:, 1]
    forward_axis = -rotation[:, 2]

    def to_local(array):
        local=array-center[None,:]
        return np.column_stack((
            local@right_axis,
            local@up_axis,
            local@forward_axis,
        ))

    surface_budget=max_points//2 if faces is not None and len(faces) else 0
    vertex_budget=max_points-surface_budget
    vertex_stride=max(1,(len(vertices)+vertex_budget-1)//max(1,vertex_budget))
    selected_vertices=vertices[::vertex_stride][:vertex_budget]
    samples=[to_local(selected_vertices)]
    retained_surface=0

    if surface_budget and faces is not None:
        face_stride=max(1,(len(faces)+surface_budget-1)//surface_budget)
        selected_faces=faces[::face_stride][:surface_budget]
        valid=(
            (selected_faces>=0).all(axis=1)
            & (selected_faces<len(vertices)).all(axis=1)
        )
        selected_faces=selected_faces[valid]
        if len(selected_faces):
            centroids=(
                vertices[selected_faces[:,0]]
                +vertices[selected_faces[:,1]]
                +vertices[selected_faces[:,2]]
            )/3.0
            samples.append(to_local(centroids))
            retained_surface=len(centroids)

    combined=np.concatenate(samples,axis=0)
    points=tuple(tuple(float(v) for v in row) for row in combined.tolist())
    if not points:
        raise ContractError("No finite PrimaryMesh surface samples available for clearance")
    return ClearanceCloud(
        points=points,
        source_point_count=len(vertices),
        retained_point_count=len(points),
        sampling_stride=vertex_stride,
        source_face_count=0 if faces is None else len(faces),
        retained_vertex_count=len(selected_vertices),
        retained_surface_sample_count=retained_surface,
        grid_cell_size=max(0.10,min(1.0,float(max(0.20,0.5)))),
    )



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
