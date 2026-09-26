from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from .contracts import ContractError
from .drone_route_plan import DroneMission, DroneWaypoint, parse_bound_route_plan
from .p9_boundary import validate_official_run
from .result_output_contract import stage_root, update_stage_status
from .result_output_nodes import _save_image


_CATEGORY = "ConceptGhost/P10 Author Integration"
_MAX_AUTHOR_ROUTES = 5
_AUTHOR_FRAME_LENGTH = 81


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _normalize(x: float, y: float, z: float) -> tuple[float, float, float]:
    length = math.sqrt(x * x + y * y + z * z)
    if length <= 1.0e-10:
        raise ContractError("Author rail look direction cannot have zero length")
    return x / length, y / length, z / length


def _point_tuple(point: DroneWaypoint) -> tuple[float, float, float]:
    return float(point.right), float(point.up), float(point.forward)


def _look_target_for_index(
    mission: DroneMission,
    points: list[DroneWaypoint],
    index: int,
) -> tuple[float, float, float]:
    point = points[index]
    px, py, pz = _point_tuple(point)

    if point.has_look_direction:
        dx, dy, dz = _normalize(
            float(point.look_right),
            float(point.look_up),
            float(point.look_forward),
        )
        return px + dx, py + dy, pz + dz

    if mission.orientation_mode == "LOOK_AT_TARGET":
        if mission.look_target is None:
            raise ContractError(f"Mission {mission.name} LOOK_AT_TARGET has no target")
        return _point_tuple(mission.look_target)

    if mission.orientation_mode == "MANUAL_DIRECTION":
        if mission.manual_direction is None:
            raise ContractError(f"Mission {mission.name} MANUAL_DIRECTION has no direction")
        dx, dy, dz = _normalize(*_point_tuple(mission.manual_direction))
        return px + dx, py + dy, pz + dz

    # LOOK_ALONG_PATH: author per-point look target follows the local route tangent.
    if index < len(points) - 1:
        nx, ny, nz = _point_tuple(points[index + 1])
        dx, dy, dz = _normalize(nx - px, ny - py, nz - pz)
    else:
        qx, qy, qz = _point_tuple(points[index - 1])
        dx, dy, dz = _normalize(px - qx, py - qy, pz - qz)
    return px + dx, py + dy, pz + dz


def mission_to_author_anchors(mission: DroneMission) -> tuple[str, dict]:
    """Convert one ConceptGhost PATH mission into the author's 6-value anchor format.

    The author CameraPlot node uses +X right, +Y up, +Z forward with the
    panorama capture at origin. ConceptGhost route files use the same local
    axes, so no invented coordinate transform is needed.
    """
    if mission.mode != "PATH":
        raise ContractError(
            f"Author CameraPlot adapter v1 requires PATH missions; {mission.name} is {mission.mode}. "
            "Use an orbit/figure8 PATH for closed-loop consistency."
        )

    points = list(mission.waypoints)
    prepended_origin = False
    first = points[0]
    first_distance = math.sqrt(first.right ** 2 + first.up ** 2 + first.forward ** 2)
    if first_distance > 1.0e-8:
        # CameraPlot pins anchor 0 to the panorama origin. Make that explicit in
        # the serialized route instead of letting the author node silently move it.
        points.insert(0, DroneWaypoint(0.0, 0.0, 0.0))
        prepended_origin = True

    rows = []
    for index, point in enumerate(points):
        px, py, pz = _point_tuple(point)
        tx, ty, tz = _look_target_for_index(mission, points, index)
        rows.append(
            f"{px:.6f}, {py:.6f}, {pz:.6f}, {tx:.6f}, {ty:.6f}, {tz:.6f}"
        )

    return "\n".join(rows), {
        "mission_name": mission.name,
        "author_orientation": "per_point_look",
        "author_frame_length": _AUTHOR_FRAME_LENGTH,
        "prepended_panorama_origin": prepended_origin,
        "coordinate_space": "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "author_coordinate_match": "+X_RIGHT_+Y_UP_+Z_FORWARD",
        "anchor_count": len(points),
        "source_orientation_mode": mission.orientation_mode,
    }


class ConceptGhostP10AuthorRouteAdapter:
    """Map one committed ConceptGhost route into the author's CameraPlot anchors."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_p9_run_dir": ("STRING", {"forceInput": True}),
                "route_plan_json": ("STRING", {"forceInput": True}),
                "mission_index": ("INT", {"default": 0, "min": 0, "max": 4, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("author_anchors", "mission_name", "author_frame_length", "diagnostics_json")
    FUNCTION = "adapt"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def adapt(self, source_p9_run_dir: str, route_plan_json: str, mission_index: int):
        boundary = validate_official_run(source_p9_run_dir)
        try:
            payload = json.loads(str(route_plan_json))
        except json.JSONDecodeError as error:
            raise ContractError(f"Author route adapter received invalid route JSON: {error}") from error

        plan, authority, route_hash = parse_bound_route_plan(
            payload,
            expected_scene_contract_id=boundary.scene_contract_id,
            expected_source_run_id=boundary.run_id,
            require_hash=True,
        )
        active = list(plan.active_missions)
        index = int(mission_index)
        if index >= len(active):
            raise ContractError(
                f"Author ADV workflow route slot {index + 1} has no active ConceptGhost mission; "
                f"active mission count is {len(active)}"
            )
        if len(active) > _MAX_AUTHOR_ROUTES:
            raise ContractError(
                f"Current author ADV integration supports {_MAX_AUTHOR_ROUTES} active routes; "
                f"received {len(active)}"
            )

        anchors, details = mission_to_author_anchors(active[index])
        diagnostics = {
            "status": "PASS",
            "schema": "ConceptGhost.AuthorRouteAdapter.v0.1",
            "mission_index": index,
            "route_plan_sha256": route_hash,
            "route_authority": authority,
            "source_run_id": boundary.run_id,
            "scene_contract_id": boundary.scene_contract_id,
            **details,
        }
        return anchors, active[index].name, _AUTHOR_FRAME_LENGTH, _pretty(diagnostics)


class ConceptGhostP10AuthorRailGate:
    """Persist CameraPlot rail evidence before allowing WAN/HiRes downstream."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "source_p9_run_dir": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "route_plan_json": ("STRING", {"forceInput": True}),
                "mission_index": ("INT", {"default": 0, "min": 0, "max": 4, "step": 1}),
                "author_anchors": ("STRING", {"forceInput": True}),
                "mission_name": ("STRING", {"forceInput": True}),
                "control_video": ("IMAGE",),
                "control_mask": ("IMAGE",),
                "camera_preview": ("IMAGE",),
                "rail_json": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "control_video",
        "control_mask",
        "rail_json",
        "mission_name",
        "diagnostics_json",
    )
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        source_p9_run_dir: str,
        scene_contract_id: str,
        route_plan_json: str,
        mission_index: int,
        author_anchors: str,
        mission_name: str,
        control_video,
        control_mask,
        camera_preview,
        rail_json: str,
    ):
        attempt = Path(p10_attempt_root).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("CG-04 author rail gate attempt identity/path mismatch")

        attempt_manifest_path = attempt / "attempt_manifest.json"
        if not attempt_manifest_path.is_file():
            raise ContractError("CG-04 requires attempt_manifest.json")
        attempt_manifest = json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
        scene_id = str(scene_contract_id or "").strip()
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("CG-04 scene_contract_id does not match attempt")

        boundary = validate_official_run(source_p9_run_dir)
        if boundary.scene_contract_id != scene_id:
            raise ContractError("CG-04 P9 scene identity mismatch")

        try:
            route_payload = json.loads(str(route_plan_json))
        except json.JSONDecodeError as error:
            raise ContractError(f"CG-04 received invalid route JSON: {error}") from error
        plan, authority, route_hash = parse_bound_route_plan(
            route_payload,
            expected_scene_contract_id=boundary.scene_contract_id,
            expected_source_run_id=boundary.run_id,
            require_hash=True,
        )
        active = list(plan.active_missions)
        index = int(mission_index)
        if index >= len(active):
            raise ContractError("CG-04 mission index is outside active route plan")
        expected_name = active[index].name
        if str(mission_name) != expected_name:
            raise ContractError(
                f"CG-04 mission name mismatch: {mission_name!r} != {expected_name!r}"
            )

        source_rail = Path(str(rail_json)).expanduser().resolve()
        if not source_rail.is_file():
            raise ContractError(f"Author CameraPlot rail JSON does not exist: {source_rail}")

        stage = stage_root(attempt, "CG_04")
        outputs = stage / "OUTPUTS"
        previews = stage / "PREVIEWS"
        manifests = stage / "MANIFESTS"
        logs = stage / "LOGS"
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in expected_name)
        mission_out = outputs / safe_name
        mission_out.mkdir(parents=True, exist_ok=True)

        anchors_path = mission_out / "anchors.txt"
        anchors_path.write_text(str(author_anchors).strip() + "\n", encoding="utf-8")
        rail_copy = mission_out / "rail.json"
        shutil.copy2(source_rail, rail_copy)
        _save_image(mission_out / "control_first_frame.png", control_video)
        _save_image(mission_out / "control_mask_first_frame.png", control_mask)

        camera_preview_path = previews / f"{safe_name}_camera_path.png"
        _save_image(camera_preview_path, camera_preview)

        mission_manifest = {
            "schema": "ConceptGhost.CG04AuthorRailMission.v0.1",
            "status": "PASS",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "source_run_id": boundary.run_id,
            "route_plan_sha256": route_hash,
            "route_authority": authority,
            "mission_index": index,
            "mission_name": expected_name,
            "author_orientation": "per_point_look",
            "author_frame_length": _AUTHOR_FRAME_LENGTH,
            "coordinate_space": "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
            "anchors_path": str(anchors_path),
            "rail_path": str(rail_copy),
            "camera_preview_path": str(camera_preview_path),
        }
        mission_manifest_path = manifests / f"{index + 1:02d}_{safe_name}.json"
        mission_manifest_path.write_text(_pretty(mission_manifest) + "\n", encoding="utf-8")
        (logs / f"{index + 1:02d}_{safe_name}.log").write_text(
            f"CG-04 author rail captured.\nmission={expected_name}\nrail={rail_copy}\n",
            encoding="utf-8",
        )

        expected_count = len(active)
        present = []
        for mission_pos, item in enumerate(active):
            item_safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in item.name)
            path = manifests / f"{mission_pos + 1:02d}_{item_safe}.json"
            if path.is_file():
                present.append(item.name)

        complete = len(present) == expected_count
        aggregate = {
            "schema": "ConceptGhost.CG04AuthorRailsIndex.v0.1",
            "status": "PASS" if complete else "PARTIAL",
            "p10_attempt_id": attempt_id,
            "route_plan_sha256": route_hash,
            "expected_active_missions": [item.name for item in active],
            "published_missions": present,
            "published_count": len(present),
            "expected_count": expected_count,
            "all_author_rails_published": complete,
        }
        aggregate_path = manifests / "cg04_author_rails_index.json"
        aggregate_path.write_text(_pretty(aggregate) + "\n", encoding="utf-8")

        status = update_stage_status(
            attempt,
            p10_attempt_id=attempt_id,
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=scene_id,
            stage_code="CG_04",
            runtime_status="PASS",
            functional_status="PASS" if complete else "PENDING",
            artist_quality_status="PENDING",
            notes=[
                f"Published author CameraPlot rail for {expected_name}.",
                f"{len(present)}/{expected_count} active mission rails are physically present.",
            ],
        )

        diagnostics = {
            "status": "PASS" if complete else "PARTIAL",
            "stage": "CG_04",
            "mission_name": expected_name,
            "rail_copy": str(rail_copy),
            "camera_preview": str(camera_preview_path),
            "aggregate_manifest": str(aggregate_path),
            "all_author_rails_published": complete,
            "stage_status_path": status["status_path"],
        }
        return (
            control_video,
            control_mask,
            str(rail_copy),
            expected_name,
            _pretty(diagnostics),
        )


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorRouteAdapter": ConceptGhostP10AuthorRouteAdapter,
    "ConceptGhostP10AuthorRailGate": ConceptGhostP10AuthorRailGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorRouteAdapter": "P10 · CG-04 · Adapt ConceptGhost Route to Author CameraPlot",
    "ConceptGhostP10AuthorRailGate": "P10 · CG-04 · Publish Author Rail Evidence + Gate",
}
