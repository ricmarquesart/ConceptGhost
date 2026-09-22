from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError


def _read_json(path: str | Path, label: str) -> tuple[Path, dict]:
    path=Path(path)
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must contain a JSON object")
    return path,payload


def build_reconstruction_input_manifest(
    wan_manifest_path: str | Path,
    camera_manifest_path: str | Path,
) -> dict[str,object]:
    """Pair each Gate 5 source-preserved composite frame with its P10 camera.

    Gate 6 never guesses pose from filenames. Global frame index is the join key
    between the WAN/composite manifest and the authoritative P9-world camera
    sequence captured during Gate 4/5 execution.
    """
    wan_path,wan=_read_json(wan_manifest_path,"WAN manifest")
    camera_path,cameras=_read_json(camera_manifest_path,"camera manifest")

    windows=wan.get("windows")
    camera_frames=cameras.get("frames")
    if not isinstance(windows,list) or not windows:
        raise ContractError("WAN manifest requires non-empty windows")
    if not isinstance(camera_frames,list) or not camera_frames:
        raise ContractError("Camera manifest requires non-empty frames")

    camera_by_index={}
    for record in camera_frames:
        if not isinstance(record,dict):
            raise ContractError("Camera frame records must be JSON objects")
        index=record.get("global_frame_index")
        if type(index) is not int or index<0:
            raise ContractError("Camera global_frame_index must be a nonnegative integer")
        if index in camera_by_index:
            raise ContractError(f"Duplicate camera global frame index: {index}")
        camera=record.get("camera")
        if not isinstance(camera,dict) or camera.get("model")!="PINHOLE":
            raise ContractError(f"Camera frame {index} must contain a PINHOLE camera")
        camera_by_index[index]=record

    frames=[]
    seen=set()
    for window in windows:
        if not isinstance(window,dict):
            raise ContractError("WAN window records must be JSON objects")
        start=window.get("source_start")
        decoded=window.get("decoded_frame_count")
        composite_dir=Path(str(window.get("composite_dir") or ""))
        name=str(window.get("name") or "").strip()
        if type(start) is not int or start<0:
            raise ContractError("WAN source_start must be a nonnegative integer")
        if type(decoded) is not int or decoded<1:
            raise ContractError("WAN decoded_frame_count must be a positive integer")
        if not name:
            raise ContractError("WAN window name cannot be empty")

        for local_index in range(decoded):
            global_index=start+local_index
            if global_index in seen:
                raise ContractError(f"Duplicate generated global frame index: {global_index}")
            seen.add(global_index)
            camera_record=camera_by_index.get(global_index)
            if camera_record is None:
                raise ContractError(f"Missing camera for generated frame {global_index}")

            image_path=composite_dir/f"frame_{local_index:04d}.png"
            if not image_path.is_file():
                raise ContractError(f"Missing source-preserved composite frame: {image_path}")

            path_name=str(camera_record.get("path_name") or "").strip()
            base_window_name=name.split("__part",1)[0]
            if path_name and path_name!=base_window_name:
                raise ContractError(
                    f"Mission mismatch for frame {global_index}: "
                    f"WAN={base_window_name!r}, camera={path_name!r}"
                )

            frames.append({
                "global_frame_index":global_index,
                "path_name":path_name or base_window_name,
                "path_frame_index":camera_record.get("path_frame_index"),
                "image_path":str(image_path.resolve()),
                "image_provenance":"P10_WAN_SOURCE_PRESERVED_COMPOSITE",
                "camera_authority":"P9_PLANNED_WORLD_CAMERA",
                "camera":camera_record["camera"],
            })

    frames.sort(key=lambda item:item["global_frame_index"])
    indexes=[item["global_frame_index"] for item in frames]
    if indexes!=list(range(len(frames))):
        raise ContractError(
            "Gate 6 first-pass reconstruction requires a contiguous generated frame sequence"
        )

    return {
        "schema":"ConceptGhost.P10ReconstructionInputs.v0.1",
        "run_id":wan.get("run_id"),
        "scene_contract_id":cameras.get("scene_contract_id"),
        "source_wan_manifest":str(wan_path.resolve()),
        "source_camera_manifest":str(camera_path.resolve()),
        "frame_count":len(frames),
        "image_authority":"SOURCE_PRESERVED_P10_COMPOSITE",
        "camera_authority":"P9_BASELINE_WORLD_DERIVED",
        "frames":frames,
    }
