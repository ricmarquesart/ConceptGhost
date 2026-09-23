from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
import shutil

from .contracts import ContractError
from .drone_route_plan import parse_bound_route_plan
from .wan_conditioning import ConceptGhostP10WanMaskedConditioning
from .wan_policy import WanRuntimeProfile


@dataclass(frozen=True)
class MissionRange:
    name: str
    start: int
    end: int
    source_name: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ContractError("MissionRange name cannot be empty")
        if type(self.start) is not int or type(self.end) is not int:
            raise ContractError("MissionRange bounds must be integers")
        if self.start < 0 or self.end <= self.start:
            raise ContractError("MissionRange must have positive length")

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def mission_name(self) -> str:
        return self.source_name or self.name


@dataclass(frozen=True)
class WanDimensions:
    requested_width: int
    requested_height: int
    width: int
    height: int
    mode: str


def normalize_wan_dimensions(width: int, height: int) -> WanDimensions:
    """Make WAN dimensions safe instead of hard-failing on stale/corrupt widgets.

    The Gate 5/6 first-pass authority profile is 832x480. Very small/out-of-range
    dimensions are treated as a stale workflow/widget state and fall back to that
    known-safe profile. Otherwise values are snapped to the nearest multiple of 16.
    """
    if type(width) is not int or type(height) is not int:
        raise ContractError("WAN width/height must be integers")
    requested_width, requested_height = width, height
    if width < 256 or height < 256 or width > 2048 or height > 2048:
        return WanDimensions(
            requested_width=requested_width,
            requested_height=requested_height,
            width=832,
            height=480,
            mode="SAFE_PROFILE_FALLBACK",
        )

    def snap(value: int) -> int:
        return max(256, min(2048, int(round(value / 16.0)) * 16))

    effective_width = snap(width)
    effective_height = snap(height)
    mode = (
        "UNCHANGED"
        if effective_width == width and effective_height == height
        else "ALIGN_TO_16"
    )
    return WanDimensions(
        requested_width=requested_width,
        requested_height=requested_height,
        width=effective_width,
        height=effective_height,
        mode=mode,
    )


def mission_ranges_from_payload(payload: dict) -> tuple[MissionRange, ...]:
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ContractError("Control manifest must contain non-empty frames")

    expected_indexes = list(range(len(frames)))
    indexes = [frame.get("global_frame_index") for frame in frames]
    if indexes != expected_indexes:
        raise ContractError("Control manifest global frame indexes must be contiguous")

    ranges: list[MissionRange] = []
    seen = set()
    start = 0
    current = str(frames[0].get("path_name") or "").strip()
    if not current:
        raise ContractError("Control manifest path_name cannot be empty")

    for index in range(1, len(frames)):
        name = str(frames[index].get("path_name") or "").strip()
        if not name:
            raise ContractError("Control manifest path_name cannot be empty")
        if name != current:
            if current in seen:
                raise ContractError("A mission cannot appear in multiple noncontiguous ranges")
            seen.add(current)
            ranges.append(MissionRange(current, start, index, current))
            if name in seen:
                raise ContractError("A mission cannot appear in multiple noncontiguous ranges")
            current = name
            start = index

    if current in seen:
        raise ContractError("A mission cannot appear in multiple noncontiguous ranges")
    ranges.append(MissionRange(current, start, len(frames), current))
    return tuple(ranges)


def _sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_control_manifest(path: str | Path) -> tuple[Path, dict, tuple[MissionRange, ...]]:
    path=Path(path)
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read control sequence manifest {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError("Control sequence manifest must be a JSON object")
    ranges=mission_ranges_from_payload(payload)
    derived_order=[mission.mission_name for mission in ranges]
    declared_order=payload.get("mission_order")
    if declared_order is not None:
        if not isinstance(declared_order,list) or declared_order!=derived_order:
            raise ContractError(
                "Control manifest mission_order must exactly match frame mission order"
            )
    declared_missions=payload.get("missions")
    if declared_missions is not None:
        if not isinstance(declared_missions,list) or len(declared_missions)!=len(ranges):
            raise ContractError("Control manifest missions metadata is inconsistent")
        for declared,mission in zip(declared_missions,ranges):
            if not isinstance(declared,dict):
                raise ContractError("Control manifest mission metadata must be JSON objects")
            if str(declared.get("name") or "")!=mission.mission_name:
                raise ContractError("Control manifest mission metadata order/name mismatch")
            if declared.get("frame_count")!=mission.length:
                raise ContractError(
                    f"Control manifest frame count mismatch for {mission.mission_name}"
                )

    route_hash=str(payload.get("route_plan_sha256") or "").strip().lower()
    route_file=str(payload.get("route_plan_file") or "").strip()
    if route_hash:
        if not route_file:
            raise ContractError("Hashed control manifest is missing route_plan_file")
        route_path=(path.parent/route_file).resolve()
        if not route_path.is_file():
            raise ContractError(f"Persisted route plan is missing: {route_path}")
        try:
            route_payload=json.loads(route_path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as error:
            raise ContractError(f"Cannot read persisted route plan {route_path}: {error}") from error
        _plan,route_authority,verified_hash=parse_bound_route_plan(
            route_payload,
            expected_scene_contract_id=str(payload.get("scene_contract_id") or ""),
            expected_source_run_id=str(payload.get("source_run_id") or ""),
            require_hash=True,
        )
        if verified_hash!=route_hash:
            raise ContractError("Control manifest route hash does not match persisted route plan")
        if route_authority!=str(payload.get("route_authority") or "").strip().upper():
            raise ContractError("Control manifest route authority does not match persisted route plan")
    elif route_file:
        raise ContractError("Unhashed control manifest must not advertise route_plan_file")

    return path,payload,ranges


def validate_control_batch_contract(
    payload: dict,
    control_shape,
    mask_shape,
) -> None:
    """Fail closed if graph tensors no longer match the serialized Gate 4 manifest."""

    expected_count=payload.get("frame_count")
    width=payload.get("width")
    height=payload.get("height")
    if type(expected_count) is not int or expected_count<1:
        raise ContractError("Control manifest frame_count must be a positive integer")
    if type(width) is not int or type(height) is not int or width<=0 or height<=0:
        raise ContractError("Control manifest width/height must be positive integers")
    try:
        control=tuple(int(value) for value in control_shape)
        mask=tuple(int(value) for value in mask_shape)
    except Exception as error:
        raise ContractError("Control/mask tensors expose invalid shapes") from error
    if len(control)!=4:
        raise ContractError(f"control_video must have shape [N,H,W,C], got {control}")
    if len(mask)!=3:
        raise ContractError(f"hole_mask must have shape [N,H,W], got {mask}")
    if control[0]!=expected_count or mask[0]!=expected_count:
        raise ContractError(
            "Gate 5 requires exact authored frame-count parity: "
            f"manifest={expected_count}, control={control[0]}, mask={mask[0]}"
        )
    if control[1:3]!=(height,width) or mask[1:3]!=(height,width):
        raise ContractError(
            "Gate 5 control/mask dimensions no longer match the Gate 4 manifest: "
            f"manifest={width}x{height}, control={control[2]}x{control[1]}, "
            f"mask={mask[2]}x{mask[1]}"
        )


def mission_ranges_from_manifest(path: str | Path) -> tuple[MissionRange, ...]:
    _path,_payload,ranges=read_control_manifest(path)
    return ranges



def collect_mission_composite_frames(
    records: list[dict] | tuple[dict,...],
    missions: tuple[MissionRange,...],
) -> dict[str,tuple[Path,...]]:
    """Reassemble final-composite frames by authored mission.

    A single mission may be split into multiple WAN windows. The preview
    contract follows the original global frame indexes rather than window
    names, so one drone always yields exactly one ordered frame sequence.
    """

    expected={mission.mission_name:list(range(mission.start,mission.end)) for mission in missions}
    collected={mission.mission_name:{} for mission in missions}

    for record in records:
        if not isinstance(record,dict):
            raise ContractError("WAN window records must be JSON-like objects")
        mission_name=str(record.get("mission_name") or "").strip()
        if mission_name not in collected:
            raise ContractError(f"WAN preview record references unknown mission {mission_name!r}")
        start=record.get("source_start")
        end=record.get("source_end")
        count=record.get("decoded_frame_count")
        directory=Path(str(record.get("composite_dir") or ""))
        if type(start) is not int or type(end) is not int or type(count) is not int:
            raise ContractError("WAN preview record requires integer source range/count")
        if end<=start or count!=end-start:
            raise ContractError(
                f"WAN preview record length mismatch for {mission_name}: "
                f"range={start}:{end}, decoded={count}"
            )
        mission_expected=expected[mission_name]
        if start<mission_expected[0] or end-1>mission_expected[-1]:
            raise ContractError(
                f"WAN preview record escapes authored mission range for {mission_name}"
            )
        for local_index,global_index in enumerate(range(start,end)):
            frame_path=directory/f"frame_{local_index:04d}.png"
            if not frame_path.is_file():
                raise ContractError(f"Final composite frame is missing: {frame_path}")
            if global_index in collected[mission_name]:
                raise ContractError(
                    f"Duplicate final composite frame {global_index} for {mission_name}"
                )
            collected[mission_name][global_index]=frame_path

    result={}
    for mission in missions:
        name=mission.mission_name
        actual=sorted(collected[name])
        if actual!=expected[name]:
            raise ContractError(
                f"Final composite sequence for {name} does not match authored frame range: "
                f"expected={expected[name]}, actual={actual}"
            )
        result[name]=tuple(collected[name][index] for index in expected[name])
    return result


def _ordered_frame_set_sha256(paths: tuple[Path,...]) -> str:
    digest=hashlib.sha256()
    for index,path in enumerate(paths):
        digest.update(f"{index}\0{_sha256_file(path)}\n".encode("utf-8"))
    return digest.hexdigest()


def _safe_preview_name(name: str) -> str:
    safe=re.sub(r"[^A-Za-z0-9._-]+","_",str(name or "").strip()).strip("._-")
    return safe or "mission"


def write_per_drone_gif_previews(
    records: list[dict] | tuple[dict,...],
    missions: tuple[MissionRange,...],
    mission_modes: dict[str,object],
    preview_root: str | Path,
    Image,
    *,
    fps: int=10,
    max_width: int=640,
    route_plan_sha256: str | None=None,
    generation_context_sha256: str | None=None,
    source_control_manifest_sha256: str | None=None,
    run_id: str | None=None,
    scene_contract_id: str | None=None,
    source_run_id: str | None=None,
    output_directory: str | Path | None=None,
) -> dict[str,object]:
    """Write one lightweight looping GIF from final composite frames per drone."""

    if type(fps) is not int or not 1<=fps<=60:
        raise ContractError("GIF preview fps must be an integer in [1,60]")
    if type(max_width) is not int or not 128<=max_width<=2048:
        raise ContractError("GIF preview max_width must be an integer in [128,2048]")

    preview_root=Path(preview_root)
    if preview_root.exists():
        shutil.rmtree(preview_root)
    preview_root.mkdir(parents=True,exist_ok=True)

    grouped=collect_mission_composite_frames(records,missions)
    duration_ms=max(1,int(round(1000.0/fps)))
    entries=[]
    for mission_index,mission in enumerate(missions):
        name=mission.mission_name
        source_paths=grouped[name]
        frames=[]
        preview_width=None
        preview_height=None
        for source_path in source_paths:
            with Image.open(source_path) as source_image:
                frame=source_image.convert("RGB")
                if frame.width>max_width:
                    height=max(1,round(frame.height*max_width/float(frame.width)))
                    resampling=getattr(getattr(Image,"Resampling",Image),"LANCZOS",1)
                    frame=frame.resize((max_width,height),resampling)
                frame=frame.convert("P")
                if preview_width is None:
                    preview_width,preview_height=frame.size
                elif frame.size!=(preview_width,preview_height):
                    raise ContractError(
                        f"GIF preview frame dimensions changed within mission {name}: "
                        f"{frame.size} vs {(preview_width,preview_height)}"
                    )
                frames.append(frame.copy())

        if not frames:
            raise ContractError(f"No final composite frames available for GIF mission {name}")

        gif_name=f"drone_{mission_index+1:02d}_{_safe_preview_name(name)}_preview.gif"
        gif_path=preview_root/gif_name
        frames[0].save(
            gif_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=False,
            disposal=2,
        )
        gif_subfolder=None
        if output_directory is not None:
            try:
                gif_subfolder=str(
                    gif_path.parent.resolve().relative_to(Path(output_directory).resolve())
                ).replace("\\","/")
            except ValueError:
                gif_subfolder=None
        entries.append({
            "drone_index":mission_index+1,
            "mission_name":name,
            "mode":mission_modes.get(name),
            "frame_count":len(frames),
            "global_frame_start":mission.start,
            "global_frame_end_exclusive":mission.end,
            "fps":fps,
            "frame_duration_ms":duration_ms,
            "preview_width":preview_width,
            "preview_height":preview_height,
            "source_type":"GATE5_FINAL_COMPOSITE",
            "source_frame_set_sha256":_ordered_frame_set_sha256(source_paths),
            "gif_filename":gif_name,
            "gif_subfolder":gif_subfolder,
            "gif_path":str(gif_path.resolve()),
            "gif_sha256":_sha256_file(gif_path),
        })

    index_path=preview_root/"drone_preview_index.json"
    index_subfolder=None
    if output_directory is not None:
        try:
            index_subfolder=str(
                preview_root.resolve().relative_to(Path(output_directory).resolve())
            ).replace("\\","/")
        except ValueError:
            index_subfolder=None
    index={
        "schema":"ConceptGhost.P10DronePreviewIndex.v0.2",
        "status":"PASS",
        "run_id":run_id,
        "scene_contract_id":scene_contract_id,
        "source_run_id":source_run_id,
        "source_type":"GATE5_FINAL_COMPOSITE",
        "source_control_manifest_sha256":source_control_manifest_sha256,
        "route_plan_sha256":route_plan_sha256,
        "generation_context_sha256":generation_context_sha256,
        "mission_order":[mission.mission_name for mission in missions],
        "mission_modes":dict(mission_modes),
        "drone_count":len(entries),
        "fps":fps,
        "max_width":max_width,
        "loop":"INFINITE",
        "index_filename":index_path.name,
        "index_subfolder":index_subfolder,
        "index_path":str(index_path.resolve()),
        "previews":entries,
    }
    index_path.write_text(json.dumps(index,indent=2,sort_keys=True),encoding="utf-8")
    return index


def validate_drone_preview_index(
    index: dict[str,object],
    missions: tuple[MissionRange,...],
    mission_modes: dict[str,object],
    *,
    route_plan_sha256: str | None,
    generation_context_sha256: str | None,
    source_control_manifest_sha256: str | None,
) -> None:
    """Fail closed if the published preview index does not describe current GIF bytes."""

    if not isinstance(index,dict):
        raise ContractError("Drone preview index must be a JSON object")
    if index.get("schema")!="ConceptGhost.P10DronePreviewIndex.v0.2":
        raise ContractError("Unsupported drone preview index schema")
    expected_order=[mission.mission_name for mission in missions]
    if index.get("mission_order")!=expected_order:
        raise ContractError("Drone preview index mission_order mismatch")
    if index.get("drone_count")!=len(missions):
        raise ContractError("Drone preview index drone_count mismatch")
    if index.get("route_plan_sha256")!=route_plan_sha256:
        raise ContractError("Drone preview index route hash mismatch")
    if index.get("generation_context_sha256")!=generation_context_sha256:
        raise ContractError("Drone preview index generation-context mismatch")
    if index.get("source_control_manifest_sha256")!=source_control_manifest_sha256:
        raise ContractError("Drone preview index control-manifest mismatch")

    previews=index.get("previews")
    if not isinstance(previews,list) or len(previews)!=len(missions):
        raise ContractError("Drone preview index previews list is inconsistent")

    for preview,mission in zip(previews,missions):
        if not isinstance(preview,dict):
            raise ContractError("Drone preview entries must be JSON objects")
        name=mission.mission_name
        if preview.get("mission_name")!=name:
            raise ContractError("Drone preview mission order/name mismatch")
        if preview.get("mode")!=mission_modes.get(name):
            raise ContractError(f"Drone preview mode mismatch for {name}")
        if preview.get("frame_count")!=mission.length:
            raise ContractError(f"Drone preview frame count mismatch for {name}")
        if preview.get("global_frame_start")!=mission.start:
            raise ContractError(f"Drone preview start index mismatch for {name}")
        if preview.get("global_frame_end_exclusive")!=mission.end:
            raise ContractError(f"Drone preview end index mismatch for {name}")
        gif_path=Path(str(preview.get("gif_path") or ""))
        if not gif_path.is_file():
            raise ContractError(f"Drone preview GIF is missing: {gif_path}")
        expected_hash=str(preview.get("gif_sha256") or "").strip().lower()
        if len(expected_hash)!=64 or _sha256_file(gif_path)!=expected_hash:
            raise ContractError(f"Drone preview GIF hash mismatch for {name}")
        if not str(preview.get("gif_filename") or "").strip():
            raise ContractError(f"Drone preview filename missing for {name}")

    index_path=Path(str(index.get("index_path") or ""))
    if not index_path.is_file():
        raise ContractError(f"Drone preview index file is missing: {index_path}")


def padded_wan_length(length: int) -> int:
    if type(length) is not int or length < 1:
        raise ContractError("WAN window length must be a positive integer")
    if length == 1:
        return 1
    remainder = (length - 1) % 4
    return length if remainder == 0 else length + (4 - remainder)


def normalize_decoded_wan_images(images):
    """Normalize ComfyUI video VAE output to IMAGE batch shape [N, H, W, C].

    ComfyUI's standard VAEDecode node flattens a five-dimensional decoded video
    tensor before exposing it as IMAGE. The P10 sequential sampler decodes the
    VAE directly, so it must apply the same normalization before compositing or
    saving frames with Pillow.
    """
    shape = getattr(images, "shape", None)
    if shape is None:
        raise ContractError("WAN VAE decode returned a value without shape")

    try:
        rank = len(shape)
    except TypeError as error:
        raise ContractError("WAN VAE decode returned an invalid shape") from error

    if rank == 5:
        images = images.reshape(
            -1,
            images.shape[-3],
            images.shape[-2],
            images.shape[-1],
        )
        shape = images.shape
        rank = len(shape)

    if rank != 4:
        raise ContractError(
            f"WAN VAE decode must normalize to [N,H,W,C], got shape {tuple(shape)}"
        )

    channels = int(shape[-1])
    if channels not in (1, 3, 4):
        raise ContractError(
            f"WAN VAE decode produced unsupported channel count {channels} "
            f"for shape {tuple(shape)}"
        )

    return images


def _window_ranges(mission: MissionRange, max_length: int) -> tuple[MissionRange, ...]:
    if type(max_length) is not int or max_length < 1:
        raise ContractError("WAN max_length must be a positive integer")
    windows = []
    cursor = mission.start
    part = 0
    while cursor < mission.end:
        end = min(mission.end, cursor + max_length)
        name = mission.name if part == 0 and end == mission.end else f"{mission.name}__part{part:02d}"
        windows.append(MissionRange(name, cursor, end, mission.mission_name))
        cursor = end
        part += 1
    return tuple(windows)


class ConceptGhostP10WanSequentialSampler:
    """Run masked WAN windows sequentially and composite known P9 pixels back in.

    This node deliberately processes only one mission/window at a time for the
    11 GB hardware target. Full generated frames are written to disk; only a
    small proxy selection is returned to the graph for visual inspection.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE",),
                "control_video": ("IMAGE",),
                "hole_mask": ("MASK",),
                "control_manifest_path": ("STRING", {"forceInput": True}),
                "wan_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "width": ("INT", {"default": 832, "min": 256, "max": 2048, "step": 16}),
                "height": ("INT", {"default": 480, "min": 256, "max": 2048, "step": 16}),
                "max_window_length": ("INT", {"default": 33, "min": 1, "max": 129, "step": 4}),
                "steps": ("INT", {"default": 4, "min": 1, "max": 20}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
            },
            "optional": {
                "clip_vision_output": ("CLIP_VISION_OUTPUT",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "composite_preview",
        "generated_dir",
        "wan_manifest_path",
        "diagnostics_json",
        "drone_preview_index_path",
    )
    FUNCTION = "sample"
    CATEGORY = "ConceptGhost/P10 Refined"
    OUTPUT_NODE = True

    def sample(
        self,
        model,
        positive,
        negative,
        vae,
        control_video,
        hole_mask,
        control_manifest_path,
        wan_seed,
        width,
        height,
        max_window_length,
        steps,
        cfg,
        clip_vision_output=None,
    ):
        dimensions = normalize_wan_dimensions(int(width), int(height))
        effective_width = dimensions.width
        effective_height = dimensions.height
        if dimensions.mode != "UNCHANGED":
            print(
                "[ConceptGhost P10 WAN] normalized dimensions "
                f"{dimensions.requested_width}x{dimensions.requested_height} -> "
                f"{effective_width}x{effective_height} ({dimensions.mode})",
                flush=True,
            )

        try:
            import torch
            import comfy.utils
            import comfy.model_management
            import folder_paths
            from PIL import Image
            from nodes import common_ksampler
        except ImportError as error:
            raise ContractError(
                "Sequential WAN sampling requires the active ComfyUI runtime"
            ) from error

        manifest_path, control_payload, missions = read_control_manifest(
            control_manifest_path
        )
        validate_control_batch_contract(
            control_payload,
            getattr(control_video,"shape",()),
            getattr(hole_mask,"shape",()),
        )
        windows = tuple(
            window
            for mission in missions
            for window in _window_ranges(mission, int(max_window_length))
        )
        if not windows:
            raise ContractError("No WAN windows were produced")

        run_id = manifest_path.parent.parent.name or "unknown_run"
        output_root = (
            Path(folder_paths.get_output_directory())
            / "conceptghost"
            / "p10_gate5"
            / run_id
        )
        output_root.mkdir(parents=True, exist_ok=True)
        raw_root = output_root / "wan_raw"
        composite_root = output_root / "composite"
        preview_root = output_root / "drone_previews"
        previous_manifest_path=output_root/"wan_manifest.json"
        previous_manifest=None
        if previous_manifest_path.is_file():
            try:
                candidate=json.loads(previous_manifest_path.read_text(encoding="utf-8"))
                if isinstance(candidate,dict):
                    previous_manifest=candidate
            except (OSError,json.JSONDecodeError):
                previous_manifest=None

        source_control_sha256=_sha256_file(manifest_path)
        generation_context_payload={
            "source_control_manifest_sha256":source_control_sha256,
            "route_plan_sha256":control_payload.get("route_plan_sha256"),
            "wan_seed":int(wan_seed),
            "requested_width":int(width),
            "requested_height":int(height),
            "effective_width":effective_width,
            "effective_height":effective_height,
            "max_window_length":int(max_window_length),
            "steps":int(steps),
            "cfg":float(cfg),
        }
        generation_context_sha256=hashlib.sha256(
            json.dumps(
                generation_context_payload,
                sort_keys=True,
                separators=(",",":"),
            ).encode("utf-8")
        ).hexdigest()

        if previous_manifest is None:
            invalidation_reason="NO_PREVIOUS_WAN_OUTPUT"
        elif previous_manifest.get("route_plan_sha256")!=control_payload.get("route_plan_sha256"):
            invalidation_reason="ROUTE_PLAN_CHANGED"
        elif previous_manifest.get("source_control_manifest_sha256")!=source_control_sha256:
            invalidation_reason="CONTROL_MANIFEST_CHANGED"
        elif previous_manifest.get("generation_context_sha256")!=generation_context_sha256:
            invalidation_reason="WAN_SETTINGS_CHANGED"
        else:
            invalidation_reason="SAME_CONTEXT_EXPLICIT_REGENERATION"

        # Gate 5 currently regenerates rather than resuming model inference.
        # Remove only ConceptGhost-owned derived windows so shorter/new routes
        # can never leave stale images that a later stage could discover.
        for owned in (raw_root,composite_root,preview_root):
            if owned.exists():
                shutil.rmtree(owned)
            owned.mkdir(parents=True,exist_ok=True)
        if previous_manifest_path.exists():
            previous_manifest_path.unlink()

        conditioner = ConceptGhostP10WanMaskedConditioning()
        records = []
        preview_frames = []

        for window_index, window in enumerate(windows):
            control_slice = control_video[window.start:window.end]
            mask_slice = hole_mask[window.start:window.end]
            actual_length = int(control_slice.shape[0])
            if actual_length <= 0:
                raise ContractError(f"WAN window {window.name} is empty")

            conditioning_length = padded_wan_length(actual_length)
            if conditioning_length > int(max_window_length):
                raise ContractError(
                    f"WAN padded length {conditioning_length} exceeds max_window_length "
                    f"{max_window_length} for {window.name}"
                )
            if conditioning_length > actual_length:
                pad_count = conditioning_length - actual_length
                control_pad = control_slice[-1:].repeat((pad_count, 1, 1, 1))
                mask_pad = mask_slice[-1:].repeat((pad_count, 1, 1))
                control_condition = torch.cat((control_slice, control_pad), dim=0)
                mask_condition = torch.cat((mask_slice, mask_pad), dim=0)
            else:
                control_condition = control_slice
                mask_condition = mask_slice

            conditioned_positive, conditioned_negative, latent = conditioner.encode(
                positive,
                negative,
                vae,
                control_condition,
                mask_condition,
                effective_width,
                effective_height,
                conditioning_length,
                clip_vision_output=clip_vision_output,
                hole_fill="black",
            )

            sampled = common_ksampler(
                model,
                int(wan_seed) + window_index,
                int(steps),
                float(cfg),
                "euler",
                "normal",
                conditioned_positive,
                conditioned_negative,
                latent,
                denoise=1.0,
            )[0]
            generated = normalize_decoded_wan_images(
                vae.decode(sampled["samples"])
            )

            control_resized = comfy.utils.common_upscale(
                control_slice.movedim(-1, 1),
                effective_width,
                effective_height,
                "bilinear",
                "center",
            ).movedim(1, -1)
            mask_resized = comfy.utils.common_upscale(
                mask_slice.unsqueeze(1).float(),
                effective_width,
                effective_height,
                "bilinear",
                "center",
            ).squeeze(1)
            mask_resized = (mask_resized > 0.5).float()

            frame_count = min(
                actual_length,
                int(generated.shape[0]),
                int(control_resized.shape[0]),
                int(mask_resized.shape[0]),
            )
            if frame_count != actual_length:
                raise ContractError(
                    f"WAN window {window.name} lost authored frames: "
                    f"requested={actual_length}, decoded={int(generated.shape[0])}, "
                    f"control={int(control_resized.shape[0])}, mask={int(mask_resized.shape[0])}"
                )
            generated = generated[:frame_count].clamp(0.0, 1.0)
            control_resized = control_resized[:frame_count].clamp(0.0, 1.0)
            mask_resized = mask_resized[:frame_count]

            composite = torch.where(
                mask_resized.unsqueeze(-1) > 0.5,
                generated,
                control_resized,
            ).clamp(0.0, 1.0)

            window_raw_dir = raw_root / f"{window_index:02d}_{window.name}"
            window_comp_dir = composite_root / f"{window_index:02d}_{window.name}"
            window_raw_dir.mkdir(parents=True, exist_ok=True)
            window_comp_dir.mkdir(parents=True, exist_ok=True)

            for local_index in range(frame_count):
                raw_array = (
                    generated[local_index]
                    .detach()
                    .cpu()
                    .numpy()
                    * 255.0
                ).round().astype("uint8")
                comp_array = (
                    composite[local_index]
                    .detach()
                    .cpu()
                    .numpy()
                    * 255.0
                ).round().astype("uint8")
                Image.fromarray(raw_array).save(
                    window_raw_dir / f"frame_{local_index:04d}.png"
                )
                Image.fromarray(comp_array).save(
                    window_comp_dir / f"frame_{local_index:04d}.png"
                )

            preview_indexes = sorted(
                set([0, frame_count // 2, max(0, frame_count - 1)])
            )
            for preview_index in preview_indexes:
                preview = composite[preview_index:preview_index + 1]
                preview_small = comfy.utils.common_upscale(
                    preview.movedim(-1, 1),
                    min(480, effective_width),
                    max(16, round(min(480, effective_width) * effective_height / effective_width)),
                    "bilinear",
                    "center",
                ).movedim(1, -1)
                preview_frames.append(preview_small.detach().cpu())

            records.append(
                {
                    "window_index": window_index,
                    "name": window.name,
                    "mission_name": window.mission_name,
                    "source_start": window.start,
                    "source_end": window.end,
                    "requested_length": actual_length,
                    "conditioning_length": conditioning_length,
                    "decoded_frame_count": frame_count,
                    "raw_dir": str(window_raw_dir),
                    "composite_dir": str(window_comp_dir),
                    "seed": int(wan_seed) + window_index,
                }
            )

            del latent, sampled, generated, control_resized, mask_resized, composite
            try:
                comfy.model_management.unload_all_models()
            except Exception:
                pass
            try:
                comfy.model_management.soft_empty_cache()
            except Exception:
                pass
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        mission_modes={
            str(item.get("name")):item.get("mode")
            for item in control_payload.get("missions",[])
            if isinstance(item,dict) and str(item.get("name") or "").strip()
        }
        mission_order=[mission.mission_name for mission in missions]
        drone_preview_index=write_per_drone_gif_previews(
            records,
            missions,
            mission_modes,
            preview_root,
            Image,
            fps=10,
            max_width=640,
            route_plan_sha256=control_payload.get("route_plan_sha256"),
            generation_context_sha256=generation_context_sha256,
            source_control_manifest_sha256=source_control_sha256,
            run_id=run_id,
            scene_contract_id=control_payload.get("scene_contract_id"),
            source_run_id=control_payload.get("source_run_id"),
            output_directory=folder_paths.get_output_directory(),
        )
        validate_drone_preview_index(
            drone_preview_index,
            missions,
            mission_modes,
            route_plan_sha256=control_payload.get("route_plan_sha256"),
            generation_context_sha256=generation_context_sha256,
            source_control_manifest_sha256=source_control_sha256,
        )
        drone_preview_index_sha256=_sha256_file(
            Path(drone_preview_index["index_path"])
        )
        wan_manifest = {
            "schema": "ConceptGhost.P10WanSequential.v0.2",
            "run_id": run_id,
            "source_control_manifest": str(manifest_path.resolve()),
            "source_control_manifest_sha256": source_control_sha256,
            "generation_context_sha256": generation_context_sha256,
            "previous_output_invalidation_reason": invalidation_reason,
            "scene_contract_id": control_payload.get("scene_contract_id"),
            "source_run_id": control_payload.get("source_run_id"),
            "route_authority": control_payload.get("route_authority"),
            "route_plan_schema": control_payload.get("route_plan_schema"),
            "route_plan_sha256": control_payload.get("route_plan_sha256"),
            "mission_order": mission_order,
            "mission_modes": mission_modes,
            "missions": [
                {
                    "name": mission.mission_name,
                    "mode": mission_modes.get(mission.mission_name),
                    "source_start": mission.start,
                    "source_end": mission.end,
                    "frame_count": mission.length,
                }
                for mission in missions
            ],
            "drone_previews": drone_preview_index,
            "drone_preview_index_path": drone_preview_index["index_path"],
            "drone_preview_index_sha256": drone_preview_index_sha256,
            "policy": WanRuntimeProfile(
                width=effective_width,
                height=effective_height,
                length=int(max_window_length),
                steps=int(steps),
                cfg=float(cfg),
                max_parallel_windows=1,
                offload_between_windows=True,
                use_fp8_unet=True,
            ).manifest(),
            "mission_count": len(missions),
            "window_count": len(windows),
            "requested_dimensions": {
                "width": dimensions.requested_width,
                "height": dimensions.requested_height,
            },
            "effective_dimensions": {
                "width": effective_width,
                "height": effective_height,
                "mode": dimensions.mode,
            },
            "windows": records,
            "known_pixel_policy": "CONTROL_VIDEO_PRESERVED_WHERE_HOLE_MASK_IS_BLACK",
            "generated_pixel_policy": "WAN_USED_ONLY_WHERE_HOLE_MASK_IS_WHITE",
        }
        wan_manifest_path = output_root / "wan_manifest.json"
        wan_manifest_path.write_text(
            json.dumps(wan_manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        if preview_frames:
            preview_batch = torch.cat(preview_frames, dim=0)
        else:
            preview_batch = torch.zeros((1, 16, 16, 3), dtype=torch.float32)

        diagnostics = {
            "status": "PASS",
            "gate": 5,
            "subgates": ["5.2", "5.3", "5.4"],
            "run_id": run_id,
            "mission_count": len(missions),
            "mission_order": mission_order,
            "mission_modes": mission_modes,
            "scene_contract_id": control_payload.get("scene_contract_id"),
            "source_run_id": control_payload.get("source_run_id"),
            "route_authority": control_payload.get("route_authority"),
            "route_plan_sha256": control_payload.get("route_plan_sha256"),
            "generation_context_sha256": generation_context_sha256,
            "previous_output_invalidation_reason": invalidation_reason,
            "window_count": len(windows),
            "requested_dimensions": {
                "width": dimensions.requested_width,
                "height": dimensions.requested_height,
            },
            "effective_dimensions": {
                "width": effective_width,
                "height": effective_height,
                "mode": dimensions.mode,
            },
            "generated_dir": str(output_root),
            "wan_manifest_path": str(wan_manifest_path),
            "drone_preview_index_path": drone_preview_index["index_path"],
            "drone_preview_index_sha256": drone_preview_index_sha256,
            "drone_preview_count": drone_preview_index["drone_count"],
            "drone_previews": drone_preview_index["previews"],
            "known_pixels_replaced_by_wan": False,
            "sequential_only": True,
        }
        gif_ui=[
            {
                "filename":preview["gif_filename"],
                "subfolder":preview.get("gif_subfolder") or "",
                "type":"output",
            }
            for preview in drone_preview_index["previews"]
        ]
        return {
            "ui": {
                "images": gif_ui,
                "text": [json.dumps(diagnostics, indent=2, sort_keys=True)],
            },
            "result": (
                preview_batch,
                str(output_root),
                str(wan_manifest_path),
                json.dumps(diagnostics, indent=2, sort_keys=True),
                str(drone_preview_index["index_path"]),
            ),
        }
