from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # allow dependency-light bundle/release validation imports
    np = None

from .contracts import ContractError

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - package contract reports the failure
    Image = ImageDraw = ImageFont = None


_SCHEMA="ConceptGhost.MoGeDepthDiagnostics.v0.1"


def _to_numpy(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    if hasattr(value,"detach"):
        value=value.detach()
    if hasattr(value,"cpu"):
        value=value.cpu()
    if hasattr(value,"numpy"):
        value=value.numpy()
    arr=np.asarray(value)
    return arr


def _first_image_rgb(image: Any) -> np.ndarray:
    arr=_to_numpy(image)
    if arr is None:
        raise ContractError("MoGe diagnostics received no source image")
    if arr.ndim==4:
        arr=arr[0]
    if arr.ndim!=3 or arr.shape[-1] not in (3,4):
        raise ContractError(f"source_image must resolve to HxWx3/4, got {arr.shape}")
    arr=arr[...,:3].astype(np.float32,copy=False)
    if arr.size and float(np.nanmax(arr))>1.5:
        arr=arr/255.0
    return np.clip(np.nan_to_num(arr,nan=0.0,posinf=1.0,neginf=0.0),0.0,1.0)


def _first_map(value: Any) -> np.ndarray | None:
    arr=_to_numpy(value)
    if arr is None:
        return None
    while arr.ndim>2 and arr.shape[0]==1:
        arr=arr[0]
    if arr.ndim==3 and arr.shape[-1]==1:
        arr=arr[...,0]
    if arr.ndim!=2:
        return None
    return np.asarray(arr)


def _first_vectors(value: Any,channels: int=3) -> np.ndarray | None:
    arr=_to_numpy(value)
    if arr is None:
        return None
    while arr.ndim>3 and arr.shape[0]==1:
        arr=arr[0]
    if arr.ndim==3 and arr.shape[-1]==channels:
        return np.asarray(arr)
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value,dict):
        return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value,np.ndarray):
        if value.size<=36:
            return value.tolist()
        return {"shape":list(value.shape),"dtype":str(value.dtype)}
    if isinstance(value,(np.floating,np.integer,np.bool_)):
        return value.item()
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    return str(value)


def _slug(value: str) -> str:
    text=re.sub(r"[^A-Za-z0-9._-]+","_",str(value or "scene").strip())
    return text.strip("._") or "scene"


def _valid_depth(depth: np.ndarray,mask: np.ndarray | None=None) -> np.ndarray:
    valid=np.isfinite(depth) & (depth>0)
    if mask is not None and mask.shape==depth.shape:
        valid &= mask.astype(bool)
    return valid


def _percentiles(values: np.ndarray,qs=(1,5,25,50,75,95,99)) -> dict[str,float]:
    if values.size==0:
        return {}
    vals=np.asarray(values,dtype=np.float64)
    return {str(q):float(np.percentile(vals,q)) for q in qs}


def _normalize_scalar(data: np.ndarray,valid: np.ndarray,*,low=1.0,high=99.0) -> tuple[np.ndarray,dict[str,float]]:
    out=np.zeros(data.shape,dtype=np.float32)
    values=np.asarray(data[valid],dtype=np.float64)
    if values.size==0:
        return out,{"low":0.0,"high":0.0}
    lo=float(np.percentile(values,low))
    hi=float(np.percentile(values,high))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi<=lo:
        lo=float(np.min(values))
        hi=float(np.max(values))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi<=lo:
        hi=lo+1.0
    out[valid]=np.clip((data[valid]-lo)/(hi-lo),0.0,1.0).astype(np.float32)
    return out,{"low":lo,"high":hi}


def _gray_rgb(norm: np.ndarray) -> np.ndarray:
    x=np.clip(norm,0,1)
    return np.repeat(x[...,None],3,axis=-1)


def _heat_rgb(norm: np.ndarray) -> np.ndarray:
    # Compact perceptual-ish blue->cyan->green->yellow->red map without matplotlib.
    x=np.clip(norm,0,1).astype(np.float32)
    anchors=np.asarray([
        [0.00, 0.02,0.05,0.30],
        [0.20, 0.00,0.45,0.90],
        [0.40, 0.00,0.85,0.75],
        [0.60, 0.25,0.90,0.20],
        [0.80, 0.98,0.85,0.05],
        [1.00, 0.90,0.05,0.02],
    ],dtype=np.float32)
    flat=x.reshape(-1)
    rgb=np.empty((flat.size,3),dtype=np.float32)
    for i,val in enumerate(flat):
        j=min(len(anchors)-2,max(0,int(np.searchsorted(anchors[:,0],val,side="right")-1)))
        a,b=anchors[j],anchors[j+1]
        t=0.0 if b[0]<=a[0] else float((val-a[0])/(b[0]-a[0]))
        rgb[i]=a[1:]*(1-t)+b[1:]*t
    return rgb.reshape(x.shape+(3,))


def _bands_rgb(depth: np.ndarray,valid: np.ndarray,bands: int=12) -> tuple[np.ndarray,list[float]]:
    out=np.zeros(depth.shape+(3,),dtype=np.float32)
    values=np.asarray(depth[valid],dtype=np.float64)
    if values.size==0:
        return out,[]
    qs=np.linspace(0,100,bands+1)
    edges=np.unique(np.percentile(values,qs))
    if edges.size<2:
        return out,[float(edges[0])] if edges.size else []
    idx=np.digitize(depth,edges[1:-1],right=False)
    palette=_heat_rgb(np.linspace(0,1,max(2,edges.size-1),dtype=np.float32).reshape((-1,1)))[:,0,:]
    out[valid]=palette[np.clip(idx[valid],0,len(palette)-1)]
    return out,[float(v) for v in edges]


def _depth_edges(depth: np.ndarray,valid: np.ndarray) -> tuple[np.ndarray,float]:
    work=np.zeros(depth.shape,dtype=np.float64)
    if np.any(valid):
        fill=float(np.median(depth[valid]))
        work[:]=fill
        work[valid]=np.log(np.maximum(depth[valid],1.0e-9))
    gy,gx=np.gradient(work)
    mag=np.hypot(gx,gy)
    values=mag[valid]
    threshold=float(np.percentile(values,92)) if values.size else 0.0
    edges=(mag>=threshold)&valid if threshold>0 else np.zeros_like(valid)
    return edges.astype(np.float32),threshold


def _contours_from_bands(bands_rgb: np.ndarray,valid: np.ndarray) -> np.ndarray:
    code=np.argmax(bands_rgb,axis=-1).astype(np.int16)
    edge=np.zeros(valid.shape,dtype=bool)
    edge[:,1:] |= code[:,1:]!=code[:,:-1]
    edge[1:,:] |= code[1:,:]!=code[:-1,:]
    edge &= valid
    out=np.zeros(valid.shape+(3,),dtype=np.float32)
    out[edge]=1.0
    return out


def _normal_rgb(normal: np.ndarray | None) -> np.ndarray | None:
    if normal is None:
        return None
    n=np.asarray(normal,dtype=np.float32)
    finite=np.isfinite(n).all(axis=-1)
    out=np.zeros_like(n,dtype=np.float32)
    if not np.any(finite):
        return out
    vals=n[finite]
    if float(np.nanmin(vals))>=-1.05 and float(np.nanmax(vals))<=1.05:
        out[finite]=np.clip(vals*0.5+0.5,0,1)
    else:
        length=np.linalg.norm(vals,axis=-1,keepdims=True)
        vals=vals/np.maximum(length,1.0e-8)
        out[finite]=np.clip(vals*0.5+0.5,0,1)
    return out


def _save_rgb(path: Path,rgb: np.ndarray) -> None:
    if Image is None:
        raise ContractError("Pillow is required for MoGe diagnostic images")
    path.parent.mkdir(parents=True,exist_ok=True)
    arr=np.clip(np.rint(np.asarray(rgb)*255.0),0,255).astype(np.uint8)
    Image.fromarray(arr,mode="RGB").save(path)


def _save_mask(path: Path,mask: np.ndarray) -> None:
    if Image is None:
        raise ContractError("Pillow is required for MoGe diagnostic images")
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray((mask.astype(np.uint8)*255),mode="L").save(path)


def _resize_for_tile(rgb: np.ndarray,width: int=420,height: int=280) -> np.ndarray:
    if Image is None:
        raise ContractError("Pillow is required for MoGe diagnostic contact sheets")
    arr=np.clip(np.rint(rgb*255),0,255).astype(np.uint8)
    image=Image.fromarray(arr,mode="RGB")
    image.thumbnail((width,height),Image.Resampling.BILINEAR)
    canvas=Image.new("RGB",(width,height),(20,20,20))
    canvas.paste(image,((width-image.width)//2,(height-image.height)//2))
    return np.asarray(canvas,dtype=np.float32)/255.0


def _labeled_tile(label: str,rgb: np.ndarray,width: int=420,height: int=320) -> np.ndarray:
    if Image is None:
        raise ContractError("Pillow is required for MoGe diagnostic contact sheets")
    body=_resize_for_tile(rgb,width,height-36)
    im=Image.fromarray(np.clip(np.rint(body*255),0,255).astype(np.uint8),mode="RGB")
    canvas=Image.new("RGB",(width,height),(14,14,14))
    canvas.paste(im,(0,36))
    draw=ImageDraw.Draw(canvas)
    draw.text((10,10),label,fill=(235,235,235))
    return np.asarray(canvas,dtype=np.float32)/255.0


def _contact_sheet(items: list[tuple[str,np.ndarray]],columns: int=3) -> np.ndarray:
    if not items:
        return np.zeros((64,64,3),dtype=np.float32)
    tiles=[_labeled_tile(label,rgb) for label,rgb in items]
    h,w,_=tiles[0].shape
    rows=int(math.ceil(len(tiles)/columns))
    sheet=np.zeros((rows*h,columns*w,3),dtype=np.float32)
    for index,tile in enumerate(tiles):
        y=(index//columns)*h
        x=(index%columns)*w
        sheet[y:y+h,x:x+w]=tile
    return sheet


def _pointcloud_preview(points: np.ndarray,source_rgb: np.ndarray,mask: np.ndarray | None) -> tuple[np.ndarray,dict[str,Any]]:
    pts=np.asarray(points,dtype=np.float32)
    if pts.ndim!=3 or pts.shape[-1]!=3:
        raise ContractError(f"MoGe points must resolve to HxWx3, got {pts.shape}")
    valid=np.isfinite(pts).all(axis=-1)
    if mask is not None and mask.shape==valid.shape:
        valid &= mask.astype(bool)
    yy,xx=np.where(valid)
    if len(xx)==0:
        return np.zeros((480,1440,3),dtype=np.float32),{"valid_points":0}
    max_points=90000
    stride=max(1,int(math.ceil(len(xx)/max_points)))
    yy=yy[::stride]; xx=xx[::stride]
    p=pts[yy,xx]
    src=source_rgb
    if src.shape[:2]!=pts.shape[:2]:
        colors=np.full((len(p),3),0.75,dtype=np.float32)
    else:
        colors=src[yy,xx]

    finite=np.isfinite(p).all(axis=1)
    p=p[finite]; colors=colors[finite]
    center=(np.min(p,axis=0)+np.max(p,axis=0))*0.5
    spans=np.maximum(np.max(p,axis=0)-np.min(p,axis=0),1.0e-6)
    views=[
        ("FRONT",0,1),
        ("SIDE",2,1),
        ("TOP",0,2),
    ]
    panel_w,panel_h=480,480
    canvas=np.zeros((panel_h,panel_w*3,3),dtype=np.float32)+0.06
    for vi,(name,a,b) in enumerate(views):
        span=max(float(spans[a]),float(spans[b]))
        x=((p[:,a]-center[a])/span+0.5)*(panel_w-40)+20
        y=(0.5-(p[:,b]-center[b])/span)*(panel_h-40)+20
        xi=np.clip(np.rint(x).astype(np.int32),0,panel_w-1)
        yi=np.clip(np.rint(y).astype(np.int32),0,panel_h-1)
        panel=canvas[:,vi*panel_w:(vi+1)*panel_w]
        panel[yi,xi]=colors
        # crosshair + label marks
        panel[panel_h//2-1:panel_h//2+1,:,]=np.maximum(panel[panel_h//2-1:panel_h//2+1,:,],0.18)
        panel[:,panel_w//2-1:panel_w//2+1,]=np.maximum(panel[:,panel_w//2-1:panel_w//2+1,],0.18)
    return canvas,{
        "valid_points":int(np.count_nonzero(valid)),
        "preview_points":int(len(p)),
        "preview_stride":int(stride),
        "bounds_min":[float(v) for v in np.min(p,axis=0)],
        "bounds_max":[float(v) for v in np.max(p,axis=0)],
    }


def _write_sampled_ply(path: Path,points: np.ndarray,source_rgb: np.ndarray,mask: np.ndarray | None,max_points: int=200000) -> dict[str,Any]:
    pts=np.asarray(points,dtype=np.float32)
    valid=np.isfinite(pts).all(axis=-1)
    if mask is not None and mask.shape==valid.shape:
        valid &= mask.astype(bool)
    yy,xx=np.where(valid)
    stride=max(1,int(math.ceil(len(xx)/max_points))) if len(xx) else 1
    yy=yy[::stride]; xx=xx[::stride]
    p=pts[yy,xx]
    if source_rgb.shape[:2]==pts.shape[:2]:
        c=np.clip(np.rint(source_rgb[yy,xx]*255),0,255).astype(np.uint8)
    else:
        c=np.full((len(p),3),190,dtype=np.uint8)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="\n") as handle:
        handle.write("ply\nformat ascii 1.0\n")
        handle.write(f"element vertex {len(p)}\n")
        handle.write("property float x\nproperty float y\nproperty float z\n")
        handle.write("property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for point,color in zip(p,c):
            handle.write(
                f"{float(point[0]):.8g} {float(point[1]):.8g} {float(point[2]):.8g} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )
    return {"point_count":int(len(p)),"source_valid_count":int(len(xx)*stride),"stride":int(stride)}


def _array_record(arr: np.ndarray) -> dict[str,Any]:
    record={"shape":list(arr.shape),"dtype":str(arr.dtype)}
    finite=np.isfinite(arr) if np.issubdtype(arr.dtype,np.number) else None
    if finite is not None and np.any(finite):
        vals=np.asarray(arr[finite],dtype=np.float64)
        record.update({
            "finite_count":int(vals.size),
            "min":float(np.min(vals)),
            "max":float(np.max(vals)),
            "mean":float(np.mean(vals)),
        })
    return record


class ConceptGhostMoGeDiagnosticProfileTap:
    """Request optional MoGe per-step evidence without changing official profile fields."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required":{
            "profile_config":("CG_GEOMETRY_PROFILE",),
            "enable_moge_diagnostics":("BOOLEAN",{"forceInput":True}),
        }}

    RETURN_TYPES=("CG_GEOMETRY_PROFILE","STRING")
    RETURN_NAMES=("profile_config","tap_report")
    FUNCTION="apply"
    CATEGORY="ConceptGhost/P9 Diagnostics"

    def apply(self,profile_config,enable_moge_diagnostics):
        original=dict(profile_config or {})
        tapped=dict(original)
        existing=bool(original.get("diagnostic_return_per_step",False))
        tapped["diagnostic_return_per_step"]=bool(existing or enable_moge_diagnostics)
        report={
            "schema":"ConceptGhost.MoGeDiagnosticProfileTap.v0.1",
            "enabled":bool(enable_moge_diagnostics),
            "existing_extra_diagnostics":existing,
            "return_per_step_requested":bool(tapped["diagnostic_return_per_step"]),
            "official_profile_fields_changed":False,
            "official_geometry_impact":False,
            "policy":"DIAGNOSTIC_RETURN_EVIDENCE_ONLY",
        }
        return (tapped,json.dumps(report,indent=2,sort_keys=True))


class ConceptGhostMoGeDiagnosticsControl:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required":{
            "enable_moge_diagnostics":("BOOLEAN",{"default":False}),
            "save_raw_outputs":("BOOLEAN",{"default":True}),
            "generate_3d_previews":("BOOLEAN",{"default":True}),
            "generate_extra_depth_visuals":("BOOLEAN",{"default":True}),
        }}

    RETURN_TYPES=("BOOLEAN","BOOLEAN","BOOLEAN","BOOLEAN","STRING")
    RETURN_NAMES=("enabled","save_raw","render_3d","extra_visuals","control_report")
    FUNCTION="configure"
    CATEGORY="ConceptGhost/P9 Diagnostics"

    def configure(self,enable_moge_diagnostics,save_raw_outputs,generate_3d_previews,generate_extra_depth_visuals):
        payload={
            "schema":"ConceptGhost.MoGeDiagnosticsControl.v0.1",
            "enabled":bool(enable_moge_diagnostics),
            "save_raw_outputs":bool(save_raw_outputs),
            "generate_3d_previews":bool(generate_3d_previews),
            "generate_extra_depth_visuals":bool(generate_extra_depth_visuals),
            "authority":"DIAGNOSTIC_ONLY",
            "geometry_impact":False,
            "default_state":"OFF",
        }
        return (
            payload["enabled"],payload["save_raw_outputs"],payload["generate_3d_previews"],
            payload["generate_extra_depth_visuals"],json.dumps(payload,indent=2,sort_keys=True),
        )


class ConceptGhostMoGeDepthDiagnostics:
    """Optional fail-open MoGe-native/derived diagnostic export.

    The node never returns or mutates geometry. It is an OUTPUT_NODE side branch
    so official P9/P10 authority remains unchanged whether diagnostics are OFF,
    ON, successful, partially successful or failed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "moge_geometry":("MOGE_GEOMETRY",),
                "source_image":("IMAGE",),
                "scene_name":("STRING",{"forceInput":True}),
                "output_root":("STRING",{"forceInput":True}),
                "enabled":("BOOLEAN",{"forceInput":True}),
                "save_raw":("BOOLEAN",{"forceInput":True}),
                "render_3d":("BOOLEAN",{"forceInput":True}),
                "extra_visuals":("BOOLEAN",{"forceInput":True}),
            },
            "optional":{
                "moge_report":("STRING",{"forceInput":True}),
            },
        }

    RETURN_TYPES=("IMAGE","STRING","STRING","STRING")
    RETURN_NAMES=("diagnostic_mosaic","diagnostics_dir","manifest_path","report_json")
    FUNCTION="run"
    CATEGORY="ConceptGhost/P9 Diagnostics"
    OUTPUT_NODE=True

    def _blank(self):
        try:
            import torch
            return torch.zeros((1,64,64,3),dtype=torch.float32)
        except Exception:
            return np.zeros((1,64,64,3),dtype=np.float32)

    def _tensor(self,rgb: np.ndarray):
        arr=np.asarray(rgb,dtype=np.float32)[None,...]
        try:
            import torch
            return torch.from_numpy(arr)
        except Exception:
            return arr

    def run(self,moge_geometry,source_image,scene_name,output_root,enabled,save_raw,render_3d,extra_visuals,moge_report=""):
        if not bool(enabled):
            payload={
                "schema":_SCHEMA,
                "status":"DISABLED",
                "enabled":False,
                "authority":"DIAGNOSTIC_ONLY",
                "geometry_impact":False,
                "files_written":0,
                "message":"MoGe diagnostics OFF; official pipeline is unchanged and no diagnostic folder is created.",
            }
            text=json.dumps(payload,indent=2,sort_keys=True)
            return {"ui":{"text":[text]},"result":(self._blank(),"","",text)}

        if np is None:
            payload={
                "schema":_SCHEMA,"status":"WARN","enabled":True,
                "authority":"DIAGNOSTIC_ONLY","geometry_impact":False,
                "message":"NumPy unavailable for diagnostic export. Diagnostics skipped; official pipeline continues unchanged.",
            }
            text=json.dumps(payload,indent=2,sort_keys=True)
            return {"ui":{"text":[text]},"result":(self._blank(),"","",text)}

        root_text=os.path.expandvars(os.path.expanduser(str(output_root or "").strip()))
        if not root_text:
            payload={
                "schema":_SCHEMA,"status":"WARN","enabled":True,
                "authority":"DIAGNOSTIC_ONLY","geometry_impact":False,
                "message":"Diagnostic output_root is empty. Diagnostics skipped; official pipeline continues unchanged.",
            }
            text=json.dumps(payload,indent=2,sort_keys=True)
            return {"ui":{"text":[text]},"result":(self._blank(),"","",text)}

        timestamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        diag_dir=Path(root_text).resolve()/"_diagnostics"/"moge_depth"/_slug(scene_name)/(timestamp+"_"+uuid.uuid4().hex[:8])
        diag_dir.mkdir(parents=True,exist_ok=False)
        manifest_path=diag_dir/"manifest.json"
        partial_manifest={
            "schema":_SCHEMA,
            "status":"RUNNING",
            "enabled":True,
            "created_at_utc":datetime.now(timezone.utc).isoformat(),
            "scene_name":str(scene_name),
            "diagnostics_dir":str(diag_dir),
            "authority":"DIAGNOSTIC_ONLY",
            "geometry_impact":False,
            "official_pipeline_mutated":False,
            "retention":"PRESERVE_EXPLICIT_DIAGNOSTIC_RUN_UNTIL_MANUAL_CLEANUP",
            "preserve_on_failure":True,
            "settings":{
                "save_raw":bool(save_raw),
                "render_3d":bool(render_3d),
                "extra_visuals":bool(extra_visuals),
            },
            "native_outputs":{},
            "derived_visualizations":{},
            "errors":[],
        }
        manifest_path.write_text(json.dumps(partial_manifest,indent=2,sort_keys=True),encoding="utf-8")

        mosaic=self._blank()
        try:
            geom=dict(moge_geometry or {})
            src=_first_image_rgb(source_image)
            original_path=diag_dir/"01_original_input.png"
            _save_rgb(original_path,src)

            depth=_first_map(geom.get("depth_metric_native",geom.get("depth")))
            mask=_first_map(geom.get("mask_native",geom.get("mask")))
            mask_bool=mask.astype(bool) if mask is not None else None
            normal=_first_vectors(geom.get("normal_native",geom.get("normal")),3)
            points=_first_vectors(geom.get("points_metric_native",geom.get("points")),3)
            intr=_to_numpy(geom.get("intrinsics_native",geom.get("intrinsics")))

            native={}
            derived={"original_input":str(original_path)}
            raw_dir=diag_dir/"raw"
            if bool(save_raw):
                raw_dir.mkdir(parents=True,exist_ok=True)
                native_candidates={
                    "depth_native":depth,
                    "normal_native":normal,
                    "mask_native":mask,
                    "intrinsics_native":intr,
                    "points_native":points,
                }
                for name,arr in native_candidates.items():
                    if arr is None:
                        native[name]={"available":False}
                        continue
                    arr=np.asarray(arr)
                    out=raw_dir/(name+".npy")
                    np.save(out,arr,allow_pickle=False)
                    native[name]={
                        "available":True,"file":str(out),**_array_record(arr)
                    }
            else:
                for name,arr in {
                    "depth_native":depth,"normal_native":normal,"mask_native":mask,
                    "intrinsics_native":intr,"points_native":points,
                }.items():
                    native[name]={"available":arr is not None,**(_array_record(np.asarray(arr)) if arr is not None else {})}

            tiles=[("Original input",src)]
            if depth is not None:
                valid=_valid_depth(depth,mask_bool)
                norm,window=_normalize_scalar(depth,valid)
                gray=_gray_rgb(norm)
                heat=_heat_rgb(norm)
                _save_rgb(diag_dir/"02_depth_grayscale.png",gray)
                _save_rgb(diag_dir/"03_depth_heatmap.png",heat)
                derived["depth_grayscale"]=str(diag_dir/"02_depth_grayscale.png")
                derived["depth_heatmap"]=str(diag_dir/"03_depth_heatmap.png")
                tiles.extend([("Depth · grayscale",gray),("Depth · heatmap",heat)])

                inv=np.zeros_like(depth,dtype=np.float32)
                inv[valid]=1.0/np.maximum(depth[valid],1.0e-9)
                inv_norm,inv_window=_normalize_scalar(inv,valid)
                inv_rgb=_gray_rgb(inv_norm)
                _save_rgb(diag_dir/"04_inverse_depth.png",inv_rgb)
                derived["inverse_depth"]=str(diag_dir/"04_inverse_depth.png")
                tiles.append(("Inverse depth / disparity",inv_rgb))

                if bool(extra_visuals):
                    bands,band_edges=_bands_rgb(depth,valid,12)
                    contours=_contours_from_bands(bands,valid)
                    edges,edge_threshold=_depth_edges(depth,valid)
                    edge_rgb=np.repeat(edges[...,None],3,axis=-1)
                    _save_rgb(diag_dir/"05_depth_bands.png",bands)
                    _save_rgb(diag_dir/"06_depth_contours.png",contours)
                    _save_rgb(diag_dir/"07_depth_discontinuities.png",edge_rgb)
                    derived.update({
                        "depth_bands":str(diag_dir/"05_depth_bands.png"),
                        "depth_contours":str(diag_dir/"06_depth_contours.png"),
                        "depth_discontinuities":str(diag_dir/"07_depth_discontinuities.png"),
                    })
                    tiles.extend([
                        ("Depth · bands",bands),
                        ("Depth · contours",contours),
                        ("Depth · discontinuities",edge_rgb),
                    ])
                    partial_manifest["depth_visualization"]={
                        "normalization_window":window,
                        "inverse_depth_window":inv_window,
                        "band_edges_m":band_edges,
                        "edge_threshold_log_depth_gradient":edge_threshold,
                        "valid_pixel_count":int(np.count_nonzero(valid)),
                        "valid_ratio":float(np.mean(valid)),
                        "depth_percentiles_m":_percentiles(depth[valid]),
                    }

            normal_rgb=_normal_rgb(normal)
            if normal_rgb is not None:
                _save_rgb(diag_dir/"08_normals.png",normal_rgb)
                derived["normals"]=str(diag_dir/"08_normals.png")
                tiles.append(("MoGe normals",normal_rgb))

            if mask_bool is not None:
                _save_mask(diag_dir/"09_mask.png",mask_bool)
                mask_rgb=np.repeat(mask_bool[...,None].astype(np.float32),3,axis=-1)
                derived["mask"]=str(diag_dir/"09_mask.png")
                tiles.append(("MoGe mask",mask_rgb))

            if intr is not None:
                intr_path=diag_dir/"10_intrinsics.json"
                intr_path.write_text(json.dumps({"intrinsics":_json_safe(intr)},indent=2,sort_keys=True),encoding="utf-8")
                derived["intrinsics_json"]=str(intr_path)

            if bool(render_3d) and points is not None:
                pc_rgb,pc_info=_pointcloud_preview(points,src,mask_bool)
                pc_path=diag_dir/"11_pointcloud_preview.png"
                _save_rgb(pc_path,pc_rgb)
                derived["pointcloud_preview"]=str(pc_path)
                tiles.append(("MoGe point cloud · 3-view",pc_rgb))
                ply_path=diag_dir/"12_pointcloud_sampled.ply"
                ply_info=_write_sampled_ply(ply_path,points,src,mask_bool)
                derived["sampled_pointcloud_ply"]=str(ply_path)
                partial_manifest["pointcloud_preview"]={**pc_info,**ply_info}

            refinement_dir=diag_dir/"refinement_steps"
            refinement=[]
            for key in sorted(geom):
                if not key.startswith(("depth_per_step_","points_per_step_","intrinsics_per_step_")):
                    continue
                arr=_to_numpy(geom.get(key))
                if arr is None:
                    continue
                record={"name":key,**_array_record(arr)}
                if bool(save_raw):
                    refinement_dir.mkdir(parents=True,exist_ok=True)
                    raw_path=refinement_dir/(key+".npy")
                    np.save(raw_path,arr,allow_pickle=False)
                    record["raw_file"]=str(raw_path)
                if bool(extra_visuals) and key.startswith("depth_per_step_"):
                    d=_first_map(arr)
                    if d is not None:
                        v=_valid_depth(d,None)
                        n,_=_normalize_scalar(d,v)
                        viz=_heat_rgb(n)
                        viz_path=refinement_dir/(key+"_heatmap.png")
                        _save_rgb(viz_path,viz)
                        record["heatmap"]=str(viz_path)
                refinement.append(record)

            mosaic_rgb=_contact_sheet(tiles,columns=3)
            mosaic_path=diag_dir/"00_moge_depth_diagnostics_mosaic.png"
            _save_rgb(mosaic_path,mosaic_rgb)
            mosaic=self._tensor(mosaic_rgb)

            partial_manifest.update({
                "status":"PASS",
                "completed_at_utc":datetime.now(timezone.utc).isoformat(),
                "native_outputs":native,
                "derived_visualizations":derived,
                "refinement_arrays":refinement,
                "mosaic_path":str(mosaic_path),
                "moge_identity":{
                    "engine":"MoGe",
                    "model":geom.get("conceptghost_model"),
                    "geometry_profile":geom.get("conceptghost_geometry_profile"),
                    "worker_report":_json_safe(geom.get("conceptghost_worker_report")),
                    "inference_report":str(moge_report or ""),
                },
                "native_vs_derived":{
                    "native":[
                        "depth_metric_native/depth","points_metric_native/points","normal_native/normal",
                        "mask_native/mask","intrinsics_native/intrinsics","*_per_step_* when returned by MoGe"
                    ],
                    "derived":[
                        "grayscale","heatmap","inverse depth","depth bands","contours",
                        "depth discontinuities","point-cloud preview","sampled PLY","mosaic"
                    ],
                    "primary_mesh_preview":"Not duplicated here. Official P9 PrimaryMesh/Primary Master remains the downstream authoritative derived mesh preview.",
                },
                "failure_fallback":"Diagnostic failures are fail-open and do not alter or replace official P9/P10 geometry.",
                "next_stage":"Official P9 geometry/evidence path continues unchanged; diagnostics are inspection-only.",
            })
            manifest_path.write_text(json.dumps(partial_manifest,indent=2,sort_keys=True),encoding="utf-8")
            report=json.dumps(partial_manifest,indent=2,sort_keys=True)
            return {
                "ui":{"text":[
                    "MoGe Depth Diagnostics: PASS",
                    f"Saved: {diag_dir}",
                    "DIAGNOSTIC ONLY · official geometry unchanged",
                ]},
                "result":(mosaic,str(diag_dir),str(manifest_path),report),
            }
        except Exception as error:
            partial_manifest.update({
                "status":"WARN_DIAGNOSTIC_FAILED",
                "completed_at_utc":datetime.now(timezone.utc).isoformat(),
                "errors":[f"{type(error).__name__}: {error}"],
                "failure_fallback":"FAIL_OPEN_DIAGNOSTIC_ONLY; OFFICIAL_PIPELINE_NOT_MUTATED",
            })
            try:
                manifest_path.write_text(json.dumps(partial_manifest,indent=2,sort_keys=True),encoding="utf-8")
            except Exception:
                pass
            report=json.dumps(partial_manifest,indent=2,sort_keys=True)
            return {
                "ui":{"text":[
                    "MoGe Depth Diagnostics: WARN · diagnostic export failed",
                    str(error),
                    f"Partial diagnostics preserved: {diag_dir}",
                    "Official geometry remains unchanged.",
                ]},
                "result":(mosaic,str(diag_dir),str(manifest_path),report),
            }
