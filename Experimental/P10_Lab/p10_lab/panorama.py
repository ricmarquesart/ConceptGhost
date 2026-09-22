from __future__ import annotations

from dataclasses import dataclass
import json
from math import atan, atan2, cos, degrees, isfinite, pi, sin, sqrt
from pathlib import Path
from typing import Any, Sequence

from .contracts import CompletionBundle, ContractError


_MATRIX_TOLERANCE = 2.0e-3
_FOV_TOLERANCE_DEG = 1.0e-4


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ContractError(f"{label} must be finite")
    return number


def _positive_number(value: Any, label: str) -> float:
    number = _finite_number(value, label)
    if number <= 0.0:
        raise ContractError(f"{label} must be positive")
    return number


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _det3(rows: Sequence[Sequence[float]]) -> float:
    a, b, c = rows
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _validate_world_matrix(value: Any) -> tuple[tuple[float, ...], ...]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(row, list) or len(row) != 4 for row in value)
    ):
        raise ContractError("camera_world_matrix must be a 4x4 array")

    matrix = tuple(
        tuple(_finite_number(cell, "camera_world_matrix cell") for cell in row)
        for row in value
    )
    if any(abs(matrix[3][index]) > _MATRIX_TOLERANCE for index in range(3)):
        raise ContractError("camera_world_matrix must use an affine bottom row")
    if abs(matrix[3][3] - 1.0) > _MATRIX_TOLERANCE:
        raise ContractError("camera_world_matrix bottom-right value must be 1")

    rotation = tuple(row[:3] for row in matrix[:3])
    for index, row in enumerate(rotation):
        if abs(_dot(row, row) - 1.0) > _MATRIX_TOLERANCE:
            raise ContractError(f"camera_world_matrix rotation row {index} is not unit length")
    for left in range(3):
        for right in range(left + 1, 3):
            if abs(_dot(rotation[left], rotation[right])) > _MATRIX_TOLERANCE:
                raise ContractError("camera_world_matrix rotation is not orthogonal")
    if abs(_det3(rotation) - 1.0) > 5.0 * _MATRIX_TOLERANCE:
        raise ContractError("camera_world_matrix rotation must be right-handed")
    return matrix


@dataclass(frozen=True)
class CameraAuthority:
    """Canonical P9/Baseline camera used by the temporary P10 panorama.

    Camera-local coordinates are +X right, +Y up and -Z forward. Image
    coordinates are continuous pixel coordinates with top-left origin. The
    original camera world matrix remains authoritative; P10 does not solve a new
    camera merely to create the temporary panorama.
    """

    scene_contract_id: str
    schema: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    lens_model: str
    world_matrix: tuple[tuple[float, ...], ...]

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        *,
        expected_scene_contract_id: str,
    ) -> "CameraAuthority":
        path = Path(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ContractError(f"Cannot read camera JSON: {path}: {error}") from error
        return cls.from_payload(
            payload,
            expected_scene_contract_id=expected_scene_contract_id,
        )

    @classmethod
    def from_bundle(cls, bundle: CompletionBundle) -> "CameraAuthority":
        return cls.from_json(
            bundle.camera,
            expected_scene_contract_id=bundle.scene_contract_id,
        )

    @classmethod
    def from_payload(
        cls,
        payload: Any,
        *,
        expected_scene_contract_id: str,
    ) -> "CameraAuthority":
        if not isinstance(payload, dict):
            raise ContractError("Camera payload must be a JSON object")
        if payload.get("valid") is not True:
            raise ContractError("Camera authority must be valid")

        scene_contract_id = str(payload.get("scene_contract_id") or "").strip()
        if not scene_contract_id:
            raise ContractError("Camera authority is missing scene_contract_id")
        if scene_contract_id != expected_scene_contract_id:
            raise ContractError(
                "Camera scene_contract_id does not match the P9 Completion Bundle"
            )

        width = payload.get("image_width")
        height = payload.get("image_height")
        if type(width) is not int or width <= 0 or type(height) is not int or height <= 0:
            raise ContractError("Camera image dimensions must be positive integers")

        intrinsics = payload.get("intrinsics")
        if not isinstance(intrinsics, dict):
            raise ContractError("Camera intrinsics are required")
        lens_model = str(intrinsics.get("lens_model") or "").strip().lower()
        if lens_model != "pinhole":
            raise ContractError(
                f"Gate 3 panorama currently requires an undistorted pinhole camera, got {lens_model!r}"
            )
        distortion = intrinsics.get("distortion")
        if distortion not in ({}, None):
            raise ContractError(
                "Gate 3 panorama does not silently ignore lens distortion"
            )

        fx = _positive_number(intrinsics.get("fx_px"), "fx_px")
        fy = _positive_number(intrinsics.get("fy_px"), "fy_px")
        cx = _finite_number(intrinsics.get("cx_px"), "cx_px")
        cy = _finite_number(intrinsics.get("cy_px"), "cy_px")
        if not 0.0 <= cx <= float(width):
            raise ContractError("cx_px must lie inside the source image")
        if not 0.0 <= cy <= float(height):
            raise ContractError("cy_px must lie inside the source image")

        extrinsics = payload.get("extrinsics")
        if not isinstance(extrinsics, dict):
            raise ContractError("Camera extrinsics are required")
        world_matrix = _validate_world_matrix(extrinsics.get("camera_world_matrix"))

        position = extrinsics.get("camera_position")
        if position is not None:
            if not isinstance(position, list) or len(position) != 3:
                raise ContractError("camera_position must contain three numbers")
            xyz = tuple(_finite_number(value, "camera_position") for value in position)
            matrix_xyz = tuple(world_matrix[index][3] for index in range(3))
            if any(abs(left - right) > 1.0e-5 for left, right in zip(xyz, matrix_xyz)):
                raise ContractError(
                    "camera_position does not match camera_world_matrix translation"
                )

        camera = cls(
            scene_contract_id=scene_contract_id,
            schema=str(payload.get("schema") or ""),
            width=width,
            height=height,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
            lens_model=lens_model,
            world_matrix=world_matrix,
        )

        reported_hfov = payload.get("horizontal_fov_deg")
        if reported_hfov is not None:
            reported = _positive_number(reported_hfov, "horizontal_fov_deg")
            if abs(reported - camera.horizontal_fov_deg) > _FOV_TOLERANCE_DEG:
                raise ContractError(
                    "Reported horizontal_fov_deg does not match authoritative intrinsics"
                )
        return camera

    @property
    def horizontal_fov_deg(self) -> float:
        left = atan(self.cx / self.fx)
        right = atan((self.width - self.cx) / self.fx)
        return degrees(left + right)

    @property
    def vertical_fov_deg(self) -> float:
        top = atan(self.cy / self.fy)
        bottom = atan((self.height - self.cy) / self.fy)
        return degrees(top + bottom)


@dataclass(frozen=True)
class PanoramaSpec:
    width: int
    height: int

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("Panorama dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("Panorama dimensions must be positive")
        if self.width != 2 * self.height:
            raise ContractError("Equirectangular panorama must have an exact 2:1 aspect ratio")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


def _validate_source_pixel(camera: CameraAuthority, x: float, y: float) -> tuple[float, float]:
    x = _finite_number(x, "source x")
    y = _finite_number(y, "source y")
    if not 0.0 <= x <= float(camera.width) or not 0.0 <= y <= float(camera.height):
        raise ContractError("Source coordinate lies outside the source image")
    return x, y


def _validate_erp_pixel(spec: PanoramaSpec, u: float, v: float) -> tuple[float, float]:
    u = _finite_number(u, "ERP u")
    v = _finite_number(v, "ERP v")
    if not 0.0 <= u <= float(spec.width) or not 0.0 <= v <= float(spec.height):
        raise ContractError("ERP coordinate lies outside the panorama")
    return u, v


def source_pixel_to_camera_ray(
    camera: CameraAuthority,
    x: float,
    y: float,
) -> tuple[float, float, float]:
    x, y = _validate_source_pixel(camera, x, y)
    ray_x = (x - camera.cx) / camera.fx
    ray_y = (camera.cy - y) / camera.fy
    ray_z = -1.0
    length = sqrt(ray_x * ray_x + ray_y * ray_y + ray_z * ray_z)
    return ray_x / length, ray_y / length, ray_z / length


def camera_ray_to_erp(
    spec: PanoramaSpec,
    ray: Sequence[float],
) -> tuple[float, float]:
    if len(ray) != 3:
        raise ContractError("Camera ray must contain three values")
    x, y, z = (_finite_number(value, "camera ray") for value in ray)
    length = sqrt(x * x + y * y + z * z)
    if length <= 0.0:
        raise ContractError("Camera ray cannot have zero length")
    x, y, z = x / length, y / length, z / length

    longitude = atan2(x, -z)
    latitude = atan2(y, sqrt(x * x + z * z))
    u = (0.5 + longitude / (2.0 * pi)) * spec.width
    v = (0.5 - latitude / pi) * spec.height
    return u, v


def source_pixel_to_erp(
    camera: CameraAuthority,
    spec: PanoramaSpec,
    x: float,
    y: float,
) -> tuple[float, float]:
    return camera_ray_to_erp(spec, source_pixel_to_camera_ray(camera, x, y))


def erp_pixel_to_camera_ray(
    spec: PanoramaSpec,
    u: float,
    v: float,
) -> tuple[float, float, float]:
    u, v = _validate_erp_pixel(spec, u, v)
    longitude = (u / spec.width - 0.5) * (2.0 * pi)
    latitude = (0.5 - v / spec.height) * pi
    cos_latitude = cos(latitude)
    return (
        sin(longitude) * cos_latitude,
        sin(latitude),
        -cos(longitude) * cos_latitude,
    )


def camera_ray_to_source_pixel(
    camera: CameraAuthority,
    ray: Sequence[float],
) -> tuple[float, float]:
    if len(ray) != 3:
        raise ContractError("Camera ray must contain three values")
    x, y, z = (_finite_number(value, "camera ray") for value in ray)
    if z >= -1.0e-12:
        raise ContractError("Camera ray does not point into the source camera's forward hemisphere")
    scale = -z
    source_x = camera.cx + camera.fx * (x / scale)
    source_y = camera.cy - camera.fy * (y / scale)
    return source_x, source_y
