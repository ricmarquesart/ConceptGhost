from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root


_CATEGORY = "ConceptGhost/P10 Author Integration"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


class ConceptGhostP10AuthorDatasetProjectPath:
    """Resolve the author's DatasetProject into the active P10 attempt RESULTS tree.

    SplatKit's DatasetProject accepts a path relative to ComfyUI/output. This node
    derives that relative project name from the immutable ConceptGhost attempt so
    CameraPlot, WAN helper files, HiResComposite and SphereSfM all write under the
    same executable-local run instead of a detached global project folder.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("dataset_project_name", "dataset_project_absolute", "diagnostics_json")
    FUNCTION = "resolve"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def resolve(self, p10_attempt_root: str, p10_attempt_id: str):
        try:
            import folder_paths
        except ImportError as error:
            raise RuntimeError(
                "Author dataset project path resolver requires the active ComfyUI runtime"
            ) from error

        attempt = Path(p10_attempt_root).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("Author dataset path attempt identity/path mismatch")

        comfy_output = Path(folder_paths.get_output_directory()).resolve()
        try:
            attempt.relative_to(comfy_output)
        except ValueError as error:
            raise ContractError(
                "P10 attempt must live under the active ComfyUI output directory"
            ) from error

        cg08_outputs = stage_root(attempt, "CG_08") / "OUTPUTS"
        cg08_outputs.mkdir(parents=True, exist_ok=True)
        absolute = (cg08_outputs / "author_splatkit_project").resolve()
        try:
            relative = absolute.relative_to(comfy_output)
        except ValueError as error:
            raise ContractError("Author dataset project escaped ComfyUI output") from error

        # SplatKit DatasetProject accepts a path-like project name under output.
        dataset_name = relative.as_posix()
        diagnostics = {
            "status": "PASS",
            "schema": "ConceptGhost.AuthorDatasetProjectPath.v0.1",
            "p10_attempt_id": attempt_id,
            "comfy_output_root": str(comfy_output),
            "dataset_project_name": dataset_name,
            "dataset_project_absolute": str(absolute),
            "canonical_stage": "CG_08",
            "manual_output_relocation_required": False,
            "author_pipeline_writes_inside_attempt_from_start": True,
        }
        return dataset_name, str(absolute), _pretty(diagnostics)


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetProjectPath": ConceptGhostP10AuthorDatasetProjectPath,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetProjectPath": "P10 · CG-08 · Author Dataset Project Inside Current Attempt",
}
