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
    route_authority: str = "UNSPECIFIED"
    route_plan_schema: str | None = None
    route_plan_sha256: str | None = None
    route_plan_file: str | None = None
    scene_contract_id: str | None = None
    source_run_id: str | None = None
    source_p9_run_dir: str | None = None
    mission_modes: tuple[tuple[str, str], ...] = ()

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
        if not str(self.route_authority).strip():
            raise ContractError("route_authority cannot be empty")
        seen=[]
        for frame in self.frames:
            if frame.path_name not in seen:
                seen.append(frame.path_name)
            elif seen[-1] != frame.path_name:
                raise ContractError("Control sequence missions must be contiguous")
        mode_names=[name for name,_mode in self.mission_modes]
        if len(mode_names)!=len(set(mode_names)):
            raise ContractError("mission_modes contains duplicate mission names")
        if mode_names and mode_names!=seen:
            raise ContractError(
                "mission_modes order must match the contiguous control-frame mission order"
            )
        route_hash=str(self.route_plan_sha256 or "").strip().lower()
        if route_hash:
            if len(route_hash)!=64 or any(ch not in "0123456789abcdef" for ch in route_hash):
                raise ContractError("route_plan_sha256 must be a 64-character lowercase hex digest")
            if not str(self.route_plan_file or "").strip():
                raise ContractError("Hashed control sequence requires route_plan_file")
            if not str(self.scene_contract_id or "").strip():
                raise ContractError("Hashed control sequence requires scene_contract_id")
            if not str(self.source_run_id or "").strip():
                raise ContractError("Hashed control sequence requires source_run_id")
        elif self.route_plan_file is not None:
            raise ContractError("Unhashed control sequence must not advertise route_plan_file")

    def to_dict(self) -> dict[str, object]:
        mission_order=[]
        mission_counts={}
        for frame in self.frames:
            if frame.path_name not in mission_counts:
                mission_order.append(frame.path_name)
                mission_counts[frame.path_name]=0
            mission_counts[frame.path_name]+=1
        mode_lookup=dict(self.mission_modes)
        return {
            "schema": "ConceptGhost.P10ControlSequence.v0.2",
            "frame_count": len(self.frames),
            "width": self.width,
            "height": self.height,
            "route_authority": self.route_authority,
            "route_plan_schema": self.route_plan_schema,
            "route_plan_sha256": self.route_plan_sha256,
            "route_plan_file": self.route_plan_file,
            "scene_contract_id": self.scene_contract_id,
            "source_run_id": self.source_run_id,
            "source_p9_run_dir": self.source_p9_run_dir,
            "mission_order": mission_order,
            "missions": [
                {
                    "name": name,
                    "mode": mode_lookup.get(name),
                    "frame_count": mission_counts[name],
                }
                for name in mission_order
            ],
            "frames": [frame.to_dict() for frame in self.frames],
        }
