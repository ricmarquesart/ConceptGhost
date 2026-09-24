from __future__ import annotations

import json
import math
from enum import IntEnum
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .dense_reconstruction import _sample_ply_points
from .p9_boundary import validate_official_run


_SCHEMA = "ConceptGhost.P10Gate7Provenance.v0.1"


class Gate7ProvenanceClass(IntEnum):
    P9_SOURCE_PROTECTED = 1
    P9_RETAINED = 2
    P10_MULTIVIEW_SUPPORTED = 3
    P10_GENERATED_ONLY = 4
    UNKNOWN = 5
    CONFLICT = 6


_CLASS_NAMES = {int(item): item.name for item in Gate7ProvenanceClass}
_IDENTITY = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7 provenance diagnostics require NumPy") from error
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


def _matrix4(value: Any, label: str) -> tuple[tuple[float, ...], ...]:
    try:
        rows = tuple(tuple(float(v) for v in row) for row in value)
    except Exception as error:
        raise ContractError(f"{label} must be a numeric 4x4 matrix") from error
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ContractError(f"{label} must be 4x4")
    if not all(math.isfinite(v) for row in rows for v in row):
        raise ContractError(f"{label} contains non-finite values")
    return rows


def _identity_registration(registration: dict[str, Any]) -> None:
    if registration.get("schema") != "ConceptGhost.P10Gate7Registration.v0.1":
        raise ContractError("Gate 7.2 requires Gate 7.1 registration schema v0.1")
    if registration.get("status") != "PASS":
        raise ContractError("Gate 7.2 requires Gate 7.1 status PASS")
    if registration.get("registration_policy") != "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION":
        raise ContractError("Gate 7.2 requires known-camera P9-world registration")
    if registration.get("sim3_refit_allowed") is not False:
        raise ContractError("Gate 7.2 refuses a registration that allows Sim(3) refit")
    if registration.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7.2 refuses changed P9 authority")
    if registration.get("ready_for_gate7_2") is not True:
        raise ContractError("Gate 7.1 did not promote this attempt to Gate 7.2")
    transform = _matrix4(registration.get("transform_p10_to_p9"), "transform_p10_to_p9")
    if transform != _IDENTITY:
        raise ContractError("Gate 7.2 first-pass provenance requires identity P10->P9 transform")
    if float(registration.get("scale", 0.0)) != 1.0:
        raise ContractError("Gate 7.2 refuses non-unit P10->P9 scale")


def _sample_primary_mesh(boundary, max_points: int, np):
    try:
        with np.load(boundary.primary_mesh, allow_pickle=False) as payload:
            if "vertices" not in payload.files:
                raise ContractError("PrimaryMesh NPZ is missing vertices")
            vertices = np.asarray(payload["vertices"], dtype=np.float64)
            if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.shape[0] < 1:
                raise ContractError("PrimaryMesh vertices must have shape [N,3]")
            if not np.isfinite(vertices).all():
                raise ContractError("PrimaryMesh vertices contain non-finite values")
            source_correspondence = None
            if "grid_xy" in payload.files:
                candidate = np.asarray(payload["grid_xy"])
                if candidate.shape == (vertices.shape[0], 2):
                    source_correspondence = np.isfinite(candidate.astype(np.float64)).all(axis=1)
            elif "source_uv" in payload.files:
                candidate = np.asarray(payload["source_uv"], dtype=np.float64)
                if candidate.shape == (vertices.shape[0], 2):
                    source_correspondence = np.isfinite(candidate).all(axis=1)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh provenance evidence: {error}") from error

    stride = max(1, math.ceil(vertices.shape[0] / max_points))
    indices = np.arange(0, vertices.shape[0], stride, dtype=np.int64)[:max_points]
    sampled = vertices[indices]
    if source_correspondence is None:
        labels = np.full(
            len(indices),
            int(Gate7ProvenanceClass.P9_RETAINED),
            dtype=np.uint8,
        )
        source_supported = np.zeros(len(indices), dtype=np.uint8)
    else:
        supported = source_correspondence[indices]
        labels = np.where(
            supported,
            int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED),
            int(Gate7ProvenanceClass.P9_RETAINED),
        ).astype(np.uint8)
        source_supported = supported.astype(np.uint8)
    return int(vertices.shape[0]), indices, sampled, labels, source_supported


def _sample_prefusion_mesh(path: Path, max_points: int, np):
    total, rows = _sample_ply_points(path, max_points)
    if total <= 0 or not rows:
        raise ContractError("Gate 7.2 requires a non-empty P10 pre-fusion mesh")
    points = np.asarray([(row[0], row[1], row[2]) for row in rows], dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ContractError("P10 pre-fusion mesh sample is invalid")
    return int(total), points


def _dataset_image_missions(dataset: dict[str, Any]) -> dict[int, str]:
    frames = dataset.get("frames")
    if not isinstance(frames, list):
        return {}
    result: dict[int, str] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        image_id = frame.get("image_id")
        mission = str(frame.get("path_name") or "").strip()
        if type(image_id) is int and image_id > 0 and mission:
            result[image_id] = mission
    return result


def _sparse_support(dataset_root: Path, max_points: int, np):
    dataset = _read_json(dataset_root / "dataset_manifest.json", "Gate 6 dataset manifest")
    image_missions = _dataset_image_missions(dataset)
    points_path = dataset_root / "sparse" / "triangulated_txt" / "points3D.txt"
    if not points_path.is_file():
        return dataset, np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int16)

    parsed = []
    with points_path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                xyz = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError:
                continue
            track_tokens = parts[8:]
            image_ids = []
            for index in range(0, len(track_tokens) - 1, 2):
                try:
                    image_ids.append(int(track_tokens[index]))
                except ValueError:
                    continue
            missions = {image_missions[item] for item in image_ids if item in image_missions}
            parsed.append((xyz, len(image_ids), len(missions)))

    if not parsed:
        return dataset, np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int16)

    stride = max(1, math.ceil(len(parsed) / max_points))
    sampled = parsed[::stride][:max_points]
    points = np.asarray([row[0] for row in sampled], dtype=np.float64)
    tracks = np.asarray([row[1] for row in sampled], dtype=np.int32)
    missions = np.asarray([row[2] for row in sampled], dtype=np.int16)
    return dataset, points, tracks, missions


def _nearest(query, reference, np, *, chunk: int = 256):
    if len(query) == 0:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64)
    if len(reference) == 0:
        return (
            np.full(len(query), np.inf, dtype=np.float64),
            np.full(len(query), -1, dtype=np.int64),
        )
    distances = np.empty(len(query), dtype=np.float64)
    indices = np.empty(len(query), dtype=np.int64)
    for start in range(0, len(query), chunk):
        stop = min(len(query), start + chunk)
        delta = query[start:stop, None, :] - reference[None, :, :]
        d2 = np.einsum("qri,qri->qr", delta, delta)
        local = np.argmin(d2, axis=1)
        distances[start:stop] = np.sqrt(d2[np.arange(stop - start), local])
        indices[start:stop] = local
    return distances, indices


def _scene_diagonal(points, np) -> float:
    lo = np.min(points, axis=0)
    hi = np.max(points, axis=0)
    diagonal = float(np.linalg.norm(hi - lo))
    if not math.isfinite(diagonal) or diagonal <= 1.0e-9:
        return 1.0
    return diagonal


def _summary(labels, np) -> dict[str, dict[str, float | int]]:
    result = {}
    total = max(1, int(len(labels)))
    for value, name in _CLASS_NAMES.items():
        count = int(np.count_nonzero(labels == value))
        result[name] = {
            "count": count,
            "fraction": count / float(total),
        }
    return result


def build_gate7_provenance(
    p9_run_dir: str | Path,
    registration_manifest_path: str | Path,
    output_root: str | Path,
    *,
    max_p9_points: int = 12000,
    max_p10_points: int = 12000,
    max_sparse_points: int = 16000,
    source_match_fraction: float = 0.003,
    conflict_band_fraction: float = 0.02,
    sparse_support_fraction: float = 0.012,
) -> dict[str, Any]:
    """Build diagnostic-only Gate 7.2 provenance evidence.

    This first-pass classifier never edits geometry. It separates immutable P9
    source authority from registered P10 evidence and deliberately fails
    conservatively when independent multiview support cannot be established.
    """

    for name, value in (
        ("max_p9_points", max_p9_points),
        ("max_p10_points", max_p10_points),
        ("max_sparse_points", max_sparse_points),
    ):
        if type(value) is not int or value < 1:
            raise ContractError(f"{name} must be a positive integer")
    for name, value in (
        ("source_match_fraction", source_match_fraction),
        ("conflict_band_fraction", conflict_band_fraction),
        ("sparse_support_fraction", sparse_support_fraction),
    ):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ContractError(f"{name} must be finite and positive")
    if conflict_band_fraction <= source_match_fraction:
        raise ContractError("conflict_band_fraction must be greater than source_match_fraction")

    np = _lazy_numpy()
    boundary = validate_official_run(p9_run_dir)
    registration_path = Path(registration_manifest_path).resolve()
    registration = _read_json(registration_path, "Gate 7.1 registration manifest")
    _identity_registration(registration)

    if str(registration.get("p9_run_id") or "") != boundary.run_id:
        raise ContractError("Gate 7.2 registration P9 run does not match authoritative P9")
    if str(registration.get("scene_contract_id") or "") != boundary.scene_contract_id:
        raise ContractError("Gate 7.2 registration Scene Contract does not match authoritative P9")
    if Path(str(registration.get("p9_run_dir") or "")).resolve() != boundary.root:
        raise ContractError("Gate 7.2 registration P9 path does not match authoritative P9")

    mesh_path = Path(str(registration.get("pre_fusion_mesh_path") or "")).resolve()
    if not mesh_path.is_file():
        raise ContractError(f"Gate 7.2 pre-fusion mesh is missing: {mesh_path}")
    dataset_manifest_path = Path(str(registration.get("dataset_manifest_path") or "")).resolve()
    dataset_root = dataset_manifest_path.parent
    if not dataset_manifest_path.is_file():
        raise ContractError("Gate 7.2 dataset manifest is missing")

    p9_total, p9_indices, p9_points, p9_labels, p9_source_supported = _sample_primary_mesh(
        boundary, max_p9_points, np
    )
    p10_total, p10_points = _sample_prefusion_mesh(mesh_path, max_p10_points, np)
    dataset, sparse_points, sparse_tracks, sparse_missions = _sparse_support(
        dataset_root, max_sparse_points, np
    )

    if str(dataset.get("scene_contract_id") or "") != boundary.scene_contract_id:
        raise ContractError("Gate 7.2 dataset Scene Contract does not match P9")
    if dataset.get("camera_authority") != "P9_BASELINE_WORLD_DERIVED":
        raise ContractError("Gate 7.2 requires P9-derived Gate 6 cameras")

    scene_diagonal = _scene_diagonal(p9_points, np)
    source_match_m = max(scene_diagonal * float(source_match_fraction), 1.0e-5)
    conflict_band_m = max(scene_diagonal * float(conflict_band_fraction), source_match_m * 1.01)
    sparse_support_m = max(scene_diagonal * float(sparse_support_fraction), source_match_m)

    p9_distance, _ = _nearest(p10_points, p9_points, np)
    sparse_distance, sparse_index = _nearest(p10_points, sparse_points, np)
    track_support = np.zeros(len(p10_points), dtype=np.int32)
    mission_support = np.zeros(len(p10_points), dtype=np.int16)
    valid_sparse = sparse_index >= 0
    if len(sparse_points) and np.any(valid_sparse):
        selected = sparse_index[valid_sparse]
        track_support[valid_sparse] = sparse_tracks[selected]
        mission_support[valid_sparse] = sparse_missions[selected]

    strong_multiview = (
        (sparse_distance <= sparse_support_m)
        & (track_support >= 2)
        & (mission_support >= 2)
    )

    p10_labels = np.full(
        len(p10_points),
        int(Gate7ProvenanceClass.UNKNOWN),
        dtype=np.uint8,
    )
    source_match = p9_distance <= source_match_m
    conflict = (
        (~source_match)
        & (p9_distance <= conflict_band_m)
        & strong_multiview
    )
    multiview = (
        (~source_match)
        & (~conflict)
        & strong_multiview
    )
    generated_only = (
        (~source_match)
        & (~conflict)
        & (~multiview)
        & (p9_distance > conflict_band_m)
    )

    p10_labels[source_match] = int(Gate7ProvenanceClass.P9_RETAINED)
    p10_labels[conflict] = int(Gate7ProvenanceClass.CONFLICT)
    p10_labels[multiview] = int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED)
    p10_labels[generated_only] = int(Gate7ProvenanceClass.P10_GENERATED_ONLY)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_path = output_root / "gate7_provenance_evidence.npz"
    np.savez_compressed(
        evidence_path,
        p9_sample_indices=p9_indices,
        p9_points=p9_points.astype(np.float32),
        p9_labels=p9_labels,
        p9_source_supported=p9_source_supported,
        p10_points=p10_points.astype(np.float32),
        p10_labels=p10_labels,
        p10_nearest_p9_distance_m=p9_distance.astype(np.float32),
        p10_nearest_sparse_distance_m=sparse_distance.astype(np.float32),
        p10_sparse_track_support=track_support,
        p10_sparse_independent_mission_support=mission_support,
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.2",
        "mode": "DIAGNOSTIC_ONLY_NO_GEOMETRY_MUTATION",
        "p9_authority": "P9_ACCEPTED_IMMUTABLE_UPSTREAM",
        "p9_authority_changed": False,
        "official_geometry_changed": False,
        "registration_manifest_path": str(registration_path),
        "scene_contract_id": boundary.scene_contract_id,
        "p9_run_id": boundary.run_id,
        "p10_attempt_id": registration.get("p10_attempt_id"),
        "coordinate_space": "P9_CANONICAL_WORLD_METERS",
        "registration_policy": registration.get("registration_policy"),
        "class_ids": {name: value for value, name in _CLASS_NAMES.items()},
        "classification_policy": {
            "p9_source_protected": (
                "P9 sampled vertex has explicit grid_xy/source_uv source correspondence"
            ),
            "p9_retained": (
                "P9 sample without explicit source correspondence, or P10 sample within "
                "the source-match band where immutable P9 remains the final authority"
            ),
            "p10_multiview_supported": (
                "P10 sample is near a triangulated sparse point observed by at least "
                "two images from at least two independent authored missions"
            ),
            "p10_generated_only": (
                "CONSERVATIVE_CANDIDATE: P10 sample is outside the P9 conflict band and "
                "lacks independent multi-mission sparse support; this label is diagnostic "
                "and cannot authorize deletion or replacement by itself"
            ),
            "conflict": (
                "P10 sample has independent multi-mission support but lies outside the "
                "tight P9 source-match band while remaining inside the P9 conflict band"
            ),
            "unknown": "Evidence is insufficient for a stronger class",
        },
        "thresholds": {
            "scene_diagonal_m": scene_diagonal,
            "source_match_m": source_match_m,
            "conflict_band_m": conflict_band_m,
            "sparse_support_m": sparse_support_m,
            "source_match_fraction": float(source_match_fraction),
            "conflict_band_fraction": float(conflict_band_fraction),
            "sparse_support_fraction": float(sparse_support_fraction),
        },
        "sampling": {
            "p9_total_vertices": p9_total,
            "p9_sampled_vertices": int(len(p9_points)),
            "p10_total_vertices": p10_total,
            "p10_sampled_vertices": int(len(p10_points)),
            "sparse_sampled_points": int(len(sparse_points)),
            "diagnostic_sampling_only": True,
        },
        "p9_summary": _summary(p9_labels, np),
        "p10_summary": _summary(p10_labels, np),
        "evidence_npz_path": str(evidence_path),
        "ready_for_gate7_2c": True,
        "ready_for_destructive_fusion": False,
        "next_required": [
            "G7.2C_GEOMETRY_CONFIDENCE",
            "G7.3_FREE_SPACE_NO_FILL",
            "G7.4_PROTECTED_FUSION_CANDIDATE",
        ],
    }
    manifest_path = output_root / "gate7_provenance.json"
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result["manifest_path"] = str(manifest_path)
    return result


def write_gate7_provenance(
    p9_run_dir: str | Path,
    registration_manifest_path: str | Path,
    output_root: str | Path,
    **kwargs,
) -> dict[str, Any]:
    return build_gate7_provenance(
        p9_run_dir,
        registration_manifest_path,
        output_root,
        **kwargs,
    )
