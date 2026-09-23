from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .contracts import ContractError
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
    return path,payload,mission_ranges_from_payload(payload)


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

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "composite_preview",
        "generated_dir",
        "wan_manifest_path",
        "diagnostics_json",
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
        raw_root = output_root / "wan_raw"
        composite_root = output_root / "composite"
        raw_root.mkdir(parents=True, exist_ok=True)
        composite_root.mkdir(parents=True, exist_ok=True)

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
        wan_manifest = {
            "schema": "ConceptGhost.P10WanSequential.v0.2",
            "run_id": run_id,
            "source_control_manifest": str(manifest_path.resolve()),
            "source_control_manifest_sha256": _sha256_file(manifest_path),
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
            "route_authority": control_payload.get("route_authority"),
            "route_plan_sha256": control_payload.get("route_plan_sha256"),
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
            "known_pixels_replaced_by_wan": False,
            "sequential_only": True,
        }
        return {
            "ui": {"text": [json.dumps(diagnostics, indent=2, sort_keys=True)]},
            "result": (
                preview_batch,
                str(output_root),
                str(wan_manifest_path),
                json.dumps(diagnostics, indent=2, sort_keys=True),
            ),
        }
