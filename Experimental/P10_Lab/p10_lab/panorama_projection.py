from __future__ import annotations

from dataclasses import dataclass
from math import floor

from .contracts import ContractError
from .panorama import (
    CameraAuthority,
    PanoramaSpec,
    camera_ray_to_source_pixel,
    erp_pixel_to_camera_ray,
    source_pixel_to_erp,
)


@dataclass(frozen=True)
class ProjectionSample:
    erp_u: float
    erp_v: float
    source_x: float
    source_y: float


@dataclass(frozen=True)
class SourceFootprint:
    min_u: float
    max_u: float
    min_v: float
    max_v: float
    boundary_samples: int

    @property
    def width(self) -> float:
        return self.max_u - self.min_u

    @property
    def height(self) -> float:
        return self.max_v - self.min_v


@dataclass(frozen=True)
class ProjectionPlan:
    """Resolution-independent source placement on a camera-local ERP canvas.

    The authoritative source camera is centered at longitude=0 / latitude=0.
    This plan does not generate missing pixels and does not change the P9 camera.
    It only defines where source evidence lands and how an ERP sample maps back
    to the source image.
    """

    camera: CameraAuthority
    spec: PanoramaSpec
    footprint: SourceFootprint

    def project_source(self, source_x: float, source_y: float) -> ProjectionSample:
        erp_u, erp_v = source_pixel_to_erp(
            self.camera,
            self.spec,
            source_x,
            source_y,
        )
        return ProjectionSample(
            erp_u=erp_u,
            erp_v=erp_v,
            source_x=float(source_x),
            source_y=float(source_y),
        )

    def sample_continuous(self, erp_u: float, erp_v: float) -> ProjectionSample | None:
        try:
            ray = erp_pixel_to_camera_ray(self.spec, erp_u, erp_v)
            source_x, source_y = camera_ray_to_source_pixel(self.camera, ray)
        except ContractError:
            return None

        epsilon = 1.0e-7
        if (
            source_x < -epsilon
            or source_y < -epsilon
            or source_x > self.camera.width + epsilon
            or source_y > self.camera.height + epsilon
        ):
            return None

        source_x = min(float(self.camera.width), max(0.0, source_x))
        source_y = min(float(self.camera.height), max(0.0, source_y))
        return ProjectionSample(
            erp_u=float(erp_u),
            erp_v=float(erp_v),
            source_x=source_x,
            source_y=source_y,
        )

    def sample_pixel(self, erp_x: int, erp_y: int) -> ProjectionSample | None:
        if type(erp_x) is not int or type(erp_y) is not int:
            raise ContractError("ERP pixel indexes must be integers")
        if not 0 <= erp_x < self.spec.width or not 0 <= erp_y < self.spec.height:
            raise ContractError("ERP pixel index lies outside the panorama")
        return self.sample_continuous(erp_x + 0.5, erp_y + 0.5)

    @property
    def integer_bounds(self) -> tuple[int, int, int, int]:
        """Return conservative inclusive/exclusive raster bounds."""
        min_x = max(0, int(floor(self.footprint.min_u)))
        min_y = max(0, int(floor(self.footprint.min_v)))
        max_x = min(self.spec.width, int(floor(self.footprint.max_u)) + 1)
        max_y = min(self.spec.height, int(floor(self.footprint.max_v)) + 1)
        return min_x, min_y, max_x, max_y


def _boundary_source_points(
    camera: CameraAuthority,
    samples_per_edge: int,
) -> tuple[tuple[float, float], ...]:
    if type(samples_per_edge) is not int or samples_per_edge < 3:
        raise ContractError("samples_per_edge must be an integer >= 3")

    width = float(camera.width)
    height = float(camera.height)
    steps = tuple(index / (samples_per_edge - 1) for index in range(samples_per_edge))
    points: list[tuple[float, float]] = []

    for amount in steps:
        x = amount * width
        points.append((x, 0.0))
        points.append((x, height))
    for amount in steps:
        y = amount * height
        points.append((0.0, y))
        points.append((width, y))
    return tuple(points)


def build_projection_plan(
    camera: CameraAuthority,
    spec: PanoramaSpec,
    *,
    boundary_samples_per_edge: int = 33,
) -> ProjectionPlan:
    points = _boundary_source_points(camera, boundary_samples_per_edge)
    projected = [source_pixel_to_erp(camera, spec, x, y) for x, y in points]

    min_u = min(point[0] for point in projected)
    max_u = max(point[0] for point in projected)
    min_v = min(point[1] for point in projected)
    max_v = max(point[1] for point in projected)

    if min_u <= 0.0 or max_u >= float(spec.width):
        raise ContractError(
            "Authoritative source footprint touches the ERP seam; "
            "camera-local panorama orientation must keep source evidence away from the seam"
        )
    if min_v <= 0.0 or max_v >= float(spec.height):
        raise ContractError(
            "Authoritative source footprint touches an ERP pole"
        )
    if max_u - min_u >= spec.width / 2.0:
        raise ContractError("Source footprint is too wide for the bounded local panorama contract")
    if max_v - min_v >= spec.height / 2.0:
        raise ContractError("Source footprint is too tall for the bounded local panorama contract")

    footprint = SourceFootprint(
        min_u=min_u,
        max_u=max_u,
        min_v=min_v,
        max_v=max_v,
        boundary_samples=len(points),
    )
    return ProjectionPlan(camera=camera, spec=spec, footprint=footprint)
