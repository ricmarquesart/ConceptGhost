from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError


_CATEGORY = "ConceptGhost/P10 Author Integration"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


class ConceptGhostP10AuthorDatasetProject:
    """Place the author's SplatKit project inside the immutable P10 attempt.

    This replaces only SplatKit_DatasetProject's location boundary. The author's
    CameraPlot, WAN, HiResComposite and SphereSfM nodes still consume the same
    dataset_dir/prefix contract, but every file now lands under the current
    ComfyUI output attempt from the beginning.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "dataset_folder_name": (
                    "STRING",
                    {"default": "author_dataset", "multiline": False},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "dataset_dir",
        "control_rgb_prefix",
        "control_mask_prefix",
        "wan_inpaint_prefix",
        "diagnostics_json",
    )
    FUNCTION = "make"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def make(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        scene_contract_id: str,
        dataset_folder_name: str = "author_dataset",
    ):
        attempt = Path(p10_attempt_root).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        scene_id = str(scene_contract_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("Author dataset project attempt identity/path mismatch")

        manifest_path = attempt / "attempt_manifest.json"
        if not manifest_path.is_file():
            raise ContractError("Author dataset project requires attempt_manifest.json")
        attempt_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("Author dataset project scene_contract_id does not match attempt")

        safe = "".join(
            ch if ch.isalnum() or ch in "-_" else "_"
            for ch in str(dataset_folder_name or "author_dataset").strip()
        ).strip("_") or "author_dataset"
        dataset_dir = (attempt / safe).resolve()
        for sub in ("condition", "camera_plot", "wan_inpaint", "_work"):
            (dataset_dir / sub).mkdir(parents=True, exist_ok=True)

        try:
            import folder_paths
            comfy_output = Path(folder_paths.get_output_directory()).resolve()
        except Exception:
            # Unit/source contexts may not import ComfyUI. The attempt itself is
            # still authoritative; infer the output root by walking above the
            # canonical conceptghost/p10_attempts/<p9>/<attempt> tail.
            parts = attempt.parts
            try:
                idx = [part.lower() for part in parts].index("conceptghost")
                comfy_output = Path(*parts[:idx]).resolve()
            except Exception as error:
                raise ContractError(
                    "Cannot resolve ComfyUI output root for author dataset prefixes"
                ) from error

        try:
            relative = dataset_dir.relative_to(comfy_output).as_posix()
        except ValueError as error:
            raise ContractError(
                "Author dataset project must live inside the active ComfyUI output directory"
            ) from error

        control_rgb_prefix = f"{relative}/camera_plot/control_rgb"
        control_mask_prefix = f"{relative}/camera_plot/control_mask"
        wan_inpaint_prefix = f"{relative}/wan_inpaint/wan_video"

        payload = {
            "schema": "ConceptGhost.AuthorDatasetProject.v0.1",
            "status": "PASS",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "dataset_dir": str(dataset_dir),
            "comfy_output_root": str(comfy_output),
            "relative_dataset_dir": relative,
            "control_rgb_prefix": control_rgb_prefix,
            "control_mask_prefix": control_mask_prefix,
            "wan_inpaint_prefix": wan_inpaint_prefix,
            "author_contract_compatibility": "SPLATKIT_DATASET_PROJECT_PATHS",
            "normal_backfill_required": False,
        }
        project_manifest = dataset_dir / "conceptghost_author_dataset_project.json"
        project_manifest.write_text(_pretty(payload) + "\n", encoding="utf-8")

        return (
            str(dataset_dir),
            control_rgb_prefix,
            control_mask_prefix,
            wan_inpaint_prefix,
            _pretty(payload),
        )


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetProject": ConceptGhostP10AuthorDatasetProject,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetProject": "P10 · Author Dataset Project Inside Current Attempt",
}
