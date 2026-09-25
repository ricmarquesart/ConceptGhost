from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .gate8_defect_analysis import Gate8DefectClass


_SCHEMA = "ConceptGhost.P10Gate8LocalRemeshCleanupPlan.v0.1"
_INPUT_SCHEMA = "ConceptGhost.P10Gate8DefectAnalysis.v0.1"


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 8.2 local remesh/cleanup planning requires NumPy") from error
    return np


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{label} must be a bool")
    return value


def _region_decision(region: dict[str, Any]) -> dict[str, Any]:
    class_name = str(region.get("class") or "")
    region_id = str(region.get("region_id") or "")
    if not region_id:
        raise ContractError("Gate 8.2 region is missing region_id")
    if region.get("automatic_geometry_edit_allowed") is not False:
        raise ContractError(f"Gate 8.2 refuses region {region_id} with automatic edits enabled")

    base = {
        "region_id": region_id,
        "class": class_name,
        "automatic_geometry_edit_allowed": False,
        "apply_in_this_subgate": False,
        "bounded_to_source_region": True,
    }
    if class_name == Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE.name:
        return {
            **base,
            "preview_action": "REMOVE_FALSE_SURFACE_IN_NON_OFFICIAL_PREVIEW_ONLY",
            "cleanup_preview_candidate": True,
            "local_remesh_candidate": False,
            "preserve_opening": True,
            "requires_new_support": False,
        }
    if class_name == Gate8DefectClass.VALID_OPENING.name:
        return {
            **base,
            "preview_action": "PRESERVE_OPENING_NO_FILL",
            "cleanup_preview_candidate": False,
            "local_remesh_candidate": False,
            "preserve_opening": True,
            "requires_new_support": False,
        }
    if class_name == Gate8DefectClass.MISSING_SURFACE_UNKNOWN.name:
        return {
            **base,
            "preview_action": "LOCAL_REMESH_PLAN_ONLY_AWAIT_SUPPORTED_BOUNDARY",
            "cleanup_preview_candidate": False,
            "local_remesh_candidate": True,
            "preserve_opening": False,
            "requires_new_support": True,
            "unknown_is_not_free": True,
        }
    if class_name == Gate8DefectClass.LOW_CONFIDENCE_SURFACE.name:
        return {
            **base,
            "preview_action": "HOLD_LOW_CONFIDENCE_NO_AUTOMATIC_EDIT",
            "cleanup_preview_candidate": False,
            "local_remesh_candidate": False,
            "preserve_opening": False,
            "requires_new_support": True,
        }
    if class_name == Gate8DefectClass.CONFLICT_REGION.name:
        return {
            **base,
            "preview_action": "HOLD_CONFLICT_REQUIRE_STRONGER_EVIDENCE",
            "cleanup_preview_candidate": False,
            "local_remesh_candidate": False,
            "preserve_opening": False,
            "requires_new_support": True,
        }
    if class_name == Gate8DefectClass.SUPPORTED_SURFACE.name:
        return {
            **base,
            "preview_action": "PRESERVE_SUPPORTED_SURFACE",
            "cleanup_preview_candidate": False,
            "local_remesh_candidate": False,
            "preserve_opening": False,
            "requires_new_support": False,
        }
    raise ContractError(f"Gate 8.2 encountered unknown defect class: {class_name!r}")


def plan_gate8_local_remesh_cleanup(
    defect_analysis_manifest_path: str | Path,
    output_root: str | Path,
    *,
    structural_analysis: bool = True,
    structural_preview: bool = True,
    apply_structural_regularization: bool = False,
) -> dict[str, Any]:
    """Build the bounded Gate 8.2 cleanup/remesh preview contract.

    Gate 8.2 deliberately separates analysis/preview from application.
    Confirmed-free false surfaces may be nominated for removal in a
    NON-OFFICIAL preview candidate. UNKNOWN may be nominated for future local
    remesh only when new support exists. No official P9/P10 geometry is edited.
    """
    np = _lazy_numpy()
    structural_analysis = _require_bool(structural_analysis, "structural_analysis")
    structural_preview = _require_bool(structural_preview, "structural_preview")
    apply_structural_regularization = _require_bool(
        apply_structural_regularization, "apply_structural_regularization"
    )
    if not structural_analysis:
        raise ContractError("Gate 8.2 requires Structural Analysis ON")
    if not structural_preview:
        raise ContractError("Gate 8.2 requires Structural Preview ON")
    if apply_structural_regularization:
        raise ContractError(
            "Gate 8.2 source/CI checkpoint requires Apply Structural Regularization OFF"
        )

    manifest_path = Path(defect_analysis_manifest_path).resolve()
    defect = _read_json(manifest_path, "Gate 8.1 defect-analysis manifest")
    if defect.get("schema") != _INPUT_SCHEMA:
        raise ContractError("Gate 8.2 requires Gate 8.1 defect-analysis schema v0.1")
    if defect.get("status") != "PASS" or defect.get("subgate") != "8.1":
        raise ContractError("Gate 8.2 requires a PASS Gate 8.1 manifest")
    if defect.get("ready_for_gate8_2") is not True:
        raise ContractError("Gate 8.1 did not authorize Gate 8.2 planning")
    for field in (
        "official_geometry_changed",
        "p9_authority_changed",
        "destructive_cleanup_performed",
        "automatic_geometry_edit_allowed",
    ):
        if defect.get(field) is not False:
            raise ContractError(f"Gate 8.2 refuses Gate 8.1 manifest with {field}=true")

    evidence_path = Path(str(defect.get("evidence_npz_path") or "")).resolve()
    if not evidence_path.is_file():
        raise ContractError("Gate 8.2 requires Gate 8.1 evidence NPZ")
    with np.load(evidence_path, allow_pickle=False) as evidence:
        required = {
            "p10_face_defect_class",
            "p10_face_region_id",
            "p10_face_gate7_reason_code",
            "p10_face_gate7_confidence",
            "missing_surface_unknown_voxel_keys",
        }
        missing = required.difference(evidence.files)
        if missing:
            raise ContractError(f"Gate 8.2 Gate 8.1 evidence missing arrays: {sorted(missing)}")
        defect_class = np.asarray(evidence["p10_face_defect_class"], dtype=np.uint8)
        face_region_id = np.asarray(evidence["p10_face_region_id"], dtype=np.int32)
        reason_code = np.asarray(evidence["p10_face_gate7_reason_code"], dtype=np.uint8)
        gate7_confidence = np.asarray(evidence["p10_face_gate7_confidence"], dtype=np.float32)
        missing_unknown_voxels = np.asarray(
            evidence["missing_surface_unknown_voxel_keys"], dtype=np.int32
        ).reshape((-1, 3))

    face_count = len(defect_class)
    if not (
        len(face_region_id)
        == len(reason_code)
        == len(gate7_confidence)
        == face_count
    ):
        raise ContractError("Gate 8.2 face evidence arrays do not align")

    valid_values = {int(item) for item in Gate8DefectClass}
    observed_values = {int(v) for v in np.unique(defect_class)}
    unknown_values = observed_values.difference(valid_values)
    if unknown_values:
        raise ContractError(f"Gate 8.2 evidence contains unknown defect classes: {sorted(unknown_values)}")

    remove_preview = defect_class == int(Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE)
    hold = np.isin(
        defect_class,
        np.asarray(
            [
                int(Gate8DefectClass.LOW_CONFIDENCE_SURFACE),
                int(Gate8DefectClass.CONFLICT_REGION),
            ],
            dtype=np.uint8,
        ),
    )
    preserve = ~remove_preview
    supported = defect_class == int(Gate8DefectClass.SUPPORTED_SURFACE)

    regions = defect.get("regions")
    if not isinstance(regions, list):
        raise ContractError("Gate 8.2 requires Gate 8.1 regions")
    region_decisions = []
    seen_region_ids: set[str] = set()
    for item in regions:
        if not isinstance(item, dict):
            raise ContractError("Gate 8.2 region entries must be JSON objects")
        decision = _region_decision(item)
        if decision["region_id"] in seen_region_ids:
            raise ContractError(f"Duplicate Gate 8.2 region_id: {decision['region_id']}")
        seen_region_ids.add(decision["region_id"])
        region_decisions.append(decision)

    false_regions = {
        int(item["region_index"])
        for item in regions
        if isinstance(item, dict)
        and item.get("class") == Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE.name
        and isinstance(item.get("region_index"), int)
    }
    referenced_false_regions = {int(v) for v in np.unique(face_region_id[remove_preview]) if int(v) >= 0}
    if referenced_false_regions != false_regions:
        raise ContractError(
            "Gate 8.2 false-surface face-region evidence does not match Gate 8.1 regions"
        )

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    preview_evidence_path = output_root / "gate8_local_remesh_cleanup_preview_evidence.npz"
    np.savez_compressed(
        preview_evidence_path,
        p10_face_preserve_mask=preserve.astype(np.uint8),
        p10_face_cleanup_preview_remove_mask=remove_preview.astype(np.uint8),
        p10_face_hold_mask=hold.astype(np.uint8),
        p10_face_supported_mask=supported.astype(np.uint8),
        p10_face_region_id=face_region_id,
        p10_face_gate7_reason_code=reason_code,
        p10_face_gate7_confidence=gate7_confidence,
        missing_surface_unknown_voxel_keys=missing_unknown_voxels,
    )

    class_counts = defect.get("class_counts") if isinstance(defect.get("class_counts"), dict) else {}
    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 8,
        "subgate": "8.2",
        "mode": "STRUCTURAL_ANALYSIS_AND_NONDESTRUCTIVE_PREVIEW_PLAN",
        "scene_contract_id": defect.get("scene_contract_id"),
        "p9_run_id": defect.get("p9_run_id"),
        "p10_attempt_id": defect.get("p10_attempt_id"),
        "coordinate_space": defect.get("coordinate_space"),
        "structural_controls": {
            "structural_analysis": True,
            "structural_preview": True,
            "apply_structural_regularization": False,
        },
        "face_counts": {
            "total": int(face_count),
            "preserved_in_preview": int(np.count_nonzero(preserve)),
            "nominated_cleanup_preview_removal": int(np.count_nonzero(remove_preview)),
            "held_for_stronger_evidence": int(np.count_nonzero(hold)),
            "supported_surface": int(np.count_nonzero(supported)),
        },
        "class_counts": class_counts,
        "region_decisions": region_decisions,
        "missing_surface_unknown_voxel_count": int(len(missing_unknown_voxels)),
        "inputs": {
            "gate8_1_manifest_path": str(manifest_path),
            "gate8_1_evidence_npz_path": str(evidence_path),
        },
        "preview_evidence_npz_path": str(preview_evidence_path),
        "preview_evidence_sha256": _sha256(preview_evidence_path),
        "policies": {
            "confirmed_free": "PREVIEW_REMOVE_FALSE_SURFACE_NEVER_FILL",
            "valid_opening": "PRESERVE_NO_FILL",
            "unknown": "REMESH_PLAN_ONLY_REQUIRES_NEW_SUPPORT",
            "low_confidence": "HOLD_NO_AUTOMATIC_EDIT",
            "conflict": "HOLD_NO_AUTOMATIC_EDIT",
            "high_source_authority": "PROTECTED",
            "bounded_locality": "SOURCE_REGION_ONLY",
        },
        "preview_candidate_is_official_geometry": False,
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "destructive_cleanup_performed": False,
        "automatic_geometry_edit_allowed": False,
        "ready_for_gate8_3_source_only": True,
        "ready_for_runtime_promotion": False,
        "promotion_blocked_by": [
            "GATE7_R6F_TARGET_PC_ACCEPTANCE",
            "GATE8_2_RUNTIME_STRUCTURAL_PREVIEW_ACCEPTANCE",
        ],
        "next_required": [
            "G8.3_UV_PRESERVATION_RECOVERY_SOURCE_CONTRACT",
            "G8.2_RUNTIME_STRUCTURAL_PREVIEW_WITH_APPLY_OFF",
        ],
    }

    output_manifest_path = output_root / "gate8_local_remesh_cleanup_manifest.json"
    output_manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["manifest_path"] = str(output_manifest_path)
    return result
