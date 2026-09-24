from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .colmap_dense_io import colmap_camera_center, qvec_to_rotation_matrix
from .contracts import ContractError
from .free_space_constraints import FreeSpaceState
from .gate7_provenance import Gate7ProvenanceClass
from .prefusion_mesh import _read_mesh


_SCHEMA = "ConceptGhost.P10Gate7VisualReview.v0.1"


def _lazy_runtime():
    try:
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise ContractError("Gate 7.5 visual review requires NumPy and Pillow") from error
    return np, Image, ImageDraw, ImageFont


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _read_candidate_ascii(path: Path, np):
    """Read the ASCII Gate 7.4 candidate including ConceptGhost metadata."""

    if not path.is_file():
        raise ContractError(f"Gate 7.5 candidate mesh is missing: {path}")
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    if not lines or lines[0].strip() != "ply":
        raise ContractError("Gate 7.5 candidate is not a PLY")
    if "format ascii 1.0" not in lines[:4]:
        raise ContractError("Gate 7.5 currently requires the ASCII Gate 7.4 candidate")

    vertex_count = None
    face_count = None
    end = None
    for index, line in enumerate(lines):
        parts = line.split()
        if len(parts) == 3 and parts[:2] == ["element", "vertex"]:
            vertex_count = int(parts[2])
        elif len(parts) == 3 and parts[:2] == ["element", "face"]:
            face_count = int(parts[2])
        elif line.strip() == "end_header":
            end = index
            break
    if end is None or vertex_count is None or face_count is None:
        raise ContractError("Gate 7.5 candidate PLY header is incomplete")

    vertex_rows = lines[end + 1 : end + 1 + vertex_count]
    face_rows = lines[end + 1 + vertex_count : end + 1 + vertex_count + face_count]
    if len(vertex_rows) != vertex_count or len(face_rows) != face_count:
        raise ContractError("Gate 7.5 candidate PLY is truncated")

    vertices = np.empty((vertex_count, 3), dtype=np.float64)
    layer = np.empty(vertex_count, dtype=np.uint8)
    provenance = np.empty(vertex_count, dtype=np.uint8)
    confidence = np.empty(vertex_count, dtype=np.float32)
    for index, raw in enumerate(vertex_rows):
        parts = raw.split()
        if len(parts) < 6:
            raise ContractError("Gate 7.5 candidate vertex metadata is incomplete")
        vertices[index] = [float(parts[0]), float(parts[1]), float(parts[2])]
        layer[index] = int(parts[3])
        provenance[index] = int(parts[4])
        confidence[index] = float(parts[5])

    faces = np.empty((face_count, 3), dtype=np.int64)
    face_layer = np.empty(face_count, dtype=np.uint8)
    face_provenance = np.empty(face_count, dtype=np.uint8)
    for index, raw in enumerate(face_rows):
        parts = raw.split()
        if len(parts) < 6 or int(parts[0]) != 3:
            raise ContractError("Gate 7.5 requires triangular candidate faces with metadata")
        faces[index] = [int(parts[1]), int(parts[2]), int(parts[3])]
        face_layer[index] = int(parts[4])
        face_provenance[index] = int(parts[5])

    if not np.isfinite(vertices).all():
        raise ContractError("Gate 7.5 candidate contains non-finite vertices")
    if np.any(faces < 0) or np.any(faces >= vertex_count):
        raise ContractError("Gate 7.5 candidate contains invalid face indices")
    return vertices, faces, layer, provenance, confidence, face_layer, face_provenance


def _mesh_centroids(path: Path, np, *, max_faces: int = 50000):
    if not path.is_file():
        return np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.int64)
    header, vertex_array, faces, invalid = _read_mesh(path, max_faces)
    if invalid:
        raise ContractError(f"Gate 7.5 rejected-source mesh has invalid faces: {invalid}")
    vertices = np.asarray(vertex_array, dtype=np.float64).reshape((-1, 3))
    triangles = np.asarray(faces, dtype=np.int64)
    if triangles.size == 0:
        return np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.int64)
    centroids = (
        vertices[triangles[:, 0]]
        + vertices[triangles[:, 1]]
        + vertices[triangles[:, 2]]
    ) / 3.0
    return centroids, np.arange(len(centroids), dtype=np.int64)


def _camera_records(dataset: dict[str, Any], np):
    frames = dataset.get("frames")
    if not isinstance(frames, list):
        raise ContractError("Gate 7.5 dataset manifest is missing frames")
    records = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        qvec = frame.get("qvec")
        tvec = frame.get("tvec")
        if not isinstance(qvec, list) or not isinstance(tvec, list):
            continue
        center = np.asarray(colmap_camera_center(qvec, tvec), dtype=np.float64)
        rotation = np.asarray(qvec_to_rotation_matrix(qvec), dtype=np.float64)
        forward = rotation.T @ np.asarray([0.0, 0.0, 1.0], dtype=np.float64)
        length = float(np.linalg.norm(forward))
        if length <= 1e-12:
            continue
        forward /= length
        records.append(
            {
                "center": center,
                "forward": forward,
                "route": str(frame.get("path_name") or "route"),
                "frame_index": frame.get("global_frame_index"),
            }
        )
    if not records:
        raise ContractError("Gate 7.5 found no valid camera records")
    return records


def _bounds(points, np):
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ContractError("Gate 7.5 requires non-empty [N,3] geometry")
    lo = np.min(points, axis=0)
    hi = np.max(points, axis=0)
    center = (lo + hi) * 0.5
    span = float(max(np.max(hi - lo), 1.0e-6))
    return lo, hi, center, span


def _sample_indices(count: int, max_count: int, np):
    if count <= max_count:
        return np.arange(count, dtype=np.int64)
    stride = max(1, math.ceil(count / max_count))
    return np.arange(0, count, stride, dtype=np.int64)[:max_count]


def _projector(kind: str, center, scale_px: float, panel_center, np):
    if kind == "front":
        right = np.asarray([1.0, 0.0, 0.0])
        up = np.asarray([0.0, 1.0, 0.0])
    elif kind == "top":
        right = np.asarray([1.0, 0.0, 0.0])
        up = np.asarray([0.0, 0.0, -1.0])
    elif kind == "side":
        right = np.asarray([0.0, 0.0, 1.0])
        up = np.asarray([0.0, 1.0, 0.0])
    elif kind == "perspective":
        right = np.asarray([1.0, 0.0, -1.0], dtype=np.float64)
        right /= np.linalg.norm(right)
        view = np.asarray([1.0, 0.8, 1.0], dtype=np.float64)
        view /= np.linalg.norm(view)
        up = np.cross(view, right)
        up /= np.linalg.norm(up)
    else:
        raise ContractError(f"Unknown Gate 7.5 projection: {kind}")

    def project(point):
        local = np.asarray(point, dtype=np.float64) - center
        return (
            float(panel_center[0] + np.dot(local, right) * scale_px),
            float(panel_center[1] - np.dot(local, up) * scale_px),
        )

    return project


def build_gate7_visual_review(
    protected_fusion_manifest_path: str | Path,
    output_root: str | Path,
    *,
    panel_size: int = 600,
    max_faces_per_layer: int = 14000,
    max_rejected_faces: int = 10000,
    max_free_space_points: int = 12000,
    max_cameras: int = 80,
) -> dict[str, Any]:
    """Render Gate 7.5 review panels without promoting the fusion candidate."""

    if type(panel_size) is not int or panel_size < 320 or panel_size > 1400:
        raise ContractError("panel_size must be an integer from 320 to 1400")
    for name, value in (
        ("max_faces_per_layer", max_faces_per_layer),
        ("max_rejected_faces", max_rejected_faces),
        ("max_free_space_points", max_free_space_points),
        ("max_cameras", max_cameras),
    ):
        if type(value) is not int or value < 1:
            raise ContractError(f"{name} must be a positive integer")

    np, Image, ImageDraw, ImageFont = _lazy_runtime()
    fusion_path = Path(protected_fusion_manifest_path).resolve()
    fusion = _read_json(fusion_path, "Gate 7.4 protected fusion manifest")
    if fusion.get("schema") != "ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1":
        raise ContractError("Gate 7.5 requires Gate 7.4 protected fusion schema v0.1")
    if fusion.get("status") != "PASS":
        raise ContractError("Gate 7.5 requires Gate 7.4 status PASS")
    if fusion.get("candidate_is_official_geometry") is not False:
        raise ContractError("Gate 7.5 refuses a candidate already marked official")
    if fusion.get("official_geometry_changed") is not False:
        raise ContractError("Gate 7.5 refuses mutated official geometry")
    if fusion.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7.5 refuses changed P9 authority")
    if fusion.get("destructive_cleanup_performed") is not False:
        raise ContractError("Gate 7.5 refuses a candidate that already performed cleanup")
    if fusion.get("ready_for_gate7_5") is not True:
        raise ContractError("Gate 7.4 did not promote this candidate to visual review")

    inputs = fusion.get("inputs")
    if not isinstance(inputs, dict):
        raise ContractError("Gate 7.4 fusion manifest is missing inputs")
    candidate_path = Path(str(fusion.get("candidate_ply_path") or "")).resolve()
    face_provenance_path = Path(str(fusion.get("face_provenance_npz_path") or "")).resolve()
    p10_input_path = Path(str(inputs.get("p10_prefusion_mesh_path") or "")).resolve()
    constraints_manifest_path = Path(str(inputs.get("free_space_constraints_manifest_path") or "")).resolve()
    constraints = _read_json(constraints_manifest_path, "Gate 7.3 free-space constraints")
    constraints_npz = Path(str(constraints.get("constraints_npz_path") or "")).resolve()
    registration_path = Path(str(inputs.get("registration_manifest_path") or "")).resolve()
    registration = _read_json(registration_path, "Gate 7.1 registration manifest")
    dataset_manifest_path = Path(str(registration.get("dataset_manifest_path") or "")).resolve()
    dataset = _read_json(dataset_manifest_path, "Gate 6 dataset manifest")

    for payload, label in ((constraints, "constraints"), (registration, "registration"), (dataset, "dataset")):
        if str(payload.get("scene_contract_id") or fusion.get("scene_contract_id") or "") != str(fusion.get("scene_contract_id") or ""):
            if label != "registration" or str(payload.get("scene_contract_id") or ""):
                raise ContractError(f"Gate 7.5 {label} Scene Contract mismatch")

    (
        candidate_vertices,
        candidate_faces,
        vertex_layer,
        vertex_provenance,
        vertex_confidence,
        face_layer,
        face_provenance,
    ) = _read_candidate_ascii(candidate_path, np)

    with np.load(face_provenance_path, allow_pickle=False) as evidence:
        if "p10_rejected_face_indices" not in evidence.files or "p10_face_reason_code" not in evidence.files:
            raise ContractError("Gate 7.5 face provenance evidence is incomplete")
        rejected_indices = np.asarray(evidence["p10_rejected_face_indices"], dtype=np.int64)
        reason_codes = np.asarray(evidence["p10_face_reason_code"], dtype=np.uint8)

    p10_centroids, p10_centroid_indices = _mesh_centroids(p10_input_path, np, max_faces=2_000_000_000)
    if len(rejected_indices):
        if np.any(rejected_indices < 0) or np.any(rejected_indices >= len(p10_centroids)):
            raise ContractError("Gate 7.5 rejected face indices exceed source P10 mesh")
        rejected_centroids = p10_centroids[rejected_indices]
        rejected_reason = reason_codes[rejected_indices]
    else:
        rejected_centroids = np.empty((0, 3), dtype=np.float64)
        rejected_reason = np.empty(0, dtype=np.uint8)

    with np.load(constraints_npz, allow_pickle=False) as free:
        free_centers = np.asarray(free["voxel_centers"], dtype=np.float64)
        free_states = np.asarray(free["state"], dtype=np.uint8)
    if len(free_centers) != len(free_states):
        raise ContractError("Gate 7.5 free-space arrays do not align")

    cameras = _camera_records(dataset, np)
    all_points = [candidate_vertices]
    if len(rejected_centroids):
        all_points.append(rejected_centroids)
    if len(free_centers):
        all_points.append(free_centers)
    all_points.append(np.asarray([row["center"] for row in cameras], dtype=np.float64))
    combined = np.concatenate(all_points, axis=0)
    _, _, center, span = _bounds(combined, np)

    margin = 54
    canvas_w = panel_size * 2 + margin * 3
    canvas_h = panel_size * 2 + margin * 3 + 90
    image = Image.new("RGB", (canvas_w, canvas_h), (19, 19, 22))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    scale_px = (panel_size * 0.82) / span
    panel_defs = [
        ("Perspective", "perspective", margin, margin + 50),
        ("Top · X/Z", "top", margin * 2 + panel_size, margin + 50),
        ("Front · X/Y", "front", margin, margin * 2 + panel_size + 50),
        ("Side · Z/Y", "side", margin * 2 + panel_size, margin * 2 + panel_size + 50),
    ]

    # Stable diagnostic palette, intentionally not written back to Maya.
    P9 = (116, 158, 210)
    P9_PROTECTED = (70, 130, 255)
    P10 = (80, 210, 120)
    REJECTED = (235, 80, 70)
    FREE = (40, 220, 210)
    CONFLICT = (225, 70, 220)
    CAMERA = (245, 205, 70)
    BORDER = (82, 82, 90)
    TEXT = (235, 235, 240)

    p9_face_idx = np.flatnonzero(face_layer == 1)
    p10_face_idx = np.flatnonzero(face_layer == 2)
    p9_face_idx = p9_face_idx[_sample_indices(len(p9_face_idx), max_faces_per_layer, np)]
    p10_face_idx = p10_face_idx[_sample_indices(len(p10_face_idx), max_faces_per_layer, np)]
    rejected_keep = _sample_indices(len(rejected_centroids), max_rejected_faces, np)
    free_keep = _sample_indices(len(free_centers), max_free_space_points, np)
    camera_keep = _sample_indices(len(cameras), max_cameras, np)

    for title, kind, x0, y0 in panel_defs:
        draw.rectangle((x0, y0, x0 + panel_size, y0 + panel_size), outline=BORDER, width=1)
        draw.text((x0 + 8, y0 + 8), title, fill=TEXT, font=font)
        project = _projector(
            kind,
            center,
            scale_px,
            (x0 + panel_size * 0.5, y0 + panel_size * 0.5),
            np,
        )

        for indices, color, width in (
            (p9_face_idx, P9, 1),
            (p10_face_idx, P10, 2),
        ):
            for face_index in indices:
                face = candidate_faces[int(face_index)]
                points = [project(candidate_vertices[int(v)]) for v in face]
                draw.line(points + [points[0]], fill=color, width=width)

        protected_vertices = np.flatnonzero(
            (vertex_layer == 1)
            & (vertex_provenance == int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED))
        )
        protected_vertices = protected_vertices[_sample_indices(len(protected_vertices), 12000, np)]
        for index in protected_vertices:
            x, y = project(candidate_vertices[int(index)])
            draw.point((x, y), fill=P9_PROTECTED)

        for index in rejected_keep:
            x, y = project(rejected_centroids[int(index)])
            r = 2
            draw.line((x - r, y - r, x + r, y + r), fill=REJECTED, width=1)
            draw.line((x - r, y + r, x + r, y - r), fill=REJECTED, width=1)

        for index in free_keep:
            state = int(free_states[int(index)])
            if state == int(FreeSpaceState.CONFIRMED_FREE):
                color = FREE
            elif state == int(FreeSpaceState.CONFLICT):
                color = CONFLICT
            else:
                continue
            x, y = project(free_centers[int(index)])
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)

        frustum_scale = max(span * 0.035, 0.05)
        for index in camera_keep:
            camera = cameras[int(index)]
            c = camera["center"]
            tip = c + camera["forward"] * frustum_scale
            x, y = project(c)
            tx, ty = project(tip)
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=CAMERA)
            draw.line((x, y, tx, ty), fill=CAMERA, width=1)

        draw.text(
            (x0 + 8, y0 + panel_size - 18),
            f"metric-isotropic · {span:.4g} m review span",
            fill=(150, 150, 158),
            font=font,
        )

    draw.text((margin, 12), "ConceptGhost · Gate 7.5 Registration / Provenance Visual Review", fill=TEXT, font=font)
    legend_y = canvas_h - 34
    legend = [
        ("P9", P9),
        ("P9_SOURCE_PROTECTED", P9_PROTECTED),
        ("P10_ACCEPTED", P10),
        ("P10_REJECTED", REJECTED),
        ("CONFIRMED_FREE", FREE),
        ("CONFLICT", CONFLICT),
        ("CAMERAS", CAMERA),
    ]
    cursor = margin
    for label, color in legend:
        draw.rectangle((cursor, legend_y, cursor + 10, legend_y + 10), fill=color)
        draw.text((cursor + 14, legend_y - 1), label, fill=TEXT, font=font)
        cursor += 14 + max(62, len(label) * 7)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    preview_path = output_root / "gate7_registration_provenance_review.png"
    image.save(preview_path)

    counts = fusion.get("counts") if isinstance(fusion.get("counts"), dict) else {}
    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.5",
        "mode": "VISUAL_REVIEW_ONLY_NO_PROMOTION",
        "scene_contract_id": fusion.get("scene_contract_id"),
        "p9_run_id": fusion.get("p9_run_id"),
        "p10_attempt_id": fusion.get("p10_attempt_id"),
        "coordinate_space": fusion.get("coordinate_space"),
        "views": ["PERSPECTIVE", "TOP_XZ", "FRONT_XY", "SIDE_ZY"],
        "metric_isotropic_orthographic": True,
        "review_layers": {
            "p9_geometry": True,
            "p9_source_protected": True,
            "p10_accepted": True,
            "p10_rejected": True,
            "confirmed_free": True,
            "conflict": True,
            "camera_context": True,
        },
        "render_counts": {
            "candidate_vertices": int(len(candidate_vertices)),
            "candidate_faces": int(len(candidate_faces)),
            "p9_faces": int(counts.get("p9_faces") or len(p9_face_idx)),
            "p10_accepted_faces": int(counts.get("p10_accepted_faces") or len(p10_face_idx)),
            "p10_rejected_faces": int(len(rejected_indices)),
            "confirmed_free_voxels": int(
                np.count_nonzero(free_states == int(FreeSpaceState.CONFIRMED_FREE))
            ),
            "conflict_voxels": int(
                np.count_nonzero(free_states == int(FreeSpaceState.CONFLICT))
            ),
            "camera_count": int(len(cameras)),
        },
        "preview_png_path": str(preview_path),
        "fusion_manifest_path": str(fusion_path),
        "free_space_constraints_manifest_path": str(constraints_manifest_path),
        "dataset_manifest_path": str(dataset_manifest_path),
        "candidate_is_official_geometry": False,
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "visual_review_required": True,
        "artist_review_status": "PENDING",
        "ready_for_gate7_6_source_closeout": True,
        "ready_for_gate8": False,
        "promotion_blockers": [
            "ARTIST_VISUAL_REVIEW_PENDING",
            "DR9R_R15_RUNTIME_UX_ACCEPTANCE_PENDING",
        ],
    }
    manifest_path = output_root / "gate7_visual_review_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(manifest_path)
    return result
