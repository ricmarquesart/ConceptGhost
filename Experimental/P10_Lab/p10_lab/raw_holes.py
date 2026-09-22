from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContractError


RAW_HOLE_POLICY = "RAW_UNSUPPORTED_P9_GEOMETRY_NO_FILL"


def coverage_to_hole_bytes(
    width: int,
    height: int,
    coverage,
) -> bytes:
    if type(width) is not int or type(height) is not int:
        raise ContractError("Raw-hole dimensions must be integers")
    if width <= 0 or height <= 0:
        raise ContractError("Raw-hole dimensions must be positive")
    values = list(coverage)
    if len(values) != width * height:
        raise ContractError("Coverage length does not match raw-hole dimensions")
    return bytes(0 if bool(value) else 255 for value in values)


@dataclass(frozen=True)
class RawHoleFrame:
    width: int
    height: int
    mask: bytes
    observed_pixel_count: int
    hole_pixel_count: int
    policy: str = RAW_HOLE_POLICY

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("Raw-hole frame dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("Raw-hole frame dimensions must be positive")
        if len(self.mask) != self.width * self.height:
            raise ContractError("Raw-hole mask size does not match dimensions")
        if not set(self.mask).issubset({0, 255}):
            raise ContractError("Raw-hole mask must be strictly binary")
        if self.observed_pixel_count < 0 or self.hole_pixel_count < 0:
            raise ContractError("Raw-hole pixel counts cannot be negative")
        if self.observed_pixel_count + self.hole_pixel_count != self.width * self.height:
            raise ContractError("Raw-hole pixel counts do not cover the full frame")

    @classmethod
    def from_coverage(cls, width: int, height: int, coverage) -> "RawHoleFrame":
        values = [bool(value) for value in coverage]
        mask = coverage_to_hole_bytes(width, height, values)
        observed = sum(values)
        holes = width * height - observed
        return cls(
            width=width,
            height=height,
            mask=mask,
            observed_pixel_count=observed,
            hole_pixel_count=holes,
        )

    @property
    def hole_fraction(self) -> float:
        return self.hole_pixel_count / float(self.width * self.height)

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10RawHoleFrame.v0.1",
            "policy": self.policy,
            "width": self.width,
            "height": self.height,
            "observed_pixel_count": self.observed_pixel_count,
            "hole_pixel_count": self.hole_pixel_count,
            "hole_fraction": self.hole_fraction,
            "geometry_fill_applied": False,
            "morphological_close_applied": False,
            "unknown_region_compensation": False,
        }
