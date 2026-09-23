from __future__ import annotations

import json
import math
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



def transform_camera_for_composite(
    camera: dict,
    *,
    target_width: int,
    target_height: int,
) -> tuple[dict, dict]:
    """Map a Gate 4 camera into the exact Gate 5 composite pixel viewport.

    Gate 5 uses ComfyUI common_upscale(..., crop="center") before saving
    the source-preserving WAN composite. COLMAP must therefore receive camera
    intrinsics expressed in that saved image coordinate system, not in the
    pre-WAN Gate 4 control viewport.

    The crop math intentionally mirrors ComfyUI's current common_upscale:
    symmetric integer center crop followed by interpolation. Principal-point
    mapping is pixel-center aware for PyTorch interpolate (align_corners=False).
    """

    if not isinstance(camera, dict) or camera.get("model") != "PINHOLE":
        raise ContractError("Composite camera transform requires a PINHOLE camera")

    source_width = camera.get("width")
    source_height = camera.get("height")
    if (
        type(source_width) is not int
        or type(source_height) is not int
        or source_width <= 0
        or source_height <= 0
    ):
        raise ContractError("Source camera dimensions must be positive integers")
    if (
        type(target_width) is not int
        or type(target_height) is not int
        or target_width <= 0
        or target_height <= 0
    ):
        raise ContractError("Target composite dimensions must be positive integers")

    try:
        fx = float(camera["fx"])
        fy = float(camera["fy"])
        cx = float(camera["cx"])
        cy = float(camera["cy"])
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError("Source camera intrinsics are incomplete") from error
    if not all(math.isfinite(v) for v in (fx, fy, cx, cy)) or fx <= 0.0 or fy <= 0.0:
        raise ContractError("Source camera intrinsics must be finite with positive fx/fy")

    old_aspect = source_width / float(source_height)
    new_aspect = target_width / float(target_height)
    crop_x = 0
    crop_y = 0
    if old_aspect > new_aspect:
        crop_x = round(
            (source_width - source_width * (new_aspect / old_aspect)) / 2.0
        )
    elif old_aspect < new_aspect:
        crop_y = round(
            (source_height - source_height * (old_aspect / new_aspect)) / 2.0
        )

    crop_width = source_width - 2 * crop_x
    crop_height = source_height - 2 * crop_y
    if crop_width <= 0 or crop_height <= 0:
        raise ContractError("Composite center crop collapsed the camera viewport")

    scale_x = target_width / float(crop_width)
    scale_y = target_height / float(crop_height)

    transformed = dict(camera)
    transformed.update({
        "width": target_width,
        "height": target_height,
        "fx": fx * scale_x,
        "fy": fy * scale_y,
        "cx": (cx - crop_x + 0.5) * scale_x - 0.5,
        "cy": (cy - crop_y + 0.5) * scale_y - 0.5,
    })
    transform = {
        "schema": "ConceptGhost.P10CompositeCameraTransform.v0.1",
        "policy": "COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
        "source_width": source_width,
        "source_height": source_height,
        "target_width": target_width,
        "target_height": target_height,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "crop_width": crop_width,
        "crop_height": crop_height,
        "scale_x": scale_x,
        "scale_y": scale_y,
    }
    return transformed, transform


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

    wan_scene_contract_id=str(wan.get("scene_contract_id") or "").strip()
    camera_scene_contract_id=str(cameras.get("scene_contract_id") or "").strip()
    wan_source_run_id=str(wan.get("source_run_id") or "").strip()
    camera_source_run_id=str(cameras.get("source_run_id") or "").strip()
    if wan_scene_contract_id != camera_scene_contract_id:
        raise ContractError(
            "Gate 6 scene contract mismatch between WAN and camera manifests"
        )
    if wan_source_run_id != camera_source_run_id:
        raise ContractError(
            "Gate 6 source run mismatch between WAN and camera manifests"
        )

    wan_route_hash=wan.get("route_plan_sha256")
    camera_route_hash=cameras.get("route_plan_sha256")
    wan_route_authority=wan.get("route_authority")
    camera_route_authority=cameras.get("route_authority")
    if wan_route_authority != camera_route_authority:
        raise ContractError(
            "Gate 6 route authority mismatch between WAN and camera manifests: "
            f"WAN={wan_route_authority!r}, camera={camera_route_authority!r}"
        )
    if wan_route_hash != camera_route_hash:
        raise ContractError(
            "Gate 6 route-plan identity mismatch between WAN and camera manifests"
        )

    wan_attempt_id=str(wan.get("p10_attempt_id") or "").strip()
    camera_attempt_id=str(cameras.get("p10_attempt_id") or "").strip()
    wan_attempt_root=str(wan.get("p10_attempt_root") or "").strip()
    camera_attempt_root=str(cameras.get("p10_attempt_root") or "").strip()
    if bool(wan_attempt_id) != bool(camera_attempt_id):
        raise ContractError("Gate 6 attempt identity is present on only one manifest")
    if wan_attempt_id and wan_attempt_id!=camera_attempt_id:
        raise ContractError("Gate 6 P10 attempt id mismatch between WAN and camera manifests")
    if bool(wan_attempt_root) != bool(camera_attempt_root):
        raise ContractError("Gate 6 attempt root is present on only one manifest")
    if wan_attempt_root and Path(wan_attempt_root).resolve()!=Path(camera_attempt_root).resolve():
        raise ContractError("Gate 6 P10 attempt root mismatch between WAN and camera manifests")

    wan_mission_order=wan.get("mission_order")
    camera_mission_order=cameras.get("mission_order")
    if not isinstance(wan_mission_order,list) or not wan_mission_order:
        raise ContractError("WAN manifest requires non-empty mission_order")
    if not isinstance(camera_mission_order,list) or not camera_mission_order:
        raise ContractError("Camera manifest requires non-empty mission_order")
    if wan_mission_order != camera_mission_order:
        raise ContractError(
            "Gate 6 mission order mismatch between WAN and camera manifests"
        )

    effective_dimensions = wan.get("effective_dimensions")
    if not isinstance(effective_dimensions, dict):
        raise ContractError(
            "WAN manifest requires effective_dimensions so Gate 6 can map "
            "camera intrinsics into the saved composite viewport"
        )
    target_width = effective_dimensions.get("width")
    target_height = effective_dimensions.get("height")
    if (
        type(target_width) is not int
        or type(target_height) is not int
        or target_width <= 0
        or target_height <= 0
    ):
        raise ContractError("WAN effective_dimensions width/height must be positive integers")

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
        mission_name=str(window.get("mission_name") or "").strip()
        if type(start) is not int or start<0:
            raise ContractError("WAN source_start must be a nonnegative integer")
        if type(decoded) is not int or decoded<1:
            raise ContractError("WAN decoded_frame_count must be a positive integer")
        if not name:
            raise ContractError("WAN window name cannot be empty")
        if not mission_name:
            raise ContractError("WAN window mission_name cannot be empty")

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
            if path_name and path_name!=mission_name:
                raise ContractError(
                    f"Mission mismatch for frame {global_index}: "
                    f"WAN={mission_name!r}, camera={path_name!r}"
                )

            composite_camera, camera_transform = transform_camera_for_composite(
                camera_record["camera"],
                target_width=target_width,
                target_height=target_height,
            )
            frames.append({
                "global_frame_index":global_index,
                "path_name":path_name or mission_name,
                "path_frame_index":camera_record.get("path_frame_index"),
                "image_path":str(image_path.resolve()),
                "image_provenance":"P10_WAN_SOURCE_PRESERVED_COMPOSITE",
                "camera_authority":"P9_PLANNED_WORLD_CAMERA",
                "camera":composite_camera,
                "source_camera":camera_record["camera"],
                "camera_image_transform":camera_transform,
            })

    frames.sort(key=lambda item:item["global_frame_index"])
    indexes=[item["global_frame_index"] for item in frames]
    if len(frames) != len(camera_frames):
        raise ContractError(
            "Gate 6 requires exact WAN/camera frame parity: "
            f"WAN composites={len(frames)}, camera frames={len(camera_frames)}"
        )
    observed_order=[]
    for item in frames:
        if item["path_name"] not in observed_order:
            observed_order.append(item["path_name"])
    if observed_order != wan_mission_order:
        raise ContractError(
            "Gate 6 reconstructed frame mission order does not match authored mission order"
        )
    if indexes!=list(range(len(frames))):
        raise ContractError(
            "Gate 6 first-pass reconstruction requires a contiguous generated frame sequence"
        )

    return {
        "schema":"ConceptGhost.P10ReconstructionInputs.v0.2",
        "run_id":wan.get("run_id"),
        "scene_contract_id":camera_scene_contract_id,
        "source_run_id":camera_source_run_id,
        "p10_attempt_id":wan_attempt_id or None,
        "p10_attempt_root":wan_attempt_root or None,
        "source_wan_manifest":str(wan_path.resolve()),
        "source_camera_manifest":str(camera_path.resolve()),
        "frame_count":len(frames),
        "image_authority":"SOURCE_PRESERVED_P10_COMPOSITE",
        "camera_authority":"P9_BASELINE_WORLD_DERIVED",
        "route_authority":wan_route_authority,
        "route_plan_sha256":wan_route_hash,
        "mission_order":wan_mission_order,
        "mission_modes":wan.get("mission_modes"),
        "camera_image_mapping_policy":"COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE",
        "composite_dimensions":{"width":target_width,"height":target_height},
        "frames":frames,
    }
