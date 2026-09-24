from __future__ import annotations

import json
import math
from enum import IntEnum
from pathlib import Path
from typing import Any

from .contracts import ContractError


_SCHEMA = "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1"


class FreeSpaceState(IntEnum):
    UNKNOWN = 0
    OCCUPIED = 1
    CONFIRMED_FREE = 2
    CONFLICT = 3


_STATE_NAMES = {int(v): v.name for v in FreeSpaceState}


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7.3 free-space classification requires NumPy") from error
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


def _write_proxy(path: Path, centers, states, free_votes, occupied_votes):
    colors = {
        int(FreeSpaceState.OCCUPIED): (235, 235, 235),
        int(FreeSpaceState.CONFIRMED_FREE): (40, 220, 210),
        int(FreeSpaceState.CONFLICT): (230, 55, 220),
    }
    visible = [i for i, state in enumerate(states) if int(state) != int(FreeSpaceState.UNKNOWN)]
    lines = [
        "ply",
        "format ascii 1.0",
        "comment ConceptGhost Gate 7.3 diagnostic-only free-space proxy",
        f"element vertex {len(visible)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "property uchar free_space_state",
        "property ushort free_votes",
        "property ushort occupied_votes",
        "end_header",
    ]
    for index in visible:
        point = centers[index]
        state = int(states[index])
        r, g, b = colors[state]
        lines.append(
            f"{float(point[0]):.9g} {float(point[1]):.9g} {float(point[2]):.9g} "
            f"{r} {g} {b} {state} {int(free_votes[index])} {int(occupied_votes[index])}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def classify_free_space(
    evidence_manifest_path: str | Path,
    output_root: str | Path,
    *,
    min_free_views: int = 3,
    min_free_routes: int = 2,
    min_free_angle_deg: float = 5.0,
    min_free_ratio: float = 0.80,
    min_occupied_views: int = 2,
    conflict_min_free_views: int = 2,
    conflict_min_occupied_views: int = 1,
) -> dict[str, Any]:
    np = _lazy_numpy()
    manifest_path = Path(evidence_manifest_path).resolve()
    evidence = _read_json(manifest_path, "Gate 7.3 free-space evidence manifest")
    if evidence.get("schema") != "ConceptGhost.P10Gate7FreeSpaceEvidence.v0.1":
        raise ContractError("Gate 7.3 classifier requires free-space evidence schema v0.1")
    if evidence.get("status") != "PASS":
        raise ContractError("Gate 7.3 classifier requires evidence status PASS")
    if evidence.get("official_geometry_changed") is not False:
        raise ContractError("Gate 7.3 classifier refuses mutated geometry input")
    if evidence.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7.3 classifier refuses changed P9 authority")
    if evidence.get("ready_for_free_space_classification") is not True:
        raise ContractError("Free-space evidence did not promote to classification")

    for name, value in (
        ("min_free_views", min_free_views),
        ("min_free_routes", min_free_routes),
        ("min_occupied_views", min_occupied_views),
        ("conflict_min_free_views", conflict_min_free_views),
        ("conflict_min_occupied_views", conflict_min_occupied_views),
    ):
        if type(value) is not int or value < 1:
            raise ContractError(f"{name} must be a positive integer")
    if not math.isfinite(float(min_free_angle_deg)) or min_free_angle_deg < 0:
        raise ContractError("min_free_angle_deg must be finite and nonnegative")
    if not math.isfinite(float(min_free_ratio)) or not 0.5 < float(min_free_ratio) <= 1.0:
        raise ContractError("min_free_ratio must be in (0.5,1]")

    raw_path = Path(str(evidence.get("evidence_npz_path") or "")).resolve()
    if not raw_path.is_file():
        raise ContractError("Gate 7.3 raw free-space NPZ is missing")
    with np.load(raw_path, allow_pickle=False) as raw:
        required = {
            "voxel_keys",
            "voxel_centers",
            "free_effective_votes",
            "occupied_effective_votes",
            "free_route_count",
            "free_max_cross_route_angle_deg",
            "p9_source_protected",
        }
        missing = required.difference(raw.files)
        if missing:
            raise ContractError(f"Free-space raw evidence missing arrays: {sorted(missing)}")
        keys = np.asarray(raw["voxel_keys"], dtype=np.int32)
        centers = np.asarray(raw["voxel_centers"], dtype=np.float64)
        free_votes = np.asarray(raw["free_effective_votes"], dtype=np.int32)
        occupied_votes = np.asarray(raw["occupied_effective_votes"], dtype=np.int32)
        free_routes = np.asarray(raw["free_route_count"], dtype=np.int16)
        free_angle = np.asarray(raw["free_max_cross_route_angle_deg"], dtype=np.float32)
        protected = np.asarray(raw["p9_source_protected"], dtype=np.uint8)

    n = len(keys)
    if not (
        centers.shape == (n, 3)
        and len(free_votes) == n
        and len(occupied_votes) == n
        and len(free_routes) == n
        and len(free_angle) == n
        and len(protected) == n
    ):
        raise ContractError("Free-space evidence arrays do not align")

    total_votes = free_votes + occupied_votes
    free_ratio = np.divide(
        free_votes,
        np.maximum(total_votes, 1),
        dtype=np.float64,
    )
    states = np.full(n, int(FreeSpaceState.UNKNOWN), dtype=np.uint8)

    occupied = (occupied_votes >= min_occupied_views) | (protected > 0)
    free_candidate = (
        (free_votes >= min_free_views)
        & (free_routes >= min_free_routes)
        & (free_angle >= float(min_free_angle_deg))
        & (free_ratio >= float(min_free_ratio))
        & (protected == 0)
    )
    conflict = (
        (free_votes >= conflict_min_free_views)
        & (occupied_votes >= conflict_min_occupied_views)
        & (protected == 0)
        & (~free_candidate)
    )

    states[occupied] = int(FreeSpaceState.OCCUPIED)
    states[free_candidate & (~occupied)] = int(FreeSpaceState.CONFIRMED_FREE)
    states[conflict] = int(FreeSpaceState.CONFLICT)
    # Source-protected P9 always remains OCCUPIED even if generated evidence disagrees.
    states[protected > 0] = int(FreeSpaceState.OCCUPIED)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    classified_path = output_root / "free_space_constraints.npz"
    np.savez_compressed(
        classified_path,
        voxel_keys=keys,
        voxel_centers=centers.astype(np.float32),
        state=states,
        free_effective_votes=free_votes,
        occupied_effective_votes=occupied_votes,
        free_ratio=free_ratio.astype(np.float32),
        free_route_count=free_routes,
        free_max_cross_route_angle_deg=free_angle,
        p9_source_protected=protected,
    )

    proxy_path = output_root / "free_space_preview_points.ply"
    _write_proxy(proxy_path, centers, states, free_votes, occupied_votes)

    counts = {}
    for value, name in _STATE_NAMES.items():
        count = int(np.count_nonzero(states == value))
        counts[name] = {"count": count, "fraction": count / float(max(1, n))}

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.3B",
        "mode": "NO_FILL_CONSTRAINT_CLASSIFICATION_ONLY",
        "scene_contract_id": evidence.get("scene_contract_id"),
        "p9_run_id": evidence.get("p9_run_id"),
        "p10_attempt_id": evidence.get("p10_attempt_id"),
        "coordinate_space": evidence.get("coordinate_space"),
        "state_ids": {name: value for value, name in _STATE_NAMES.items()},
        "voxel": evidence.get("voxel"),
        "thresholds": {
            "confirmed_free_min_effective_views": min_free_views,
            "confirmed_free_min_routes": min_free_routes,
            "confirmed_free_min_cross_route_angle_deg": float(min_free_angle_deg),
            "confirmed_free_min_free_ratio": float(min_free_ratio),
            "occupied_min_effective_views": min_occupied_views,
            "conflict_min_free_views": conflict_min_free_views,
            "conflict_min_occupied_views": conflict_min_occupied_views,
        },
        "authority_rules": {
            "CONFIRMED_FREE": "NO_FILL_NO_BRIDGE_CONSTRAINT",
            "UNKNOWN": "NOT_FREE_NOT_OCCUPIED_NO_AUTOMATIC_ACTION",
            "CONFLICT": "DIAGNOSTIC_REPAIR_CANDIDATE_NO_AUTOMATIC_DELETE_OR_FILL",
            "P9_SOURCE_PROTECTED": "FORCED_OCCUPIED_HIGHEST_AUTHORITY",
            "behind_first_surface": "UNKNOWN",
        },
        "summary": counts,
        "constraints_npz_path": str(classified_path),
        "preview_ply_path": str(proxy_path),
        "preview_role": "COMFYUI_DIAGNOSTIC_ONLY_NEVER_MAYA_EXPORT",
        "source_evidence_manifest_path": str(manifest_path),
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "ready_for_gate7_4": True,
        "ready_for_destructive_fusion": False,
        "next_required": ["G7.4_PROTECTED_FUSION_CANDIDATE"],
    }
    out = output_root / "free_space_constraints_manifest.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(out)
    return result
