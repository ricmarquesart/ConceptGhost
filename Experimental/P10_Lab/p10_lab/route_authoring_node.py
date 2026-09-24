from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError
from .drone_route_plan import (
    DroneRoutePlan,
    bind_route_plan,
    parse_bound_route_plan,
    seed_plan_from_footprint,
)
from .drone_route_preview import build_route_preview_geometry, render_route_authoring_preview
from .mesh_clearance import build_clearance_cloud
from .route_collision import preflight_drone_route_plan
from .p9_boundary import validate_official_run
from .panorama import CameraAuthority
from .scene_coverage import derive_scene_footprint_from_primary_mesh


_CATEGORY="ConceptGhost/P10 Refined"


def _pretty(payload: dict) -> str:
    return json.dumps(payload,indent=2,sort_keys=True)


class ConceptGhostP10DroneRouteAuthoring:
    """Artist-authored P10 drone mission editor backend.

    The frontend owns click/drag/orbit interaction. This node validates and renders
    the same serialized 3D route plan into one Perspective orbit view plus
    synchronized metric-isotropic TOP/SIDE/FRONT views.
    Automatic geometry-aware planning is no longer route authority here; when
    no authored plan exists, a single editable starter mission is produced.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "run_dir":("STRING",{"forceInput":True}),
                "route_plan_json":(
                    "STRING",
                    {
                        "default":"",
                        "multiline":True,
                        "dynamicPrompts":False,
                    },
                ),
                "frames_per_drone":(
                    "INT",
                    {"default":30,"min":2,"max":240,"step":1},
                ),
                "min_clearance_m":(
                    "FLOAT",
                    {"default":0.20,"min":0.0,"max":10.0,"step":0.05},
                ),
            }
        }

    RETURN_TYPES=("IMAGE","STRING","STRING","STRING")
    RETURN_NAMES=(
        "route_workspace",
        "route_plan_json",
        "projection_json",
        "diagnostics_json",
    )
    FUNCTION="author"
    CATEGORY=_CATEGORY
    OUTPUT_NODE=True

    def author(
        self,
        run_dir: str,
        route_plan_json: str,
        frames_per_drone: int,
        min_clearance_m: float,
    ):
        try:
            import folder_paths
        except ImportError as error:
            raise RuntimeError("P10 route authoring requires ComfyUI folder_paths") from error

        boundary=validate_official_run(run_dir)
        camera=CameraAuthority.from_json(
            boundary.camera,
            expected_scene_contract_id=boundary.scene_contract_id,
        )
        footprint,footprint_evidence=derive_scene_footprint_from_primary_mesh(
            boundary.primary_mesh,
            camera,
        )

        authored=str(route_plan_json or "").strip()
        if authored:
            try:
                payload=json.loads(authored)
            except json.JSONDecodeError as error:
                raise ContractError(f"route_plan_json is invalid JSON: {error}") from error

            declared_authority=str(payload.get("route_authority") or "").strip().upper()
            try:
                plan,source,_stored_or_computed_hash=parse_bound_route_plan(
                    payload,
                    expected_scene_contract_id=boundary.scene_contract_id,
                    expected_source_run_id=boundary.run_id,
                    require_hash=False,
                )
            except ContractError:
                # An untouched seed from a previous source run is disposable
                # UI state. Never silently carry an artist-authored route into
                # another run/scene, but allow an old seed to regenerate.
                if declared_authority!="EDITABLE_SEED":
                    raise
                plan=seed_plan_from_footprint(
                    footprint,
                    frames_per_drone=int(frames_per_drone),
                )
                source="EDITABLE_SEED"

            # Global node settings are authoritative for all enabled drones.
            plan=DroneRoutePlan(
                missions=plan.missions,
                frames_per_drone=int(frames_per_drone),
                collision_mode=plan.collision_mode,
                min_clearance_m=float(min_clearance_m),
            )
        else:
            plan=seed_plan_from_footprint(
                footprint,
                frames_per_drone=int(frames_per_drone),
            )
            plan=DroneRoutePlan(
                missions=plan.missions,
                frames_per_drone=plan.frames_per_drone,
                collision_mode=plan.collision_mode,
                min_clearance_m=float(min_clearance_m),
            )
            source="EDITABLE_SEED"

        clearance_cloud=build_clearance_cloud(
            boundary.primary_mesh,
            camera,
            max_points=40000,
        )
        collision_report=preflight_drone_route_plan(
            plan,
            clearance_cloud,
        )

        preview,projection,render_diagnostics=render_route_authoring_preview(
            boundary.primary_mesh,
            camera,
            plan,
            source_image=boundary.source_image,
        )
        preview_geometry=build_route_preview_geometry(
            boundary.primary_mesh,
            camera,
            source_image=boundary.source_image,
            max_points=100000,
            max_mesh_faces=24000,
        )

        # DR9R-F: the four-view editor is rendered dynamically from preview_geometry.
        # Do not persist static route-editor PNGs that can become stale, duplicate
        # the Perspective geometry, or accumulate as disposable cache.
        output_root=(
            Path(folder_paths.get_output_directory())
            /"conceptghost"/"p10_route_editor"/boundary.run_id
        )
        output_root.mkdir(parents=True,exist_ok=True)

        serialized=bind_route_plan(
            plan,
            scene_contract_id=boundary.scene_contract_id,
            source_run_id=boundary.run_id,
            route_authority=source,
        )
        rendered_plan=_pretty(serialized)
        rendered_projection=_pretty(projection)
        diagnostics={
            "status":"PASS",
            "gate":"4.1R",
            "route_authority":source,
            "route_plan_sha256":serialized["route_plan_sha256"],
            "route_binding_schema":serialized["binding_schema"],
            "route_plan_persistence":"WORKFLOW_WIDGET_PLUS_SCENE_BOUND_HASH",
            "automatic_route_role":"SEED_FALLBACK_ONLY",
            "source_run_id":boundary.run_id,
            "scene_contract_id":boundary.scene_contract_id,
            "active_drone_count":len(plan.active_missions),
            "maximum_drone_count":7,
            "frames_per_drone":plan.frames_per_drone,
            "collision_mode":plan.collision_mode,
            "min_clearance_m":plan.min_clearance_m,
            "collision_preflight":collision_report.to_dict(),
            "clearance_surface":clearance_cloud.manifest(),
            "route_ready_for_generation":collision_report.blocked_mission_count==0,
            "scene_footprint":footprint_evidence,
            "preview":render_diagnostics,
            "base_preview":None,
            "preview_png_path":None,
            "base_preview_png_path":None,
            "workspace_rendering":"DYNAMIC_GEOMETRY_NO_STATIC_BACKGROUND",
            "preview_point_budget":preview_geometry["point_count"],
            "preview_point_lods":{
                name:int(payload["point_count"])
                for name,payload in preview_geometry.get("point_lods",{}).items()
            },
            "preview_mesh_lod":{
                "available":bool(preview_geometry.get("mesh_lod",{}).get("available")),
                "face_count":int(preview_geometry.get("mesh_lod",{}).get("face_count",0)),
                "vertex_count":int(preview_geometry.get("mesh_lod",{}).get("vertex_count",0)),
                "authority":"DISPLAY_ONLY_P9_PRIMARYMESH_LOD",
            },
            "route_editor_cache_path":str(output_root.resolve()),
            "interaction_contract":{
                "perspective":"ORBIT_PAN_ZOOM_INSPECTION_ONLY",
                "top":"RIGHT + FORWARD · AXIS_LOCKED · PAN_ZOOM",
                "side":"FORWARD + UP · AXIS_LOCKED · PAN_ZOOM",
                "front":"RIGHT + UP · AXIS_LOCKED · PAN_ZOOM",
                "same_3d_waypoint_shared_across_views":True,
                "orthographic_metric_scale_preserved":True,
                "perspective_uses_same_p9_local_geometry":True,
                "downstream_updates_on_next_queue_prompt":True,
                "reset_route_preserves_scene":True,
                "viewport_reset_preserves_route":True,
                "route_edit_preserves_zoom_pan":True,
                "max_orthographic_zoom":160.0,
                "max_perspective_zoom":48.0,
                "route_preset_export_import":True,
                "route_preset_rebinds_current_scene":True,
                "four_view_internal_resolution":[720,660],
                "static_background_used":False,
                "preview_modes":["POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH","MESH_SURFACE","MESH_WIREFRAME"],
                "preview_default":"POINTS_MEDIUM",
                "point_size_control":True,
                "mesh_preview_is_display_only":True,
                "selected_camera_live_preview":True,
                "selected_camera_frustum":True,
                "selected_camera_authoritative_refresh_node":"ConceptGhostP10SelectedDroneCameraPreview",
            },
        }
        rendered_diagnostics=_pretty(diagnostics)
        ui_metadata={
            "plan":serialized,
            "projection":projection,
            "collision_preflight":collision_report.to_dict(),
            "preview_geometry":preview_geometry,
            "camera_preview_contract":{
                "width":int(camera.width),
                "height":int(camera.height),
                "fx":float(camera.fx),
                "fy":float(camera.fy),
                "cx":float(camera.cx),
                "cy":float(camera.cy),
                "horizontal_fov_deg":float(camera.horizontal_fov_deg),
                "vertical_fov_deg":float(camera.vertical_fov_deg),
                "authority":"P9_ACCEPTED_CAMERA",
            },
            "diagnostics":diagnostics,
        }
        return {
            "ui":{
                # Do not expose the normal ComfyUI image widget here. The DOM
                # editor already renders the authoritative scene background;
                # a second image widget below it was a stale snapshot of the
                # previous execution and looked like a second, frozen route.
                "route_editor":[ui_metadata],
                "text":[rendered_diagnostics],
            },
            "result":(
                preview,
                rendered_plan,
                rendered_projection,
                rendered_diagnostics,
            ),
        }
