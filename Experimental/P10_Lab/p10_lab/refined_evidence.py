from __future__ import annotations

from dataclasses import dataclass
import json
from math import atan2, cos, pi, sin, sqrt
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .scene_coverage import derive_scene_footprint_from_primary_mesh, plan_geometry_aware_flights
from .mesh_clearance import build_clearance_cloud, adapt_paths_for_clearance
from .raw_holes import RawHoleFrame
from .disocclusion import build_disocclusion_mask
from .control_sequence import ControlFrameRecord, ControlSequenceManifest
from .camera_sequence import CameraFrameRecord, CameraSequenceManifest
from .drone_route_diagnostics import build_drone_route_diagnostics
from .drone_route_plan import (
    DroneRoutePlan,
    apply_hold_and_resume_clearance,
    bind_route_plan,
    parse_bound_route_plan,
    sample_route_plan,
)
from .p9_boundary import validate_official_run
from .panorama import CameraAuthority, PanoramaSpec
from .path_planner import RelativeWaypoint, plan_flights
from .world_camera import resolve_world_camera


@dataclass(frozen=True)
class RefinedEvidenceResult:
    p9_erp: Any
    source_erp: Any
    source_lock: Any
    flight_views: Any
    hole_masks: Any
    trajectory_map: Any
    gif_path: str
    control_manifest_path: str
    camera_manifest_path: str
    diagnostics: dict[str, Any]
    ui_images: tuple[dict[str, str], ...]


def _lazy_runtime():
    try:
        import numpy as np
        import torch
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise ContractError(
            "P10 Refined visual evidence requires NumPy, Torch and Pillow from the ComfyUI runtime"
        ) from error
    return np, torch, Image, ImageDraw


def _load_source_colors(boundary, np, Image):
    with Image.open(boundary.source_image) as opened:
        source = np.asarray(opened.convert("RGB"), dtype=np.uint8).copy()

    with np.load(boundary.primary_mesh, allow_pickle=False) as payload:
        required = {"vertices", "camera_depth"}
        missing = required.difference(payload.files)
        if missing:
            raise ContractError(f"PrimaryMesh missing evidence arrays: {sorted(missing)}")
        vertices = np.asarray(payload["vertices"], dtype=np.float32)
        depths = np.asarray(payload["camera_depth"], dtype=np.float32)
        if "grid_xy" in payload.files:
            grid = np.asarray(payload["grid_xy"], dtype=np.int64)
        elif "source_uv" in payload.files:
            grid = np.rint(np.asarray(payload["source_uv"], dtype=np.float64)).astype(np.int64)
        else:
            raise ContractError("PrimaryMesh is missing grid_xy/source_uv needed for preview colors")

    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ContractError("PrimaryMesh vertices must have shape [N,3]")
    if grid.shape != (vertices.shape[0], 2):
        raise ContractError("PrimaryMesh source coordinates do not match vertex count")
    if depths.reshape(-1).shape[0] != vertices.shape[0]:
        raise ContractError("PrimaryMesh camera_depth does not match vertex count")

    grid_x = np.clip(grid[:, 0], 0, source.shape[1] - 1)
    grid_y = np.clip(grid[:, 1], 0, source.shape[0] - 1)
    colors = source[grid_y, grid_x]
    return source, vertices, colors, depths.reshape(-1)


def _matrix_arrays(camera: CameraAuthority, np):
    world = np.asarray(camera.world_matrix, dtype=np.float64)
    rotation = world[:3, :3]
    center = world[:3, 3]
    return rotation, center


def _splat_points(indices, depth, colors, width, height, radius, np):
    zbuffer = np.full(width * height, np.inf, dtype=np.float32)
    idx_chunks = []
    dep_chunks = []
    col_chunks = []
    u, v = indices
    for dy in range(-radius, radius + 1):
        vv = v + dy
        row_ok = (vv >= 0) & (vv < height)
        for dx in range(-radius, radius + 1):
            uu = u + dx
            valid = row_ok & (uu >= 0) & (uu < width)
            if not np.any(valid):
                continue
            idx_chunks.append(vv[valid] * width + uu[valid])
            dep_chunks.append(depth[valid])
            col_chunks.append(colors[valid])
    if not idx_chunks:
        return np.zeros((height, width, 3), dtype=np.uint8), np.zeros((height, width), dtype=bool)

    flat_index = np.concatenate(idx_chunks)
    flat_depth = np.concatenate(dep_chunks)
    flat_color = np.concatenate(col_chunks)
    np.minimum.at(zbuffer, flat_index, flat_depth)

    nearest = np.isclose(flat_depth, zbuffer[flat_index], rtol=0.0, atol=1.0e-5)
    chosen_index = flat_index[nearest]
    chosen_color = flat_color[nearest]
    _, first = np.unique(chosen_index, return_index=True)

    image = np.zeros((height, width, 3), dtype=np.uint8)
    image.reshape(-1, 3)[chosen_index[first]] = chosen_color[first]
    coverage = np.isfinite(zbuffer).reshape(height, width)
    return image, coverage


def _render_perspective(
    vertices,
    colors,
    camera: CameraAuthority,
    pose,
    *,
    width: int,
    height: int,
    np,
):
    pose_world = np.asarray(pose.world_matrix, dtype=np.float64)
    rotation = pose_world[:3, :3]
    camera_center = pose_world[:3, 3]
    camera_points = (vertices - camera_center[None, :]) @ rotation
    depth = -camera_points[:, 2]
    valid = depth > 0.05

    scale_x = width / float(camera.width)
    scale_y = height / float(camera.height)
    u = (camera.cx + camera.fx * (camera_points[:, 0] / depth)) * scale_x
    v = (camera.cy - camera.fy * (camera_points[:, 1] / depth)) * scale_y
    valid &= (u >= -1.0) & (u < width + 1.0) & (v >= -1.0) & (v < height + 1.0)

    return _splat_points(
        (
            np.rint(u[valid]).astype(np.int32),
            np.rint(v[valid]).astype(np.int32),
        ),
        depth[valid].astype(np.float32),
        colors[valid],
        width,
        height,
        1,
        np,
    )


def _render_mesh_erp(vertices, colors, camera: CameraAuthority, spec: PanoramaSpec, np):
    rotation, center = _matrix_arrays(camera, np)
    points = (vertices - center[None, :]) @ rotation
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    radius = np.linalg.norm(points, axis=1)
    valid = radius > 1.0e-6

    yaw = np.arctan2(x, -z)
    pitch = np.arctan2(y, np.sqrt(x * x + z * z))
    u = (yaw / (2.0 * np.pi) + 0.5) * spec.width
    v = (0.5 - pitch / np.pi) * spec.height
    valid &= (u >= 0.0) & (u < spec.width) & (v >= 0.0) & (v < spec.height)

    return _splat_points(
        (
            np.rint(u[valid]).astype(np.int32),
            np.rint(v[valid]).astype(np.int32),
        ),
        radius[valid].astype(np.float32),
        colors[valid],
        spec.width,
        spec.height,
        1,
        np,
    )


def _render_source_erp(source, camera: CameraAuthority, spec: PanoramaSpec, np):
    ys = (np.arange(spec.height, dtype=np.float64) + 0.5)[:, None]
    xs = (np.arange(spec.width, dtype=np.float64) + 0.5)[None, :]
    latitude = (0.5 - ys / spec.height) * np.pi
    longitude = (xs / spec.width - 0.5) * (2.0 * np.pi)
    cos_latitude = np.cos(latitude)

    ray_x = np.sin(longitude) * cos_latitude
    ray_y = np.sin(latitude) * np.ones((1, spec.width), dtype=np.float64)
    ray_z = -np.cos(longitude) * cos_latitude
    forward = -ray_z
    safe_forward = np.maximum(forward, 1.0e-9)

    source_x = camera.cx + camera.fx * (ray_x / safe_forward)
    source_y = camera.cy - camera.fy * (ray_y / safe_forward)
    observed = (
        (forward > 0.0)
        & (source_x >= 0.0)
        & (source_x < camera.width)
        & (source_y >= 0.0)
        & (source_y < camera.height)
    )

    source_x = np.clip(np.rint(source_x).astype(np.int64), 0, camera.width - 1)
    source_y = np.clip(np.rint(source_y).astype(np.int64), 0, camera.height - 1)
    panorama = np.zeros((spec.height, spec.width, 3), dtype=np.uint8)
    panorama[observed] = source[source_y[observed], source_x[observed]]
    return panorama, observed


def _interpolate_look_direction(left: RelativeWaypoint, right: RelativeWaypoint, amount: float):
    """Interpolate camera look direction in angular space.

    A linear vector blend is invalid for antipodal directions because +forward
    and -forward cancel to (0,0,0) at the midpoint. Yaw/pitch interpolation
    keeps every intermediate look vector unit length and turns the camera
    continuously through 180 degrees at the far end of a round trip.
    """

    def angles(waypoint: RelativeWaypoint):
        look_right = float(waypoint.look_right)
        look_up = float(waypoint.look_up)
        look_forward = float(waypoint.look_forward)
        length = sqrt(
            look_right * look_right
            + look_up * look_up
            + look_forward * look_forward
        )
        if length <= 1.0e-12:
            raise ContractError("Waypoint look vector cannot have zero length")
        look_right /= length
        look_up /= length
        look_forward /= length
        yaw = atan2(look_right, look_forward)
        horizontal = sqrt(look_right * look_right + look_forward * look_forward)
        pitch = atan2(look_up, horizontal)
        return yaw, pitch

    left_yaw, left_pitch = angles(left)
    right_yaw, right_pitch = angles(right)

    delta_yaw = (right_yaw - left_yaw + pi) % (2.0 * pi) - pi
    # Exact 180-degree turns are ambiguous. Choose +pi deterministically so
    # the turnaround always rotates through camera-local +right instead of
    # allowing platform/library floating-point differences to pick a side.
    if abs(delta_yaw + pi) <= 1.0e-12:
        delta_yaw = pi

    yaw = left_yaw + delta_yaw * amount
    pitch = left_pitch * (1.0 - amount) + right_pitch * amount
    cos_pitch = cos(pitch)
    return (
        sin(yaw) * cos_pitch,
        sin(pitch),
        cos(yaw) * cos_pitch,
    )


def _interpolated_waypoints(path, steps_per_segment: int):
    result = []
    for index in range(len(path.waypoints) - 1):
        left = path.waypoints[index]
        right = path.waypoints[index + 1]
        for step in range(steps_per_segment):
            amount = step / float(steps_per_segment)
            look_right, look_up, look_forward = _interpolate_look_direction(
                left,
                right,
                amount,
            )
            result.append(
                RelativeWaypoint(
                    right=left.right * (1.0 - amount) + right.right * amount,
                    up=left.up * (1.0 - amount) + right.up * amount,
                    forward=left.forward * (1.0 - amount) + right.forward * amount,
                    look_right=look_right,
                    look_up=look_up,
                    look_forward=look_forward,
                )
            )
    result.append(path.waypoints[-1])
    return tuple(result)


def _trajectory_image(vertices, camera: CameraAuthority, resolved_paths, width, height, np, Image, ImageDraw):
    rotation, center = _matrix_arrays(camera, np)
    right_axis = rotation[:, 0]
    forward_axis = -rotation[:, 2]

    local = vertices - center[None, :]
    x = local @ right_axis
    z = local @ forward_axis
    sample = slice(None, None, max(1, vertices.shape[0] // 5000))
    x = x[sample]
    z = z[sample]

    all_positions = []
    for _, poses in resolved_paths:
        for pose in poses:
            delta = np.asarray(pose.position, dtype=np.float64) - center
            all_positions.append((float(delta @ right_axis), float(delta @ forward_axis)))

    radius = max(1.0, max(abs(value) for point in all_positions for value in point) * 1.35)
    local_mask = (np.abs(x) <= radius * 2.0) & (z >= -radius) & (z <= radius * 3.0)
    x = x[local_mask]
    z = z[local_mask]

    canvas = Image.new("RGB", (width, height), (22, 22, 22))
    draw = ImageDraw.Draw(canvas)
    margin = 28
    x_min, x_max = -radius * 1.5, radius * 1.5
    z_min, z_max = -radius * 0.5, radius * 2.5

    def map_point(px, pz):
        ux = margin + (px - x_min) / (x_max - x_min) * (width - 2 * margin)
        uy = height - margin - (pz - z_min) / (z_max - z_min) * (height - 2 * margin)
        return int(round(ux)), int(round(uy))

    for px, pz in zip(x, z):
        u, v = map_point(float(px), float(pz))
        if 0 <= u < width and 0 <= v < height:
            draw.point((u, v), fill=(90, 90, 90))

    path_colors = ((255, 180, 70), (80, 190, 255), (145, 235, 130), (220, 120, 255))
    for path_index, (name, poses) in enumerate(resolved_paths):
        points = []
        for pose in poses:
            delta = np.asarray(pose.position, dtype=np.float64) - center
            points.append(map_point(float(delta @ right_axis), float(delta @ forward_axis)))
        color = path_colors[path_index % len(path_colors)]
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        for point in points:
            draw.ellipse((point[0]-3, point[1]-3, point[0]+3, point[1]+3), fill=color)
        if points:
            draw.text((points[-1][0] + 5, points[-1][1] - 10), name, fill=color)

    origin = map_point(0.0, 0.0)
    draw.ellipse((origin[0]-5, origin[1]-5, origin[0]+5, origin[1]+5), fill=(255,255,255))
    draw.text((10, 8), "P10 camera paths over P9 local geometry", fill=(240,240,240))
    return np.asarray(canvas, dtype=np.uint8)


def _save_evidence_images(
    *,
    run_id: str,
    p9_erp,
    source_erp,
    source_lock,
    trajectory,
    flight_frames,
    hole_masks,
    raw_hole_frames,
    disocclusion_masks,
    frame_path_names,
    frame_path_indexes,
    camera_frames,
    scene_contract_id,
    path_labels,
    route_authority,
    route_plan_schema,
    route_plan_sha256,
    route_plan_payload,
    source_run_id,
    mission_modes,
    np,
    Image,
    ImageDraw,
):
    try:
        import folder_paths
        root = Path(folder_paths.get_output_directory()) / "conceptghost" / "p10_gate4" / run_id
    except ImportError:
        root = Path.cwd() / "conceptghost_p10_gate4" / run_id
    root.mkdir(parents=True, exist_ok=True)

    def save_ui(filename, array, *, mode="RGB"):
        if mode == "L":
            image = Image.fromarray(array.astype(np.uint8), mode="L").convert("RGB")
        else:
            image = Image.fromarray(array.astype(np.uint8))
        image.save(root / filename)
        ui_images.append({
            "filename": filename,
            "subfolder": f"conceptghost/p10_gate4/{run_id}",
            "type": "output",
        })

    def contact_sheet(arrays, *, mask=False, max_items=6):
        if not arrays:
            return None
        count=len(arrays)
        if count<=max_items:
            indexes=list(range(count))
        else:
            indexes=sorted({
                int(round(i*(count-1)/float(max_items-1)))
                for i in range(max_items)
            })
        tiles=[]
        tile_w=320
        for index in indexes:
            raw=np.asarray(arrays[index])
            if mask:
                if raw.dtype != np.uint8:
                    raw=(np.clip(raw,0.0,1.0)*255.0).round().astype(np.uint8)
                if raw.ndim==2:
                    image=Image.fromarray(raw,mode="L").convert("RGB")
                else:
                    image=Image.fromarray(raw.astype(np.uint8)).convert("RGB")
            else:
                image=Image.fromarray(raw.astype(np.uint8)).convert("RGB")
            tile_h=max(1,round(image.height*tile_w/float(image.width)))
            tiles.append(image.resize((tile_w,tile_h)))
        tile_h=max(image.height for image in tiles)
        sheet=Image.new("RGB",(tile_w*len(tiles),tile_h),(18,18,18))
        for i,image in enumerate(tiles):
            y=(tile_h-image.height)//2
            sheet.paste(image,(i*tile_w,y))
        return np.asarray(sheet,dtype=np.uint8)

    ui_images = []
    save_ui("p9_3d_partial_erp.png", p9_erp)
    save_ui("source_authority_partial_erp.png", source_erp)
    lock_preview=(np.asarray(source_lock,dtype=np.float32)>0.5).astype(np.uint8)*255
    save_ui("source_lock_known_unknown.png",lock_preview,mode="L")
    flight_sheet=contact_sheet(flight_frames,mask=False)
    if flight_sheet is not None:
        save_ui("drone_flight_views_contact_sheet.png",flight_sheet)
    hole_sheet=contact_sheet(hole_masks,mask=True)
    if hole_sheet is not None:
        save_ui("raw_holes_contact_sheet.png",hole_sheet)
    save_ui("camera_paths_topdown.png", trajectory)

    gif_frames = []
    for index, raw in enumerate(flight_frames):
        hole = hole_masks[index] > 0.5
        overlay = raw.astype(np.float32).copy()
        overlay[hole] = overlay[hole] * 0.45 + np.asarray([255.0, 64.0, 48.0]) * 0.55

        height, width = raw.shape[:2]
        frame = Image.new("RGB", (width * 2, height + 40), (18, 18, 18))
        frame.paste(Image.fromarray(raw), (0, 40))
        frame.paste(Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)), (width, 40))
        draw = ImageDraw.Draw(frame)
        draw.text((10, 10), path_labels[index], fill=(245,245,245))
        gif_frames.append(frame)

    gif_path = root / "P10_drone_flights_P9_holes.gif"
    if gif_frames:
        gif_frames[0].save(
            gif_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=160,
            loop=0,
            optimize=False,
        )

    control_root = root / "control_sequence"
    frame_root = control_root / "frames"
    mask_root = control_root / "masks"

    # These folders are ConceptGhost-owned derived state. Rebuild them exactly
    # so a shorter edited route cannot leave stale frames from an older plan.
    import shutil
    for owned in (frame_root, mask_root):
        if owned.exists():
            shutil.rmtree(owned)
        owned.mkdir(parents=True, exist_ok=True)

    route_plan_path = control_root / "route_plan.json"
    if route_plan_payload is not None:
        route_plan_path.write_text(
            json.dumps(route_plan_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    elif route_plan_path.exists():
        route_plan_path.unlink()

    records = []
    for global_index, raw in enumerate(flight_frames):
        frame_name = f"frame_{global_index:04d}.png"
        mask_name = f"mask_{global_index:04d}.png"
        Image.fromarray(raw).save(frame_root / frame_name)
        mask_array = (
            np.frombuffer(disocclusion_masks[global_index].mask, dtype=np.uint8)
            .reshape(raw_hole_frames[global_index].height, raw_hole_frames[global_index].width)
            .copy()
        )
        Image.fromarray(mask_array, mode="L").save(mask_root / mask_name)
        records.append(
            ControlFrameRecord(
                global_frame_index=global_index,
                path_name=frame_path_names[global_index],
                path_frame_index=frame_path_indexes[global_index],
                hole_fraction=raw_hole_frames[global_index].hole_fraction,
                frame_file=f"frames/{frame_name}",
                mask_file=f"masks/{mask_name}",
            )
        )

    control_manifest = ControlSequenceManifest(
        frames=tuple(records),
        width=int(flight_frames[0].shape[1]),
        height=int(flight_frames[0].shape[0]),
        route_authority=route_authority,
        route_plan_schema=route_plan_schema,
        route_plan_sha256=route_plan_sha256,
        route_plan_file=("route_plan.json" if route_plan_payload is not None else None),
        scene_contract_id=scene_contract_id,
        source_run_id=source_run_id,
        mission_modes=tuple(mission_modes),
    )
    control_manifest_path = control_root / "manifest.json"
    control_manifest_path.write_text(
        json.dumps(control_manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    camera_manifest = CameraSequenceManifest(
        frames=tuple(camera_frames),
        scene_contract_id=scene_contract_id,
        route_authority=route_authority,
        route_plan_schema=route_plan_schema,
        route_plan_sha256=route_plan_sha256,
        route_plan_file=("route_plan.json" if route_plan_payload is not None else None),
        source_run_id=source_run_id,
        mission_modes=tuple(mission_modes),
    )
    camera_manifest_path = control_root / "camera_manifest.json"
    camera_manifest_path.write_text(
        json.dumps(camera_manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return (
        str(gif_path),
        str(control_manifest_path),
        str(camera_manifest_path),
        tuple(ui_images),
    )


def build_refined_evidence(
    run_dir: str | Path,
    *,
    panorama_width: int = 1024,
    view_width: int = 640,
    steps_per_segment: int = 4,
    route_plan_json: str = "",
) -> RefinedEvidenceResult:
    if type(panorama_width) is not int or panorama_width < 512 or panorama_width % 2:
        raise ContractError("panorama_width must be an even integer >= 512")
    if type(view_width) is not int or view_width < 320:
        raise ContractError("view_width must be an integer >= 320")
    if type(steps_per_segment) is not int or not 1 <= steps_per_segment <= 12:
        raise ContractError("steps_per_segment must be in [1, 12]")

    np, torch, Image, ImageDraw = _lazy_runtime()
    boundary = validate_official_run(run_dir)
    camera = CameraAuthority.from_json(
        boundary.camera,
        expected_scene_contract_id=boundary.scene_contract_id,
    )
    source, vertices, colors, _ = _load_source_colors(boundary, np, Image)

    panorama_spec = PanoramaSpec(panorama_width, panorama_width // 2)
    p9_erp, p9_erp_coverage = _render_mesh_erp(vertices, colors, camera, panorama_spec, np)
    source_erp, source_lock = _render_source_erp(source, camera, panorama_spec, np)

    scene_footprint, footprint_evidence = derive_scene_footprint_from_primary_mesh(
        boundary.primary_mesh,
        camera,
    )
    clearance_cloud = build_clearance_cloud(
        boundary.primary_mesh,
        camera,
        max_points=40000 if str(route_plan_json or "").strip() else 12000,
    )

    authored_route_plan = None
    authored_clearance_reports = []
    authored_payload = str(route_plan_json or "").strip()
    if authored_payload:
        try:
            authored_route_payload = json.loads(authored_payload)
            authored_route_plan,declared_route_authority,route_plan_sha256 = parse_bound_route_plan(
                authored_route_payload,
                expected_scene_contract_id=boundary.scene_contract_id,
                expected_source_run_id=boundary.run_id,
                require_hash=False,
            )
        except (json.JSONDecodeError, ContractError) as error:
            raise ContractError(f"Artist drone route plan is invalid: {error}") from error

        sampled_paths = sample_route_plan(authored_route_plan)
        if authored_route_plan.collision_mode == "HOLD_AND_RESUME":
            active = []
            for path in sampled_paths:
                safe_path, report = apply_hold_and_resume_clearance(
                    path,
                    clearance_cloud.query,
                    min_clearance=authored_route_plan.min_clearance_m,
                    segment_is_blocked=lambda start, end: clearance_cloud.segment_is_blocked(
                        start,
                        end,
                        authored_route_plan.min_clearance_m,
                    ),
                )
                active.append(safe_path)
                authored_clearance_reports.append(report.to_dict())
            active_paths = tuple(active)
        else:
            active_paths = sampled_paths

        flight_plan = None
        clearance_batch = None
        clearance_fallback_to_unadapted = False
        route_authority = declared_route_authority
    else:
        flight_plan = plan_geometry_aware_flights(scene_footprint)
        clearance_batch = adapt_paths_for_clearance(
            flight_plan.paths,
            clearance_cloud,
            min_clearance=max(0.05, scene_footprint.median_depth * 0.01),
            samples_per_segment=2,
            shrink_factor=0.85,
            max_shrink_attempts=4,
        )
        clearance_fallback_to_unadapted = not clearance_batch.paths
        active_paths = clearance_batch.paths or flight_plan.paths
        route_authority = "AUTOMATIC_SEED_FALLBACK"

    if authored_route_plan is not None:
        route_plan_payload=bind_route_plan(
            authored_route_plan,
            scene_contract_id=boundary.scene_contract_id,
            source_run_id=boundary.run_id,
            route_authority=route_authority,
        )
        route_plan_schema=str(route_plan_payload.get("schema") or "")
        route_plan_sha256=str(route_plan_payload["route_plan_sha256"])
        mission_modes=tuple(
            (mission.name,mission.mode)
            for mission in authored_route_plan.active_missions
        )
    else:
        route_plan_payload=None
        route_plan_schema=None
        route_plan_sha256=None
        mission_modes=tuple((path.name,"AUTO") for path in active_paths)

    resolved_paths = []
    flight_frames = []
    hole_masks = []
    raw_hole_frames = []
    disocclusion_masks = []
    frame_path_names = []
    frame_path_indexes = []
    camera_frames = []
    labels = []
    coverage_by_path: dict[str, list[float]] = {}
    hole_fraction_by_path: dict[str, list[float]] = {}
    view_height = int(round(view_width * camera.height / camera.width))

    for path in active_paths:
        waypoints = (
            tuple(path.waypoints)
            if authored_route_plan is not None
            else _interpolated_waypoints(path, steps_per_segment)
        )
        poses = tuple(resolve_world_camera(camera, waypoint, frame_index=index) for index, waypoint in enumerate(waypoints))
        resolved_paths.append((path.name, poses))
        coverage_by_path[path.name] = []
        hole_fraction_by_path[path.name] = []
        for index, pose in enumerate(poses):
            frame, coverage = _render_perspective(
                vertices,
                colors,
                camera,
                pose,
                width=view_width,
                height=view_height,
                np=np,
            )
            flight_frames.append(frame)
            holes = (~coverage).astype(np.float32)
            hole_masks.append(holes)
            raw_frame = RawHoleFrame.from_coverage(
                view_width,
                view_height,
                coverage.reshape(-1).tolist(),
            )
            raw_hole_frames.append(raw_frame)
            hole_fraction_by_path[path.name].append(float(raw_frame.hole_fraction))
            disocclusion_masks.append(
                build_disocclusion_mask(
                    view_width,
                    view_height,
                    raw_frame.mask,
                )
            )
            frame_path_names.append(path.name)
            frame_path_indexes.append(index)
            sx = view_width / float(camera.width)
            sy = view_height / float(camera.height)
            camera_frames.append(
                CameraFrameRecord(
                    global_frame_index=len(camera_frames),
                    path_name=path.name,
                    path_frame_index=index,
                    width=view_width,
                    height=view_height,
                    fx=camera.fx * sx,
                    fy=camera.fy * sy,
                    cx=camera.cx * sx,
                    cy=camera.cy * sy,
                    world_matrix=pose.world_matrix,
                )
            )
            fraction = float(coverage.mean())
            coverage_by_path[path.name].append(fraction)
            waypoint = pose.relative_waypoint
            labels.append(
                f"{path.name}  frame {index + 1}/{len(poses)}  "
                f"coverage {fraction * 100.0:.1f}%  "
                f"R/U/F {waypoint.right:.2f}/{waypoint.up:.2f}/{waypoint.forward:.2f}"
            )

    trajectory = _trajectory_image(
        vertices,
        camera,
        resolved_paths,
        800,
        560,
        np,
        Image,
        ImageDraw,
    )

    gif_path, control_manifest_path, camera_manifest_path, ui_images = _save_evidence_images(
        run_id=boundary.run_id,
        p9_erp=p9_erp,
        source_erp=source_erp,
        source_lock=source_lock,
        trajectory=trajectory,
        flight_frames=flight_frames,
        hole_masks=hole_masks,
        raw_hole_frames=raw_hole_frames,
        disocclusion_masks=disocclusion_masks,
        frame_path_names=frame_path_names,
        frame_path_indexes=frame_path_indexes,
        camera_frames=camera_frames,
        scene_contract_id=boundary.scene_contract_id,
        path_labels=labels,
        route_authority=route_authority,
        route_plan_schema=route_plan_schema,
        route_plan_sha256=route_plan_sha256,
        route_plan_payload=route_plan_payload,
        source_run_id=boundary.run_id,
        mission_modes=mission_modes,
        np=np,
        Image=Image,
        ImageDraw=ImageDraw,
    )

    route_diagnostics = build_drone_route_diagnostics(
        authored_route_plan,
        tuple(active_paths),
        coverage_by_path,
        hole_fraction_by_path,
        authored_clearance_reports,
        route_authority=route_authority,
        route_plan_sha256=route_plan_sha256,
        scene_contract_id=boundary.scene_contract_id,
        source_run_id=boundary.run_id,
    )
    route_diagnostics_root = Path(control_manifest_path).parent.parent / "diagnostics"
    route_diagnostics_root.mkdir(parents=True, exist_ok=True)
    route_diagnostics_path = route_diagnostics_root / "drone_route_diagnostics.json"
    route_diagnostics_path.write_text(
        json.dumps(route_diagnostics, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    diagnostics = {
        "status": "PASS",
        "gate": 4,
        "subgate": "4.2",
        "source_run_id": boundary.run_id,
        "scene_contract_id": boundary.scene_contract_id,
        "source_stage": boundary.source_stage,
        "preview_kind": "INTEGRATED_REFINED_VISUAL_EVIDENCE",
        "panorama": {
            "width": panorama_spec.width,
            "height": panorama_spec.height,
            "p9_3d_observed_fraction": float(p9_erp_coverage.mean()),
            "source_authority_fraction": float(source_lock.mean()),
            "is_full_generated_panorama": False,
            "unknown_region_policy": "BLACK / UNGENERATED",
        },
        "scene_footprint": footprint_evidence,
        "route_authority": route_authority,
        "route_plan_schema": route_plan_schema,
        "route_plan_sha256": route_plan_sha256,
        "mission_order": [name for name,_mode in mission_modes],
        "mission_modes": {name:mode for name,mode in mission_modes},
        "artist_route_plan": route_plan_payload,
        "route_plan_file": (
            str((Path(control_manifest_path).parent / "route_plan.json").resolve())
            if route_plan_payload is not None else None
        ),
        "flight_plan": flight_plan.manifest() if flight_plan is not None else None,
        "clearance": {
            "cloud": clearance_cloud.manifest(),
            "batch": clearance_batch.manifest() if clearance_batch is not None else None,
            "artist_hold_and_resume": authored_clearance_reports,
            "minimum_required": (
                authored_route_plan.min_clearance_m
                if authored_route_plan is not None
                else max(0.05, scene_footprint.median_depth * 0.01)
            ),
            "all_blocked_advisory_fallback": clearance_fallback_to_unadapted,
            "policy": (
                "ARTIST_ROUTE_HOLD_LAST_SAFE_AND_RESUME"
                if authored_route_plan is not None
                else "ADVISORY_APPROXIMATE_VERTEX_CLEARANCE_FOR_END_TO_END_FIRST_PASS"
            ),
        },
        "route_diagnostics_path": str(route_diagnostics_path.resolve()),
        "route_diagnostics": route_diagnostics,
        "paths": {
            name: {
                "frame_count": len(values),
                "min_p9_coverage": min(values),
                "mean_p9_coverage": sum(values) / len(values),
                "max_p9_coverage": max(values),
                "min_hole_fraction": min(hole_fraction_by_path[name]),
                "mean_hole_fraction": (
                    sum(hole_fraction_by_path[name]) / len(hole_fraction_by_path[name])
                ),
                "max_hole_fraction": max(hole_fraction_by_path[name]),
            }
            for name, values in coverage_by_path.items()
        },
        "flight_gif_path": gif_path,
        "control_sequence_manifest_path": control_manifest_path,
        "camera_sequence_manifest_path": camera_manifest_path,
        "raw_holes": {
            "frame_count": len(raw_hole_frames),
            "policy": raw_hole_frames[0].policy if raw_hole_frames else None,
            "mean_hole_fraction": (
                sum(frame.hole_fraction for frame in raw_hole_frames) / len(raw_hole_frames)
                if raw_hole_frames else 0.0
            ),
        },
        "disocclusion": {
            "frame_count": len(disocclusion_masks),
            "policy": disocclusion_masks[0].policy if disocclusion_masks else None,
            "feathered": False,
            "dilated": False,
        },
        "rules": {
            "baseline_modified": False,
            "wan_generation_performed": False,
            "holes_are_raw_missing_P9_geometry": True,
            "source_authority_preserved": True,
        },
    }

    def image_tensor(array):
        return torch.from_numpy(array.astype(np.float32) / 255.0).unsqueeze(0)

    return RefinedEvidenceResult(
        p9_erp=image_tensor(p9_erp),
        source_erp=image_tensor(source_erp),
        source_lock=torch.from_numpy(source_lock.astype(np.float32)).unsqueeze(0),
        flight_views=torch.from_numpy(np.stack(flight_frames).astype(np.float32) / 255.0),
        hole_masks=torch.from_numpy(np.stack(hole_masks).astype(np.float32)),
        trajectory_map=image_tensor(trajectory),
        gif_path=gif_path,
        control_manifest_path=control_manifest_path,
        camera_manifest_path=camera_manifest_path,
        diagnostics=diagnostics,
        ui_images=ui_images,
    )
