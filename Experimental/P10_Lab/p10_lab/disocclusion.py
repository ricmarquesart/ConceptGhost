from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContractError


DISOCCLUSION_POLICY = "RAW_P9_UNSUPPORTED_AS_GENERATION_CANDIDATE"


@dataclass(frozen=True)
class DisocclusionMask:
    width: int
    height: int
    mask: bytes
    policy: str = DISOCCLUSION_POLICY
    feathered: bool = False
    dilated: bool = False

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("Disocclusion dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("Disocclusion dimensions must be positive")
        if len(self.mask) != self.width * self.height:
            raise ContractError("Disocclusion mask size does not match dimensions")
        if not set(self.mask).issubset({0, 255}):
            raise ContractError("Disocclusion mask must be strictly binary")

    @property
    def candidate_pixel_count(self) -> int:
        return self.mask.count(255)

    @property
    def candidate_fraction(self) -> float:
        return self.candidate_pixel_count / float(self.width * self.height)

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10DisocclusionMask.v0.1",
            "policy": self.policy,
            "width": self.width,
            "height": self.height,
            "candidate_pixel_count": self.candidate_pixel_count,
            "candidate_fraction": self.candidate_fraction,
            "feathered": self.feathered,
            "dilated": self.dilated,
            "geometry_fill_applied": False,
        }


def build_disocclusion_mask(width: int, height: int, raw_hole_mask: bytes) -> DisocclusionMask:
    return DisocclusionMask(width=width, height=height, mask=bytes(raw_hole_mask))
