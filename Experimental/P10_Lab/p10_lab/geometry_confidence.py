from __future__ import annotations

import json
import math
from enum import IntEnum
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .gate7_provenance import Gate7ProvenanceClass


_SCHEMA = "ConceptGhost.P10Gate7GeometryConfidence.v0.1"


class GeometryConfidenceClass(IntEnum):
    VERY_LOW = 0
    LOW = 1
    NEUTRAL = 2
    HIGH = 3


_CONFIDENCE_NAMES = {int(item): item.name for item in GeometryConfidenceClass}


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7.2C geometry confidence requires NumPy") from error
    return np


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object: {path}")
    return payload


def _validate_thresholds(high: float, neutral: float, low: float) -> tuple[float, float, float]:
    values = (float(high), float(neutral), float(low))
    if not all(math.isfinite(v) for v in values):
        raise ContractError("Geometry confidence thresholds must be finite")
    if not (0.0 < values[2] < values[1] < values[0] <= 1.0):
        raise ContractError("Require 0 < low < neutral < high <= 1")
    return values


def _classify(scores, *, high: float, neutral: float, low: float, np):
    classes = np.full(len(scores), int(GeometryConfidenceClass.VERY_LOW), dtype=np.uint8)
    classes[scores >= low] = int(GeometryConfidenceClass.LOW)
    classes[scores >= neutral] = int(GeometryConfidenceClass.NEUTRAL)
    classes[scores >= high] = int(GeometryConfidenceClass.HIGH)
    return classes


def _histogram(classes, scores, np) -> dict[str, dict[str, float | int]]:
    result = {}
    total = max(1, int(len(classes)))
    for value, name in _CONFIDENCE_NAMES.items():
        mask = classes == value
        count = int(np.count_nonzero(mask))
        result[name] = {
            "count": count,
            "fraction": count / float(total),
            "mean_confidence": float(np.mean(scores[mask])) if count else None,
        }
    return result


def _write_point_proxy(path: Path, p9_points, p9_scores, p9_classes, p9_provenance, p10_points, p10_scores, p10_classes, p10_provenance):
    color = {
        int(GeometryConfidenceClass.HIGH): (45, 110, 255),
        int(GeometryConfidenceClass.NEUTRAL): (175, 175, 175),
        int(GeometryConfidenceClass.LOW): (255, 100, 70),
        int(GeometryConfidenceClass.VERY_LOW): (200, 25, 25),
    }
    count = len(p9_points) + len(p10_points)
    lines = [
        "ply",
        "format ascii 1.0",
        "comment ConceptGhost Gate 7.2C diagnostic-only confidence point proxy",
        f"element vertex {count}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "property float confidence",
        "property uchar confidence_class",
        "property uchar provenance_class",
        "property uchar geometry_layer",
        "end_header",
    ]
    for points, scores, classes, provenance, layer in (
        (p9_points, p9_scores, p9_classes, p9_provenance, 1),
        (p10_points, p10_scores, p10_classes, p10_provenance, 2),
    ):
        for point, score, cls, prov in zip(points, scores, classes, provenance):
            r, g, b = color[int(cls)]
            lines.append(
                f"{float(point[0]):.9g} {float(point[1]):.9g} {float(point[2]):.9g} "
                f"{r} {g} {b} {float(score):.6f} {int(cls)} {int(prov)} {layer}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_geometry_confidence(
    provenance_manifest_path: str | Path,
    output_root: str | Path,
    *,
    high_threshold: float = 0.75,
    neutral_threshold: float = 0.40,
    low_threshold: float = 0.20,
) -> dict[str, Any]:
    """Compute Gate 7.2C confidence without modifying geometry.

    This first pass intentionally uses only evidence already available at G7.2.
    Free-space evidence is not guessed before G7.3; UNKNOWN alone never receives
    a negative free-space penalty.
    """

    high_threshold, neutral_threshold, low_threshold = _validate_thresholds(
        high_threshold,
        neutral_threshold,
        low_threshold,
    )
    np = _lazy_numpy()
    manifest_path = Path(provenance_manifest_path).resolve()
    provenance = _read_json(manifest_path, "Gate 7.2 provenance manifest")

    if provenance.get("schema") != "ConceptGhost.P10Gate7Provenance.v0.1":
        raise ContractError("Gate 7.2C requires Gate 7.2 provenance schema v0.1")
    if provenance.get("status") != "PASS":
        raise ContractError("Gate 7.2C requires provenance status PASS")
    if provenance.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7.2C refuses changed P9 authority")
    if provenance.get("official_geometry_changed") is not False:
        raise ContractError("Gate 7.2C input must be diagnostic-only")
    if provenance.get("ready_for_destructive_fusion") is not False:
        raise ContractError("Gate 7.2C refuses provenance that already permits destructive fusion")
    if provenance.get("ready_for_gate7_2c") is not True:
        raise ContractError("Gate 7.2 provenance did not promote to 7.2C")

    evidence_path = Path(str(provenance.get("evidence_npz_path") or "")).resolve()
    if not evidence_path.is_file():
        raise ContractError(f"Gate 7.2 provenance evidence NPZ is missing: {evidence_path}")

    with np.load(evidence_path, allow_pickle=False) as evidence:
        required = {
            "p9_points",
            "p9_labels",
            "p10_points",
            "p10_labels",
            "p10_nearest_sparse_distance_m",
            "p10_sparse_track_support",
            "p10_sparse_independent_mission_support",
        }
        missing = required.difference(evidence.files)
        if missing:
            raise ContractError(f"Gate 7.2 provenance evidence is missing arrays: {sorted(missing)}")
        p9_points = np.asarray(evidence["p9_points"], dtype=np.float64)
        p9_labels = np.asarray(evidence["p9_labels"], dtype=np.uint8)
        p10_points = np.asarray(evidence["p10_points"], dtype=np.float64)
        p10_labels = np.asarray(evidence["p10_labels"], dtype=np.uint8)
        p10_sparse_distance = np.asarray(evidence["p10_nearest_sparse_distance_m"], dtype=np.float64)
        p10_track_support = np.asarray(evidence["p10_sparse_track_support"], dtype=np.int32)
        p10_mission_support = np.asarray(
            evidence["p10_sparse_independent_mission_support"],
            dtype=np.int16,
        )

    if p9_points.ndim != 2 or p9_points.shape[1] != 3 or len(p9_points) != len(p9_labels):
        raise ContractError("Gate 7.2C P9 evidence shape mismatch")
    if p10_points.ndim != 2 or p10_points.shape[1] != 3 or len(p10_points) != len(p10_labels):
        raise ContractError("Gate 7.2C P10 evidence shape mismatch")
    if not (
        len(p10_points)
        == len(p10_sparse_distance)
        == len(p10_track_support)
        == len(p10_mission_support)
    ):
        raise ContractError("Gate 7.2C P10 support arrays do not align")

    thresholds = provenance.get("thresholds") if isinstance(provenance.get("thresholds"), dict) else {}
    sparse_support_m = float(thresholds.get("sparse_support_m") or 0.0)
    if not math.isfinite(sparse_support_m) or sparse_support_m <= 0.0:
        raise ContractError("Gate 7.2C requires positive sparse_support_m from provenance")

    p9_scores = np.full(len(p9_points), 0.62, dtype=np.float32)
    p9_scores[p9_labels == int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED)] = 0.95
    p9_scores[p9_labels == int(Gate7ProvenanceClass.P9_RETAINED)] = 0.62

    p10_scores = np.full(len(p10_points), 0.42, dtype=np.float32)
    retained = p10_labels == int(Gate7ProvenanceClass.P9_RETAINED)
    multiview = p10_labels == int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED)
    generated = p10_labels == int(Gate7ProvenanceClass.P10_GENERATED_ONLY)
    conflict = p10_labels == int(Gate7ProvenanceClass.CONFLICT)
    unknown = p10_labels == int(Gate7ProvenanceClass.UNKNOWN)

    p10_scores[retained] = 0.55
    p10_scores[generated] = 0.28
    p10_scores[conflict] = 0.12
    p10_scores[unknown] = 0.42

    if np.any(multiview):
        mission_boost = np.clip(p10_mission_support.astype(np.float32) - 1.0, 0.0, 3.0) * 0.07
        track_boost = np.clip(p10_track_support.astype(np.float32) - 2.0, 0.0, 5.0) * 0.015
        distance_ratio = np.clip(p10_sparse_distance / sparse_support_m, 0.0, 1.0).astype(np.float32)
        support_score = 0.70 + mission_boost + track_boost - 0.08 * distance_ratio
        p10_scores[multiview] = np.clip(support_score[multiview], 0.0, 0.92)

    p9_classes = _classify(
        p9_scores,
        high=high_threshold,
        neutral=neutral_threshold,
        low=low_threshold,
        np=np,
    )
    p10_classes = _classify(
        p10_scores,
        high=high_threshold,
        neutral=neutral_threshold,
        low=low_threshold,
        np=np,
    )

    virtual_hole_candidate = (
        (p10_classes == int(GeometryConfidenceClass.VERY_LOW))
        & (
            (p10_labels == int(Gate7ProvenanceClass.CONFLICT))
            | (p10_labels == int(Gate7ProvenanceClass.P10_GENERATED_ONLY))
            | (p10_labels == int(Gate7ProvenanceClass.UNKNOWN))
        )
    ).astype(np.uint8)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_out = output_root / "gate7_geometry_confidence_evidence.npz"
    np.savez_compressed(
        evidence_out,
        p9_points=p9_points.astype(np.float32),
        p9_provenance_labels=p9_labels,
        p9_confidence=p9_scores,
        p9_confidence_class=p9_classes,
        p10_points=p10_points.astype(np.float32),
        p10_provenance_labels=p10_labels,
        p10_confidence=p10_scores,
        p10_confidence_class=p10_classes,
        p10_confidence_virtual_hole_candidate=virtual_hole_candidate,
    )

    proxy_path = output_root / "gate7_geometry_confidence_points.ply"
    _write_point_proxy(
        proxy_path,
        p9_points,
        p9_scores,
        p9_classes,
        p9_labels,
        p10_points,
        p10_scores,
        p10_classes,
        p10_labels,
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.2C",
        "mode": "ANALYSIS_AND_VISUALIZATION_ONLY",
        "geometry_confidence_analysis": True,
        "show_geometry_confidence": True,
        "geometry_confidence_refine": False,
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "scene_contract_id": provenance.get("scene_contract_id"),
        "p9_run_id": provenance.get("p9_run_id"),
        "p10_attempt_id": provenance.get("p10_attempt_id"),
        "coordinate_space": provenance.get("coordinate_space"),
        "provenance_manifest_path": str(manifest_path),
        "confidence_thresholds": {
            "HIGH": high_threshold,
            "NEUTRAL": neutral_threshold,
            "LOW": low_threshold,
            "VERY_LOW": 0.0,
            "policy": "HIGH>=0.75; NEUTRAL>=0.40; LOW>=0.20; VERY_LOW<0.20 by default",
        },
        "scoring_policy": {
            "p9_source_protected_prior": 0.95,
            "p9_retained_prior": 0.62,
            "p10_p9_overlap_prior": 0.55,
            "p10_multiview_base": 0.70,
            "p10_generated_only_prior": 0.28,
            "unknown_prior": 0.42,
            "conflict_prior": 0.12,
            "multiview_terms": "independent mission count + track count - sparse support distance",
            "free_space_penalty": "NOT_APPLIED_G7_3_PENDING",
            "unknown_free_space_penalty": 0.0,
        },
        "p9_histogram": _histogram(p9_classes, p9_scores, np),
        "p10_histogram": _histogram(p10_classes, p10_scores, np),
        "virtual_hole_candidates": {
            "count": int(np.count_nonzero(virtual_hole_candidate)),
            "fraction_of_p10_sample": (
                int(np.count_nonzero(virtual_hole_candidate)) / float(max(1, len(p10_points)))
            ),
            "diagnostic_only": True,
            "physical_holes_not_inferred_here": True,
        },
        "evidence_npz_path": str(evidence_out),
        "confidence_proxy_ply_path": str(proxy_path),
        "confidence_proxy_role": "COMFYUI_DIAGNOSTIC_ONLY_NEVER_MAYA_EXPORT",
        "ready_for_gate7_3": True,
        "ready_for_destructive_fusion": False,
        "next_required": [
            "G7.3_FREE_SPACE_NO_FILL",
            "G7.4_PROTECTED_FUSION_CANDIDATE",
        ],
    }
    out = output_root / "geometry_confidence_manifest.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(out)
    return result
