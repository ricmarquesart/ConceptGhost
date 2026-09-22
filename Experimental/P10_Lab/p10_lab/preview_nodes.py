from __future__ import annotations

import json
from pathlib import Path

from .completion_envelope import (
    build_completion_envelope,
    build_generation_candidate_map,
)
from .observation_map import build_observation_map
from .p9_boundary import build_completion_bundle, load_completion_bundle
from .panorama import CameraAuthority, PanoramaSpec
from .panorama_projection import build_projection_plan


_CATEGORY = "ConceptGhost/P10 Lab"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


class ConceptGhostP10CompletionBundleBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_dir": ("STRING", {"default": ""}),
                "output_zip": ("STRING", {"default": "ConceptGhost_P9_CompletionBundle.zip"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("completion_bundle", "diagnostics_json")
    FUNCTION = "build"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def build(self, run_dir: str, output_zip: str):
        result = build_completion_bundle(run_dir, output_zip)
        diagnostics = {
            "status": "PASS",
            "gate": 2,
            "source_stage": result.source_stage,
            "source_run_id": result.source_run_id,
            "scene_contract_id": result.scene_contract_id,
            "bundle_path": str(result.zip_path),
            "bundle_sha256": result.bundle_sha256,
        }
        rendered = _pretty(diagnostics)
        return {"ui": {"text": [rendered]}, "result": (str(result.zip_path), rendered)}


class ConceptGhostP10BundleLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bundle_path": ("STRING", {"default": ""}),
                "cache_root": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "bundle_root",
        "source_image",
        "camera_json",
        "primary_mesh",
        "diagnostics_json",
    )
    FUNCTION = "load"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def load(self, bundle_path: str, cache_root: str):
        cache = Path(cache_root).expanduser() if str(cache_root).strip() else None
        bundle = load_completion_bundle(bundle_path, extract_root=cache)
        diagnostics = {
            "status": "PASS",
            "gate": 2,
            "source_stage": bundle.source_stage,
            "source_equivalent_to": bundle.source_equivalent_to,
            "source_run_id": bundle.source_run_id,
            "scene_contract_id": bundle.scene_contract_id,
            "source_branch_mode": bundle.source_branch_mode,
            "source_manifest_schema": bundle.source_manifest_schema,
            "identity_status": "PASS",
            "primary_mesh_format": bundle.primary_mesh.suffix.lower(),
            "optional_inputs": sorted(bundle.optional),
        }
        rendered = _pretty(diagnostics)
        return {
            "ui": {"text": [rendered]},
            "result": (
                str(bundle.root),
                str(bundle.source_image),
                str(bundle.camera),
                str(bundle.primary_mesh),
                rendered,
            ),
        }


class ConceptGhostP10PanoramaPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bundle_path": ("STRING", {"default": ""}),
                "panorama_width": (
                    "INT",
                    {"default": 2048, "min": 512, "max": 8192, "step": 2},
                ),
                "cache_root": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "MASK", "STRING")
    RETURN_NAMES = (
        "temporary_panorama",
        "source_lock_mask",
        "generation_candidate_mask",
        "diagnostics_json",
    )
    FUNCTION = "preview"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    @staticmethod
    def _panorama_height(width: int) -> int:
        if type(width) is not int:
            raise ValueError("panorama_width must be an integer")
        if width < 512 or width > 8192 or width % 2 != 0:
            raise ValueError("panorama_width must be an even integer from 512 to 8192")
        return width // 2

    def preview(self, bundle_path: str, panorama_width: int, cache_root: str):
        from .panorama_runtime import (
            derive_scene_scale_from_primary_mesh,
            render_temporary_panorama,
            save_comfyui_preview_images,
        )

        panorama_height = self._panorama_height(panorama_width)
        cache = Path(cache_root).expanduser() if str(cache_root).strip() else None
        bundle = load_completion_bundle(bundle_path, extract_root=cache)
        camera = CameraAuthority.from_bundle(bundle)
        spec = PanoramaSpec(width=panorama_width, height=panorama_height)
        projection = build_projection_plan(camera, spec)
        observation = build_observation_map(projection)
        scene_scale, scale_evidence = derive_scene_scale_from_primary_mesh(
            bundle.primary_mesh
        )
        envelope = build_completion_envelope(camera, scene_scale)
        candidates = build_generation_candidate_map(
            projection,
            observation,
            envelope,
        )
        panorama, source_lock, candidate_mask = render_temporary_panorama(
            bundle.source_image,
            camera,
            spec,
            observation,
            candidates,
        )

        diagnostics = {
            "status": "PASS",
            "gate": 3,
            "subgate": "3.5",
            "source_run_id": bundle.source_run_id,
            "scene_contract_id": bundle.scene_contract_id,
            "panorama": {
                "width": spec.width,
                "height": spec.height,
                "aspect_ratio": spec.aspect_ratio,
                "source_footprint": {
                    "min_u": projection.footprint.min_u,
                    "max_u": projection.footprint.max_u,
                    "min_v": projection.footprint.min_v,
                    "max_v": projection.footprint.max_v,
                    "boundary_samples": projection.footprint.boundary_samples,
                },
            },
            "camera": {
                "horizontal_fov_deg": camera.horizontal_fov_deg,
                "vertical_fov_deg": camera.vertical_fov_deg,
                "lens_model": camera.lens_model,
                "authority": "P9_BASELINE_CANONICAL_CAMERA",
            },
            "source_lock": observation.manifest(),
            "generation_candidates": candidates.manifest(),
            "scene_scale_measurement": scale_evidence.manifest(),
            "completion_envelope": envelope.manifest(),
            "preview_rules": {
                "source_pixels_preserved": True,
                "unknown_pixels_black": True,
                "generation_performed": False,
                "world_scale_exploration": False,
                "full_360_generation": False,
            },
        }
        rendered = _pretty(diagnostics)
        ui = {"text": [rendered]}
        ui_images = save_comfyui_preview_images(
            panorama,
            source_lock,
            candidate_mask,
            scene_contract_id=bundle.scene_contract_id,
            panorama_width=panorama_width,
        )
        if ui_images:
            ui["images"] = ui_images

        return {
            "ui": ui,
            "result": (panorama, source_lock, candidate_mask, rendered),
        }


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10CompletionBundleBuilder": ConceptGhostP10CompletionBundleBuilder,
    "ConceptGhostP10BundleLoader": ConceptGhostP10BundleLoader,
    "ConceptGhostP10PanoramaPreview": ConceptGhostP10PanoramaPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10CompletionBundleBuilder": "P10 P9 Completion Bundle Builder",
    "ConceptGhostP10BundleLoader": "P10 P9 Bundle Loader / Validator",
    "ConceptGhostP10PanoramaPreview": "P10 Temporary Panorama / Authority Preview",
}
