from __future__ import annotations

import json
import math
from pathlib import Path

from .contracts import ContractError
from .dense_reconstruction import _sample_ply_points
from .p9_boundary import validate_official_run


_SCHEMA="ConceptGhost.P10MetricReconstructionOverlay.v0.1"


def _lazy_runtime():
    try:
        import numpy as np
        from PIL import Image,ImageDraw
    except ImportError as error:
        raise ContractError(
            "Metric reconstruction overlay requires NumPy and Pillow"
        ) from error
    return np,Image,ImageDraw


def _read_json(path: str | Path,label: str) -> dict:
    path=Path(path)
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must be a JSON object")
    return payload


def _sample_rows(points,max_points,np):
    points=np.asarray(points,dtype=np.float64)
    if points.ndim!=2 or points.shape[1]!=3:
        raise ContractError("Overlay point arrays must have shape [N,3]")
    if len(points)<=max_points:
        return points
    stride=max(1,math.ceil(len(points)/max_points))
    return points[::stride][:max_points]


def _load_p9_points(run_dir: str | Path,max_points: int,np,Image):
    boundary=validate_official_run(run_dir)
    with np.load(boundary.primary_mesh,allow_pickle=False) as payload:
        if "vertices" not in payload.files:
            raise ContractError("P9 PrimaryMesh is missing vertices")
        vertices=np.asarray(payload["vertices"],dtype=np.float64)
        if "grid_xy" in payload.files:
            grid=np.asarray(payload["grid_xy"],dtype=np.int64)
        elif "source_uv" in payload.files:
            grid=np.rint(np.asarray(payload["source_uv"],dtype=np.float64)).astype(np.int64)
        else:
            grid=None

    stride=max(1,math.ceil(len(vertices)/max_points))
    sampled=vertices[::stride][:max_points]
    colors=None
    if grid is not None and grid.shape==(vertices.shape[0],2):
        with Image.open(boundary.source_image) as opened:
            source=np.asarray(opened.convert("RGB"),dtype=np.uint8)
        sampled_grid=grid[::stride][:len(sampled)]
        gx=np.clip(sampled_grid[:,0],0,source.shape[1]-1)
        gy=np.clip(sampled_grid[:,1],0,source.shape[0]-1)
        colors=source[gy,gx]
    return boundary,sampled,colors,int(vertices.shape[0])


def _load_sparse_points(dataset_root: Path,max_points: int,np):
    path=dataset_root/"sparse"/"triangulated_txt"/"points3D.txt"
    if not path.is_file():
        return np.empty((0,3),dtype=np.float64),0
    values=[]
    total=0
    for raw in path.read_text(encoding="utf-8",errors="replace").splitlines():
        line=raw.strip()
        if not line or line.startswith("#"):
            continue
        parts=line.split()
        if len(parts)<4:
            continue
        total+=1
        if len(values)<max_points:
            values.append((float(parts[1]),float(parts[2]),float(parts[3])))
        elif total % max(1,total//max_points+1)==0:
            # Keep bounded memory; dense/mesh views carry the overall shape.
            pass
    return (
        np.asarray(values,dtype=np.float64).reshape((-1,3))
        if values else np.empty((0,3),dtype=np.float64),
        total,
    )


def _load_ply_points(path: Path,max_points: int,np):
    if not path.is_file():
        return np.empty((0,3),dtype=np.float64),0
    total,sampled=_sample_ply_points(path,max_points)
    points=np.asarray(
        [(item[0],item[1],item[2]) for item in sampled],
        dtype=np.float64,
    )
    if points.size==0:
        points=np.empty((0,3),dtype=np.float64)
    return points,int(total)


def _camera_records(camera_manifest_path: str | Path,np):
    payload=_read_json(camera_manifest_path,"camera manifest")
    frames=payload.get("frames")
    if not isinstance(frames,list) or not frames:
        raise ContractError("Metric overlay requires camera frames")
    records=[]
    for frame in frames:
        camera=frame.get("camera") if isinstance(frame,dict) else None
        if not isinstance(camera,dict):
            continue
        world=np.asarray(camera.get("world_matrix"),dtype=np.float64)
        if world.shape!=(4,4):
            continue
        center=world[:3,3]
        right=world[:3,0]
        up=world[:3,1]
        forward=-world[:3,2]
        records.append({
            "mission":str(frame.get("path_name") or "unknown"),
            "frame_index":frame.get("path_frame_index"),
            "center":center,
            "right":right,
            "up":up,
            "forward":forward,
            "width":int(camera.get("width") or 1),
            "height":int(camera.get("height") or 1),
            "fx":float(camera.get("fx") or 1.0),
            "fy":float(camera.get("fy") or 1.0),
        })
    if not records:
        raise ContractError("Metric overlay found no valid camera matrices")
    return payload,records


def _bounds(points,np):
    if len(points)==0:
        return None
    return {
        "min":[float(v) for v in np.min(points,axis=0)],
        "max":[float(v) for v in np.max(points,axis=0)],
        "span":[float(v) for v in np.ptp(points,axis=0)],
        "center":[float(v) for v in ((np.min(points,axis=0)+np.max(points,axis=0))*0.5)],
    }


def _robust_bounds(points,np,low=0.005,high=0.995):
    if len(points)==0:
        return None
    lo=np.quantile(points,low,axis=0)
    hi=np.quantile(points,high,axis=0)
    for axis in range(3):
        if hi[axis]-lo[axis]<1.0e-6:
            lo[axis]-=0.5
            hi[axis]+=0.5
    return lo,hi


def _nearest_distance_stats(reference,query,np):
    if len(reference)==0 or len(query)==0:
        return {
            "available":False,
            "reason":"EMPTY_REFERENCE_OR_QUERY",
        }
    reference=_sample_rows(reference,12000,np)
    query=_sample_rows(query,2500,np)
    distances=None
    method=None
    approximate=False
    try:
        from scipy.spatial import cKDTree
        tree=cKDTree(reference)
        distances,_=tree.query(query,k=1,workers=-1)
        method="SCIPY_CKDTREE"
    except Exception:
        # Deterministic bounded fallback. Sampling makes this approximate but
        # avoids a hard SciPy dependency in ComfyUI/CI.
        approximate=True
        method="NUMPY_CHUNKED_SAMPLED"
        values=[]
        chunk=64
        for start in range(0,len(query),chunk):
            q=query[start:start+chunk]
            delta=q[:,None,:]-reference[None,:,:]
            squared=np.sum(delta*delta,axis=2)
            values.extend(np.sqrt(np.min(squared,axis=1)).tolist())
        distances=np.asarray(values,dtype=np.float64)

    ordered=np.sort(np.asarray(distances,dtype=np.float64))
    def q(fraction):
        return float(np.quantile(ordered,fraction))
    return {
        "available":True,
        "method":method,
        "approximate":approximate,
        "reference_sample_count":int(len(reference)),
        "query_sample_count":int(len(query)),
        "min_m":float(ordered[0]),
        "median_m":q(0.5),
        "p90_m":q(0.90),
        "p95_m":q(0.95),
        "p99_m":q(0.99),
        "max_m":float(ordered[-1]),
    }


def _common_display_bounds(point_sets,camera_centers,np):
    robust=[]
    for points in point_sets:
        if len(points):
            rb=_robust_bounds(points,np)
            if rb is not None:
                robust.append(rb)
    if not robust:
        raise ContractError("Metric overlay has no geometry points")
    lo=np.min(np.vstack([item[0] for item in robust]),axis=0)
    hi=np.max(np.vstack([item[1] for item in robust]),axis=0)
    if len(camera_centers):
        lo=np.minimum(lo,np.min(camera_centers,axis=0))
        hi=np.maximum(hi,np.max(camera_centers,axis=0))
    span=np.maximum(hi-lo,1.0e-6)
    lo-=span*0.06
    hi+=span*0.06
    return lo,hi


def _panel_extents(lo,hi,a,b,panel_w,panel_h,pad):
    usable_w=panel_w-2*pad
    usable_h=panel_h-2*pad
    span_a=max(float(hi[a]-lo[a]),1.0e-9)
    span_b=max(float(hi[b]-lo[b]),1.0e-9)
    ppm=min(usable_w/span_a,usable_h/span_b)
    display_a=usable_w/ppm
    display_b=usable_h/ppm
    center_a=float((lo[a]+hi[a])*0.5)
    center_b=float((lo[b]+hi[b])*0.5)
    return (
        (center_a-display_a*0.5,center_a+display_a*0.5),
        (center_b-display_b*0.5,center_b+display_b*0.5),
        float(ppm),
    )


def build_metric_reconstruction_overlay(
    p9_run_dir: str | Path,
    camera_manifest_path: str | Path,
    dataset_root: str | Path,
    output_path: str | Path,
    *,
    max_p9_points: int=50000,
    max_sparse_points: int=12000,
    max_dense_points: int=40000,
    max_mesh_points: int=30000,
) -> dict[str,object]:
    """Render P9/P10/camera evidence with one real metric scale per panel."""

    np,Image,ImageDraw=_lazy_runtime()
    dataset_root=Path(dataset_root).resolve()
    output_path=Path(output_path).resolve()
    if not dataset_root.is_dir():
        raise ContractError(f"Metric overlay dataset root does not exist: {dataset_root}")

    boundary,p9,p9_colors,p9_total=_load_p9_points(
        p9_run_dir,max_p9_points,np,Image
    )
    camera_payload,cameras=_camera_records(camera_manifest_path,np)
    if str(camera_payload.get("scene_contract_id") or "")!=boundary.scene_contract_id:
        raise ContractError("Metric overlay camera/P9 scene contract mismatch")
    if str(camera_payload.get("source_run_id") or "")!=boundary.run_id:
        raise ContractError("Metric overlay camera/P9 source run mismatch")

    sparse,sparse_total=_load_sparse_points(dataset_root,max_sparse_points,np)
    dense,dense_total=_load_ply_points(dataset_root/"dense"/"fused.ply",max_dense_points,np)
    mesh,mesh_total=_load_ply_points(
        dataset_root/"dense"/"pre_fusion_mesh.ply",max_mesh_points,np
    )
    camera_centers=np.asarray([record["center"] for record in cameras],dtype=np.float64)

    lo,hi=_common_display_bounds((p9,sparse,dense,mesh),camera_centers,np)
    panel_w=500
    panel_h=500
    pad=36
    gap=18
    header=104
    width=panel_w*3+gap*4
    height=header+panel_h+gap
    image=Image.new("RGB",(width,height),(13,13,13))
    draw=ImageDraw.Draw(image)
    draw.text((16,14),"ConceptGhost P10 · METRIC P9/P10 RECONSTRUCTION OVERLAY",fill=(245,245,245))
    draw.text(
        (16,38),
        f"P9 {p9_total:,} · sparse {sparse_total:,} · dense {dense_total:,} · mesh {mesh_total:,} · cameras {len(cameras):,}",
        fill=(190,190,190),
    )
    draw.text(
        (16,60),
        "P9 source-color/dim · sparse orange · dense cyan · mesh blue · cameras yellow · all panels metric-isotropic",
        fill=(165,165,165),
    )
    draw.text(
        (16,80),
        "P10→P9 distance is descriptive for generated unseen surfaces; P9 remains immutable authority.",
        fill=(145,145,145),
    )

    specs=((0,2,"TOP XZ"),(0,1,"FRONT XY"),(2,1,"SIDE ZY"))
    panels=[]
    projection_cache={}
    for index,(a,b,label) in enumerate(specs):
        x0=gap+index*(panel_w+gap)
        y0=header
        a_extent,b_extent,ppm=_panel_extents(lo,hi,a,b,panel_w,panel_h,pad)
        panel={
            "name":label,
            "axis_a":a,
            "axis_b":b,
            "x":x0,
            "y":y0,
            "width":panel_w,
            "height":panel_h,
            "pad":pad,
            "a_extent":list(a_extent),
            "b_extent":list(b_extent),
            "pixels_per_meter":ppm,
        }
        panels.append(panel)
        draw.rectangle((x0,y0,x0+panel_w,y0+panel_h),fill=(23,23,23),outline=(85,85,85))
        draw.text((x0+10,y0+10),label,fill=(238,238,238))
        draw.text((x0+10,y0+27),f"{ppm:.2f} px/m",fill=(145,145,145))

        def project(point,panel=panel):
            ae=panel["a_extent"]; be=panel["b_extent"]
            usable_w=panel["width"]-2*panel["pad"]
            usable_h=panel["height"]-2*panel["pad"]
            px=panel["x"]+panel["pad"]+(float(point[panel["axis_a"]])-ae[0])/(ae[1]-ae[0])*usable_w
            py=panel["y"]+panel["height"]-panel["pad"]-(float(point[panel["axis_b"]])-be[0])/(be[1]-be[0])*usable_h
            return px,py
        projection_cache[label]=project

        # P9: preserve source readability but dim it so P10 evidence is obvious.
        p9_stride=max(1,math.ceil(len(p9)/30000))
        for point_index,point in enumerate(p9[::p9_stride]):
            px,py=project(point)
            if p9_colors is not None:
                raw=p9_colors[::p9_stride][point_index]
                fill=tuple(int(float(v)*0.48+52) for v in raw)
            else:
                fill=(92,92,92)
            draw.point((px,py),fill=fill)

        for points,fill,radius in (
            (sparse,(255,174,70),2),
            (dense,(80,220,235),1),
            (mesh,(105,160,255),1),
        ):
            if not len(points):
                continue
            draw_stride=max(1,math.ceil(len(points)/18000))
            for point in points[::draw_stride]:
                px,py=project(point)
                if radius<=1:
                    draw.point((px,py),fill=fill)
                else:
                    draw.ellipse((px-radius,py-radius,px+radius,py+radius),fill=fill)

        # Camera centers and a bounded frustum footprint.
        by_mission={}
        for record in cameras:
            by_mission.setdefault(record["mission"],[]).append(record)
        scene_diag=float(np.linalg.norm(hi-lo))
        frustum_depth=max(scene_diag*0.035,0.25)
        for mission_index,(mission,records) in enumerate(by_mission.items()):
            stride=max(1,math.ceil(len(records)/10))
            for record in records[::stride]:
                center=record["center"]
                forward=record["forward"]
                right=record["right"]
                up=record["up"]
                half_w=frustum_depth*record["width"]/(2.0*max(record["fx"],1.0e-6))
                half_h=frustum_depth*record["height"]/(2.0*max(record["fy"],1.0e-6))
                tip=center+forward*frustum_depth
                corners=[
                    tip+right*sx*half_w+up*sy*half_h
                    for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))
                ]
                cx,cy=project(center)
                draw.ellipse((cx-2,cy-2,cx+2,cy+2),fill=(255,225,75))
                projected=[project(corner) for corner in corners]
                for corner in projected:
                    draw.line((cx,cy,corner[0],corner[1]),fill=(220,195,70),width=1)
                draw.line(projected+[projected[0]],fill=(220,195,70),width=1)

    distance=_nearest_distance_stats(p9,dense,np)
    dense_bounds=_bounds(dense,np)
    p9_bounds=_bounds(p9,np)
    sparse_manifest_path=dataset_root/"sparse_triangulation_manifest.json"
    sparse_manifest=_read_json(sparse_manifest_path,"sparse manifest") if sparse_manifest_path.is_file() else {}
    prefusion_manifest_path=dataset_root/"prefusion_mesh_manifest.json"
    prefusion_manifest=_read_json(prefusion_manifest_path,"prefusion manifest") if prefusion_manifest_path.is_file() else {}

    result={
        "schema":_SCHEMA,
        "status":"PASS",
        "scene_contract_id":boundary.scene_contract_id,
        "source_run_id":boundary.run_id,
        "p9_authority_changed":False,
        "coordinate_space":"P9_CANONICAL_WORLD_METERS",
        "projection_policy":"METRIC_ISOTROPIC_COMMON_BOUNDS",
        "p9":{"total_points":p9_total,"sampled_points":len(p9),"bounds":p9_bounds},
        "p10_sparse":{"total_points":sparse_total,"sampled_points":len(sparse),"bounds":_bounds(sparse,np)},
        "p10_dense":{"total_points":dense_total,"sampled_points":len(dense),"bounds":dense_bounds},
        "p10_prefusion_mesh":{"total_vertices":mesh_total,"sampled_vertices":len(mesh),"bounds":_bounds(mesh,np)},
        "cameras":{
            "count":len(cameras),
            "bounds":_bounds(camera_centers,np),
            "missions":sorted({record["mission"] for record in cameras}),
        },
        "verified_sparse_component_count":sparse_manifest.get("verified_component_count"),
        "mission_contribution":sparse_manifest.get("mission_contribution",[]),
        "mesh_health":prefusion_manifest.get("mesh_health"),
        "p10_dense_to_p9_distance":distance,
        "display_bounds":{"min":[float(v) for v in lo],"max":[float(v) for v in hi]},
        "panels":panels,
        "preview_png_path":str(output_path),
    }
    output_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(output_path)
    manifest_path=output_path.with_suffix(".json")
    result["manifest_path"]=str(manifest_path)
    manifest_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    return result
