from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .free_space_constraints import FreeSpaceState


_SCHEMA = "ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1"


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7.3 confidence/free-space overlay requires NumPy") from error
    return np


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _voxel_key(point, voxel_size: float) -> tuple[int, int, int]:
    return tuple(int(math.floor(float(v) / voxel_size)) for v in point)


def build_confidence_free_space_overlay(
    confidence_manifest_path: str | Path,
    free_space_constraints_manifest_path: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    """Couple G7.3 FREE/CONFLICT evidence back into confidence diagnostics.

    This overlay remains analysis-only: it does not move/delete faces and does
    not enable geometry_confidence_refine.
    """

    np = _lazy_numpy()
    confidence_path = Path(confidence_manifest_path).resolve()
    constraints_path = Path(free_space_constraints_manifest_path).resolve()
    confidence = _read_json(confidence_path, "Gate 7.2C confidence manifest")
    constraints = _read_json(constraints_path, "Gate 7.3 constraints manifest")

    if confidence.get("schema") != "ConceptGhost.P10Gate7GeometryConfidence.v0.1":
        raise ContractError("Free-space confidence overlay requires Gate 7.2C schema v0.1")
    if constraints.get("schema") != "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1":
        raise ContractError("Free-space confidence overlay requires Gate 7.3 constraints schema v0.1")
    for field in ("scene_contract_id", "p9_run_id", "p10_attempt_id"):
        if str(confidence.get(field) or "") != str(constraints.get(field) or ""):
            raise ContractError(f"Confidence/free-space identity mismatch for {field}")
    if confidence.get("geometry_confidence_refine") is not False:
        raise ContractError("Free-space overlay requires confidence refinement OFF")
    if constraints.get("ready_for_destructive_fusion") is not False:
        raise ContractError("Free-space overlay refuses already-destructive constraints")

    voxel = constraints.get("voxel") if isinstance(constraints.get("voxel"), dict) else {}
    voxel_size = float(voxel.get("voxel_size_m") or 0.0)
    if not math.isfinite(voxel_size) or voxel_size <= 0.0:
        raise ContractError("Free-space constraints are missing voxel_size_m")

    confidence_evidence = Path(str(confidence.get("evidence_npz_path") or "")).resolve()
    constraints_evidence = Path(str(constraints.get("constraints_npz_path") or "")).resolve()
    if not confidence_evidence.is_file() or not constraints_evidence.is_file():
        raise ContractError("Confidence/free-space overlay evidence files are missing")

    with np.load(confidence_evidence, allow_pickle=False) as conf:
        required = {
            "p9_points", "p9_provenance_labels", "p9_confidence", "p9_confidence_class",
            "p10_points", "p10_provenance_labels", "p10_confidence", "p10_confidence_class",
        }
        missing = required.difference(conf.files)
        if missing:
            raise ContractError(f"Confidence evidence missing arrays: {sorted(missing)}")
        p9_points = np.asarray(conf["p9_points"], dtype=np.float32)
        p9_provenance = np.asarray(conf["p9_provenance_labels"], dtype=np.uint8)
        p9_confidence = np.asarray(conf["p9_confidence"], dtype=np.float32)
        p9_class = np.asarray(conf["p9_confidence_class"], dtype=np.uint8)
        p10_points = np.asarray(conf["p10_points"], dtype=np.float32)
        p10_provenance = np.asarray(conf["p10_provenance_labels"], dtype=np.uint8)
        p10_confidence = np.asarray(conf["p10_confidence"], dtype=np.float32)
        p10_class = np.asarray(conf["p10_confidence_class"], dtype=np.uint8)

    with np.load(constraints_evidence, allow_pickle=False) as free:
        keys = np.asarray(free["voxel_keys"], dtype=np.int32)
        states = np.asarray(free["state"], dtype=np.uint8)
    if len(keys) != len(states):
        raise ContractError("Free-space constraint key/state arrays do not align")

    state_by_key = {tuple(int(v) for v in key): int(state) for key, state in zip(keys, states)}
    p10_state = np.asarray(
        [state_by_key.get(_voxel_key(point, voxel_size), int(FreeSpaceState.UNKNOWN)) for point in p10_points],
        dtype=np.uint8,
    )
    adjusted = p10_confidence.copy()
    confirmed_free = p10_state == int(FreeSpaceState.CONFIRMED_FREE)
    conflict = p10_state == int(FreeSpaceState.CONFLICT)
    # UNKNOWN has no penalty. OCCUPIED does not receive an automatic boost here.
    adjusted[confirmed_free] = np.minimum(adjusted[confirmed_free], 0.05)
    adjusted[conflict] = np.minimum(adjusted[conflict], 0.18)

    thresholds = confidence.get("confidence_thresholds")
    if not isinstance(thresholds, dict):
        raise ContractError("Confidence manifest is missing thresholds")
    high = float(thresholds.get("HIGH") or 0.75)
    neutral = float(thresholds.get("NEUTRAL") or 0.40)
    low = float(thresholds.get("LOW") or 0.20)
    adjusted_class = np.zeros(len(adjusted), dtype=np.uint8)
    adjusted_class[adjusted >= low] = 1
    adjusted_class[adjusted >= neutral] = 2
    adjusted_class[adjusted >= high] = 3

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_out = output_root / "gate7_confidence_free_space_overlay.npz"
    np.savez_compressed(
        evidence_out,
        p9_points=p9_points,
        p9_provenance_labels=p9_provenance,
        p9_confidence=p9_confidence,
        p9_confidence_class=p9_class,
        p10_points=p10_points,
        p10_provenance_labels=p10_provenance,
        p10_confidence_before_free_space=p10_confidence,
        p10_confidence_after_free_space=adjusted,
        p10_confidence_class_after_free_space=adjusted_class,
        p10_free_space_state=p10_state,
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.3D",
        "mode": "CONFIDENCE_DIAGNOSTIC_OVERLAY_ONLY",
        "scene_contract_id": confidence.get("scene_contract_id"),
        "p9_run_id": confidence.get("p9_run_id"),
        "p10_attempt_id": confidence.get("p10_attempt_id"),
        "geometry_confidence_refine": False,
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "policy": {
            "CONFIRMED_FREE": "CAP_P10_CONFIDENCE_AT_0.05",
            "CONFLICT": "CAP_P10_CONFIDENCE_AT_0.18",
            "UNKNOWN": "NO_PENALTY",
            "OCCUPIED": "NO_AUTOMATIC_BOOST",
            "P9_CONFIDENCE": "UNCHANGED",
        },
        "counts": {
            "p10_points": int(len(p10_points)),
            "confirmed_free_hits": int(np.count_nonzero(confirmed_free)),
            "conflict_hits": int(np.count_nonzero(conflict)),
            "unknown_hits": int(np.count_nonzero(p10_state == int(FreeSpaceState.UNKNOWN))),
            "occupied_hits": int(np.count_nonzero(p10_state == int(FreeSpaceState.OCCUPIED))),
        },
        "evidence_npz_path": str(evidence_out),
        "source_confidence_manifest_path": str(confidence_path),
        "source_free_space_constraints_manifest_path": str(constraints_path),
        "ready_for_gate7_4": True,
        "ready_for_destructive_fusion": False,
    }
    out = output_root / "confidence_free_space_overlay_manifest.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(out)
    return result
