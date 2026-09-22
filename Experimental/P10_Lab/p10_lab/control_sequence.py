from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContractError


@dataclass(frozen=True)
class ControlFrameRecord:
    global_frame_index: int
    path_name: str
    path_frame_index: int
    hole_fraction: float
    frame_file: str
    mask_file: str

    def __post_init__(self) -> None:
        if type(self.global_frame_index) is not int or self.global_frame_index < 0:
            raise ContractError("global_frame_index must be a nonnegative integer")
        if type(self.path_frame_index) is not int or self.path_frame_index < 0:
            raise ContractError("path_frame_index must be a nonnegative integer")
        if not str(self.path_name).strip():
            raise ContractError("path_name cannot be empty")
        if not 0.0 <= float(self.hole_fraction) <= 1.0:
            raise ContractError("hole_fraction must be in [0,1]")
        if not str(self.frame_file).strip() or not str(self.mask_file).strip():
            raise ContractError("control frame and mask filenames are required")

    def to_dict(self) -> dict[str, object]:
        return {
            "global_frame_index": self.global_frame_index,
            "path_name": self.path_name,
            "path_frame_index": self.path_frame_index,
            "hole_fraction": float(self.hole_fraction),
            "frame_file": self.frame_file,
            "mask_file": self.mask_file,
        }


@dataclass(frozen=True)
class ControlSequenceManifest:
    frames: tuple[ControlFrameRecord, ...]
    width: int
    height: int

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ContractError("Control sequence dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("Control sequence dimensions must be positive")
        if not self.frames:
            raise ContractError("Control sequence requires at least one frame")
        expected = list(range(len(self.frames)))
        actual = [frame.global_frame_index for frame in self.frames]
        if actual != expected:
            raise ContractError("Control sequence global frame indexes must be contiguous from zero")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10ControlSequence.v0.1",
            "frame_count": len(self.frames),
            "width": self.width,
            "height": self.height,
            "frames": [frame.to_dict() for frame in self.frames],
        }
