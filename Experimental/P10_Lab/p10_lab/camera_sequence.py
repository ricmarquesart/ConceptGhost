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
    route_authority: str = "UNSPECIFIED"
    route_plan_schema: str | None = None
    route_plan_sha256: str | None = None
    mission_modes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.frames:
            raise ContractError("Camera sequence requires at least one frame")
        expected=list(range(len(self.frames)))
        actual=[frame.global_frame_index for frame in self.frames]
        if actual!=expected:
            raise ContractError("Camera sequence global indexes must be contiguous from zero")
        if not str(self.route_authority).strip():
            raise ContractError("route_authority cannot be empty")
        seen=[]
        for frame in self.frames:
            if frame.path_name not in seen:
                seen.append(frame.path_name)
            elif seen[-1] != frame.path_name:
                raise ContractError("Camera sequence missions must be contiguous")
        mode_names=[name for name,_mode in self.mission_modes]
        if len(mode_names)!=len(set(mode_names)):
            raise ContractError("mission_modes contains duplicate mission names")
        if mode_names and mode_names!=seen:
            raise ContractError(
                "mission_modes order must match the contiguous camera-frame mission order"
            )

    def to_dict(self) -> dict[str,object]:
        mission_order=[]
        mission_counts={}
        for frame in self.frames:
            if frame.path_name not in mission_counts:
                mission_order.append(frame.path_name)
                mission_counts[frame.path_name]=0
            mission_counts[frame.path_name]+=1
        mode_lookup=dict(self.mission_modes)
        return {
            "schema":"ConceptGhost.P10CameraSequence.v0.2",
            "scene_contract_id":self.scene_contract_id,
            "coordinate_authority":"P9_BASELINE_WORLD",
            "camera_model":"PINHOLE",
            "frame_count":len(self.frames),
            "route_authority":self.route_authority,
            "route_plan_schema":self.route_plan_schema,
            "route_plan_sha256":self.route_plan_sha256,
            "mission_order":mission_order,
            "missions":[
                {
                    "name":name,
                    "mode":mode_lookup.get(name),
                    "frame_count":mission_counts[name],
                }
                for name in mission_order
            ],
            "frames":[frame.to_dict() for frame in self.frames],
        }
