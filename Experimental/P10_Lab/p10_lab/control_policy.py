from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import ContractError


@dataclass(frozen=True)
class RawHoleControlPolicy:
    """Rendering policy for the P10-only evidence-mesh derivative.

    These defaults deliberately preserve absence of evidence. They are not
    settings for the standalone Baseline mesh and must never mutate it.
    """

    fill_holes: bool = False
    bridge_depth_discontinuities: bool = False
    smooth_unknown_regions: bool = False
    extrapolate_silhouettes: bool = False
    unknown_pixel_mode: str = "black"
    emit_binary_mask: bool = True
    lock_observed_pixels: bool = True

    def __post_init__(self) -> None:
        prohibited = {
            "fill_holes": self.fill_holes,
            "bridge_depth_discontinuities": self.bridge_depth_discontinuities,
            "smooth_unknown_regions": self.smooth_unknown_regions,
            "extrapolate_silhouettes": self.extrapolate_silhouettes,
        }
        enabled = [name for name, value in prohibited.items() if value is not False]
        if enabled:
            raise ContractError(
                "Raw-hole policy cannot enable missing-geometry compensation: "
                + ", ".join(enabled)
            )
        if self.unknown_pixel_mode != "black":
            raise ContractError("Raw-hole unknown pixels must render as black")
        if self.emit_binary_mask is not True:
            raise ContractError("Raw-hole control must emit a binary mask")
        if self.lock_observed_pixels is not True:
            raise ContractError("Observed source pixels must remain locked")

    def to_manifest(self) -> dict[str, Any]:
        return {
            "scope": "p10_control_derivative",
            "baseline_mutated": False,
            **asdict(self),
        }
