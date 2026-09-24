from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from .colmap_dense_io import (
    colmap_camera_center,
    colmap_camera_point_to_world,
    load_colmap_sparse_cameras,
    load_colmap_sparse_images,
    read_colmap_consistency_graph,
    read_colmap_float_map,
)
from .contracts import ContractError
from .gate7_provenance import Gate7ProvenanceClass


_SCHEMA = "ConceptGhost.P10Gate7FreeSpaceEvidence.v0.1"


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 7.3 free-space evidence requires NumPy") from error
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


def _voxel_key(point, voxel_size: float) -> tuple[int, int, int]:
    return tuple(int(math.floor(float(value) / voxel_size)) for value in point)


def _voxel_center(key: tuple[int, int, int], voxel_size: float) -> tuple[float, float, float]:
    return tuple((float(value) + 0.5) * voxel_size for value in key)


def _distance(a, b) -> float:
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def _max_cross_route_angle_deg(entries, voxel_center) -> float:
    best = 0.0
    for i in range(len(entries)):
        route_i, center_i = entries[i]
        vi = tuple(float(voxel_center[k]) - float(center_i[k]) for k in range(3))
        ni = math.sqrt(sum(v * v for v in vi))
        if ni <= 1.0e-9:
            continue
        for j in range(i + 1, len(entries)):
            route_j, center_j = entries[j]
            if route_i == route_j:
                continue
            vj = tuple(float(voxel_center[k]) - float(center_j[k]) for k in range(3))
            nj = math.sqrt(sum(v * v for v in vj))
            if nj <= 1.0e-9:
                continue
            cosine = sum(vi[k] * vj[k] for k in range(3)) / (ni * nj)
            cosine = max(-1.0, min(1.0, cosine))
            best = max(best, math.degrees(math.acos(cosine)))
    return best


def _effective_frame_votes(by_route: dict[str, set[int]], cap_per_route: int) -> int:
    return sum(min(cap_per_route, len(frames)) for frames in by_route.values())


def _parse_dataset_frame_map(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frames = dataset.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ContractError("Gate 7.3 requires non-empty Gate 6 dataset frames")
    result = {}
    for frame in frames:
        if not isinstance(frame, dict):
            raise ContractError("Gate 6 dataset frame row must be an object")
        name = str(frame.get("image_name") or "").strip()
        route = str(frame.get("path_name") or "").strip()
        global_index = frame.get("global_frame_index")
        if not name or not route or type(global_index) is not int:
            raise ContractError("Gate 6 dataset frame is missing image_name/path_name/global_frame_index")
        if name in result:
            raise ContractError(f"Duplicate Gate 6 dataset image name: {name}")
        result[name] = frame
    return result


def _depth_and_graph_paths(dense_root: Path, image_name: str) -> tuple[Path, Path]:
    suffix = f"{image_name}.geometric.bin"
    return (
        dense_root / "stereo" / "depth_maps" / suffix,
        dense_root / "stereo" / "consistency_graphs" / suffix,
    )


def build_free_space_evidence(
    confidence_manifest_path: str | Path,
    output_root: str | Path,
    *,
    max_pixels_per_frame: int = 2200,
    voxel_fraction: float = 1.0 / 160.0,
    min_voxel_size_m: float = 0.01,
    max_voxel_size_m: float = 0.25,
    surface_margin_voxels: float = 1.5,
    free_step_voxels: float = 1.5,
    max_free_samples_per_ray: int = 96,
    min_consistent_sources: int = 2,
    cap_frames_per_route: int = 2,
    min_frame_coverage_ratio: float = 0.70,
    min_mission_coverage_ratio: float = 0.70,
    min_per_mission_frame_ratio: float = 0.70,
) -> dict[str, Any]:
    """Build sparse FREE/OCCUPIED evidence from COLMAP geometric depth maps.

    This stage does not alter geometry. Only geometrically-consistent depth
    samples contribute. Space behind the first supported surface is never
    labeled free.
    """

    np = _lazy_numpy()
    confidence_path = Path(confidence_manifest_path).resolve()
    confidence = _read_json(confidence_path, "Gate 7.2C confidence manifest")
    if confidence.get("schema") != "ConceptGhost.P10Gate7GeometryConfidence.v0.1":
        raise ContractError("Gate 7.3 requires Gate 7.2C confidence schema v0.1")
    if confidence.get("status") != "PASS":
        raise ContractError("Gate 7.3 requires Gate 7.2C status PASS")
    if confidence.get("geometry_confidence_refine") is not False:
        raise ContractError("Gate 7.3 source stage requires confidence refinement OFF")
    if confidence.get("official_geometry_changed") is not False:
        raise ContractError("Gate 7.3 refuses confidence input that changed geometry")
    if confidence.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7.3 refuses changed P9 authority")
    if confidence.get("ready_for_gate7_3") is not True:
        raise ContractError("Gate 7.2C did not promote this attempt to Gate 7.3")

    provenance_path = Path(str(confidence.get("provenance_manifest_path") or "")).resolve()
    provenance = _read_json(provenance_path, "Gate 7.2 provenance manifest")
    registration_path = Path(str(provenance.get("registration_manifest_path") or "")).resolve()
    registration = _read_json(registration_path, "Gate 7.1 registration manifest")
    dataset_manifest_path = Path(str(registration.get("dataset_manifest_path") or "")).resolve()
    dataset = _read_json(dataset_manifest_path, "Gate 6 dataset manifest")
    dataset_root = dataset_manifest_path.parent
    dense_root = dataset_root / "dense"

    if dataset.get("camera_authority") != "P9_BASELINE_WORLD_DERIVED":
        raise ContractError("Gate 7.3 requires P9-derived known cameras")
    if str(dataset.get("scene_contract_id") or "") != str(confidence.get("scene_contract_id") or ""):
        raise ContractError("Gate 7.3 Scene Contract mismatch")
    if str(dataset.get("run_id") or "") != str(confidence.get("p9_run_id") or ""):
        raise ContractError("Gate 7.3 source P9 run mismatch")

    for ratio_name, ratio_value in (
        ("min_frame_coverage_ratio", min_frame_coverage_ratio),
        ("min_mission_coverage_ratio", min_mission_coverage_ratio),
        ("min_per_mission_frame_ratio", min_per_mission_frame_ratio),
    ):
        if not math.isfinite(float(ratio_value)) or not 0.0 <= float(ratio_value) <= 1.0:
            raise ContractError(f"{ratio_name} must be finite within [0,1]")

    for name, value in (
        ("max_pixels_per_frame", max_pixels_per_frame),
        ("max_free_samples_per_ray", max_free_samples_per_ray),
        ("min_consistent_sources", min_consistent_sources),
        ("cap_frames_per_route", cap_frames_per_route),
    ):
        if type(value) is not int or value < 1:
            raise ContractError(f"{name} must be a positive integer")
    for name, value in (
        ("voxel_fraction", voxel_fraction),
        ("min_voxel_size_m", min_voxel_size_m),
        ("max_voxel_size_m", max_voxel_size_m),
        ("surface_margin_voxels", surface_margin_voxels),
        ("free_step_voxels", free_step_voxels),
    ):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
            raise ContractError(f"{name} must be finite and positive")
    if min_voxel_size_m > max_voxel_size_m:
        raise ContractError("min_voxel_size_m cannot exceed max_voxel_size_m")

    confidence_evidence_path = Path(str(confidence.get("evidence_npz_path") or "")).resolve()
    if not confidence_evidence_path.is_file():
        raise ContractError("Gate 7.2C confidence evidence NPZ is missing")
    with np.load(confidence_evidence_path, allow_pickle=False) as evidence:
        required = {"p9_points", "p9_provenance_labels"}
        missing = required.difference(evidence.files)
        if missing:
            raise ContractError(f"Confidence evidence is missing arrays: {sorted(missing)}")
        p9_points = np.asarray(evidence["p9_points"], dtype=np.float64)
        p9_labels = np.asarray(evidence["p9_provenance_labels"], dtype=np.uint8)

    if p9_points.ndim != 2 or p9_points.shape[1] != 3 or len(p9_points) != len(p9_labels):
        raise ContractError("Gate 7.3 P9 confidence evidence shape mismatch")
    if not np.isfinite(p9_points).all():
        raise ContractError("Gate 7.3 P9 points contain non-finite values")

    provenance_thresholds = provenance.get("thresholds") if isinstance(provenance.get("thresholds"), dict) else {}
    scene_diagonal_m = float(provenance_thresholds.get("scene_diagonal_m") or 0.0)
    if not math.isfinite(scene_diagonal_m) or scene_diagonal_m <= 0:
        raise ContractError("Gate 7.3 requires scene_diagonal_m from Gate 7.2 provenance")
    voxel_size = max(
        float(min_voxel_size_m),
        min(float(max_voxel_size_m), scene_diagonal_m * float(voxel_fraction)),
    )
    surface_margin = voxel_size * float(surface_margin_voxels)
    free_step = voxel_size * float(free_step_voxels)

    frame_by_name = _parse_dataset_frame_map(dataset)
    dense_sparse_root = dense_root / "sparse"
    cameras, camera_model_storage = load_colmap_sparse_cameras(dense_sparse_root)
    dense_images, image_model_storage = load_colmap_sparse_images(dense_sparse_root)
    dense_name_order = [str(row["name"]) for row in dense_images]
    dense_by_name = {str(row["name"]): row for row in dense_images}
    dataset_names = set(frame_by_name)
    dense_names = set(dense_name_order)
    missing_dense = sorted(dataset_names - dense_names)
    missing_dataset = sorted(dense_names - dataset_names)
    if missing_dataset:
        raise ContractError(
            "Dense sparse model contains images outside the authoritative Gate 6 dataset: "
            f"missing_dataset={missing_dataset[:10]}"
        )

    # Gate 7 uses the intersection of views that COLMAP actually registered and
    # for which geometric depth + consistency evidence exists. Missing views are
    # explicit diagnostics, not silently treated as FREE space.
    usable_dense_images = []
    missing_geometric_evidence = []
    for image_row in dense_images:
        image_name = str(image_row["name"])
        if image_name not in frame_by_name:
            continue
        depth_path, graph_path = _depth_and_graph_paths(dense_root, image_name)
        if depth_path.is_file() and graph_path.is_file():
            usable_dense_images.append(image_row)
        else:
            missing_geometric_evidence.append({
                "image_name": image_name,
                "depth_exists": depth_path.is_file(),
                "consistency_exists": graph_path.is_file(),
            })

    total_dataset_frames = len(frame_by_name)
    registered_frame_names = dataset_names & dense_names
    usable_frame_names = {str(row["name"]) for row in usable_dense_images}
    registered_frame_count = len(registered_frame_names)
    usable_frame_count = len(usable_frame_names)

    # Coverage authority is deliberately two-layered:
    # 1) authored -> COLMAP registration is a reconstruction-quality diagnostic;
    # 2) registered -> geometric evidence is the Gate 7 safety gate.
    #
    # Missing authored views remain UNKNOWN and never vote FREE.  Requiring 70%
    # of *all authored* frames here duplicated Gate 6 quality policy and made a
    # partial but valid known-camera reconstruction impossible to inspect.
    authored_registration_ratio = (
        registered_frame_count / float(total_dataset_frames)
        if total_dataset_frames else 0.0
    )
    frame_coverage_ratio = (
        usable_frame_count / float(registered_frame_count)
        if registered_frame_count else 0.0
    )

    route_totals: dict[str, int] = defaultdict(int)
    route_registered: dict[str, int] = defaultdict(int)
    route_usable: dict[str, int] = defaultdict(int)
    for frame in frame_by_name.values():
        route_totals[str(frame["path_name"])] += 1
    for name in registered_frame_names:
        route_registered[str(frame_by_name[name]["path_name"])] += 1
    for name in usable_frame_names:
        route_usable[str(frame_by_name[name]["path_name"])] += 1

    mission_rows = []
    qualifying_missions = 0
    registered_missions = 0
    for route in sorted(route_totals):
        total_frames = int(route_totals[route])
        registered_frames = int(route_registered.get(route, 0))
        usable_frames = int(route_usable.get(route, 0))
        if registered_frames:
            registered_missions += 1
        ratio = usable_frames / float(registered_frames) if registered_frames else 0.0
        authored_ratio = registered_frames / float(total_frames) if total_frames else 0.0
        qualifies = (
            registered_frames > 0
            and ratio >= float(min_per_mission_frame_ratio)
        )
        if qualifies:
            qualifying_missions += 1
        mission_rows.append({
            "mission": route,
            "dataset_frames": total_frames,
            "registered_colmap_frames": registered_frames,
            "usable_colmap_frames": usable_frames,
            "authored_registration_ratio": authored_ratio,
            "geometric_evidence_ratio": ratio,
            # Backward-compatible field name now explicitly means
            # usable / registered for Gate 7 evidence authority.
            "frame_coverage_ratio": ratio,
            "qualifies": qualifies,
        })

    mission_count = len(route_totals)
    mission_coverage_ratio = (
        qualifying_missions / float(registered_missions)
        if registered_missions else 0.0
    )
    authored_mission_registration_ratio = (
        registered_missions / float(mission_count)
        if mission_count else 0.0
    )

    if registered_frame_count <= 0:
        raise ContractError(
            "Gate 7 COLMAP dense sparse model contains no registered authoritative dataset views"
        )
    if frame_coverage_ratio < float(min_frame_coverage_ratio):
        raise ContractError(
            "Gate 7 COLMAP geometric-evidence coverage below threshold: "
            f"{usable_frame_count}/{registered_frame_count}="
            f"{frame_coverage_ratio:.3f} < {float(min_frame_coverage_ratio):.3f}; "
            f"authored_registration={registered_frame_count}/{total_dataset_frames}="
            f"{authored_registration_ratio:.3f}; "
            f"missing_dense={missing_dense[:10]}, "
            f"missing_geometric={[row['image_name'] for row in missing_geometric_evidence[:10]]}"
        )
    if mission_coverage_ratio < float(min_mission_coverage_ratio):
        raise ContractError(
            "Gate 7 COLMAP registered-mission geometric coverage below threshold: "
            f"{qualifying_missions}/{registered_missions}={mission_coverage_ratio:.3f} "
            f"< {float(min_mission_coverage_ratio):.3f}; "
            f"authored_mission_registration={registered_missions}/{mission_count}="
            f"{authored_mission_registration_ratio:.3f}; missions={mission_rows}"
        )
    if registered_missions < 2 or qualifying_missions < 2:
        raise ContractError(
            "Gate 7 free-space evidence requires at least two qualifying independent "
            "registered missions"
        )

    # All downstream evidence uses only registered + geometrically usable views.
    dense_images = tuple(usable_dense_images)
    dense_name_order = [str(row["name"]) for row in dense_images]
    dense_by_name = {str(row["name"]): row for row in dense_images}

    cells: dict[tuple[int, int, int], dict[str, Any]] = {}

    def cell_for(key):
        cell = cells.get(key)
        if cell is None:
            cell = {
                "free_by_route": defaultdict(set),
                "occupied_by_route": defaultdict(set),
                "free_camera_entries": [],
                "occupied_camera_entries": [],
                "free_consistency_sum": 0,
                "free_consistency_samples": 0,
                "occupied_consistency_sum": 0,
                "occupied_consistency_samples": 0,
                "p9_source_protected": False,
            }
            cells[key] = cell
        return cell

    protected_mask = p9_labels == int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED)
    for point in p9_points[protected_mask]:
        cell_for(_voxel_key(point, voxel_size))["p9_source_protected"] = True

    frame_diagnostics = []
    total_valid_depth_samples = 0
    total_selected_rays = 0
    total_free_cell_visits = 0

    for dense_index, image_row in enumerate(dense_images):
        image_name = str(image_row["name"])
        frame = frame_by_name[image_name]
        route = str(frame["path_name"])
        frame_id = int(frame["global_frame_index"])
        camera_id = int(image_row["camera_id"])
        camera = cameras.get(camera_id)
        if camera is None:
            raise ContractError(f"Dense image references missing camera {camera_id}: {image_name}")

        depth_path, graph_path = _depth_and_graph_paths(dense_root, image_name)
        depth = read_colmap_float_map(depth_path, expected_channels=1)
        height, width = depth.shape
        if width != int(camera["width"]) or height != int(camera["height"]):
            raise ContractError(
                f"Depth/camera calibration mismatch for {image_name}: "
                f"depth={width}x{height}, camera={camera['width']}x{camera['height']}"
            )

        stride = max(1, int(math.ceil(math.sqrt((width * height) / float(max_pixels_per_frame)))))
        selected_pixels = []
        valid_depth_count = 0
        for row in range(stride // 2, height, stride):
            for col in range(stride // 2, width, stride):
                value = float(depth[row, col])
                if math.isfinite(value) and value > 0.0:
                    valid_depth_count += 1
                    selected_pixels.append((row, col))

        graph_header, graph = read_colmap_consistency_graph(
            graph_path,
            selected_pixels=selected_pixels,
            max_source_index=len(dense_name_order) - 1,
        )
        if graph_header[0] != width or graph_header[1] != height:
            raise ContractError(f"Depth/consistency dimensions mismatch for {image_name}")

        center = colmap_camera_center(image_row["qvec"], image_row["tvec"])
        fx, fy = float(camera["fx"]), float(camera["fy"])
        cx, cy = float(camera["cx"]), float(camera["cy"])

        accepted = 0
        for row, col in selected_pixels:
            sources = graph.get((row, col), ())
            if len(sources) < min_consistent_sources:
                continue
            depth_value = float(depth[row, col])
            x_camera = ((float(col) + 0.5) - cx) / fx * depth_value
            y_camera = ((float(row) + 0.5) - cy) / fy * depth_value
            z_camera = depth_value
            endpoint = colmap_camera_point_to_world(
                image_row["qvec"],
                image_row["tvec"],
                (x_camera, y_camera, z_camera),
            )
            ray_distance = _distance(center, endpoint)
            if not math.isfinite(ray_distance) or ray_distance <= surface_margin:
                continue

            occupied = cell_for(_voxel_key(endpoint, voxel_size))
            occupied["occupied_by_route"][route].add(frame_id)
            occupied["occupied_camera_entries"].append((route, center))
            occupied["occupied_consistency_sum"] += len(sources)
            occupied["occupied_consistency_samples"] += 1

            dx = endpoint[0] - center[0]
            dy = endpoint[1] - center[1]
            dz = endpoint[2] - center[2]
            free_length = max(0.0, ray_distance - surface_margin)
            sample_count = min(
                max_free_samples_per_ray,
                max(0, int(math.floor(free_length / free_step))),
            )
            previous_key = None
            for step_index in range(1, sample_count + 1):
                travel = min(free_length, step_index * free_step)
                alpha = travel / ray_distance
                point = (
                    center[0] + dx * alpha,
                    center[1] + dy * alpha,
                    center[2] + dz * alpha,
                )
                key = _voxel_key(point, voxel_size)
                if key == previous_key:
                    continue
                previous_key = key
                free = cell_for(key)
                free["free_by_route"][route].add(frame_id)
                free["free_camera_entries"].append((route, center))
                free["free_consistency_sum"] += len(sources)
                free["free_consistency_samples"] += 1
                total_free_cell_visits += 1

            accepted += 1
            total_selected_rays += 1

        total_valid_depth_samples += valid_depth_count
        frame_diagnostics.append(
            {
                "image_name": image_name,
                "global_frame_index": frame_id,
                "route": route,
                "depth_width": width,
                "depth_height": height,
                "sampling_stride": stride,
                "sampled_valid_depth_pixels": valid_depth_count,
                "accepted_consistent_rays": accepted,
            }
        )

    keys = sorted(cells)
    voxel_centers = []
    free_votes = []
    occupied_votes = []
    free_route_count = []
    occupied_route_count = []
    free_frame_count = []
    occupied_frame_count = []
    free_angle_deg = []
    occupied_angle_deg = []
    free_consistency_mean = []
    occupied_consistency_mean = []
    protected = []

    for key in keys:
        cell = cells[key]
        center = _voxel_center(key, voxel_size)
        voxel_centers.append(center)
        f_votes = _effective_frame_votes(cell["free_by_route"], cap_frames_per_route)
        o_votes = _effective_frame_votes(cell["occupied_by_route"], cap_frames_per_route)
        free_votes.append(f_votes)
        occupied_votes.append(o_votes)
        free_route_count.append(len(cell["free_by_route"]))
        occupied_route_count.append(len(cell["occupied_by_route"]))
        free_frame_count.append(sum(len(v) for v in cell["free_by_route"].values()))
        occupied_frame_count.append(sum(len(v) for v in cell["occupied_by_route"].values()))
        free_angle_deg.append(_max_cross_route_angle_deg(cell["free_camera_entries"], center))
        occupied_angle_deg.append(_max_cross_route_angle_deg(cell["occupied_camera_entries"], center))
        free_consistency_mean.append(
            cell["free_consistency_sum"] / float(max(1, cell["free_consistency_samples"]))
        )
        occupied_consistency_mean.append(
            cell["occupied_consistency_sum"] / float(max(1, cell["occupied_consistency_samples"]))
        )
        protected.append(1 if cell["p9_source_protected"] else 0)

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_path = output_root / "free_space_raw_evidence.npz"
    np.savez_compressed(
        evidence_path,
        voxel_keys=np.asarray(keys, dtype=np.int32),
        voxel_centers=np.asarray(voxel_centers, dtype=np.float32),
        free_effective_votes=np.asarray(free_votes, dtype=np.int16),
        occupied_effective_votes=np.asarray(occupied_votes, dtype=np.int16),
        free_route_count=np.asarray(free_route_count, dtype=np.int16),
        occupied_route_count=np.asarray(occupied_route_count, dtype=np.int16),
        free_frame_count=np.asarray(free_frame_count, dtype=np.int16),
        occupied_frame_count=np.asarray(occupied_frame_count, dtype=np.int16),
        free_max_cross_route_angle_deg=np.asarray(free_angle_deg, dtype=np.float32),
        occupied_max_cross_route_angle_deg=np.asarray(occupied_angle_deg, dtype=np.float32),
        free_consistency_mean=np.asarray(free_consistency_mean, dtype=np.float32),
        occupied_consistency_mean=np.asarray(occupied_consistency_mean, dtype=np.float32),
        p9_source_protected=np.asarray(protected, dtype=np.uint8),
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.3A",
        "mode": "SPARSE_VISIBILITY_EVIDENCE_ONLY_NO_GEOMETRY_MUTATION",
        "scene_contract_id": confidence.get("scene_contract_id"),
        "p9_run_id": confidence.get("p9_run_id"),
        "p10_attempt_id": confidence.get("p10_attempt_id"),
        "coordinate_space": "P9_CANONICAL_WORLD_METERS",
        "camera_authority": dataset.get("camera_authority"),
        "image_authority": dataset.get("image_authority"),
        "dense_sparse_model_storage": {
            "camera_model": camera_model_storage,
            "image_model": image_model_storage,
            "sparse_root": str(dense_sparse_root.resolve()),
        },
        "depth_authority": "COLMAP_PATCHMATCH_GEOMETRIC",
        "consistency_policy": "REQUIRE_GEOMETRIC_CONSISTENCY_GRAPH_SUPPORT",
        "ray_policy": {
            "free_segment": "CAMERA_TO_FIRST_SUPPORTED_SURFACE_MINUS_MARGIN",
            "occupied_surface": "FIRST_SUPPORTED_DEPTH_ENDPOINT",
            "behind_surface": "UNKNOWN_NEVER_FREE",
            "invalid_depth": "UNKNOWN_NEVER_FREE",
        },
        "voxel": {
            "voxel_size_m": voxel_size,
            "voxel_fraction_of_scene_diagonal": float(voxel_fraction),
            "surface_margin_m": surface_margin,
            "free_step_m": free_step,
            "cap_frames_per_route": cap_frames_per_route,
        },
        "colmap_coverage": {
            "policy": "REGISTERED_VIEW_GEOMETRIC_EVIDENCE_REQUIRE_70_PERCENT_MISSING_AUTHORED_UNKNOWN",
            "dataset_frame_count": total_dataset_frames,
            "dense_sparse_registered_frame_count": registered_frame_count,
            "usable_geometric_frame_count": usable_frame_count,
            "missing_dense_frame_count": len(missing_dense),
            "missing_dense_frames": missing_dense,
            "missing_geometric_evidence_count": len(missing_geometric_evidence),
            "missing_geometric_evidence": missing_geometric_evidence,
            "authored_registration_ratio": authored_registration_ratio,
            "frame_coverage_ratio": frame_coverage_ratio,
            "geometric_evidence_coverage_ratio": frame_coverage_ratio,
            "min_frame_coverage_ratio": float(min_frame_coverage_ratio),
            "mission_count": mission_count,
            "registered_mission_count": registered_missions,
            "authored_mission_registration_ratio": authored_mission_registration_ratio,
            "qualifying_mission_count": qualifying_missions,
            "mission_coverage_ratio": mission_coverage_ratio,
            "min_mission_coverage_ratio": float(min_mission_coverage_ratio),
            "min_per_mission_frame_ratio": float(min_per_mission_frame_ratio),
            "missions": mission_rows,
            "pass": True,
        },
        "sampling": {
            "max_pixels_per_frame": max_pixels_per_frame,
            "max_free_samples_per_ray": max_free_samples_per_ray,
            "min_consistent_sources": min_consistent_sources,
            "frame_count": len(frame_diagnostics),
            "dataset_frame_count": total_dataset_frames,
            "authored_registration_ratio": authored_registration_ratio,
            "usable_frame_coverage_ratio": frame_coverage_ratio,
            "qualifying_mission_coverage_ratio": mission_coverage_ratio,
            "sampled_valid_depth_pixels": total_valid_depth_samples,
            "accepted_consistent_rays": total_selected_rays,
            "free_cell_visits": total_free_cell_visits,
            "sparse_voxel_count": len(keys),
        },
        "frames": frame_diagnostics,
        "evidence_npz_path": str(evidence_path),
        "confidence_manifest_path": str(confidence_path),
        "dataset_manifest_path": str(dataset_manifest_path),
        "dense_workspace": str(dense_root),
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "ready_for_free_space_classification": True,
        "ready_for_destructive_fusion": False,
    }
    manifest_path = output_root / "free_space_evidence_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(manifest_path)
    return result
