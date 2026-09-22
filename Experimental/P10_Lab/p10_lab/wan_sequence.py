from __future__ import annotations

from dataclasses import dataclass
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
            ranges.append(MissionRange(current, start, index))
            if name in seen:
                raise ContractError("A mission cannot appear in multiple noncontiguous ranges")
            current = name
            start = index

    if current in seen:
        raise ContractError("A mission cannot appear in multiple noncontiguous ranges")
    ranges.append(MissionRange(current, start, len(frames)))
    return tuple(ranges)


def mission_ranges_from_manifest(path: str | Path) -> tuple[MissionRange, ...]:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read control sequence manifest {path}: {error}") from error
    return mission_ranges_from_payload(payload)



def padded_wan_length(length: int) -> int:
    if type(length) is not int or length < 1:
        raise ContractError("WAN window length must be a positive integer")
    if length == 1:
        return 1
    remainder = (length - 1) % 4
    return length if remainder == 0 else length + (4 - remainder)


def _window_ranges(mission: MissionRange, max_length: int) -> tuple[MissionRange, ...]:
    if type(max_length) is not int or max_length < 1:
        raise ContractError("WAN max_length must be a positive integer")
    windows = []
    cursor = mission.start
    part = 0
    while cursor < mission.end:
        end = min(mission.end, cursor + max_length)
        name = mission.name if part == 0 and end == mission.end else f"{mission.name}__part{part:02d}"
        windows.append(MissionRange(name, cursor, end))
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
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "width": ("INT", {"default": 832, "min": 16, "max": 2048, "step": 16}),
                "height": ("INT", {"default": 480, "min": 16, "max": 2048, "step": 16}),
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
        seed,
        width,
        height,
        max_window_length,
        steps,
        cfg,
        clip_vision_output=None,
    ):
        if width % 16 or height % 16:
            raise ContractError("WAN width/height must be multiples of 16")

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

        manifest_path = Path(control_manifest_path)
        missions = mission_ranges_from_manifest(manifest_path)
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
                int(width),
                int(height),
                conditioning_length,
                clip_vision_output=clip_vision_output,
                hole_fill="black",
            )

            sampled = common_ksampler(
                model,
                int(seed) + window_index,
                int(steps),
                float(cfg),
                "euler",
                "normal",
                conditioned_positive,
                conditioned_negative,
                latent,
                denoise=1.0,
            )[0]
            generated = vae.decode(sampled["samples"])

            control_resized = comfy.utils.common_upscale(
                control_slice.movedim(-1, 1),
                int(width),
                int(height),
                "bilinear",
                "center",
            ).movedim(1, -1)
            mask_resized = comfy.utils.common_upscale(
                mask_slice.unsqueeze(1).float(),
                int(width),
                int(height),
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
                    min(480, int(width)),
                    max(16, round(min(480, int(width)) * int(height) / int(width))),
                    "bilinear",
                    "center",
                ).movedim(1, -1)
                preview_frames.append(preview_small.detach().cpu())

            records.append(
                {
                    "window_index": window_index,
                    "name": window.name,
                    "source_start": window.start,
                    "source_end": window.end,
                    "requested_length": actual_length,
                    "conditioning_length": conditioning_length,
                    "decoded_frame_count": frame_count,
                    "raw_dir": str(window_raw_dir),
                    "composite_dir": str(window_comp_dir),
                    "seed": int(seed) + window_index,
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

        wan_manifest = {
            "schema": "ConceptGhost.P10WanSequential.v0.1",
            "run_id": run_id,
            "policy": WanRuntimeProfile(
                width=int(width),
                height=int(height),
                length=int(max_window_length),
                steps=int(steps),
                cfg=float(cfg),
                max_parallel_windows=1,
                offload_between_windows=True,
                use_fp8_unet=True,
            ).manifest(),
            "mission_count": len(missions),
            "window_count": len(windows),
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
            "window_count": len(windows),
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
