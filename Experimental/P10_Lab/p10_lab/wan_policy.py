from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContractError


@dataclass(frozen=True)
class WanRuntimeProfile:
    width: int
    height: int
    length: int
    steps: int
    cfg: float
    max_parallel_windows: int
    offload_between_windows: bool
    use_fp8_unet: bool
    hardware_target: str = "RTX_2080_TI_11GB"
    hole_fill: str = "black"

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("WAN width/height must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("WAN width/height must be positive")
        if self.width % 16 or self.height % 16:
            raise ContractError("WAN width/height must be multiples of 16")
        if type(self.length) is not int or self.length < 1:
            raise ContractError("WAN length must be a positive integer")
        if type(self.steps) is not int or self.steps < 1:
            raise ContractError("WAN steps must be a positive integer")
        if float(self.cfg) <= 0.0:
            raise ContractError("WAN cfg must be positive")
        if type(self.max_parallel_windows) is not int or self.max_parallel_windows != 1:
            raise ContractError(
                "Gate 5 first-pass WAN policy requires exactly one active window on 11 GB"
            )
        if not self.offload_between_windows:
            raise ContractError("11 GB WAN profile requires offload_between_windows=True")
        if not self.use_fp8_unet:
            raise ContractError("11 GB WAN profile requires fp8 UNet")
        if self.hole_fill not in {"black", "gray"}:
            raise ContractError("hole_fill must be black or gray")

    @classmethod
    def default_11gb(cls) -> "WanRuntimeProfile":
        return cls(
            width=832,
            height=480,
            length=33,
            steps=4,
            cfg=1.0,
            max_parallel_windows=1,
            offload_between_windows=True,
            use_fp8_unet=True,
            hardware_target="RTX_2080_TI_11GB",
            hole_fill="black",
        )

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10WanRuntimeProfile.v0.1",
            "hardware_target": self.hardware_target,
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "steps": self.steps,
            "cfg": self.cfg,
            "use_fp8_unet": self.use_fp8_unet,
            "window_policy": "SEQUENTIAL_ONLY",
            "max_parallel_windows": self.max_parallel_windows,
            "offload_between_windows": self.offload_between_windows,
            "hole_fill": self.hole_fill,
        }
