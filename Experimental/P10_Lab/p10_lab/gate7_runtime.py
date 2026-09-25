from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .dense_reconstruction import inspect_dense_geometric_evidence, repair_dense_geometric_evidence
from .free_space_confidence import build_confidence_free_space_overlay
from .free_space_constraints import classify_free_space
from .free_space_evidence import build_free_space_evidence
from .gate7_provenance import build_gate7_provenance
from .gate7_registration import write_gate7_registration
from .gate7_visual_review import build_gate7_visual_review
from .geometry_confidence import build_geometry_confidence
from .geometry_quality import write_gate6_geometry_quality
from .gate_output_contract import publish_gate7_output_tree
from .prefusion_mesh import run_delaunay_visibility_meshing, run_prefusion_meshing
from .protected_fusion import build_protected_fusion_candidate
from .reconstruction_runtime import resolve_colmap_executable
from .run_audit_bundle import build_partial_run_audit_bundle, build_run_audit_bundle


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


def _resolve_gate7_repair_colmap(
    dataset_root: Path,
    requested: str,
) -> str:
    """Resolve the exact installed COLMAP runtime for every Gate 7 native call.

    Gate 6 auto-discovers ConceptGhost's private COLMAP runtime, but the Gate 7
    UI historically converted an empty field to the bare token "colmap".
    On Windows that token is not on PATH, so Delaunay could fail with WinError 2
    even though Gate 6 had already used the installed runtime successfully.
    """

    dense_manifest_path = dataset_root / "dense_reconstruction_manifest.json"
    if dense_manifest_path.is_file():
        try:
            dense_manifest = _read_json(
                dense_manifest_path,
                "Gate 6 dense reconstruction manifest",
            )
        except ContractError:
            dense_manifest = {}
        stored = str(dense_manifest.get("colmap_executable") or "").strip()
        if stored and Path(stored).is_file():
            return str(Path(stored).resolve())

    requested = str(requested or "").strip()
    if requested and requested.lower() not in {"colmap", "colmap.exe"}:
        return resolve_colmap_executable(requested)

    # Empty/default "colmap" means AUTO, matching Gate 6 behavior:
    # env override -> ConceptGhost ThirdParty runtime -> PATH.
    return resolve_colmap_executable(None)


def _repair_gate6_dense_evidence_for_gate7(
    gate6: dict[str, Any],
    gate6_runtime_path: Path,
    *,
    colmap_executable: str,
) -> dict[str, Any]:
    """Repair incomplete geometric PatchMatch evidence in place before Gate 7.1.

    This preserves WAN, sparse known-camera registration, route authority and P9.
    Only the dense PatchMatch/fusion and derived pre-fusion mesh are refreshed.
    """

    dataset_value=str(gate6.get("dataset_root") or "").strip()
    if not dataset_value:
        raise ContractError("Gate 7 dense preflight cannot resolve Gate 6 dataset_root")
    dataset_root=Path(dataset_value).resolve()
    before=inspect_dense_geometric_evidence(
        dataset_root,
        min_coverage_ratio=0.70,
    )
    if before.get("gate7_geometric_evidence_ready") is True:
        return {
            "status":"REUSED",
            "before":before,
            "after":before,
            "p9_authority_changed":False,
            "sparse_rebuilt":False,
            "wan_rebuilt":False,
        }

    executable=_resolve_gate7_repair_colmap(dataset_root,colmap_executable)
    repair=repair_dense_geometric_evidence(
        dataset_root,
        colmap_executable=executable,
        min_coverage_ratio=0.70,
    )

    # fused.ply changed, therefore refresh the derived Poisson candidate used by
    # Gate 7 registration/fusion.  This is still P10 candidate geometry only.
    mesh=run_prefusion_meshing(
        dataset_root,
        colmap_executable=executable,
        overwrite_output=True,
    )

    # Any previous Delaunay comparison refers to the stale dense cloud.
    dense_root=dataset_root/"dense"
    for stale in (
        dense_root/"free_space_meshing_comparison.json",
        dense_root/"pre_fusion_mesh_delaunay.ply",
        dense_root/"pre_fusion_mesh_delaunay_preview.svg",
    ):
        if stale.is_file():
            stale.unlink()

    output_root_value=str(gate6.get("output_root") or "").strip()
    output_root=(
        Path(output_root_value).resolve()
        if output_root_value else gate6_runtime_path.parent.resolve()
    )
    quality=write_gate6_geometry_quality(
        dataset_root,
        output_root/"diagnostics"/"gate6_geometry_quality.json",
        expected_missions=tuple(str(name) for name in (gate6.get("mission_order") or [])),
        p9_roundtrip=(
            gate6.get("p9_roundtrip_audit")
            if isinstance(gate6.get("p9_roundtrip_audit"),dict) else None
        ),
        metric_overlay=(
            gate6.get("metric_overlay")
            if isinstance(gate6.get("metric_overlay"),dict) else None
        ),
    )

    stages=gate6.get("stages")
    if not isinstance(stages,dict):
        stages={}
        gate6["stages"]=stages
    stages["dense"]={
        "state":"REPAIRED_FOR_GATE7_GEOMETRIC_COVERAGE",
        "manifest_path":repair.get("dense_manifest_path"),
        "before":repair.get("before"),
        "after":repair.get("after"),
    }
    stages["mesh"]={
        "state":"REBUILT_AFTER_GATE7_DENSE_REPAIR",
        "manifest_path":str((dataset_root/"prefusion_mesh_manifest.json").resolve()),
    }
    stages["geometry_quality"]={
        "state":"REEVALUATED_AFTER_GATE7_DENSE_REPAIR",
        "status":quality.get("status"),
        "manifest_path":quality.get("manifest_path"),
        "alerts":quality.get("alerts",[]),
    }
    gate6["geometry_quality"]=quality
    gate6["geometry_quality_status"]=quality.get("status","FAIL")
    gate6["geometry_quality_manifest_path"]=quality.get("manifest_path")
    gate6["gate7_promotion_allowed"]=quality.get("status")!="FAIL"
    gate6["pre_fusion_mesh_path"]=str((dataset_root/"dense"/"pre_fusion_mesh.ply").resolve())
    gate6["mesh_preview_svg_path"]=str((dataset_root/"dense"/"pre_fusion_mesh_preview.svg").resolve())
    gate6["gate7_dense_evidence_repair"]={
        "status":repair.get("status"),
        "before":repair.get("before"),
        "after":repair.get("after"),
        "colmap_executable":executable,
        "p9_authority_changed":False,
        "official_geometry_changed":False,
        "sparse_rebuilt":False,
        "wan_rebuilt":False,
    }
    gate6_runtime_path.write_text(
        json.dumps(gate6,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    return {
        "status":"REPAIRED",
        "before":repair.get("before"),
        "after":repair.get("after"),
        "mesh_status":mesh.get("status"),
        "geometry_quality_status":quality.get("status"),
        "colmap_executable":executable,
        "p9_authority_changed":False,
        "sparse_rebuilt":False,
        "wan_rebuilt":False,
    }


def _write_failure_manifest(
    path: Path,
    *,
    stage: str,
    error: Exception,
    p9_run_dir: Path,
    gate6_runtime_path: Path,
    attempt_root: Path,
    gate6: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "ConceptGhost.P10Gate7Failure.v0.1",
        "status": "FAIL",
        "failed_stage": stage,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "exception_type": type(error).__name__,
        "exception_message": str(error),
        "traceback": traceback.format_exc(),
        "p9_run_id": gate6.get("run_id"),
        "p10_attempt_id": gate6.get("p10_attempt_id"),
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_root": str(attempt_root),
        "gate6_runtime_manifest_path": str(gate6_runtime_path),
        "p9_authority_changed": False,
        "official_geometry_changed": False,
        "gate8_promotion": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["manifest_path"] = str(path)
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

    Gate 7 always leaves a Drive-visible audit bundle. On success it creates an
    initial audit automatically; the terminal audit node later rebuilds the same
    bundle with the visual-evidence pack. On failure it writes a failure
    manifest and a PARTIAL_FAILURE audit before re-raising the original error.
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
            try:
                audit = build_run_audit_bundle(runtime_manifest_path)
                reused["auto_audit"] = {
                    "status": "PASS",
                    "bundle_path": audit["bundle_path"],
                    "manifest_path": audit["manifest_path"],
                    "storage": "P9_RUN_ROOT/RUN_AUDIT_BUNDLE.zip",
                }
            except Exception as audit_error:
                reused["auto_audit"] = {
                    "status": "WARN",
                    "error": f"{type(audit_error).__name__}: {audit_error}",
                }
            return reused

    current_stage = "G7_0_DENSE_GEOMETRIC_PREFLIGHT"
    try:
        dense_repair=_repair_gate6_dense_evidence_for_gate7(
            gate6,
            gate6_runtime_path,
            colmap_executable=colmap_executable,
        )

        current_stage = "G7_1_REGISTRATION"
        registration_path = root / "g7_1" / "gate7_registration.json"
        registration = write_gate7_registration(
            p9_run_dir,
            gate6_runtime_path,
            registration_path,
        )

        current_stage = "G7_2_PROVENANCE"
        provenance = build_gate7_provenance(
            p9_run_dir,
            registration["manifest_path"],
            root / "g7_2",
        )

        current_stage = "G7_2C_CONFIDENCE"
        confidence = build_geometry_confidence(
            provenance["manifest_path"],
            root / "g7_2c",
        )

        current_stage = "G7_3_FREE_SPACE_EVIDENCE"
        free_evidence = build_free_space_evidence(
            confidence["manifest_path"],
            root / "g7_3" / "evidence",
            min_frame_coverage_ratio=0.70,
            min_mission_coverage_ratio=0.70,
            min_per_mission_frame_ratio=0.70,
        )

        current_stage = "G7_3_FREE_SPACE_CONSTRAINTS"
        free_constraints = classify_free_space(
            free_evidence["manifest_path"],
            root / "g7_3" / "constraints",
        )

        dataset_manifest = Path(str(registration["dataset_manifest_path"])).resolve()
        dataset_root = dataset_manifest.parent
        delaunay_comparison_path = dataset_root / "dense" / "free_space_meshing_comparison.json"
        delaunay_status: dict[str, Any]
        current_stage = "G7_3_DELAUNAY_COMPARISON"
        if run_delaunay:
            if delaunay_comparison_path.is_file():
                existing = _read_json(delaunay_comparison_path, "G7.3 Delaunay comparison")
                if existing.get("schema") == "ConceptGhost.P10FreeSpaceMeshingComparison.v0.1" and existing.get("status") == "PASS":
                    delaunay_status = existing
                    delaunay_status["resumed"] = True
                else:
                    raise ContractError("Existing Delaunay comparison is not a valid Gate 7.3 artifact")
            else:
                delaunay_executable = _resolve_gate7_repair_colmap(
                    dataset_root,
                    colmap_executable,
                )
                delaunay_status = run_delaunay_visibility_meshing(
                    dataset_root,
                    colmap_executable=delaunay_executable,
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

        current_stage = "G7_3_CONFIDENCE_FREE_SPACE_OVERLAY"
        free_confidence = build_confidence_free_space_overlay(
            confidence["manifest_path"],
            free_constraints["manifest_path"],
            root / "g7_3" / "confidence_overlay",
        )

        current_stage = "G7_4_PROTECTED_FUSION"
        fusion = build_protected_fusion_candidate(
            p9_run_dir,
            registration["manifest_path"],
            free_confidence["manifest_path"],
            free_constraints["manifest_path"],
            root / "g7_4",
        )

        current_stage = "G7_5_VISUAL_REVIEW"
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
            "dense_geometric_preflight":dense_repair,
            "colmap_coverage_policy": {
                "view_selection": "REGISTERED_GEOMETRIC_INTERSECTION",
                "min_frame_coverage_ratio": 0.70,
                "min_mission_coverage_ratio": 0.70,
                "min_per_mission_frame_ratio": 0.70,
                "coverage_manifest_path": free_evidence["manifest_path"],
                "dense_repair_policy":"AUTO_REPAIR_EXPLICIT_REGISTERED_REFERENCES_IF_BELOW_70_PERCENT",
            },
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
                "GATE7_RUNTIME_ACCEPTANCE_REQUIRED",
                "DR9R_R15_RUNTIME_UX_ACCEPTANCE_REQUIRED",
            ],
            "resumed": False,
        }
        runtime_manifest_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result["manifest_path"] = str(runtime_manifest_path)

        current_stage = "G7_GATE_OUTPUT_CONTRACT"
        gate_output_contract = publish_gate7_output_tree(
            p9_run_dir,
            attempt_root,
            p10_attempt_id=str(registration.get("p10_attempt_id") or attempt_root.name),
        )
        result["gate_output_contract"] = gate_output_contract
        runtime_manifest_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        current_stage = "AUTO_RUN_AUDIT_BUNDLE"
        try:
            audit = build_run_audit_bundle(runtime_manifest_path)
            result["auto_audit"] = {
                "status": "PASS",
                "bundle_path": audit["bundle_path"],
                "manifest_path": audit["manifest_path"],
                "storage": "P9_RUN_ROOT/RUN_AUDIT_BUNDLE.zip",
                "terminal_node_will_rebuild_with_visual_pack": True,
            }
        except Exception as audit_error:
            result["auto_audit"] = {
                "status": "WARN",
                "error": f"{type(audit_error).__name__}: {audit_error}",
            }
        return result

    except Exception as error:
        failure_path = root / "gate7_failure_manifest.json"
        failure = _write_failure_manifest(
            failure_path,
            stage=current_stage,
            error=error,
            p9_run_dir=p9_run_dir,
            gate6_runtime_path=gate6_runtime_path,
            attempt_root=attempt_root,
            gate6=gate6,
        )
        audit_path = None
        audit_error_text = None
        try:
            audit = build_partial_run_audit_bundle(
                p9_run_dir,
                gate6_runtime_path,
                gate7_failure_manifest_path=failure_path,
            )
            audit_path = audit["bundle_path"]
            failure["auto_audit_bundle_path"] = audit_path
            failure["auto_audit_manifest_path"] = audit["manifest_path"]
        except Exception as audit_error:
            audit_error_text = f"{type(audit_error).__name__}: {audit_error}"
            failure["auto_audit_error"] = audit_error_text
        failure_path.write_text(json.dumps(failure, indent=2, sort_keys=True), encoding="utf-8")

        if isinstance(error, ContractError):
            suffix = (
                f"\nAutomatic RUN_AUDIT_BUNDLE: {audit_path}"
                if audit_path
                else f"\nAutomatic RUN_AUDIT_BUNDLE failed: {audit_error_text}"
            )
            raise ContractError(str(error) + suffix) from error
        raise
