from __future__ import annotations

import json
from pathlib import Path

from .p9_boundary import build_completion_bundle, load_completion_bundle


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
        return (str(result.zip_path), _pretty(diagnostics))


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
        return (
            str(bundle.root),
            str(bundle.source_image),
            str(bundle.camera),
            str(bundle.primary_mesh),
            _pretty(diagnostics),
        )


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10CompletionBundleBuilder": ConceptGhostP10CompletionBundleBuilder,
    "ConceptGhostP10BundleLoader": ConceptGhostP10BundleLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10CompletionBundleBuilder": "P10 P9 Completion Bundle Builder",
    "ConceptGhostP10BundleLoader": "P10 P9 Bundle Loader / Validator",
}
