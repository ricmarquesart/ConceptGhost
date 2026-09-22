from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .contracts import ContractError
from .panorama_projection import ProjectionPlan


SOURCE_LOCK_POLICY = "SOURCE_OBSERVED_LOCKED_NO_GENERATION"


@dataclass(frozen=True)
class RowSpan:
    start_x: int
    end_x: int

    def __post_init__(self) -> None:
        if type(self.start_x) is not int or type(self.end_x) is not int:
            raise ContractError("RowSpan bounds must be integers")
        if self.start_x < 0 or self.end_x <= self.start_x:
            raise ContractError("RowSpan must have positive width")

    @property
    def width(self) -> int:
        return self.end_x - self.start_x


@dataclass(frozen=True)
class ObservationMap:
    width: int
    height: int
    scene_contract_id: str
    row_spans: tuple[RowSpan | None, ...]
    policy: str = SOURCE_LOCK_POLICY

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("ObservationMap dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("ObservationMap dimensions must be positive")
        if len(self.row_spans) != self.height:
            raise ContractError("ObservationMap must provide exactly one row span per ERP row")
        if not self.scene_contract_id:
            raise ContractError("ObservationMap requires scene_contract_id")
        for span in self.row_spans:
            if span is not None and span.end_x > self.width:
                raise ContractError("Observed row span exceeds panorama width")

    def _check_pixel(self, x: int, y: int) -> None:
        if type(x) is not int or type(y) is not int:
            raise ContractError("Pixel coordinates must be integers")
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ContractError("Pixel coordinate lies outside the observation map")

    def is_observed(self, x: int, y: int) -> bool:
        self._check_pixel(x, y)
        span = self.row_spans[y]
        return span is not None and span.start_x <= x < span.end_x

    def is_unknown(self, x: int, y: int) -> bool:
        return not self.is_observed(x, y)

    @property
    def observed_pixel_count(self) -> int:
        return sum(span.width for span in self.row_spans if span is not None)

    @property
    def unknown_pixel_count(self) -> int:
        return self.width * self.height - self.observed_pixel_count

    @property
    def observed_fraction(self) -> float:
        return self.observed_pixel_count / (self.width * self.height)

    def source_lock_bytes(self) -> bytes:
        """Return one byte per ERP pixel: observed=255, unknown=0."""
        result = bytearray(self.width * self.height)
        for y, span in enumerate(self.row_spans):
            if span is None:
                continue
            start = y * self.width + span.start_x
            end = y * self.width + span.end_x
            result[start:end] = b"\xff" * span.width
        return bytes(result)

    def unknown_mask_bytes(self) -> bytes:
        """Return one byte per ERP pixel: unknown=255, observed=0."""
        lock = self.source_lock_bytes()
        return bytes(255 - value for value in lock)

    @property
    def sha256(self) -> str:
        return sha256(self.source_lock_bytes()).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10ObservationMap.v0.1",
            "scene_contract_id": self.scene_contract_id,
            "policy": self.policy,
            "width": self.width,
            "height": self.height,
            "observed_value": 255,
            "unknown_value": 0,
            "observed_pixel_count": self.observed_pixel_count,
            "unknown_pixel_count": self.unknown_pixel_count,
            "observed_fraction": self.observed_fraction,
            "source_lock_sha256": self.sha256,
        }


def build_observation_map(plan: ProjectionPlan) -> ObservationMap:
    """Rasterize authoritative source visibility without dilation or feathering.

    The map is an authority mask, not an aesthetic blend mask. A pixel is
    observed only when its ERP pixel center maps back inside the original source
    camera. Unknown is the exact complement and is the only region later stages
    may nominate for generation.
    """

    min_x, min_y, max_x, max_y = plan.integer_bounds
    rows: list[RowSpan | None] = [None] * plan.spec.height

    for y in range(min_y, max_y):
        observed_x = [
            x
            for x in range(min_x, max_x)
            if plan.sample_pixel(x, y) is not None
        ]
        if not observed_x:
            continue

        start = observed_x[0]
        end = observed_x[-1] + 1

        # The projection of one undistorted pinhole image must be contiguous on
        # each row in this camera-local, seam-safe ERP orientation.
        for x in range(start, end):
            if plan.sample_pixel(x, y) is None:
                raise ContractError(
                    "Observed source footprint became non-contiguous; "
                    "refuse to create a misleading source-lock mask"
                )
        rows[y] = RowSpan(start, end)

    observation = ObservationMap(
        width=plan.spec.width,
        height=plan.spec.height,
        scene_contract_id=plan.camera.scene_contract_id,
        row_spans=tuple(rows),
    )
    if observation.observed_pixel_count <= 0:
        raise ContractError("Source projection produced no observed ERP pixels")
    return observation
