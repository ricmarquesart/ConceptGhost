from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ContractError


_SCHEMA = "ConceptGhost.VisualEvidenceContract.v0.1"


# Project-wide policy. A gate is not considered reviewable merely because its
# numerical/runtime contract passed: a terminal diagnostic branch must expose
# what changed and, when the gate changes geometry/evidence, a comparison must
# show the input/reference beside the gate result.
VISUAL_EVIDENCE_RULES: dict[str, dict[str, Any]] = {
    "G7.1": {
        "title": "P10→P9 Registration Authority",
        "preview": "registration_overlay",
        "comparison": "p9_vs_registered_p10",
        "preferred_media": ["PNG"],
    },
    "G7.2": {
        "title": "Authority-aware Geometry Provenance",
        "preview": "provenance_overlay",
        "comparison": "raw_geometry_vs_provenance_classification",
        "preferred_media": ["PNG", "PLY"],
    },
    "G7.2C": {
        "title": "Geometry Confidence",
        "preview": "confidence_heatmap_blue_high_red_low",
        "comparison": "confidence_before_vs_after_evidence",
        "preferred_media": ["PNG", "PLY"],
    },
    "G7.3": {
        "title": "Free-Space / No-Fill",
        "preview": "free_occupied_unknown_conflict_overlay",
        "comparison": "surface_before_vs_no_fill_constraints",
        "preferred_media": ["PNG", "PLY"],
    },
    "G7.4": {
        "title": "Protected Fusion Candidate",
        "preview": "accepted_rejected_protected_fusion_overlay",
        "comparison": "pre_fusion_vs_protected_fusion",
        "preferred_media": ["PNG", "GIF", "PLY"],
    },
    "G7.5": {
        "title": "Registration / Provenance Visual Review",
        "preview": "four_view_review",
        "comparison": "gate7_evidence_summary",
        "preferred_media": ["PNG"],
    },
    "G7.6": {
        "title": "Gate 7 Closeout",
        "preview": "gate7_visual_evidence_index",
        "comparison": "gate7_input_output_summary",
        "preferred_media": ["PNG", "JSON"],
    },
}


def rule_for_gate(gate_id: str) -> dict[str, Any]:
    gate_id = str(gate_id).strip().upper()
    if gate_id not in VISUAL_EVIDENCE_RULES:
        # Future gates inherit the same mandatory shape even before a more
        # specific presentation is designed.
        return {
            "title": gate_id,
            "preview": "gate_specific_state_preview",
            "comparison": "before_vs_after_or_reference_vs_result",
            "preferred_media": ["PNG"],
        }
    return dict(VISUAL_EVIDENCE_RULES[gate_id])


def build_visual_evidence_manifest(
    gate_id: str,
    output_root: str | Path,
    *,
    preview_artifacts: list[str | Path],
    comparison_artifacts: list[str | Path],
    diagnostics_artifacts: list[str | Path] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze a terminal, non-authoritative visual-evidence branch contract."""

    gate = str(gate_id).strip().upper()
    rule = rule_for_gate(gate)
    previews = [Path(item).resolve() for item in preview_artifacts]
    comparisons = [Path(item).resolve() for item in comparison_artifacts]
    diagnostics = [Path(item).resolve() for item in (diagnostics_artifacts or [])]

    if not previews:
        raise ContractError(f"{gate} visual evidence requires at least one preview artifact")
    if not comparisons:
        raise ContractError(f"{gate} visual evidence requires at least one comparison artifact")

    missing = [path for path in (*previews, *comparisons, *diagnostics) if not path.is_file()]
    if missing:
        raise ContractError(
            f"{gate} visual evidence references missing artifacts: "
            + ", ".join(str(path) for path in missing[:8])
        )

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate_id": gate,
        "gate_title": rule["title"],
        "required_preview_kind": rule["preview"],
        "required_comparison_kind": rule["comparison"],
        "preferred_media": rule["preferred_media"],
        "preview_artifacts": [str(path) for path in previews],
        "comparison_artifacts": [str(path) for path in comparisons],
        "diagnostics_artifacts": [str(path) for path in diagnostics],
        "branch_contract": {
            "terminal_visual_branch": True,
            "feeds_geometry_pipeline": False,
            "may_modify_geometry": False,
            "may_modify_p9": False,
            "may_promote_result": False,
            "may_be_deleted_without_affecting_authoritative_result": True,
        },
        "comparison_contract": {
            "same_camera_when_camera_replay_is_used": True,
            "same_projection_or_scale_when_static_comparison_is_used": True,
            "before_reference_must_be_named": True,
            "after_result_must_be_named": True,
            "difference_or_changed_region_should_be_exposed_when_meaningful": True,
        },
        "metadata": metadata or {},
    }
    path = output_root / f"{gate.lower().replace('.', '_')}_visual_evidence_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(path)
    return manifest


def validate_visual_evidence_manifest(path: str | Path, gate_id: str | None = None) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read visual evidence manifest: {path}: {error}") from error
    if not isinstance(value, dict) or value.get("schema") != _SCHEMA:
        raise ContractError("Visual evidence manifest schema mismatch")
    if value.get("status") != "PASS":
        raise ContractError("Visual evidence manifest must have status PASS")
    actual_gate = str(value.get("gate_id") or "").upper()
    if gate_id is not None and actual_gate != str(gate_id).strip().upper():
        raise ContractError("Visual evidence gate identity mismatch")
    branch = value.get("branch_contract")
    if not isinstance(branch, dict):
        raise ContractError("Visual evidence manifest is missing branch_contract")
    required_false = ("feeds_geometry_pipeline", "may_modify_geometry", "may_modify_p9", "may_promote_result")
    if branch.get("terminal_visual_branch") is not True:
        raise ContractError("Visual evidence branch must be terminal")
    for field in required_false:
        if branch.get(field) is not False:
            raise ContractError(f"Visual evidence branch must keep {field}=false")
    previews = value.get("preview_artifacts")
    comparisons = value.get("comparison_artifacts")
    if not isinstance(previews, list) or not previews:
        raise ContractError("Visual evidence manifest has no preview artifacts")
    if not isinstance(comparisons, list) or not comparisons:
        raise ContractError("Visual evidence manifest has no comparison artifacts")
    missing = [
        Path(item)
        for item in [*previews, *comparisons, *(value.get("diagnostics_artifacts") or [])]
        if not Path(item).is_file()
    ]
    if missing:
        raise ContractError("Visual evidence manifest has missing artifact files")
    return value
