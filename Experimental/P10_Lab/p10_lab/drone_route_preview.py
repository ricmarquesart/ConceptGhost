from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .drone_route_plan import DroneRoutePlan
from .panorama import CameraAuthority


_PREVIEW_GEOMETRY_CACHE: dict[tuple[object, ...], dict[str, object]] = {}


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
    max_points: int = 100000,
    max_mesh_faces: int = 24000,
) -> dict[str, object]:
    """Return bounded display-only P9 geometry LODs for the interactive editor."""

    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise ContractError("Route preview geometry requires NumPy and Pillow") from error

    if type(max_points) is not int or max_points < 500:
        raise ContractError("max_points must be an integer >= 500")
    if type(max_mesh_faces) is not int or max_mesh_faces < 100:
        raise ContractError("max_mesh_faces must be an integer >= 100")

    mesh_path=Path(primary_mesh).resolve()
    source_path=Path(source_image).resolve() if source_image is not None else None
    try:
        mesh_stat=mesh_path.stat()
    except OSError as error:
        raise ContractError(f"Cannot stat PrimaryMesh for route preview: {mesh_path}: {error}") from error
    source_stamp=None
    if source_path is not None and source_path.is_file():
        try:
            source_stat=source_path.stat()
            source_stamp=(str(source_path),int(source_stat.st_mtime_ns),int(source_stat.st_size))
        except OSError:
            source_stamp=None
    camera_key=tuple(round(float(value),9) for row in camera.world_matrix for value in row)
    cache_key=(
        str(mesh_path),int(mesh_stat.st_mtime_ns),int(mesh_stat.st_size),
        source_stamp,camera_key,int(max_points),int(max_mesh_faces),
    )
    cached=_PREVIEW_GEOMETRY_CACHE.get(cache_key)
    if cached is not None:
        return cached

    local=_local_vertices(mesh_path,camera)
    vertex_colors=np.full((local.shape[0],3),150,dtype=np.uint8)
    faces=None
    grid=None
    try:
        with np.load(mesh_path,allow_pickle=False) as payload:
            if "faces" in payload.files:
                candidate=np.asarray(payload["faces"],dtype=np.int64)
                if candidate.ndim==2 and candidate.shape[1]>=3:
                    faces=candidate[:,:3]
            if "grid_xy" in payload.files:
                grid=np.asarray(payload["grid_xy"],dtype=np.int64)
            elif "source_uv" in payload.files:
                grid=np.rint(np.asarray(payload["source_uv"],dtype=np.float64)).astype(np.int64)
    except Exception:
        faces=None
        grid=None

    if source_path is not None and source_path.is_file() and grid is not None and grid.shape==(local.shape[0],2):
        try:
            with Image.open(source_path) as opened:
                source=np.asarray(opened.convert("RGB"),dtype=np.uint8)
            gx=np.clip(grid[:,0],0,source.shape[1]-1)
            gy=np.clip(grid[:,1],0,source.shape[0]-1)
            vertex_colors=source[gy,gx]
        except Exception:
            vertex_colors=np.full((local.shape[0],3),150,dtype=np.uint8)

    grid_is_usable=bool(
        grid is not None
        and getattr(grid,"shape",None)==(local.shape[0],2)
        and local.shape[0]>0
    )

    def _image_grid_partition(target_cells: int):
        """Map every PrimaryMesh vertex to a deterministic image-space cell.

        PrimaryMesh is one depth sample per source pixel.  Partitioning in source
        image space preserves thin/distant structures far better than flattened
        vertex/face strides, while remaining display-only.
        """
        target_cells=max(1,min(int(target_cells),int(local.shape[0])))
        if not grid_is_usable:
            return None
        gx=np.asarray(grid[:,0],dtype=np.float64)
        gy=np.asarray(grid[:,1],dtype=np.float64)
        xmin,xmax=float(gx.min()),float(gx.max())
        ymin,ymax=float(gy.min()),float(gy.max())
        span_x=max(xmax-xmin+1.0,1.0)
        span_y=max(ymax-ymin+1.0,1.0)
        aspect=max(span_x/span_y,1.0e-6)
        cells_x=max(1,int(round((target_cells*aspect)**0.5)))
        cells_y=max(1,int(np.ceil(target_cells/cells_x)))
        bx=np.clip(((gx-xmin)*cells_x/span_x).astype(np.int64),0,cells_x-1)
        by=np.clip(((gy-ymin)*cells_y/span_y).astype(np.int64),0,cells_y-1)
        cell=by*cells_x+bx
        center_x=xmin+(bx.astype(np.float64)+0.5)*span_x/cells_x
        center_y=ymin+(by.astype(np.float64)+0.5)*span_y/cells_y
        score=(gx-center_x)**2+(gy-center_y)**2

        # Never collapse visibly different depth layers merely because they
        # occupy the same image-space LOD cell.  The PrimaryMesh already split
        # discontinuities at roughly the 4% depth-edge policy; mirror that
        # separation in the display-only clustering so thin silhouettes and
        # foreground/background cuts do not become stretched bridge triangles.
        forward=np.asarray(local[:,2],dtype=np.float64)
        abs_forward=np.maximum(np.abs(forward),1.0e-6)
        depth_bin=np.floor(np.log(abs_forward)/np.log(1.04)).astype(np.int64)
        depth_sign=(forward>=0.0).astype(np.int8)

        order=np.lexsort((score,depth_bin,depth_sign,cell))
        sorted_cells=cell[order]
        sorted_depth=depth_bin[order]
        sorted_sign=depth_sign[order]
        first=np.empty(order.shape[0],dtype=bool)
        first[0]=True
        first[1:]=(
            (sorted_cells[1:]!=sorted_cells[:-1])
            |(sorted_depth[1:]!=sorted_depth[:-1])
            |(sorted_sign[1:]!=sorted_sign[:-1])
        )
        representatives=order[first]
        cluster_sorted=np.cumsum(first,dtype=np.int64)-1
        cluster_ids=np.empty(order.shape[0],dtype=np.int64)
        cluster_ids[order]=cluster_sorted
        return cluster_ids,representatives

    def _image_stratified_indices(budget: int):
        budget=max(500,min(int(budget),int(max_points),int(local.shape[0])))
        partition=_image_grid_partition(budget)
        if partition is None:
            stride=max(1,(int(local.shape[0])+budget-1)//budget)
            return np.arange(0,int(local.shape[0]),stride,dtype=np.int64)[:budget],stride,"FLAT_STRIDE_FALLBACK"
        _,representatives=partition
        indices=np.asarray(representatives,dtype=np.int64)
        if indices.shape[0]>budget:
            positions=np.rint(np.linspace(0,indices.shape[0]-1,budget)).astype(np.int64)
            indices=indices[positions]
        elif indices.shape[0]<budget:
            selected=np.zeros(local.shape[0],dtype=bool)
            selected[indices]=True
            remaining=np.flatnonzero(~selected)
            need=min(budget-indices.shape[0],remaining.shape[0])
            if need:
                positions=np.rint(np.linspace(0,remaining.shape[0]-1,need)).astype(np.int64)
                indices=np.concatenate((indices,remaining[positions]))
        return indices,0,"IMAGE_SPACE_STRATIFIED"

    def point_lod(budget: int) -> dict[str,object]:
        budget=max(500,min(int(budget),int(max_points),int(local.shape[0])))
        indices,stride,policy=_image_stratified_indices(budget)
        sampled=local[indices]
        colors=vertex_colors[indices]
        return {
            "budget":int(budget),
            "sample_stride":int(stride),
            "sampling_policy":policy,
            "point_count":int(sampled.shape[0]),
            "points":[
                [float(p[0]),float(p[1]),float(p[2]),int(c[0]),int(c[1]),int(c[2])]
                for p,c in zip(sampled,colors)
            ],
        }

    point_lods={
        "POINTS_LOW":point_lod(min(15000,max_points)),
        "POINTS_MEDIUM":point_lod(min(50000,max_points)),
        "POINTS_HIGH":point_lod(max_points),
    }
    medium=point_lods["POINTS_MEDIUM"]

    mesh_lod={
        "available":False,
        "source_face_count":0,
        "face_budget":int(max_mesh_faces),
        "face_sampling_stride":0,
        "face_count":0,
        "vertex_count":0,
        "vertices":[],
        "faces":[],
        "lod_policy":"UNAVAILABLE",
        "authority":"DISPLAY_ONLY_P9_PRIMARYMESH_LOD",
    }
    if faces is not None and len(faces):
        source_face_count=int(len(faces))
        source_faces=np.asarray(faces,dtype=np.int64)
        valid=((source_faces>=0).all(axis=1)&(source_faces<local.shape[0]).all(axis=1))
        source_faces=source_faces[valid]
        remapped=None
        used=None
        representatives=None
        lod_policy="FLAT_FACE_STRIDE_FALLBACK"
        face_stride=0

        if grid_is_usable and len(source_faces):
            # Cluster the dense image-grid mesh, then remap ALL source faces
            # through those cells.  This creates one coherent coarse surface
            # instead of disconnected every-Nth triangles.
            min_mesh_cells=16
        target_cells=max(min_mesh_cells,int(max_mesh_faces//2))
            for _ in range(8):
                partition=_image_grid_partition(target_cells)
                if partition is None:
                    break
                cluster_ids,representatives=partition
                candidate=cluster_ids[source_faces]
                keep=(
                    (candidate[:,0]!=candidate[:,1])
                    &(candidate[:,1]!=candidate[:,2])
                    &(candidate[:,0]!=candidate[:,2])
                )
                candidate=candidate[keep]
                if not len(candidate):
                    target_cells=max(min_mesh_cells,int(target_cells*0.6))
                    continue
                canonical=np.sort(candidate,axis=1)
                _,first_indices=np.unique(canonical,axis=0,return_index=True)
                candidate=candidate[np.sort(first_indices)]
                if len(candidate)<=max_mesh_faces or target_cells<=min_mesh_cells:
                    remapped=candidate
                    lod_policy="IMAGE_GRID_CLUSTERED_CONNECTED_LOD"
                    break
                scale=max(0.25,min(0.90,float(max_mesh_faces)/float(len(candidate))*0.90))
                target_cells=max(min_mesh_cells,int(target_cells*scale))

            if remapped is not None and len(remapped):
                used=np.unique(remapped.reshape(-1))
                compact=np.full(representatives.shape[0],-1,dtype=np.int64)
                compact[used]=np.arange(used.shape[0],dtype=np.int64)
                remapped=compact[remapped]
                representatives=representatives[used]

        if remapped is None and len(source_faces):
            face_stride=max(1,(len(source_faces)+max_mesh_faces-1)//max_mesh_faces)
            selected=np.asarray(source_faces[::face_stride][:max_mesh_faces],dtype=np.int64)
            used=np.unique(selected.reshape(-1))
            compact=np.full(local.shape[0],-1,dtype=np.int64)
            compact[used]=np.arange(used.shape[0],dtype=np.int64)
            remapped=compact[selected]
            representatives=used

        if remapped is not None and len(remapped):
            mv=local[representatives]
            mc=vertex_colors[representatives]
            mesh_lod={
                "available":True,
                "source_face_count":source_face_count,
                "face_budget":int(max_mesh_faces),
                "face_sampling_stride":int(face_stride),
                "face_count":int(remapped.shape[0]),
                "vertex_count":int(mv.shape[0]),
                "vertices":[
                    [float(p[0]),float(p[1]),float(p[2]),int(c[0]),int(c[1]),int(c[2])]
                    for p,c in zip(mv,mc)
                ],
                "faces":[[int(face[0]),int(face[1]),int(face[2])] for face in remapped],
                "lod_policy":lod_policy,
                "depth_layer_policy":"RELATIVE_4PCT_CAMERA_FORWARD_BINS" if lod_policy=="IMAGE_GRID_CLUSTERED_CONNECTED_LOD" else "SOURCE_FACE_STRIDE",
                "authority":"DISPLAY_ONLY_P9_PRIMARYMESH_LOD",
            }

    minimum=local.min(axis=0)
    maximum=local.max(axis=0)
    center=(minimum+maximum)*0.5
    radius=float(max(np.linalg.norm(local-center[None,:],axis=1).max(),1.0e-3))
    result={
        "schema":"ConceptGhost.P10RoutePreviewGeometry.v0.2",
        "coordinate_space":"P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "authority":"DISPLAY_ONLY_NEVER_GEOMETRY_AUTHORITY",
        "default_mode":"POINTS_MEDIUM",
        "point_lods":point_lods,
        "mesh_lod":mesh_lod,
        "sample_stride":int(medium["sample_stride"]),
        "point_count":int(medium["point_count"]),
        "center":[float(v) for v in center],
        "radius":radius,
        "points":medium["points"],
    }
    if len(_PREVIEW_GEOMETRY_CACHE)>=3:
        _PREVIEW_GEOMETRY_CACHE.pop(next(iter(_PREVIEW_GEOMETRY_CACHE)))
    _PREVIEW_GEOMETRY_CACHE[cache_key]=result
    return result

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
            "projection_mode":"ORTHOGRAPHIC_ISOTROPIC",
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
    panel_width: int=720,
    panel_height: int=660,
    gap: int=14,
    max_geometry_points: int=70000,
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

    def project(panel,point):
        plot=panel["plot_rect_px"]
        x_axis=axis_index[panel["x_axis"]]
        y_axis=axis_index[panel["y_axis"]]
        xe=panel["x_extent"]
        ye=panel["y_extent"]
        xspan=max(float(xe["max"])-float(xe["min"]),1.0e-12)
        yspan=max(float(ye["max"])-float(ye["min"]),1.0e-12)
        x=plot["x"]+(float(point[x_axis])-float(xe["min"]))/xspan*plot["width"]
        amount=(float(point[y_axis])-float(ye["min"]))/yspan
        y=plot["y"]+(1.0-amount)*plot["height"]
        return int(round(x)),int(round(y))

    perspective_center=np.mean(local,axis=0)
    perspective_radius=max(
        float(np.linalg.norm(local-perspective_center[None,:],axis=1).max()),
        1.0e-3,
    )

    def project_perspective(point):
        yaw=float(perspective["default_yaw_deg"])*np.pi/180.0
        pitch=float(perspective["default_pitch_deg"])*np.pi/180.0
        vector=np.asarray(point,dtype=np.float64)-perspective_center
        cy,sy=np.cos(yaw),np.sin(yaw)
        cp,sp=np.cos(pitch),np.sin(pitch)
        x1=cy*vector[0]-sy*vector[2]
        z1=sy*vector[0]+cy*vector[2]
        y2=cp*vector[1]-sp*z1
        z2=sp*vector[1]+cp*z1
        distance=perspective_radius*2.8
        depth=distance-z2
        if depth<=perspective_radius*0.02:
            return None
        focal=min(pplot["width"],pplot["height"])*1.05
        x=pplot["x"]+pplot["width"]*0.5+(x1/depth)*focal
        y=pplot["y"]+pplot["height"]*0.5-(y2/depth)*focal
        return int(round(x)),int(round(y))

    def mission_look(mission,point_index):
        point=mission.waypoints[point_index]
        if mission.mode=="SPIN_360":
            return np.asarray((0.0,0.0,1.0),dtype=np.float64)
        if mission.orientation_mode=="LOOK_AT_TARGET" and mission.look_target is not None:
            raw=np.asarray((
                mission.look_target.right-point.right,
                mission.look_target.up-point.up,
                mission.look_target.forward-point.forward,
            ),dtype=np.float64)
        elif mission.orientation_mode=="MANUAL_DIRECTION" and mission.manual_direction is not None:
            raw=np.asarray((
                mission.manual_direction.right,
                mission.manual_direction.up,
                mission.manual_direction.forward,
            ),dtype=np.float64)
        else:
            if point_index<len(mission.waypoints)-1:
                other=mission.waypoints[point_index+1]
                raw=np.asarray((
                    other.right-point.right,
                    other.up-point.up,
                    other.forward-point.forward,
                ),dtype=np.float64)
            else:
                other=mission.waypoints[max(0,point_index-1)]
                raw=np.asarray((
                    point.right-other.right,
                    point.up-other.up,
                    point.forward-other.forward,
                ),dtype=np.float64)
        length=float(np.linalg.norm(raw))
        if length<=1.0e-12:
            return np.asarray((0.0,0.0,1.0),dtype=np.float64)
        return raw/length

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


    for point_index,point in enumerate(points):
        projected=project_perspective(point)
        if projected is None:
            continue
        x,y=projected
        if not (
            pplot["x"]<=x<=pplot["x"]+pplot["width"]
            and pplot["y"]<=y<=pplot["y"]+pplot["height"]
        ):
            continue
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
                metric_span=max(
                    float(panel["x_extent"]["max"])-float(panel["x_extent"]["min"]),
                    float(panel["y_extent"]["max"])-float(panel["y_extent"]["min"]),
                )
                for point_index,(x,y) in enumerate(projected):
                    r=5
                    draw.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=(245,245,245))
                    draw.text((x+7,y-8),str(point_index+1),fill=color)
                    if mission.mode=="PATH":
                        look=mission_look(mission,point_index)
                        tip=pts[point_index]+look*max(metric_span*0.045,0.20)
                        tx,ty=project(panel,tip)
                        draw.line((x,y,tx,ty),fill=(240,240,240),width=2)
                if mission.orientation_mode=="LOOK_AT_TARGET" and mission.look_target is not None:
                    target=np.asarray(
                        [mission.look_target.right,mission.look_target.up,mission.look_target.forward],
                        dtype=np.float64,
                    )
                    tx,ty=project(panel,target)
                    draw.line((tx-7,ty,tx+7,ty),fill=color,width=2)
                    draw.line((tx,ty-7,tx,ty+7),fill=color,width=2)
                    draw.rectangle((tx-4,ty-4,tx+4,ty+4),outline=color,width=2)
                if projected:
                    x,y=projected[-1]
                    draw.text((x+7,y+7),mission.name,fill=color)

            perspective_points=[project_perspective(point) for point in pts]
            valid_perspective=[p for p in perspective_points if p is not None]
            if mission.mode=="PATH" and len(valid_perspective)>1:
                draw.line(valid_perspective,fill=color,width=3)
            elif mission.mode=="SPIN_360" and valid_perspective:
                x,y=valid_perspective[0]
                draw.ellipse((x-13,y-13,x+13,y+13),outline=color,width=3)

            orientation_scale=max(perspective_radius*0.08,0.25)
            for point_index,projected_point in enumerate(perspective_points):
                if projected_point is None:
                    continue
                x,y=projected_point
                draw.ellipse((x-5,y-5,x+5,y+5),fill=color,outline=(245,245,245))
                if mission.mode=="PATH":
                    look=mission_look(mission,point_index)
                    tip=pts[point_index]+look*orientation_scale
                    projected_tip=project_perspective(tip)
                    if projected_tip is not None:
                        draw.line((x,y,projected_tip[0],projected_tip[1]),fill=(240,240,240),width=2)
            if mission.orientation_mode=="LOOK_AT_TARGET" and mission.look_target is not None:
                target=np.asarray(
                    [mission.look_target.right,mission.look_target.up,mission.look_target.forward],
                    dtype=np.float64,
                )
                projected_target=project_perspective(target)
                if projected_target is not None:
                    tx,ty=projected_target
                    draw.line((tx-7,ty,tx+7,ty),fill=color,width=2)
                    draw.line((tx,ty-7,tx,ty+7),fill=color,width=2)
                    draw.rectangle((tx-4,ty-4,tx+4,ty+4),outline=color,width=2)

    arr=np.asarray(image,dtype=np.float32)/255.0
    tensor=torch.from_numpy(arr).unsqueeze(0)
    diagnostics={
        "status":"PASS",
        "preview":"P10_DRONE_ROUTE_FOUR_VIEW",
        "vertex_count":int(local.shape[0]),
        "rendered_geometry_points":int(points.shape[0]),
        "geometry_sampling_stride":int(stride),
        "source_color_preview":bool(point_colors is not None),
        "projection_mode":"PERSPECTIVE_PLUS_ORTHOGRAPHIC_ISOTROPIC",
        "bounds":bounds.to_dict(),
        "projection":projection,
        "route_plan":plan.to_dict() if plan is not None else None,
    }
    return tensor,projection,diagnostics
