from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .free_space_confidence import build_confidence_free_space_overlay
from .free_space_constraints import classify_free_space
from .free_space_evidence import build_free_space_evidence
from .gate7_provenance import build_gate7_provenance
from .gate7_registration import write_gate7_registration
from .gate7_visual_review import build_gate7_visual_review
from .geometry_confidence import build_geometry_confidence
from .prefusion_mesh import run_delaunay_visibility_meshing
from .protected_fusion import build_protected_fusion_candidate


_SCHEMA = "ConceptGhost.P10Gate7Runtime.v0.1"


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _valid_file(path: Any) -> bool:
    try:
        return Path(str(path)).resolve().is_file()
    except Exception:
        return False


def _reuse_runtime(path: Path, p9_run_dir: Path, gate6_runtime_path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = _read_json(path, "Gate 7 runtime manifest")
    if payload.get("schema") != _SCHEMA or payload.get("status") != "PASS":
        return None
    if Path(str(payload.get("p9_run_dir") or "")).resolve() != p9_run_dir:
        return None
    if Path(str(payload.get("gate6_runtime_manifest_path") or "")).resolve() != gate6_runtime_path:
        return None
    required = payload.get("artifacts")
    if not isinstance(required, dict):
        return None
    required_files = (
        "registration_manifest_path",
        "provenance_manifest_path",
        "confidence_manifest_path",
        "free_space_evidence_manifest_path",
        "free_space_constraints_manifest_path",
        "confidence_free_space_overlay_manifest_path",
        "protected_fusion_manifest_path",
        "visual_review_manifest_path",
    )
    if not all(_valid_file(required.get(key)) for key in required_files):
        return None
    payload["manifest_path"] = str(path)
    payload["resumed"] = True
    return payload


def run_gate7_pipeline(
    p9_run_dir: str | Path,
    reconstruction_runtime_manifest_path: str | Path,
    *,
    output_root: str | Path | None = None,
    resume_existing: bool = True,
    run_delaunay: bool = True,
    colmap_executable: str = "colmap",
) -> dict[str, Any]:
    """Execute G7.1→G7.5 without promoting Gate 8.

    G7.6 runtime acceptance remains a separate visual/human-review branch.
    The Gate 7 runtime produces only derived attempt-owned artifacts and never
    modifies the authoritative P9 run.
    """

    p9_run_dir = Path(p9_run_dir).resolve()
    gate6_runtime_path = Path(reconstruction_runtime_manifest_path).resolve()
    if not gate6_runtime_path.is_file():
        raise ContractError(f"Gate 6 runtime manifest is missing: {gate6_runtime_path}")

    gate6 = _read_json(gate6_runtime_path, "Gate 6 reconstruction runtime manifest")
    attempt_root_raw = gate6.get("p10_attempt_root")
    if not attempt_root_raw:
        wan_path = Path(str(gate6.get("wan_manifest_path") or "")).resolve()
        wan = _read_json(wan_path, "Gate 5 WAN manifest")
        attempt_root_raw = wan.get("p10_attempt_root")
    if not attempt_root_raw:
        raise ContractError("Gate 7 runtime cannot resolve p10_attempt_root")

    attempt_root = Path(str(attempt_root_raw)).resolve()
    root = (
        Path(output_root).resolve()
        if output_root is not None and str(output_root).strip()
        else attempt_root / "gate7"
    )
    root.mkdir(parents=True, exist_ok=True)
    runtime_manifest_path = root / "gate7_runtime_manifest.json"

    if resume_existing:
        reused = _reuse_runtime(runtime_manifest_path, p9_run_dir, gate6_runtime_path)
        if reused is not None:
            return reused

    registration_path = root / "g7_1" / "gate7_registration.json"
    registration = write_gate7_registration(
        p9_run_dir,
        gate6_runtime_path,
        registration_path,
    )

    provenance = build_gate7_provenance(
        p9_run_dir,
        registration["manifest_path"],
        root / "g7_2",
    )

    confidence = build_geometry_confidence(
        provenance["manifest_path"],
        root / "g7_2c",
    )

    free_evidence = build_free_space_evidence(
        confidence["manifest_path"],
        root / "g7_3" / "evidence",
    )
    free_constraints = classify_free_space(
        free_evidence["manifest_path"],
        root / "g7_3" / "constraints",
    )

    dataset_manifest = Path(str(registration["dataset_manifest_path"])).resolve()
    dataset_root = dataset_manifest.parent
    delaunay_comparison_path = dataset_root / "dense" / "free_space_meshing_comparison.json"
    delaunay_status: dict[str, Any]
    if run_delaunay:
        if delaunay_comparison_path.is_file():
            existing = _read_json(delaunay_comparison_path, "G7.3 Delaunay comparison")
            if existing.get("schema") == "ConceptGhost.P10FreeSpaceMeshingComparison.v0.1" and existing.get("status") == "PASS":
                delaunay_status = existing
                delaunay_status["resumed"] = True
            else:
                raise ContractError("Existing Delaunay comparison is not a valid Gate 7.3 artifact")
        else:
            delaunay_status = run_delaunay_visibility_meshing(
                dataset_root,
                colmap_executable=colmap_executable,
                overwrite_output=False,
            )
    else:
        delaunay_status = {
            "status": "SKIPPED",
            "reason": "run_delaunay=false",
            "automatic_winner": None,
            "official_geometry_changed": False,
            "ready_for_destructive_fusion": False,
        }

    free_confidence = build_confidence_free_space_overlay(
        confidence["manifest_path"],
        free_constraints["manifest_path"],
        root / "g7_3" / "confidence_overlay",
    )

    fusion = build_protected_fusion_candidate(
        p9_run_dir,
        registration["manifest_path"],
        free_confidence["manifest_path"],
        free_constraints["manifest_path"],
        root / "g7_4",
    )

    review = build_gate7_visual_review(
        fusion["manifest_path"],
        root / "g7_5",
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "mode": "G7_1_TO_G7_5_RUNTIME_NO_GATE8_PROMOTION",
        "scene_contract_id": registration.get("scene_contract_id"),
        "p9_run_id": registration.get("p9_run_id"),
        "p10_attempt_id": registration.get("p10_attempt_id"),
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_root": str(attempt_root),
        "gate6_runtime_manifest_path": str(gate6_runtime_path),
        "gate7_root": str(root),
        "artifacts": {
            "registration_manifest_path": registration["manifest_path"],
            "provenance_manifest_path": provenance["manifest_path"],
            "confidence_manifest_path": confidence["manifest_path"],
            "free_space_evidence_manifest_path": free_evidence["manifest_path"],
            "free_space_constraints_manifest_path": free_constraints["manifest_path"],
            "delaunay_comparison_path": str(delaunay_comparison_path) if delaunay_comparison_path.is_file() else None,
            "confidence_free_space_overlay_manifest_path": free_confidence["manifest_path"],
            "protected_fusion_manifest_path": fusion["manifest_path"],
            "visual_review_manifest_path": review["manifest_path"],
            "protected_fusion_candidate_ply_path": fusion["candidate_ply_path"],
            "visual_review_png_path": review["preview_png_path"],
        },
        "delaunay": {
            "requested": bool(run_delaunay),
            "status": delaunay_status.get("status"),
            "comparison_path": str(delaunay_comparison_path) if delaunay_comparison_path.is_file() else None,
        },
        "authority": {
            "p9_changed": False,
            "official_geometry_changed": False,
            "candidate_is_official_geometry": False,
            "gate8_promotion": False,
        },
        "ready_for_visual_evidence_pack": True,
        "ready_for_gate7_6_runtime_closeout": False,
        "ready_for_gate8": False,
        "promotion_blockers": [
            "VISUAL_EVIDENCE_PACK_REQUIRED",
            "ARTIST_VISUAL_REVIEW_REQUIRED",
            "DR9R_R15_RUNTIME_UX_ACCEPTANCE_REQUIRED",
        ],
        "resumed": False,
    }
    runtime_manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result["manifest_path"] = str(runtime_manifest_path)
    return result
