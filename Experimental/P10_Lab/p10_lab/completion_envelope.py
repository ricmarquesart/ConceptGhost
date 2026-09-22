from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, isfinite, sqrt
from typing import Sequence

from .contracts import ContractError, SceneScale
from .observation_map import ObservationMap
from .panorama import CameraAuthority, _finite_number, erp_pixel_to_camera_ray
from .panorama_projection import ProjectionPlan


@dataclass(frozen=True)
class CompletionEnvelopeConfig:
    lateral_limit_fraction: float = 0.35
    forward_limit_fraction: float = 0.35
    backward_limit_fraction: float = 0.08
    elevation_limit_fraction: float = 0.15
    yaw_margin_deg: float = 55.0
    pitch_margin_deg: float = 35.0
    max_yaw_deg: float = 95.0
    max_pitch_deg: float = 70.0

    def __post_init__(self) -> None:
        for name in (
            "lateral_limit_fraction",
            "forward_limit_fraction",
            "backward_limit_fraction",
            "elevation_limit_fraction",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0.0
                or value > 1.0
            ):
                raise ContractError(f"{name} must be finite and in (0, 1]")

        for name in ("yaw_margin_deg", "pitch_margin_deg", "max_yaw_deg", "max_pitch_deg"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0.0
            ):
                raise ContractError(f"{name} must be finite and positive")

        if self.max_yaw_deg >= 180.0:
            raise ContractError("max_yaw_deg must remain below the ERP rear seam")
        if self.max_pitch_deg >= 90.0:
            raise ContractError("max_pitch_deg must remain below the ERP poles")


@dataclass(frozen=True)
class CompletionEnvelope:
    scene_contract_id: str
    scene_radius: float
    right_limit: float
    up_limit: float
    forward_min: float
    forward_max: float
    yaw_limit_deg: float
    pitch_limit_deg: float

    def contains_offset(self, right: float, up: float, forward: float) -> bool:
        right = _finite_number(right, "right offset")
        up = _finite_number(up, "up offset")
        forward = _finite_number(forward, "forward offset")
        return (
            -self.right_limit <= right <= self.right_limit
            and -self.up_limit <= up <= self.up_limit
            and self.forward_min <= forward <= self.forward_max
        )

    def contains_camera_ray(self, ray: Sequence[float]) -> bool:
        if len(ray) != 3:
            raise ContractError("Camera ray must contain three values")
        x, y, z = (_finite_number(value, "camera ray") for value in ray)
        length = sqrt(x * x + y * y + z * z)
        if length <= 0.0:
            raise ContractError("Camera ray cannot have zero length")
        x, y, z = x / length, y / length, z / length

        yaw = degrees(atan2(x, -z))
        pitch = degrees(atan2(y, sqrt(x * x + z * z)))
        return abs(yaw) <= self.yaw_limit_deg and abs(pitch) <= self.pitch_limit_deg

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10CompletionEnvelope.v0.1",
            "scene_contract_id": self.scene_contract_id,
            "scene_radius": self.scene_radius,
            "translation_limits": {
                "right_abs": self.right_limit,
                "up_abs": self.up_limit,
                "forward_min": self.forward_min,
                "forward_max": self.forward_max,
            },
            "angular_limits_deg": {
                "yaw_abs": self.yaw_limit_deg,
                "pitch_abs": self.pitch_limit_deg,
            },
            "world_scale_exploration": False,
            "full_360_generation": False,
        }


@dataclass(frozen=True)
class GenerationCandidateMap:
    width: int
    height: int
    scene_contract_id: str
    pixels: bytes

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("Candidate map dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("Candidate map dimensions must be positive")
        if len(self.pixels) != self.width * self.height:
            raise ContractError("Candidate map byte count does not match dimensions")
        if not set(self.pixels).issubset({0, 255}):
            raise ContractError("Candidate map must be strictly binary")

    def _index(self, x: int, y: int) -> int:
        if type(x) is not int or type(y) is not int:
            raise ContractError("Candidate pixel coordinates must be integers")
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ContractError("Candidate pixel lies outside the panorama")
        return y * self.width + x

    def is_candidate(self, x: int, y: int) -> bool:
        return self.pixels[self._index(x, y)] == 255

    @property
    def candidate_pixel_count(self) -> int:
        return self.pixels.count(255)

    @property
    def candidate_fraction(self) -> float:
        return self.candidate_pixel_count / (self.width * self.height)

    def mask_bytes(self) -> bytes:
        return self.pixels

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10GenerationCandidateMap.v0.1",
            "scene_contract_id": self.scene_contract_id,
            "candidate_value": 255,
            "blocked_value": 0,
            "candidate_pixel_count": self.candidate_pixel_count,
            "candidate_fraction": self.candidate_fraction,
            "rule": "UNKNOWN_AND_INSIDE_LOCAL_COMPLETION_ENVELOPE",
        }


def build_completion_envelope(
    camera: CameraAuthority,
    scale: SceneScale,
    config: CompletionEnvelopeConfig | None = None,
) -> CompletionEnvelope:
    config = config or CompletionEnvelopeConfig()
    radius = float(scale.radius)

    yaw_limit = min(
        config.max_yaw_deg,
        camera.horizontal_fov_deg / 2.0 + config.yaw_margin_deg,
    )
    pitch_limit = min(
        config.max_pitch_deg,
        camera.vertical_fov_deg / 2.0 + config.pitch_margin_deg,
    )

    return CompletionEnvelope(
        scene_contract_id=camera.scene_contract_id,
        scene_radius=radius,
        right_limit=config.lateral_limit_fraction * radius,
        up_limit=config.elevation_limit_fraction * radius,
        forward_min=-config.backward_limit_fraction * radius,
        forward_max=config.forward_limit_fraction * radius,
        yaw_limit_deg=yaw_limit,
        pitch_limit_deg=pitch_limit,
    )


def build_generation_candidate_map(
    projection: ProjectionPlan,
    observation: ObservationMap,
    envelope: CompletionEnvelope,
) -> GenerationCandidateMap:
    if observation.width != projection.spec.width or observation.height != projection.spec.height:
        raise ContractError("Observation map and panorama projection dimensions differ")
    if observation.scene_contract_id != projection.camera.scene_contract_id:
        raise ContractError("Observation map scene identity differs from projection")
    if envelope.scene_contract_id != projection.camera.scene_contract_id:
        raise ContractError("Completion envelope scene identity differs from projection")

    pixels = bytearray(projection.spec.width * projection.spec.height)
    for y in range(projection.spec.height):
        for x in range(projection.spec.width):
            if observation.is_observed(x, y):
                continue
            ray = erp_pixel_to_camera_ray(
                projection.spec,
                x + 0.5,
                y + 0.5,
            )
            if envelope.contains_camera_ray(ray):
                pixels[y * projection.spec.width + x] = 255

    result = GenerationCandidateMap(
        width=projection.spec.width,
        height=projection.spec.height,
        scene_contract_id=projection.camera.scene_contract_id,
        pixels=bytes(pixels),
    )
    if result.candidate_pixel_count <= 0:
        raise ContractError("Local completion envelope produced no generation candidates")
    return result
