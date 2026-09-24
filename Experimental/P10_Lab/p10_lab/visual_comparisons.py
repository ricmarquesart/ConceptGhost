from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .colmap_dense_io import parse_colmap_cameras_txt, qvec_to_rotation_matrix
from .contracts import ContractError
from .prefusion_mesh import _read_mesh


def _runtime():
    try:
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise ContractError("Visual comparisons require NumPy and Pillow") from error
    return np, Image, ImageDraw, ImageFont


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _confidence_color(score: float) -> tuple[int, int, int]:
    """Red=low confidence, blue=high confidence, neutral near gray/purple."""
    value = max(0.0, min(1.0, float(score)))
    red = int(round(235.0 * (1.0 - value) + 35.0 * value))
    green = int(round(55.0 + 75.0 * (1.0 - abs(value - 0.5) * 2.0)))
    blue = int(round(45.0 * (1.0 - value) + 240.0 * value))
    return red, green, blue


def _best_axis_pair(points, np) -> tuple[int, int, str]:
    spans = np.ptp(points, axis=0)
    pairs = [
        (0, 1, "X/Y"),
        (0, 2, "X/Z"),
        (2, 1, "Z/Y"),
    ]
    pair = max(pairs, key=lambda item: float(spans[item[0]] * spans[item[1]]))
    return pair


def _point_panel(draw, rect, points, scores, title: str, *, axis_pair, np, max_points: int = 50000):
    x0, y0, width, height = rect
    draw.rectangle((x0, y0, x0 + width, y0 + height), fill=(20, 20, 23), outline=(85, 85, 92))
    draw.text((x0 + 10, y0 + 8), title, fill=(240, 240, 244))
    if len(points) == 0:
        draw.text((x0 + 10, y0 + 30), "no points", fill=(170, 170, 175))
        return
    ax, ay, label = axis_pair
    sample_stride = max(1, math.ceil(len(points) / max_points))
    pts = points[::sample_stride]
    vals = scores[::sample_stride]
    xmin, xmax = float(np.min(points[:, ax])), float(np.max(points[:, ax]))
    ymin, ymax = float(np.min(points[:, ay])), float(np.max(points[:, ay]))
    span_x = max(xmax - xmin, 1e-9)
    span_y = max(ymax - ymin, 1e-9)
    pad = 36
    usable_w = max(1, width - pad * 2)
    usable_h = max(1, height - pad * 2)
    ppm = min(usable_w / span_x, usable_h / span_y)
    display_x = usable_w / ppm
    display_y = usable_h / ppm
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5
    xmin_d, ymin_d = cx - display_x * 0.5, cy - display_y * 0.5
    for point, score in zip(pts, vals):
        px = x0 + pad + (float(point[ax]) - xmin_d) * ppm
        py = y0 + height - pad - (float(point[ay]) - ymin_d) * ppm
        draw.ellipse((px - 1.5, py - 1.5, px + 1.5, py + 1.5), fill=_confidence_color(float(score)))
    draw.text((x0 + 10, y0 + height - 20), f"metric-isotropic projection {label}", fill=(150, 150, 158))


def render_confidence_before_after(
    confidence_manifest_path: str | Path,
    confidence_free_space_overlay_manifest_path: str | Path,
    output_root: str | Path,
    *,
    panel_size: int = 620,
) -> dict[str, Any]:
    """Render confidence before/after free-space coupling using one metric projection."""

    np, Image, ImageDraw, _ImageFont = _runtime()
    confidence = _read_json(confidence_manifest_path, "Gate 7.2C confidence manifest")
    overlay = _read_json(
        confidence_free_space_overlay_manifest_path,
        "Gate 7.3D confidence/free-space overlay",
    )
    if confidence.get("schema") != "ConceptGhost.P10Gate7GeometryConfidence.v0.1":
        raise ContractError("Confidence comparison requires Gate 7.2C schema v0.1")
    if overlay.get("schema") != "ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1":
        raise ContractError("Confidence comparison requires Gate 7.3D overlay schema v0.1")
    for field in ("scene_contract_id", "p9_run_id", "p10_attempt_id"):
        if str(confidence.get(field) or "") != str(overlay.get(field) or ""):
            raise ContractError(f"Confidence comparison identity mismatch for {field}")

    before_path = Path(str(confidence.get("evidence_npz_path") or "")).resolve()
    after_path = Path(str(overlay.get("evidence_npz_path") or "")).resolve()
    with np.load(before_path, allow_pickle=False) as before:
        points = np.asarray(before["p10_points"], dtype=np.float64)
        before_scores = np.asarray(before["p10_confidence"], dtype=np.float64)
    with np.load(after_path, allow_pickle=False) as after:
        after_points = np.asarray(after["p10_points"], dtype=np.float64)
        after_scores = np.asarray(after["p10_confidence_after_free_space"], dtype=np.float64)
    if points.shape != after_points.shape or not np.allclose(points, after_points, atol=1e-7, rtol=0):
        raise ContractError("Confidence before/after points do not align")
    if len(points) != len(before_scores) or len(points) != len(after_scores):
        raise ContractError("Confidence before/after arrays do not align")
    if len(points) == 0:
        raise ContractError("Confidence comparison requires P10 points")

    axis_pair = _best_axis_pair(points, np)
    delta = after_scores - before_scores
    delta_norm = np.clip((delta + 0.75) / 1.5, 0.0, 1.0)

    width = panel_size * 3 + 48
    height = panel_size + 90
    image = Image.new("RGB", (width, height), (15, 15, 18))
    draw = ImageDraw.Draw(image)
    draw.text((16, 12), "ConceptGhost · Confidence Comparison · BLUE=HIGH · RED=LOW", fill=(245,245,248))

    rects = [
        (12, 46, panel_size, panel_size),
        (24 + panel_size, 46, panel_size, panel_size),
        (36 + panel_size * 2, 46, panel_size, panel_size),
    ]
    _point_panel(draw, rects[0], points, before_scores, "BEFORE · G7.2C confidence", axis_pair=axis_pair, np=np)
    _point_panel(draw, rects[1], points, after_scores, "AFTER · G7.3 free-space coupling", axis_pair=axis_pair, np=np)
    _point_panel(draw, rects[2], points, delta_norm, "DELTA · red=confidence reduced", axis_pair=axis_pair, np=np)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    png = output_root / "confidence_before_after_comparison.png"
    image.save(png)
    manifest = {
        "schema": "ConceptGhost.P10ConfidenceComparison.v0.1",
        "status": "PASS",
        "scene_contract_id": confidence.get("scene_contract_id"),
        "p9_run_id": confidence.get("p9_run_id"),
        "p10_attempt_id": confidence.get("p10_attempt_id"),
        "before": "G7.2C_CONFIDENCE_BEFORE_FREE_SPACE",
        "after": "G7.3D_CONFIDENCE_AFTER_FREE_SPACE",
        "projection_axes": axis_pair[2],
        "same_metric_projection": True,
        "high_confidence_color": "BLUE",
        "low_confidence_color": "RED",
        "changed_point_count": int(np.count_nonzero(np.abs(delta) > 1e-6)),
        "mean_confidence_before": float(np.mean(before_scores)),
        "mean_confidence_after": float(np.mean(after_scores)),
        "comparison_png_path": str(png),
        "terminal_visual_branch": True,
        "feeds_geometry_pipeline": False,
        "official_geometry_changed": False,
    }
    out = output_root / "confidence_before_after_comparison.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(out)
    return manifest


def _mesh_for_replay(path: str | Path, max_faces: int, np):
    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"Replay mesh is missing: {path}")
    header, vertex_array, faces, invalid = _read_mesh(path, max_faces)
    if invalid:
        raise ContractError(f"Replay mesh has invalid faces: {path}: {invalid}")
    vertices = np.asarray(vertex_array, dtype=np.float64).reshape((-1, 3))
    triangles = np.asarray(faces, dtype=np.int64)
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ContractError("Replay mesh must contain triangular faces")
    return vertices, triangles


def _render_mesh_camera(
    vertices,
    faces,
    qvec,
    tvec,
    camera,
    *,
    width: int,
    height: int,
    title: str,
    np,
    Image,
    ImageDraw,
):
    rotation = np.asarray(qvec_to_rotation_matrix(qvec), dtype=np.float64)
    t = np.asarray(tvec, dtype=np.float64)
    camera_points = vertices @ rotation.T + t[None, :]
    z = camera_points[:, 2]
    valid_vertex = z > 1e-5
    fx, fy = float(camera["fx"]), float(camera["fy"])
    cx, cy = float(camera["cx"]), float(camera["cy"])
    scale_x = width / float(camera["width"])
    scale_y = height / float(camera["height"])
    u = (fx * camera_points[:, 0] / np.maximum(z, 1e-9) + cx) * scale_x
    v = (fy * camera_points[:, 1] / np.maximum(z, 1e-9) + cy) * scale_y

    image = Image.new("RGB", (width, height), (18, 18, 21))
    draw = ImageDraw.Draw(image)
    visible = valid_vertex[faces[:, 0]] & valid_vertex[faces[:, 1]] & valid_vertex[faces[:, 2]]
    visible_faces = faces[visible]
    if len(visible_faces):
        depth = np.mean(z[visible_faces], axis=1)
        order = np.argsort(depth)[::-1]
        for face in visible_faces[order]:
            pts = [(float(u[int(i)]), float(v[int(i)])) for i in face]
            if all(
                (-width <= px <= width * 2 and -height <= py <= height * 2)
                for px, py in pts
            ):
                shade = int(max(65, min(205, 220.0 - float(np.mean(z[face])) * 3.0)))
                draw.polygon(pts, fill=(shade, shade, shade), outline=(35, 35, 38))
    draw.rectangle((0, 0, width - 1, height - 1), outline=(85, 85, 92))
    draw.rectangle((8, 8, min(width - 8, 8 + len(title) * 7 + 12), 28), fill=(0, 0, 0))
    draw.text((14, 12), title, fill=(245, 245, 248))
    return image


def render_drone_mesh_before_after_replay(
    dataset_manifest_path: str | Path,
    before_mesh_path: str | Path,
    after_mesh_path: str | Path,
    output_root: str | Path,
    *,
    before_label: str = "BEFORE",
    after_label: str = "AFTER",
    width: int = 640,
    height: int = 360,
    max_frames: int = 48,
    max_faces: int = 10000,
    duration_ms: int = 110,
) -> dict[str, Any]:
    """Replay the exact Gate-6 drone cameras over BEFORE/AFTER geometry.

    This is a terminal diagnostic branch. Both halves use the same qvec/tvec,
    intrinsics, frame selection and image dimensions.
    """

    np, Image, ImageDraw, _ImageFont = _runtime()
    dataset_path = Path(dataset_manifest_path).resolve()
    dataset = _read_json(dataset_path, "Gate 6 dataset manifest")
    if dataset.get("camera_authority") != "P9_BASELINE_WORLD_DERIVED":
        raise ContractError("Drone comparison replay requires P9-derived known cameras")
    frames = dataset.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ContractError("Drone comparison replay requires dataset frames")
    known_sparse = Path(str(dataset.get("known_sparse_model_dir") or "")).resolve()
    cameras = parse_colmap_cameras_txt(known_sparse / "cameras.txt")

    before_vertices, before_faces = _mesh_for_replay(before_mesh_path, max_faces, np)
    after_vertices, after_faces = _mesh_for_replay(after_mesh_path, max_faces, np)

    stride = max(1, math.ceil(len(frames) / max_frames))
    selected = frames[::stride][:max_frames]
    if not selected:
        raise ContractError("Drone comparison replay selected no frames")

    before_images = []
    after_images = []
    combined_images = []
    selected_ids = []
    for frame in selected:
        camera_id = int(frame["camera_id"])
        camera = cameras.get(camera_id)
        if camera is None:
            raise ContractError(f"Replay frame references missing camera {camera_id}")
        qvec = frame.get("qvec")
        tvec = frame.get("tvec")
        if not isinstance(qvec, list) or not isinstance(tvec, list):
            raise ContractError("Replay frame is missing qvec/tvec")
        before_image = _render_mesh_camera(
            before_vertices,
            before_faces,
            qvec,
            tvec,
            camera,
            width=width,
            height=height,
            title=before_label,
            np=np,
            Image=Image,
            ImageDraw=ImageDraw,
        )
        after_image = _render_mesh_camera(
            after_vertices,
            after_faces,
            qvec,
            tvec,
            camera,
            width=width,
            height=height,
            title=after_label,
            np=np,
            Image=Image,
            ImageDraw=ImageDraw,
        )
        combined = Image.new("RGB", (width * 2 + 8, height + 28), (10, 10, 12))
        combined.paste(before_image, (0, 28))
        combined.paste(after_image, (width + 8, 28))
        d = ImageDraw.Draw(combined)
        idx = frame.get("global_frame_index")
        route = str(frame.get("path_name") or "")
        d.text(
            (10, 8),
            f"SAME DRONE CAMERA · route={route} · frame={idx}",
            fill=(245,245,248),
        )
        before_images.append(before_image)
        after_images.append(after_image)
        combined_images.append(combined)
        selected_ids.append(idx)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    before_gif = output_root / "drone_replay_before.gif"
    after_gif = output_root / "drone_replay_after.gif"
    comparison_gif = output_root / "drone_replay_before_after.gif"
    before_images[0].save(
        before_gif,
        save_all=True,
        append_images=before_images[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    after_images[0].save(
        after_gif,
        save_all=True,
        append_images=after_images[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    combined_images[0].save(
        comparison_gif,
        save_all=True,
        append_images=combined_images[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )

    manifest = {
        "schema": "ConceptGhost.P10DroneMeshComparisonReplay.v0.1",
        "status": "PASS",
        "dataset_manifest_path": str(dataset_path),
        "scene_contract_id": dataset.get("scene_contract_id"),
        "p9_run_id": dataset.get("run_id"),
        "before_mesh_path": str(Path(before_mesh_path).resolve()),
        "after_mesh_path": str(Path(after_mesh_path).resolve()),
        "before_label": before_label,
        "after_label": after_label,
        "camera_contract": {
            "same_qvec_tvec_on_both_sides": True,
            "same_intrinsics_on_both_sides": True,
            "same_frame_selection_on_both_sides": True,
            "camera_authority": dataset.get("camera_authority"),
        },
        "selected_global_frame_indices": selected_ids,
        "frame_stride": stride,
        "frame_count": len(selected),
        "before_gif_path": str(before_gif),
        "after_gif_path": str(after_gif),
        "comparison_gif_path": str(comparison_gif),
        "terminal_visual_branch": True,
        "feeds_geometry_pipeline": False,
        "official_geometry_changed": False,
        "intended_reuse": (
            "Use the same renderer for later hole-fill/refinement gates so the "
            "artist sees the identical drone-camera replay before and after each adjustment."
        ),
    }
    out = output_root / "drone_replay_before_after.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(out)
    return manifest
