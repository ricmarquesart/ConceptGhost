from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .free_space_constraints import FreeSpaceState
from .gate7_provenance import Gate7ProvenanceClass
from .p9_boundary import validate_official_run
from .prefusion_mesh import _read_mesh


_SCHEMA = "ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1"

_REASON = {
    "ACCEPTED_P10_MULTIVIEW": 0,
    "CONFIRMED_FREE_VETO": 1,
    "FREE_SPACE_CONFLICT": 2,
    "P9_SOURCE_PROTECTED_OVERLAP": 3,
    "INSUFFICIENT_PROVENANCE": 4,
    "LOW_CONFIDENCE": 5,
    "SUPPORT_DISTANCE": 6,
    "DELAUNAY_DISAGREEMENT": 7,
}


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7.4 protected fusion requires NumPy") from error
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


def _ply_mesh(path: Path, np):
    if not path.is_file():
        raise ContractError(f"Gate 7.4 mesh is missing: {path}")
    header, vertex_array, faces, invalid = _read_mesh(path, 2_000_000_000)
    if invalid:
        raise ContractError(f"Gate 7.4 mesh contains {invalid} invalid faces: {path}")
    vertices = np.asarray(vertex_array, dtype=np.float64).reshape((-1, 3))
    triangles = np.asarray(faces, dtype=np.int64)
    if triangles.shape != (header.face_count, 3):
        raise ContractError("Gate 7.4 requires all triangular faces, not a sampled mesh")
    if not np.isfinite(vertices).all():
        raise ContractError("Gate 7.4 mesh contains non-finite vertices")
    return vertices, triangles


def _primary_mesh(boundary, np):
    try:
        with np.load(boundary.primary_mesh, allow_pickle=False) as payload:
            if "vertices" not in payload.files or "faces" not in payload.files:
                raise ContractError("Gate 7.4 requires PrimaryMesh vertices + triangular faces")
            vertices = np.asarray(payload["vertices"], dtype=np.float64)
            faces = np.asarray(payload["faces"], dtype=np.int64)
            if faces.ndim != 2 or faces.shape[1] < 3:
                raise ContractError("PrimaryMesh faces must have shape [M,>=3]")
            faces = faces[:, :3]
            source_supported = np.zeros(len(vertices), dtype=np.uint8)
            if "grid_xy" in payload.files:
                grid = np.asarray(payload["grid_xy"])
                if grid.shape == (len(vertices), 2):
                    source_supported = np.isfinite(grid.astype(np.float64)).all(axis=1).astype(np.uint8)
            elif "source_uv" in payload.files:
                uv = np.asarray(payload["source_uv"], dtype=np.float64)
                if uv.shape == (len(vertices), 2):
                    source_supported = np.isfinite(uv).all(axis=1).astype(np.uint8)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read authoritative PrimaryMesh: {error}") from error
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) == 0:
        raise ContractError("PrimaryMesh vertices must have shape [N,3]")
    if not np.isfinite(vertices).all():
        raise ContractError("PrimaryMesh contains non-finite vertices")
    if len(faces) == 0 or np.any(faces < 0) or np.any(faces >= len(vertices)):
        raise ContractError("PrimaryMesh contains invalid or empty faces")
    return vertices, faces, source_supported


def _voxel_key(point, voxel_size: float) -> tuple[int, int, int]:
    return tuple(int(math.floor(float(v) / voxel_size)) for v in point)


def _face_probe_points(vertices, faces, np):
    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    centroid = (a + b + c) / 3.0
    ab = (a + b) * 0.5
    bc = (b + c) * 0.5
    ca = (c + a) * 0.5
    return centroid, (a, b, c, ab, bc, ca, centroid)


def _free_space_face_state(probes, state_by_key, voxel_size: float, np):
    face_count = len(probes[0])
    has_free = np.zeros(face_count, dtype=bool)
    has_conflict = np.zeros(face_count, dtype=bool)
    has_occupied = np.zeros(face_count, dtype=bool)
    for points in probes:
        states = np.asarray(
            [
                state_by_key.get(
                    _voxel_key(point, voxel_size),
                    int(FreeSpaceState.UNKNOWN),
                )
                for point in points
            ],
            dtype=np.uint8,
        )
        has_free |= states == int(FreeSpaceState.CONFIRMED_FREE)
        has_conflict |= states == int(FreeSpaceState.CONFLICT)
        has_occupied |= states == int(FreeSpaceState.OCCUPIED)
    return has_free, has_conflict, has_occupied


def _write_candidate_ply(
    path: Path,
    p9_vertices,
    p9_faces,
    p9_source_supported,
    p10_vertices,
    p10_faces,
    p10_vertex_provenance,
    p10_vertex_confidence,
):
    p10_offset = len(p9_vertices)
    lines = [
        "ply",
        "format ascii 1.0",
        "comment ConceptGhost Gate 7.4 protected fusion candidate",
        "comment candidate only; P9 upstream remains immutable",
        f"element vertex {len(p9_vertices) + len(p10_vertices)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar cg_layer",
        "property uchar cg_provenance",
        "property float cg_confidence",
        f"element face {len(p9_faces) + len(p10_faces)}",
        "property list uchar int vertex_indices",
        "property uchar cg_layer",
        "property uchar cg_provenance",
        "end_header",
    ]
    for point, supported in zip(p9_vertices, p9_source_supported):
        provenance = (
            int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED)
            if supported
            else int(Gate7ProvenanceClass.P9_RETAINED)
        )
        confidence = 0.95 if supported else 0.62
        lines.append(
            f"{float(point[0]):.9g} {float(point[1]):.9g} {float(point[2]):.9g} "
            f"1 {provenance} {confidence:.6f}"
        )
    for point, provenance, confidence in zip(
        p10_vertices,
        p10_vertex_provenance,
        p10_vertex_confidence,
    ):
        lines.append(
            f"{float(point[0]):.9g} {float(point[1]):.9g} {float(point[2]):.9g} "
            f"2 {int(provenance)} {float(confidence):.6f}"
        )
    for face in p9_faces:
        supported = bool(
            p9_source_supported[int(face[0])]
            or p9_source_supported[int(face[1])]
            or p9_source_supported[int(face[2])]
        )
        provenance = (
            int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED)
            if supported
            else int(Gate7ProvenanceClass.P9_RETAINED)
        )
        lines.append(
            f"3 {int(face[0])} {int(face[1])} {int(face[2])} 1 {provenance}"
        )
    for face in p10_faces:
        a, b, c = (int(v) + p10_offset for v in face)
        lines.append(
            f"3 {a} {b} {c} 2 {int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED)}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_protected_fusion_candidate(
    p9_run_dir: str | Path,
    registration_manifest_path: str | Path,
    confidence_free_space_overlay_manifest_path: str | Path,
    free_space_constraints_manifest_path: str | Path,
    output_root: str | Path,
    *,
    minimum_p10_confidence: float = 0.40,
    support_radius_fraction: float = 0.015,
    protected_overlap_fraction: float = 0.004,
    delaunay_support_fraction: float = 0.020,
    max_delaunay_points: int = 40000,
) -> dict[str, Any]:
    """Create a non-destructive P9 + admissible-P10 fusion candidate.

    All P9 faces are copied unchanged into the candidate. P10 faces are added
    only when independently multiview-supported, confidence-qualified, outside
    protected-source overlap, and not crossing CONFIRMED_FREE or CONFLICT.
    This stage never removes P9 geometry; overlap cleanup belongs to Gate 8.
    """

    np = _lazy_numpy()
    for name, value in (
        ("minimum_p10_confidence", minimum_p10_confidence),
        ("support_radius_fraction", support_radius_fraction),
        ("protected_overlap_fraction", protected_overlap_fraction),
        ("delaunay_support_fraction", delaunay_support_fraction),
    ):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
            raise ContractError(f"{name} must be finite and positive")
    if type(max_delaunay_points) is not int or max_delaunay_points < 1:
        raise ContractError("max_delaunay_points must be a positive integer")

    boundary = validate_official_run(p9_run_dir)
    registration_path = Path(registration_manifest_path).resolve()
    registration = _read_json(registration_path, "Gate 7.1 registration manifest")
    if registration.get("schema") != "ConceptGhost.P10Gate7Registration.v0.1":
        raise ContractError("Gate 7.4 requires Gate 7.1 registration schema v0.1")
    if registration.get("status") != "PASS" or registration.get("ready_for_gate7_2") is not True:
        raise ContractError("Gate 7.4 requires accepted Gate 7.1 registration")
    if registration.get("registration_policy") != "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION":
        raise ContractError("Gate 7.4 forbids non-identity registration")
    if registration.get("sim3_refit_allowed") is not False or float(registration.get("scale", 0.0)) != 1.0:
        raise ContractError("Gate 7.4 forbids Sim(3) or non-unit scale")
    if str(registration.get("p9_run_id") or "") != boundary.run_id:
        raise ContractError("Gate 7.4 registration P9 run mismatch")
    if str(registration.get("scene_contract_id") or "") != boundary.scene_contract_id:
        raise ContractError("Gate 7.4 registration Scene Contract mismatch")

    overlay_path = Path(confidence_free_space_overlay_manifest_path).resolve()
    overlay = _read_json(overlay_path, "Gate 7.3 confidence/free-space overlay")
    constraints_path = Path(free_space_constraints_manifest_path).resolve()
    constraints = _read_json(constraints_path, "Gate 7.3 free-space constraints")
    if overlay.get("schema") != "ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1":
        raise ContractError("Gate 7.4 requires Gate 7.3D confidence/free-space overlay")
    if constraints.get("schema") != "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1":
        raise ContractError("Gate 7.4 requires Gate 7.3B constraints")
    for payload, label in ((overlay, "overlay"), (constraints, "constraints")):
        if payload.get("status") != "PASS":
            raise ContractError(f"Gate 7.4 requires {label} status PASS")
        if payload.get("official_geometry_changed") is not False:
            raise ContractError(f"Gate 7.4 refuses {label} that changed official geometry")
        if payload.get("p9_authority_changed") is not False:
            raise ContractError(f"Gate 7.4 refuses {label} that changed P9 authority")
        if payload.get("ready_for_destructive_fusion") is not False:
            raise ContractError(f"Gate 7.4 refuses already-destructive {label}")
        for field, expected in (
            ("scene_contract_id", boundary.scene_contract_id),
            ("p9_run_id", boundary.run_id),
            ("p10_attempt_id", registration.get("p10_attempt_id")),
        ):
            if str(payload.get(field) or "") != str(expected or ""):
                raise ContractError(f"Gate 7.4 {label} identity mismatch for {field}")

    voxel = constraints.get("voxel") if isinstance(constraints.get("voxel"), dict) else {}
    voxel_size = float(voxel.get("voxel_size_m") or 0.0)
    if not math.isfinite(voxel_size) or voxel_size <= 0:
        raise ContractError("Gate 7.4 free-space constraints are missing voxel_size_m")

    overlay_npz = Path(str(overlay.get("evidence_npz_path") or "")).resolve()
    constraints_npz = Path(str(constraints.get("constraints_npz_path") or "")).resolve()
    if not overlay_npz.is_file() or not constraints_npz.is_file():
        raise ContractError("Gate 7.4 diagnostic evidence files are missing")

    with np.load(overlay_npz, allow_pickle=False) as evidence:
        required = {
            "p10_points",
            "p10_provenance_labels",
            "p10_confidence_after_free_space",
        }
        missing = required.difference(evidence.files)
        if missing:
            raise ContractError(f"Gate 7.4 overlay evidence missing arrays: {sorted(missing)}")
        support_points = np.asarray(evidence["p10_points"], dtype=np.float64)
        support_provenance = np.asarray(evidence["p10_provenance_labels"], dtype=np.uint8)
        support_confidence = np.asarray(
            evidence["p10_confidence_after_free_space"],
            dtype=np.float64,
        )
    if support_points.ndim != 2 or support_points.shape[1] != 3:
        raise ContractError("Gate 7.4 support points must have shape [N,3]")
    if not (len(support_points) == len(support_provenance) == len(support_confidence)):
        raise ContractError("Gate 7.4 support evidence arrays do not align")

    with np.load(constraints_npz, allow_pickle=False) as free:
        keys = np.asarray(free["voxel_keys"], dtype=np.int32)
        states = np.asarray(free["state"], dtype=np.uint8)
    if len(keys) != len(states):
        raise ContractError("Gate 7.4 free-space arrays do not align")
    state_by_key = {tuple(int(v) for v in key): int(state) for key, state in zip(keys, states)}

    confidence_manifest_path = Path(str(overlay.get("source_confidence_manifest_path") or "")).resolve()
    confidence_manifest = _read_json(confidence_manifest_path, "Gate 7.2C confidence manifest")
    provenance_manifest_path = Path(str(confidence_manifest.get("provenance_manifest_path") or "")).resolve()
    provenance = _read_json(provenance_manifest_path, "Gate 7.2 provenance manifest")
    thresholds = provenance.get("thresholds") if isinstance(provenance.get("thresholds"), dict) else {}
    scene_diagonal = float(thresholds.get("scene_diagonal_m") or 0.0)
    if not math.isfinite(scene_diagonal) or scene_diagonal <= 0:
        raise ContractError("Gate 7.4 requires scene_diagonal_m from Gate 7.2")

    support_radius = max(scene_diagonal * float(support_radius_fraction), 1.0e-5)
    protected_overlap_radius = max(scene_diagonal * float(protected_overlap_fraction), 1.0e-5)
    delaunay_support_radius = max(scene_diagonal * float(delaunay_support_fraction), support_radius)

    p9_vertices, p9_faces, p9_source_supported = _primary_mesh(boundary, np)
    protected_points = p9_vertices[p9_source_supported > 0]

    p10_mesh_path = Path(str(registration.get("pre_fusion_mesh_path") or "")).resolve()
    p10_vertices, p10_faces = _ply_mesh(p10_mesh_path, np)
    centroids, probes = _face_probe_points(p10_vertices, p10_faces, np)

    support_distance, support_index = _nearest(centroids, support_points, np)
    nearest_provenance = np.full(len(centroids), int(Gate7ProvenanceClass.UNKNOWN), dtype=np.uint8)
    nearest_confidence = np.zeros(len(centroids), dtype=np.float64)
    valid_support = support_index >= 0
    if np.any(valid_support):
        nearest_provenance[valid_support] = support_provenance[support_index[valid_support]]
        nearest_confidence[valid_support] = support_confidence[support_index[valid_support]]

    protected_distance, _ = _nearest(centroids, protected_points, np)
    has_free, has_free_conflict, _ = _free_space_face_state(
        probes,
        state_by_key,
        voxel_size,
        np,
    )

    dataset_manifest_path = Path(str(registration.get("dataset_manifest_path") or "")).resolve()
    default_delaunay = dataset_manifest_path.parent / "dense" / "pre_fusion_mesh_delaunay.ply"
    delaunay_path = default_delaunay if default_delaunay.is_file() else None
    delaunay_distance = np.full(len(centroids), np.inf, dtype=np.float64)
    if delaunay_path is not None:
        delaunay_vertices, _delaunay_faces = _ply_mesh(delaunay_path, np)
        stride = max(1, math.ceil(len(delaunay_vertices) / max_delaunay_points))
        delaunay_sample = delaunay_vertices[::stride][:max_delaunay_points]
        delaunay_distance, _ = _nearest(centroids, delaunay_sample, np)

    reason = np.full(len(p10_faces), _REASON["ACCEPTED_P10_MULTIVIEW"], dtype=np.uint8)
    accepted = np.ones(len(p10_faces), dtype=bool)

    def reject(mask, code):
        nonlocal accepted
        mask = mask & accepted
        reason[mask] = code
        accepted[mask] = False

    reject(has_free, _REASON["CONFIRMED_FREE_VETO"])
    reject(has_free_conflict, _REASON["FREE_SPACE_CONFLICT"])
    reject(protected_distance <= protected_overlap_radius, _REASON["P9_SOURCE_PROTECTED_OVERLAP"])
    reject(support_distance > support_radius, _REASON["SUPPORT_DISTANCE"])
    reject(
        nearest_provenance != int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED),
        _REASON["INSUFFICIENT_PROVENANCE"],
    )
    reject(nearest_confidence < float(minimum_p10_confidence), _REASON["LOW_CONFIDENCE"])
    if delaunay_path is not None:
        reject(
            delaunay_distance > delaunay_support_radius,
            _REASON["DELAUNAY_DISAGREEMENT"],
        )

    accepted_face_indices = np.flatnonzero(accepted).astype(np.int64)
    rejected_face_indices = np.flatnonzero(~accepted).astype(np.int64)
    accepted_faces_source = p10_faces[accepted_face_indices]

    if len(accepted_faces_source):
        used_vertices = np.unique(accepted_faces_source.reshape(-1))
        remap = np.full(len(p10_vertices), -1, dtype=np.int64)
        remap[used_vertices] = np.arange(len(used_vertices), dtype=np.int64)
        accepted_vertices = p10_vertices[used_vertices]
        accepted_faces = remap[accepted_faces_source]

        vertex_distance, vertex_support_index = _nearest(accepted_vertices, support_points, np)
        vertex_provenance = np.full(
            len(accepted_vertices),
            int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED),
            dtype=np.uint8,
        )
        vertex_confidence = np.full(len(accepted_vertices), float(minimum_p10_confidence), dtype=np.float32)
        valid_vertex_support = vertex_support_index >= 0
        vertex_provenance[valid_vertex_support] = support_provenance[vertex_support_index[valid_vertex_support]]
        vertex_confidence[valid_vertex_support] = support_confidence[vertex_support_index[valid_vertex_support]].astype(np.float32)
    else:
        used_vertices = np.empty(0, dtype=np.int64)
        accepted_vertices = np.empty((0, 3), dtype=np.float64)
        accepted_faces = np.empty((0, 3), dtype=np.int64)
        vertex_provenance = np.empty(0, dtype=np.uint8)
        vertex_confidence = np.empty(0, dtype=np.float32)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    candidate_path = output_root / "protected_fusion_candidate.ply"
    _write_candidate_ply(
        candidate_path,
        p9_vertices,
        p9_faces,
        p9_source_supported,
        accepted_vertices,
        accepted_faces,
        vertex_provenance,
        vertex_confidence,
    )

    evidence_path = output_root / "protected_fusion_face_provenance.npz"
    np.savez_compressed(
        evidence_path,
        p10_accepted_face_indices=accepted_face_indices,
        p10_rejected_face_indices=rejected_face_indices,
        p10_face_accept_mask=accepted.astype(np.uint8),
        p10_face_reason_code=reason,
        p10_face_nearest_provenance=nearest_provenance,
        p10_face_confidence=nearest_confidence.astype(np.float32),
        p10_face_support_distance_m=support_distance.astype(np.float32),
        p10_face_protected_p9_distance_m=protected_distance.astype(np.float32),
        p10_face_delaunay_distance_m=delaunay_distance.astype(np.float32),
        p10_used_vertex_indices=used_vertices,
        p9_source_supported_vertex_mask=p9_source_supported,
    )

    reason_counts = {}
    for name, code in _REASON.items():
        reason_counts[name] = int(np.count_nonzero(reason == code))

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.4",
        "mode": "PROTECTED_ADDITIVE_FUSION_CANDIDATE_NO_CLEANUP",
        "scene_contract_id": boundary.scene_contract_id,
        "p9_run_id": boundary.run_id,
        "p10_attempt_id": registration.get("p10_attempt_id"),
        "coordinate_space": "P9_CANONICAL_WORLD_METERS",
        "p9_policy": {
            "all_p9_faces_copied_unchanged": True,
            "p9_faces_removed": 0,
            "p9_vertices_moved": 0,
            "source_protected_overlap_accepts_p10": False,
        },
        "p10_acceptance_policy": {
            "required_provenance": "P10_MULTIVIEW_SUPPORTED",
            "minimum_confidence": float(minimum_p10_confidence),
            "support_radius_m": support_radius,
            "protected_overlap_radius_m": protected_overlap_radius,
            "confirmed_free": "HARD_VETO",
            "free_space_conflict": "HARD_VETO_TO_UNRESOLVED",
            "unknown_free_space": "NOT_A_VETO_BY_ITSELF",
            "delaunay": (
                "REQUIRED_LOCAL_AGREEMENT_WHEN_DELAUNAY_EVIDENCE_EXISTS"
                if delaunay_path is not None
                else "NOT_AVAILABLE_RECORDED_NO_AUTOMATIC_PENALTY"
            ),
            "delaunay_support_radius_m": delaunay_support_radius,
        },
        "counts": {
            "p9_vertices": int(len(p9_vertices)),
            "p9_faces": int(len(p9_faces)),
            "p9_source_supported_vertices": int(np.count_nonzero(p9_source_supported)),
            "p10_input_vertices": int(len(p10_vertices)),
            "p10_input_faces": int(len(p10_faces)),
            "p10_accepted_faces": int(len(accepted_face_indices)),
            "p10_rejected_faces": int(len(rejected_face_indices)),
            "p10_candidate_vertices": int(len(accepted_vertices)),
            "candidate_total_vertices": int(len(p9_vertices) + len(accepted_vertices)),
            "candidate_total_faces": int(len(p9_faces) + len(accepted_faces)),
        },
        "reason_codes": _REASON,
        "reason_counts": reason_counts,
        "inputs": {
            "registration_manifest_path": str(registration_path),
            "confidence_free_space_overlay_manifest_path": str(overlay_path),
            "free_space_constraints_manifest_path": str(constraints_path),
            "p9_primary_mesh_path": str(boundary.primary_mesh),
            "p10_prefusion_mesh_path": str(p10_mesh_path),
            "delaunay_evidence_mesh_path": str(delaunay_path) if delaunay_path else None,
        },
        "candidate_ply_path": str(candidate_path),
        "face_provenance_npz_path": str(evidence_path),
        "candidate_is_official_geometry": False,
        "candidate_may_be_discarded": True,
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "destructive_cleanup_performed": False,
        "ready_for_gate7_5": True,
        "ready_for_destructive_fusion": False,
        "next_required": [
            "G7.5_REGISTRATION_PROVENANCE_VISUAL_REVIEW",
            "G7.6_GATE7_CLOSEOUT",
        ],
    }
    manifest_path = output_root / "protected_fusion_candidate_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(manifest_path)
    return result
