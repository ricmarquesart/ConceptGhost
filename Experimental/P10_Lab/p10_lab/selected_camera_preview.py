from __future__ import annotations

import json
import math
from pathlib import Path

from .contracts import ContractError
from .drone_route_plan import DroneMission, DroneRoutePlan, parse_bound_route_plan
from .drone_route_preview import build_route_preview_geometry
from .p9_boundary import validate_official_run
from .panorama import CameraAuthority


def _normalize(vector: tuple[float,float,float], label: str) -> tuple[float,float,float]:
    length=math.sqrt(sum(float(value)*float(value) for value in vector))
    if not math.isfinite(length) or length<=1.0e-12:
        raise ContractError(f"{label} cannot have zero length")
    return tuple(float(value)/length for value in vector)


def _dot(a,b) -> float:
    return sum(float(left)*float(right) for left,right in zip(a,b))


def _cross_standard(a,b) -> tuple[float,float,float]:
    return (
        a[1]*b[2]-a[2]*b[1],
        a[2]*b[0]-a[0]*b[2],
        a[0]*b[1]-a[1]*b[0],
    )


def _physical_cross_in_ruf(a,b) -> tuple[float,float,float]:
    # RUF = right/up/forward where forward is -camera-Z. This basis is
    # left-handed relative to XYZ, so a physical world cross product is the
    # negative of the ordinary component-space cross product.
    raw=_cross_standard(a,b)
    return tuple(-value for value in raw)


def route_local_camera_basis(
    look: tuple[float,float,float],
) -> tuple[
    tuple[float,float,float],
    tuple[float,float,float],
    tuple[float,float,float],
]:
    """Return right/up/forward camera axes expressed in P9 RUF coordinates.

    This matches world_camera._resolved_rotation, including its canonical-up
    fallback, but stays entirely in the Route Editor's camera-local coordinate
    system.
    """

    forward=_normalize(look,"selected camera look direction")
    canonical_up=(0.0,1.0,0.0)
    right_candidate=_physical_cross_in_ruf(forward,canonical_up)
    if math.sqrt(_dot(right_candidate,right_candidate))<=1.0e-12:
        canonical_right=(1.0,0.0,0.0)
        projection=_dot(canonical_right,forward)
        right_candidate=tuple(
            canonical_right[index]-projection*forward[index]
            for index in range(3)
        )
    right=_normalize(right_candidate,"selected camera right axis")
    up=_normalize(
        _physical_cross_in_ruf(right,forward),
        "selected camera up axis",
    )
    return right,up,forward


def mission_waypoint_look(
    mission: DroneMission,
    waypoint_index: int,
) -> tuple[float,float,float]:
    points=mission.waypoints
    if not 0<=waypoint_index<len(points):
        raise ContractError("Selected waypoint index is outside the mission")
    point=points[waypoint_index]

    if point.has_look_direction:
        return (
            float(point.look_right),
            float(point.look_up),
            float(point.look_forward),
        )

    if mission.mode=="SPIN_360":
        pitch=math.radians(mission.spin_pitch_deg)
        yaw=math.radians(mission.spin_yaw_start_deg)
        cp=math.cos(pitch)
        return _normalize(
            (math.sin(yaw)*cp,math.sin(pitch),math.cos(yaw)*cp),
            "selected SPIN_360 direction",
        )

    if mission.orientation_mode=="LOOK_AT_TARGET":
        target=mission.look_target
        if target is None:
            raise ContractError("LOOK_AT_TARGET mission has no target")
        return _normalize(
            (
                target.right-point.right,
                target.up-point.up,
                target.forward-point.forward,
            ),
            "selected LOOK_AT_TARGET direction",
        )

    if mission.orientation_mode=="MANUAL_DIRECTION":
        direction=mission.manual_direction
        if direction is None:
            raise ContractError("MANUAL_DIRECTION mission has no direction")
        return _normalize(
            (direction.right,direction.up,direction.forward),
            "selected MANUAL_DIRECTION",
        )

    if waypoint_index<len(points)-1:
        neighbor=points[waypoint_index+1]
        raw=(
            neighbor.right-point.right,
            neighbor.up-point.up,
            neighbor.forward-point.forward,
        )
    else:
        neighbor=points[max(0,waypoint_index-1)]
        raw=(
            point.right-neighbor.right,
            point.up-neighbor.up,
            point.forward-neighbor.forward,
        )
    return _normalize(raw,"selected LOOK_ALONG_PATH direction")


def _parse_route_for_run(payload: dict, boundary) -> DroneRoutePlan:
    if payload.get("scene_contract_id") or payload.get("source_run_id"):
        plan,_,_=parse_bound_route_plan(
            payload,
            expected_scene_contract_id=boundary.scene_contract_id,
            expected_source_run_id=boundary.run_id,
            require_hash=False,
        )
        return plan
    return DroneRoutePlan.from_dict(payload)


def _project_point(
    raw,
    *,
    position,
    right_axis,
    up_axis,
    forward_axis,
    width: int,
    height: int,
    hfov_deg: float,
    vfov_deg: float,
):
    delta=(
        float(raw[0])-position[0],
        float(raw[1])-position[1],
        float(raw[2])-position[2],
    )
    depth=_dot(delta,forward_axis)
    if depth<=1.0e-4:
        return None
    x=_dot(delta,right_axis)
    y=_dot(delta,up_axis)
    fx=(width*0.5)/math.tan(math.radians(hfov_deg)*0.5)
    fy=(height*0.5)/math.tan(math.radians(vfov_deg)*0.5)
    return (
        width*0.5 + x/depth*fx,
        height*0.5 - y/depth*fy,
        depth,
    )


def render_selected_camera_preview(
    run_dir: str | Path,
    route_plan_json: str,
    *,
    mission_index: int=0,
    waypoint_index: int=0,
    preview_mode: str="POINTS_HIGH",
    preview_width: int=720,
):
    """Render the exact selected control-camera view from accepted P9 geometry."""

    try:
        import numpy as np
        import torch
        from PIL import Image,ImageDraw
    except ImportError as error:
        raise RuntimeError("Selected camera preview requires NumPy, Pillow and torch") from error

    boundary=validate_official_run(run_dir)
    camera=CameraAuthority.from_json(
        boundary.camera,
        expected_scene_contract_id=boundary.scene_contract_id,
    )
    try:
        payload=json.loads(str(route_plan_json or ""))
    except json.JSONDecodeError as error:
        raise ContractError(f"route_plan_json is invalid JSON: {error}") from error
    plan=_parse_route_for_run(payload,boundary)
    if not 0<=int(mission_index)<len(plan.missions):
        raise ContractError("mission_index is outside the route plan")
    mission=plan.missions[int(mission_index)]
    if not 0<=int(waypoint_index)<len(mission.waypoints):
        raise ContractError("waypoint_index is outside the selected mission")
    point=mission.waypoints[int(waypoint_index)]
    look=mission_waypoint_look(mission,int(waypoint_index))
    right_axis,up_axis,forward_axis=route_local_camera_basis(look)
    position=(point.right,point.up,point.forward)

    mode=str(preview_mode or "POINTS_HIGH").strip().upper()
    if mode not in {"POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH","MESH_SURFACE","MESH_WIREFRAME"}:
        raise ContractError(f"Unsupported selected camera preview mode: {mode}")
    width=max(320,min(1600,int(preview_width)))
    height=max(180,int(round(width*float(camera.height)/float(camera.width))))

    geometry=build_route_preview_geometry(
        boundary.primary_mesh,
        camera,
        source_image=boundary.source_image,
        max_points=100000,
        max_mesh_faces=30000,
    )
    image=Image.new("RGB",(width,height),(15,15,15))
    draw=ImageDraw.Draw(image,"RGBA")

    if mode.startswith("POINTS_"):
        points=geometry.get("point_lods",{}).get(mode,{}).get("points") or geometry.get("points") or []
        radius=1 if mode=="POINTS_LOW" else (2 if mode=="POINTS_MEDIUM" else 2)
        for raw in points:
            projected=_project_point(
                raw,
                position=position,
                right_axis=right_axis,
                up_axis=up_axis,
                forward_axis=forward_axis,
                width=width,
                height=height,
                hfov_deg=camera.horizontal_fov_deg,
                vfov_deg=camera.vertical_fov_deg,
            )
            if projected is None:
                continue
            x,y,_=projected
            if x<0 or x>=width or y<0 or y>=height:
                continue
            color=(int(raw[3]),int(raw[4]),int(raw[5]),205)
            draw.rectangle((x-radius,y-radius,x+radius,y+radius),fill=color)
    else:
        mesh=geometry.get("mesh_lod") or {}
        if not mesh.get("available"):
            raise ContractError("Selected camera mesh preview is unavailable for this PrimaryMesh")
        vertices=mesh.get("vertices") or []
        triangles=[]
        for face in mesh.get("faces") or []:
            pa=_project_point(
                vertices[face[0]],position=position,right_axis=right_axis,up_axis=up_axis,
                forward_axis=forward_axis,width=width,height=height,
                hfov_deg=camera.horizontal_fov_deg,vfov_deg=camera.vertical_fov_deg,
            )
            pb=_project_point(
                vertices[face[1]],position=position,right_axis=right_axis,up_axis=up_axis,
                forward_axis=forward_axis,width=width,height=height,
                hfov_deg=camera.horizontal_fov_deg,vfov_deg=camera.vertical_fov_deg,
            )
            pc=_project_point(
                vertices[face[2]],position=position,right_axis=right_axis,up_axis=up_axis,
                forward_axis=forward_axis,width=width,height=height,
                hfov_deg=camera.horizontal_fov_deg,vfov_deg=camera.vertical_fov_deg,
            )
            if pa is None or pb is None or pc is None:
                continue
            color=tuple(
                int(round(sum(int(vertices[idx][channel]) for idx in face)/3.0))
                for channel in (3,4,5)
            )
            triangles.append((sum((pa[2],pb[2],pc[2]))/3.0,pa,pb,pc,color))
        if mode=="MESH_SURFACE":
            triangles.sort(key=lambda row:row[0],reverse=True)
        for _,pa,pb,pc,color in triangles:
            xy=[(pa[0],pa[1]),(pb[0],pb[1]),(pc[0],pc[1])]
            if mode=="MESH_SURFACE":
                draw.polygon(xy,fill=(*color,118),outline=(25,25,25,65))
            else:
                draw.line((xy[0],xy[1],xy[2],xy[0]),fill=(210,220,230,155),width=1)

    draw.line((width*0.5-7,height*0.5,width*0.5+7,height*0.5),fill=(255,255,255,165),width=1)
    draw.line((width*0.5,height*0.5-7,width*0.5,height*0.5+7),fill=(255,255,255,165),width=1)

    array=np.asarray(image,dtype=np.float32)/255.0
    tensor=torch.from_numpy(array).unsqueeze(0)
    diagnostics={
        "status":"PASS",
        "schema":"ConceptGhost.P10SelectedCameraPreview.v0.1",
        "source_run_id":boundary.run_id,
        "scene_contract_id":boundary.scene_contract_id,
        "mission_index":int(mission_index),
        "mission_name":mission.name,
        "waypoint_index":int(waypoint_index),
        "preview_mode":mode,
        "preview_size":[width,height],
        "position":{"right":point.right,"up":point.up,"forward":point.forward},
        "look":{"right":look[0],"up":look[1],"forward":look[2]},
        "camera_fov_deg":{
            "horizontal":camera.horizontal_fov_deg,
            "vertical":camera.vertical_fov_deg,
        },
        "geometry_authority":"P9_ACCEPTED_PRIMARYMESH",
        "preview_authority":"DISPLAY_ONLY",
        "p9_authority_changed":False,
    }
    return tensor,diagnostics


class ConceptGhostP10SelectedDroneCameraPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "run_dir":("STRING",{"forceInput":True}),
                "route_plan_json":("STRING",{"forceInput":True}),
                "mission_index":("INT",{"default":0,"min":0,"max":6,"step":1}),
                "waypoint_index":("INT",{"default":0,"min":0,"max":239,"step":1}),
                "preview_mode":(
                    ["POINTS_HIGH","POINTS_MEDIUM","MESH_SURFACE","MESH_WIREFRAME"],
                    {"default":"POINTS_HIGH"},
                ),
                "preview_width":("INT",{"default":720,"min":320,"max":1600,"step":16}),
            }
        }

    RETURN_TYPES=("IMAGE","STRING")
    RETURN_NAMES=("selected_camera_preview","diagnostics_json")
    FUNCTION="preview"
    CATEGORY="ConceptGhost/P10 Refined"
    OUTPUT_NODE=True

    def preview(
        self,
        run_dir: str,
        route_plan_json: str,
        mission_index: int,
        waypoint_index: int,
        preview_mode: str,
        preview_width: int,
    ):
        tensor,diagnostics=render_selected_camera_preview(
            run_dir,
            route_plan_json,
            mission_index=int(mission_index),
            waypoint_index=int(waypoint_index),
            preview_mode=str(preview_mode),
            preview_width=int(preview_width),
        )
        rendered=json.dumps(diagnostics,indent=2,sort_keys=True)
        return {"ui":{"text":[rendered]},"result":(tensor,rendered)}
