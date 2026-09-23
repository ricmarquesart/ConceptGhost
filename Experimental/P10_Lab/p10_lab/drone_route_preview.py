from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .drone_route_plan import DroneRoutePlan
from .panorama import CameraAuthority


_ROUTE_COLORS = (
    (255, 176, 64),
    (78, 190, 255),
    (134, 226, 118),
    (222, 118, 255),
    (255, 104, 104),
    (255, 220, 90),
    (94, 232, 212),
)


@dataclass(frozen=True)
class AxisExtent:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.maximum <= self.minimum:
            raise ContractError("Orthographic extent maximum must exceed minimum")

    @property
    def span(self) -> float:
        return self.maximum - self.minimum

    def padded(self, fraction: float) -> "AxisExtent":
        pad=max(self.span * float(fraction), 1.0e-4)
        return AxisExtent(self.minimum-pad, self.maximum+pad)

    def to_dict(self) -> dict[str,float]:
        return {"min":self.minimum,"max":self.maximum}


@dataclass(frozen=True)
class RoutePreviewBounds:
    right: AxisExtent
    up: AxisExtent
    forward: AxisExtent

    def to_dict(self) -> dict[str,object]:
        return {
            "right":self.right.to_dict(),
            "up":self.up.to_dict(),
            "forward":self.forward.to_dict(),
        }


def _local_vertices(primary_mesh: str | Path, camera: CameraAuthority):
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required for P10 route authoring preview") from error

    path=Path(primary_mesh)
    if not path.is_file() or path.suffix.lower()!=".npz":
        raise ContractError(f"Route preview requires authoritative PrimaryMesh NPZ: {path}")
    try:
        with np.load(path,allow_pickle=False) as payload:
            if "vertices" not in payload.files:
                raise ContractError("PrimaryMesh is missing vertices")
            vertices=np.asarray(payload["vertices"],dtype=np.float64)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh for route preview: {path}: {error}") from error

    if vertices.ndim!=2 or vertices.shape[1]!=3 or vertices.shape[0]<3:
        raise ContractError("PrimaryMesh vertices must have shape [N,3] with N>=3")
    if not np.isfinite(vertices).all():
        raise ContractError("PrimaryMesh contains non-finite vertices")

    world=np.asarray(camera.world_matrix,dtype=np.float64)
    rotation=world[:3,:3]
    center=world[:3,3]
    right_axis=rotation[:,0]
    up_axis=rotation[:,1]
    forward_axis=-rotation[:,2]
    local=vertices-center[None,:]
    return np.column_stack((
        local@right_axis,
        local@up_axis,
        local@forward_axis,
    ))


def build_route_preview_geometry(
    primary_mesh: str | Path,
    camera: CameraAuthority,
    *,
    source_image: str | Path | None = None,
    max_points: int = 12000,
) -> dict[str, object]:
    """Return a bounded colored P9-local point sample for the interactive orbit view."""

    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise ContractError("Route preview geometry requires NumPy and Pillow") from error

    if type(max_points) is not int or max_points < 500:
        raise ContractError("max_points must be an integer >= 500")

    local = _local_vertices(primary_mesh, camera)
    stride = max(1, (len(local) + max_points - 1) // max_points)
    sampled = local[::stride]
    colors = np.full((sampled.shape[0], 3), 150, dtype=np.uint8)

    source_path = Path(source_image) if source_image is not None else None
    if source_path is not None and source_path.is_file():
        try:
            with np.load(Path(primary_mesh), allow_pickle=False) as payload:
                if "grid_xy" in payload.files:
                    grid = np.asarray(payload["grid_xy"], dtype=np.int64)
                elif "source_uv" in payload.files:
                    grid = np.rint(np.asarray(payload["source_uv"], dtype=np.float64)).astype(np.int64)
                else:
                    grid = None
            if grid is not None and grid.shape == (local.shape[0], 2):
                with Image.open(source_path) as opened:
                    source = np.asarray(opened.convert("RGB"), dtype=np.uint8)
                gx = np.clip(grid[:, 0], 0, source.shape[1] - 1)
                gy = np.clip(grid[:, 1], 0, source.shape[0] - 1)
                colors = source[gy, gx][::stride]
        except Exception:
            pass

    minimum = sampled.min(axis=0)
    maximum = sampled.max(axis=0)
    center = (minimum + maximum) * 0.5
    radius = float(max(np.linalg.norm(sampled - center[None, :], axis=1).max(), 1.0e-3))

    return {
        "schema": "ConceptGhost.P10RoutePreviewGeometry.v0.1",
        "coordinate_space": "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "sample_stride": int(stride),
        "point_count": int(sampled.shape[0]),
        "center": [float(v) for v in center],
        "radius": radius,
        "points": [
            [
                float(point[0]), float(point[1]), float(point[2]),
                int(color[0]), int(color[1]), int(color[2]),
            ]
            for point, color in zip(sampled, colors)
        ],
    }


def measure_route_preview_bounds(
    local_vertices,
    *,
    lower_percentile: float=0.2,
    upper_percentile: float=99.8,
    padding_fraction: float=0.06,
) -> RoutePreviewBounds:
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required for P10 route authoring preview") from error
    if not 0.0<=lower_percentile<upper_percentile<=100.0:
        raise ContractError("Route preview percentiles are invalid")
    arr=np.asarray(local_vertices,dtype=np.float64)
    if arr.ndim!=2 or arr.shape[1]!=3 or arr.shape[0]<3:
        raise ContractError("Route preview vertices must have shape [N,3]")
    if not np.isfinite(arr).all():
        raise ContractError("Route preview vertices must be finite")

    # Keep true extrema when they are not pathological, but use robust percentiles
    # to prevent a handful of depth outliers from making the scene unreadably tiny.
    extents=[]
    for axis in range(3):
        values=arr[:,axis]
        robust_lo=float(np.percentile(values,lower_percentile))
        robust_hi=float(np.percentile(values,upper_percentile))
        true_lo=float(np.min(values))
        true_hi=float(np.max(values))
        robust_span=max(robust_hi-robust_lo,1.0e-6)
        lo=true_lo if robust_lo-true_lo<=robust_span*0.20 else robust_lo
        hi=true_hi if true_hi-robust_hi<=robust_span*0.20 else robust_hi
        if hi-lo<1.0e-6:
            lo-=0.5
            hi+=0.5
        extents.append(AxisExtent(lo,hi).padded(padding_fraction))
    return RoutePreviewBounds(
        right=extents[0],
        up=extents[1],
        forward=extents[2],
    )


def _projection_manifest(bounds: RoutePreviewBounds, panel_width: int, panel_height: int, gap: int):
    margin=34
    usable_w=panel_width-2*margin
    usable_h=panel_height-2*margin

    def isotropic_extents(x_extent: AxisExtent, y_extent: AxisExtent):
        pixels_per_meter=min(
            usable_w/max(x_extent.span,1.0e-9),
            usable_h/max(y_extent.span,1.0e-9),
        )
        display_x_span=usable_w/pixels_per_meter
        display_y_span=usable_h/pixels_per_meter
        x_center=(x_extent.minimum+x_extent.maximum)*0.5
        y_center=(y_extent.minimum+y_extent.maximum)*0.5
        return (
            AxisExtent(x_center-display_x_span*0.5,x_center+display_x_span*0.5),
            AxisExtent(y_center-display_y_span*0.5,y_center+display_y_span*0.5),
            pixels_per_meter,
        )

    def ortho_panel(name,row,column,x_axis,y_axis,x_extent,y_extent):
        x_extent,y_extent,pixels_per_meter=isotropic_extents(x_extent,y_extent)
        x0=gap+column*(panel_width+gap)
        y0=gap+row*(panel_height+gap)
        return {
            "name":name,
            "panel_rect_px":{"x":x0,"y":y0,"width":panel_width,"height":panel_height},
            "plot_rect_px":{
                "x":x0+margin,
                "y":y0+margin,
                "width":usable_w,
                "height":usable_h,
            },
            "x_axis":x_axis,
            "y_axis":y_axis,
            "x_extent":x_extent.to_dict(),
            "y_extent":y_extent.to_dict(),
            "y_screen_inverted":True,
            "pixels_per_meter":float(pixels_per_meter),
            "projection_mode":"PERSPECTIVE_PLUS_ORTHOGRAPHIC_ISOTROPIC",
        }

    perspective={
        "name":"PERSPECTIVE",
        "panel_rect_px":{"x":gap,"y":gap,"width":panel_width,"height":panel_height},
        "plot_rect_px":{
            "x":gap+margin,
            "y":gap+margin,
            "width":usable_w,
            "height":usable_h,
        },
        "projection_mode":"PERSPECTIVE_ORBIT",
        "interaction":"ORBIT_INSPECTION_ONLY",
        "default_yaw_deg":-35.0,
        "default_pitch_deg":-18.0,
        "default_zoom":1.0,
    }

    return {
        "schema":"ConceptGhost.P10DroneRouteFourViewProjection.v0.3",
        "coordinate_space":"P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "projection_mode":"PERSPECTIVE_PLUS_ORTHOGRAPHIC_ISOTROPIC",
        "layout":"2X2_PERSPECTIVE_TOP_SIDE_FRONT",
        "interaction_rule":{
            "PERSPECTIVE":"orbit/zoom inspection; no depth-ambiguous waypoint creation",
            "TOP":"drag edits RIGHT + FORWARD",
            "SIDE":"drag edits FORWARD + UP",
            "FRONT":"drag edits RIGHT + UP",
        },
        "perspective_panel":perspective,
        "panels":[
            ortho_panel("TOP",0,1,"right","forward",bounds.right,bounds.forward),
            ortho_panel("SIDE",1,0,"forward","up",bounds.forward,bounds.up),
            ortho_panel("FRONT",1,1,"right","up",bounds.right,bounds.up),
        ],
    }

def render_route_authoring_preview(
    primary_mesh: str | Path,
    camera: CameraAuthority,
    plan: DroneRoutePlan | None,
    *,
    source_image: str | Path | None = None,
    panel_width: int=600,
    panel_height: int=560,
    gap: int=14,
    max_geometry_points: int=50000,
):
    try:
        import numpy as np
        import torch
        from PIL import Image,ImageDraw
    except ImportError as error:
        raise ContractError("Route authoring preview requires NumPy, Pillow and Torch") from error

    if panel_width<320 or panel_height<320:
        raise ContractError("Route authoring preview panels must be at least 320 px")
    if max_geometry_points<100:
        raise ContractError("max_geometry_points must be at least 100")

    local=_local_vertices(primary_mesh,camera)
    bounds=measure_route_preview_bounds(local)
    projection=_projection_manifest(bounds,panel_width,panel_height,gap)

    stride=max(1,(len(local)+max_geometry_points-1)//max_geometry_points)
    points=local[::stride]

    point_colors=None
    if source_image is not None:
        source_path=Path(source_image)
        if source_path.is_file():
            try:
                with np.load(Path(primary_mesh),allow_pickle=False) as payload:
                    if "grid_xy" in payload.files:
                        grid=np.asarray(payload["grid_xy"],dtype=np.int64)
                    elif "source_uv" in payload.files:
                        grid=np.rint(np.asarray(payload["source_uv"],dtype=np.float64)).astype(np.int64)
                    else:
                        grid=None
                if grid is not None and grid.shape==(local.shape[0],2):
                    with Image.open(source_path) as opened:
                        source=np.asarray(opened.convert("RGB"),dtype=np.uint8)
                    gx=np.clip(grid[:,0],0,source.shape[1]-1)
                    gy=np.clip(grid[:,1],0,source.shape[0]-1)
                    point_colors=source[gy,gx][::stride]
            except Exception:
                # Color is a readability enhancement only. Route geometry and
                # projection authority remain the PrimaryMesh coordinates.
                point_colors=None
    canvas_w=panel_width*2+gap*3
    canvas_h=panel_height*2+gap*3
    image=Image.new("RGB",(canvas_w,canvas_h),(18,18,18))
    draw=ImageDraw.Draw(image)

    perspective=projection["perspective_panel"]
    prect=perspective["panel_rect_px"]
    pplot=perspective["plot_rect_px"]
    draw.rectangle(
        (prect["x"],prect["y"],prect["x"]+prect["width"],prect["y"]+prect["height"]),
        fill=(24,24,24),outline=(82,82,82),width=1,
    )
    draw.rectangle(
        (pplot["x"],pplot["y"],pplot["x"]+pplot["width"],pplot["y"]+pplot["height"]),
        outline=(52,52,52),width=1,
    )
    draw.text((prect["x"]+12,prect["y"]+9),"PERSPECTIVE",fill=(240,240,240))
    draw.text(
        (prect["x"]+12,prect["y"]+27),
        "ORBIT / ZOOM INSPECTION IN COMFYUI",
        fill=(150,150,150),
    )

    axis_index={"right":0,"up":1,"forward":2}
    extent_map={"right":bounds.right,"up":bounds.up,"forward":bounds.forward}

    def project(panel,point):
        plot=panel["plot_rect_px"]
        x_axis=axis_index[panel["x_axis"]]
        y_axis=axis_index[panel["y_axis"]]
        xe=extent_map[panel["x_axis"]]
        ye=extent_map[panel["y_axis"]]
        x=plot["x"]+(float(point[x_axis])-xe.minimum)/xe.span*plot["width"]
        amount=(float(point[y_axis])-ye.minimum)/ye.span
        y=plot["y"]+(1.0-amount)*plot["height"]
        return int(round(x)),int(round(y))

    for panel in projection["panels"]:
        rect=panel["panel_rect_px"]
        draw.rectangle(
            (rect["x"],rect["y"],rect["x"]+rect["width"],rect["y"]+rect["height"]),
            fill=(24,24,24),
            outline=(82,82,82),
            width=1,
        )
        plot=panel["plot_rect_px"]
        draw.rectangle(
            (plot["x"],plot["y"],plot["x"]+plot["width"],plot["y"]+plot["height"]),
            outline=(52,52,52),
            width=1,
        )
        draw.text((rect["x"]+12,rect["y"]+9),panel["name"],fill=(240,240,240))
        draw.text(
            (rect["x"]+12,rect["y"]+27),
            f'{panel["x_axis"].upper()} / {panel["y_axis"].upper()}',
            fill=(150,150,150),
        )
        for point_index,point in enumerate(points):
            x,y=project(panel,point)
            if plot["x"]<=x<=plot["x"]+plot["width"] and plot["y"]<=y<=plot["y"]+plot["height"]:
                if point_colors is None:
                    fill=(105,105,105)
                else:
                    raw=point_colors[point_index]
                    fill=tuple(int(min(255,max(0,float(value)*0.78+42.0))) for value in raw[:3])
                draw.point((x,y),fill=fill)

    if plan is not None:
        for mission_index,mission in enumerate(plan.active_missions):
            color=_ROUTE_COLORS[mission_index%len(_ROUTE_COLORS)]
            pts=np.asarray(
                [[p.right,p.up,p.forward] for p in mission.waypoints],
                dtype=np.float64,
            )
            for panel in projection["panels"]:
                projected=[project(panel,p) for p in pts]
                if mission.mode=="PATH" and len(projected)>1:
                    draw.line(projected,fill=color,width=3)
                elif mission.mode=="SPIN_360" and projected:
                    x,y=projected[0]
                    radius=13
                    draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline=color,width=3)
                for point_index,(x,y) in enumerate(projected):
                    r=5
                    draw.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=(245,245,245))
                    draw.text((x+7,y-8),str(point_index+1),fill=color)
                if projected:
                    x,y=projected[-1]
                    draw.text((x+7,y+7),mission.name,fill=color)

    arr=np.asarray(image,dtype=np.float32)/255.0
    tensor=torch.from_numpy(arr).unsqueeze(0)
    diagnostics={
        "status":"PASS",
        "preview":"P10_DRONE_ROUTE_FOUR_VIEW",
        "vertex_count":int(local.shape[0]),
        "rendered_geometry_points":int(points.shape[0]),
        "geometry_sampling_stride":int(stride),
        "source_color_preview":bool(point_colors is not None),
        "projection_mode":"ORTHOGRAPHIC_ISOTROPIC",
        "bounds":bounds.to_dict(),
        "projection":projection,
        "route_plan":plan.to_dict() if plan is not None else None,
    }
    return tensor,projection,diagnostics
