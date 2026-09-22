from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .contracts import ContractError


def _matrix_tuple(value) -> tuple[tuple[float, float, float, float], ...]:
    try:
        rows=tuple(tuple(float(v) for v in row) for row in value)
    except Exception as error:
        raise ContractError("world_matrix must be a numeric 4x4 matrix") from error
    if len(rows)!=4 or any(len(row)!=4 for row in rows):
        raise ContractError("world_matrix must be 4x4")
    if not all(isfinite(v) for row in rows for v in row):
        raise ContractError("world_matrix must be finite")
    if any(abs(rows[3][i]-expected)>1e-6 for i,expected in enumerate((0.0,0.0,0.0,1.0))):
        raise ContractError("world_matrix must be affine")
    return rows


@dataclass(frozen=True)
class CameraFrameRecord:
    global_frame_index: int
    path_name: str
    path_frame_index: int
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    world_matrix: tuple[tuple[float, float, float, float], ...]

    def __post_init__(self) -> None:
        if type(self.global_frame_index) is not int or self.global_frame_index < 0:
            raise ContractError("global_frame_index must be a nonnegative integer")
        if type(self.path_frame_index) is not int or self.path_frame_index < 0:
            raise ContractError("path_frame_index must be a nonnegative integer")
        if not str(self.path_name).strip():
            raise ContractError("path_name cannot be empty")
        if type(self.width) is not int or type(self.height) is not int or self.width<=0 or self.height<=0:
            raise ContractError("camera dimensions must be positive integers")
        for name,value in (("fx",self.fx),("fy",self.fy),("cx",self.cx),("cy",self.cy)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(float(value)):
                raise ContractError(f"{name} must be finite")
        if float(self.fx)<=0 or float(self.fy)<=0:
            raise ContractError("fx/fy must be positive")
        object.__setattr__(self,"world_matrix",_matrix_tuple(self.world_matrix))

    def to_dict(self) -> dict[str,object]:
        return {
            "global_frame_index": self.global_frame_index,
            "path_name": self.path_name,
            "path_frame_index": self.path_frame_index,
            "camera": {
                "model":"PINHOLE",
                "width":self.width,
                "height":self.height,
                "fx":float(self.fx),
                "fy":float(self.fy),
                "cx":float(self.cx),
                "cy":float(self.cy),
                "world_matrix":[list(row) for row in self.world_matrix],
            },
        }


@dataclass(frozen=True)
class CameraSequenceManifest:
    frames: tuple[CameraFrameRecord,...]
    scene_contract_id: str | None = None

    def __post_init__(self) -> None:
        if not self.frames:
            raise ContractError("Camera sequence requires at least one frame")
        expected=list(range(len(self.frames)))
        actual=[frame.global_frame_index for frame in self.frames]
        if actual!=expected:
            raise ContractError("Camera sequence global indexes must be contiguous from zero")

    def to_dict(self) -> dict[str,object]:
        return {
            "schema":"ConceptGhost.P10CameraSequence.v0.1",
            "scene_contract_id":self.scene_contract_id,
            "coordinate_authority":"P9_BASELINE_WORLD",
            "camera_model":"PINHOLE",
            "frame_count":len(self.frames),
            "frames":[frame.to_dict() for frame in self.frames],
        }
