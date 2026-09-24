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
from .wan_conditioning import ConceptGhostP10WanMaskedConditioning
from .wan_sequence import ConceptGhostP10WanSequentialSampler
from .reconstruction_node import ConceptGhostP10ReconstructionRuntime
from .route_authoring_node import ConceptGhostP10DroneRouteAuthoring
from .route_handoff import ConceptGhostP10RouteCommit, ConceptGhostP10ProductionEntryLoader
from .moge_diagnostics import ConceptGhostMoGeDiagnosticsControl, ConceptGhostMoGeDiagnosticProfileTap, ConceptGhostMoGeDepthDiagnostics


_CATEGORY = "ConceptGhost/P10 Lab"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


class ConceptGhostP10WorkflowInstructions:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "instructions":(
                    "STRING",
                    {
                        "default":"ConceptGhost P10 workflow instructions",
                        "multiline":True,
                        "dynamicPrompts":False,
                    },
                ),
            }
        }

    RETURN_TYPES=("STRING",)
    RETURN_NAMES=("instructions",)
    FUNCTION="show"
    CATEGORY="ConceptGhost/P10 Refined"
    OUTPUT_NODE=True

    def show(self,instructions: str):
        text=str(instructions or "").strip()
        return {"ui":{"text":[text]},"result":(text,)}


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


class ConceptGhostP10RefinedEvidencePreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_dir": ("STRING", {"forceInput": True}),
                "panorama_width": ("INT", {"default": 1024, "min": 512, "max": 4096, "step": 2}),
                "view_width": ("INT", {"default": 640, "min": 320, "max": 1280, "step": 16}),
                "steps_per_segment": ("INT", {"default": 4, "min": 1, "max": 12, "step": 1}),
            },
            "optional": {
                "route_plan_json": ("STRING", {"forceInput": True}),
                "p10_attempt_root": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK", "IMAGE", "MASK", "IMAGE", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "p9_3d_partial_erp",
        "source_authority_erp",
        "source_lock_mask",
        "flight_views",
        "hole_masks",
        "trajectory_map",
        "flight_gif_path",
        "control_manifest_path",
        "camera_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "preview"
    CATEGORY = "ConceptGhost/P10 Refined"
    OUTPUT_NODE = True

    def preview(
        self,
        run_dir: str,
        panorama_width: int,
        view_width: int,
        steps_per_segment: int,
        route_plan_json: str = "",
        p10_attempt_root: str = "",
    ):
        from .refined_evidence import build_refined_evidence

        evidence = build_refined_evidence(
            run_dir,
            panorama_width=panorama_width,
            view_width=view_width,
            steps_per_segment=steps_per_segment,
            route_plan_json=route_plan_json,
            p10_attempt_root=p10_attempt_root,
        )
        rendered = _pretty(evidence.diagnostics)
        ui = {"text": [rendered]}
        if evidence.ui_images:
            ui["images"] = list(evidence.ui_images)
        return {
            "ui": ui,
            "result": (
                evidence.p9_erp,
                evidence.source_erp,
                evidence.source_lock,
                evidence.flight_views,
                evidence.hole_masks,
                evidence.trajectory_map,
                evidence.gif_path,
                evidence.control_manifest_path,
                evidence.camera_manifest_path,
                rendered,
            ),
        }


class ConceptGhostP10Gate7VisualReview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "protected_fusion_manifest_path": ("STRING", {"forceInput": True}),
                "panel_size": ("INT", {"default": 600, "min": 320, "max": 1400, "step": 20}),
            },
            "optional": {
                "output_root": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "review_image",
        "preview_png_path",
        "visual_review_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "review"
    CATEGORY = "ConceptGhost/P10 Refined"
    OUTPUT_NODE = True

    def review(
        self,
        protected_fusion_manifest_path: str,
        panel_size: int,
        output_root: str = "",
    ):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError(
                "Gate 7 visual review requires NumPy, Pillow and torch in the ComfyUI runtime"
            ) from error

        from .gate7_visual_review import build_gate7_visual_review

        manifest_path = Path(protected_fusion_manifest_path).expanduser().resolve()
        root = (
            Path(output_root).expanduser().resolve()
            if str(output_root or "").strip()
            else manifest_path.parent / "gate7_visual_review"
        )
        result = build_gate7_visual_review(
            manifest_path,
            root,
            panel_size=int(panel_size),
        )
        preview_path = Path(result["preview_png_path"])
        with Image.open(preview_path) as opened:
            array = np.asarray(opened.convert("RGB"), dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).unsqueeze(0)
        rendered = _pretty(result)
        ui = {"text": [rendered]}
        try:
            import shutil
            import folder_paths

            subfolder = "conceptghost_p10_gate7"
            temp_root = Path(folder_paths.get_temp_directory()) / subfolder
            temp_root.mkdir(parents=True, exist_ok=True)
            temp_preview = temp_root / preview_path.name
            shutil.copy2(preview_path, temp_preview)
            ui["images"] = [
                {
                    "filename": temp_preview.name,
                    "subfolder": subfolder,
                    "type": "temp",
                }
            ]
        except Exception:
            # The IMAGE tensor remains the authoritative ComfyUI output even
            # when folder_paths is unavailable in source/unit-test contexts.
            pass
        return {
            "ui": ui,
            "result": (
                tensor,
                str(preview_path),
                str(result["manifest_path"]),
                rendered,
            ),
        }


class ConceptGhostP10ConfidenceComparison:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "confidence_manifest_path": ("STRING", {"forceInput": True}),
                "confidence_free_space_overlay_manifest_path": ("STRING", {"forceInput": True}),
                "panel_size": ("INT", {"default": 620, "min": 320, "max": 1000, "step": 20}),
            },
            "optional": {
                "output_root": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "comparison_image",
        "comparison_png_path",
        "comparison_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "compare"
    CATEGORY = "ConceptGhost/P10 Visual Evidence"
    OUTPUT_NODE = True

    def compare(
        self,
        confidence_manifest_path: str,
        confidence_free_space_overlay_manifest_path: str,
        panel_size: int,
        output_root: str = "",
    ):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Confidence comparison requires NumPy, Pillow and torch") from error

        from .visual_comparisons import render_confidence_before_after

        source = Path(confidence_manifest_path).expanduser().resolve()
        root = (
            Path(output_root).expanduser().resolve()
            if str(output_root or "").strip()
            else source.parent / "visual_evidence" / "confidence"
        )
        result = render_confidence_before_after(
            confidence_manifest_path,
            confidence_free_space_overlay_manifest_path,
            root,
            panel_size=int(panel_size),
        )
        preview_path = Path(result["comparison_png_path"])
        with Image.open(preview_path) as opened:
            array = np.asarray(opened.convert("RGB"), dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).unsqueeze(0)
        rendered = _pretty(result)
        return {
            "ui": {"text": [rendered]},
            "result": (
                tensor,
                str(preview_path),
                str(result["manifest_path"]),
                rendered,
            ),
        }


class ConceptGhostP10DroneMeshComparisonReplay:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataset_manifest_path": ("STRING", {"forceInput": True}),
                "before_mesh_path": ("STRING", {"forceInput": True}),
                "after_mesh_path": ("STRING", {"forceInput": True}),
                "before_label": ("STRING", {"default": "BEFORE"}),
                "after_label": ("STRING", {"default": "AFTER"}),
            },
            "optional": {
                "output_root": ("STRING", {"default": ""}),
                "max_frames": ("INT", {"default": 48, "min": 2, "max": 160, "step": 1}),
                "max_faces": ("INT", {"default": 10000, "min": 500, "max": 100000, "step": 500}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "comparison_first_frame",
        "before_gif_path",
        "after_gif_path",
        "comparison_gif_path",
        "diagnostics_json",
    )
    FUNCTION = "replay"
    CATEGORY = "ConceptGhost/P10 Visual Evidence"
    OUTPUT_NODE = True

    def replay(
        self,
        dataset_manifest_path: str,
        before_mesh_path: str,
        after_mesh_path: str,
        before_label: str,
        after_label: str,
        output_root: str = "",
        max_frames: int = 48,
        max_faces: int = 10000,
    ):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Drone comparison replay requires NumPy, Pillow and torch") from error

        from .visual_comparisons import render_drone_mesh_before_after_replay

        source = Path(dataset_manifest_path).expanduser().resolve()
        root = (
            Path(output_root).expanduser().resolve()
            if str(output_root or "").strip()
            else source.parent / "visual_evidence" / "drone_comparison"
        )
        result = render_drone_mesh_before_after_replay(
            dataset_manifest_path,
            before_mesh_path,
            after_mesh_path,
            root,
            before_label=before_label,
            after_label=after_label,
            max_frames=int(max_frames),
            max_faces=int(max_faces),
        )
        comparison_gif = Path(result["comparison_gif_path"])
        with Image.open(comparison_gif) as opened:
            opened.seek(0)
            array = np.asarray(opened.convert("RGB"), dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).unsqueeze(0)
        rendered = _pretty(result)
        return {
            "ui": {"text": [rendered]},
            "result": (
                tensor,
                str(result["before_gif_path"]),
                str(result["after_gif_path"]),
                str(comparison_gif),
                rendered,
            ),
        }


class ConceptGhostP10Gate7Runtime:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p9_run_dir": ("STRING", {"forceInput": True}),
                "reconstruction_runtime_manifest_path": ("STRING", {"forceInput": True}),
                "resume_existing": ("BOOLEAN", {"default": True}),
                "run_delaunay": ("BOOLEAN", {"default": True}),
                "colmap_executable": ("STRING", {"default": ""}),
            },
            "optional": {
                "output_root": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "gate7_review_image",
        "protected_fusion_candidate_ply",
        "gate7_runtime_manifest_path",
        "protected_fusion_manifest_path",
        "visual_review_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "run"
    CATEGORY = "ConceptGhost/P10 Refined"
    OUTPUT_NODE = True

    def run(
        self,
        p9_run_dir: str,
        reconstruction_runtime_manifest_path: str,
        resume_existing: bool,
        run_delaunay: bool,
        colmap_executable: str,
        output_root: str = "",
    ):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Gate 7 runtime requires NumPy, Pillow and torch") from error

        from .gate7_runtime import run_gate7_pipeline

        result = run_gate7_pipeline(
            p9_run_dir,
            reconstruction_runtime_manifest_path,
            output_root=output_root or None,
            resume_existing=bool(resume_existing),
            run_delaunay=bool(run_delaunay),
            colmap_executable=str(colmap_executable or "colmap"),
        )
        artifacts = result["artifacts"]
        preview_path = Path(artifacts["visual_review_png_path"])
        with Image.open(preview_path) as opened:
            array = np.asarray(opened.convert("RGB"), dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).unsqueeze(0)
        rendered = _pretty(result)
        ui = {"text": [rendered]}
        try:
            import shutil
            import folder_paths

            subfolder = "conceptghost_p10_gate7"
            temp_root = Path(folder_paths.get_temp_directory()) / subfolder
            temp_root.mkdir(parents=True, exist_ok=True)
            temp_preview = temp_root / preview_path.name
            shutil.copy2(preview_path, temp_preview)
            ui["images"] = [{
                "filename": temp_preview.name,
                "subfolder": subfolder,
                "type": "temp",
            }]
        except Exception:
            pass
        return {
            "ui": ui,
            "result": (
                tensor,
                str(artifacts["protected_fusion_candidate_ply_path"]),
                str(result["manifest_path"]),
                str(artifacts["protected_fusion_manifest_path"]),
                str(artifacts["visual_review_manifest_path"]),
                rendered,
            ),
        }


class ConceptGhostP10Gate7VisualEvidencePack:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gate7_runtime_manifest_path": ("STRING", {"forceInput": True}),
                "dr9r_runtime_accepted": ("BOOLEAN", {"default": False}),
                "artist_visual_review_approved": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "output_root": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "visual_evidence_index",
        "visual_pack_manifest_path",
        "confidence_before_after_png",
        "drone_before_after_gif",
        "gate7_closeout_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "build"
    CATEGORY = "ConceptGhost/P10 Visual Evidence"
    OUTPUT_NODE = True

    def build(
        self,
        gate7_runtime_manifest_path: str,
        dr9r_runtime_accepted: bool,
        artist_visual_review_approved: bool,
        output_root: str = "",
    ):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Gate 7 visual pack requires NumPy, Pillow and torch") from error

        from .gate7_visual_pack import build_gate7_visual_evidence_pack

        source = Path(gate7_runtime_manifest_path).expanduser().resolve()
        root = (
            Path(output_root).expanduser().resolve()
            if str(output_root or "").strip()
            else source.parent / "visual_evidence"
        )
        result = build_gate7_visual_evidence_pack(
            source,
            root,
            dr9r_runtime_accepted=bool(dr9r_runtime_accepted),
            artist_visual_review_approved=bool(artist_visual_review_approved),
        )
        outputs = result["key_outputs"]
        index_path = Path(outputs["gate7_visual_evidence_index_png"])
        with Image.open(index_path) as opened:
            array = np.asarray(opened.convert("RGB"), dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).unsqueeze(0)
        closeout_manifest = Path(root) / "g7_6" / "gate7_closeout_manifest.json"
        rendered = _pretty(result)
        ui = {"text": [rendered]}
        try:
            import shutil
            import folder_paths

            subfolder = "conceptghost_p10_gate7_visual_evidence"
            temp_root = Path(folder_paths.get_temp_directory()) / subfolder
            temp_root.mkdir(parents=True, exist_ok=True)
            temp_preview = temp_root / index_path.name
            shutil.copy2(index_path, temp_preview)
            ui["images"] = [{
                "filename": temp_preview.name,
                "subfolder": subfolder,
                "type": "temp",
            }]
        except Exception:
            pass
        return {
            "ui": ui,
            "result": (
                tensor,
                str(result["manifest_path"]),
                str(outputs["confidence_before_after_png"]),
                str(outputs["drone_replay_comparison_gif"]),
                str(closeout_manifest),
                rendered,
            ),
        }


NODE_CLASS_MAPPINGS = {
    "ConceptGhostMoGeDiagnosticsControl": ConceptGhostMoGeDiagnosticsControl,
    "ConceptGhostMoGeDiagnosticProfileTap": ConceptGhostMoGeDiagnosticProfileTap,
    "ConceptGhostMoGeDepthDiagnostics": ConceptGhostMoGeDepthDiagnostics,
    "ConceptGhostP10WorkflowInstructions": ConceptGhostP10WorkflowInstructions,
    "ConceptGhostP10CompletionBundleBuilder": ConceptGhostP10CompletionBundleBuilder,
    "ConceptGhostP10BundleLoader": ConceptGhostP10BundleLoader,
    "ConceptGhostP10PanoramaPreview": ConceptGhostP10PanoramaPreview,
    "ConceptGhostP10RefinedEvidencePreview": ConceptGhostP10RefinedEvidencePreview,
    "ConceptGhostP10DroneRouteAuthoring": ConceptGhostP10DroneRouteAuthoring,
    "ConceptGhostP10RouteCommit": ConceptGhostP10RouteCommit,
    "ConceptGhostP10ProductionEntryLoader": ConceptGhostP10ProductionEntryLoader,
    "ConceptGhostP10WanMaskedConditioning": ConceptGhostP10WanMaskedConditioning,
    "ConceptGhostP10WanSequentialSampler": ConceptGhostP10WanSequentialSampler,
    "ConceptGhostP10ReconstructionRuntime": ConceptGhostP10ReconstructionRuntime,
    "ConceptGhostP10Gate7VisualReview": ConceptGhostP10Gate7VisualReview,
    "ConceptGhostP10ConfidenceComparison": ConceptGhostP10ConfidenceComparison,
    "ConceptGhostP10DroneMeshComparisonReplay": ConceptGhostP10DroneMeshComparisonReplay,
    "ConceptGhostP10Gate7Runtime": ConceptGhostP10Gate7Runtime,
    "ConceptGhostP10Gate7VisualEvidencePack": ConceptGhostP10Gate7VisualEvidencePack,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostMoGeDiagnosticsControl": "P9 · MoGe Depth Diagnostics · Controls",
    "ConceptGhostMoGeDiagnosticProfileTap": "P9 · MoGe Depth Diagnostics · Per-Step Tap",
    "ConceptGhostMoGeDepthDiagnostics": "P9 · MoGe Depth Diagnostics · Export / Preview",
    "ConceptGhostP10WorkflowInstructions": "P10 · START HERE · Workflow Instructions",
    "ConceptGhostP10CompletionBundleBuilder": "P10 P9 Completion Bundle Builder",
    "ConceptGhostP10BundleLoader": "P10 P9 Bundle Loader / Validator",
    "ConceptGhostP10PanoramaPreview": "P10 Temporary Panorama / Authority Preview",
    "ConceptGhostP10RefinedEvidencePreview": "P10 Refined · ERP + Drone + Hole Evidence",
    "ConceptGhostP10DroneRouteAuthoring": "P10 Refined · Artist Drone Route Authoring",
    "ConceptGhostP10RouteCommit": "P10 Refined · Commit Artist Route / Production Entry",
    "ConceptGhostP10ProductionEntryLoader": "P10 Refined · Load Production Entry",
    "ConceptGhostP10WanMaskedConditioning": "P10 Refined · WAN Masked Conditioning",
    "ConceptGhostP10WanSequentialSampler": "P10 Refined · Sequential WAN + Source Composite",
    "ConceptGhostP10ReconstructionRuntime": "P10 Refined · Reconstruction Runtime + Mesh Preview",
    "ConceptGhostP10Gate7VisualReview": "P10 · Gate 7 · Registration + Provenance Review",
    "ConceptGhostP10ConfidenceComparison": "P10 · Visual Evidence · Confidence BEFORE / AFTER",
    "ConceptGhostP10DroneMeshComparisonReplay": "P10 · Visual Evidence · Same-Camera BEFORE / AFTER GIF",
    "ConceptGhostP10Gate7Runtime": "P10 · STEP 5 · Gate 7 Protected Fusion Runtime",
    "ConceptGhostP10Gate7VisualEvidencePack": "P10 · Gate 7 · Visual Evidence + BEFORE / AFTER Pack",
}
