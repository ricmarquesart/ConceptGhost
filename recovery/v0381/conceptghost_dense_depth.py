from __future__ import annotations

import math
from typing import Any

import numpy as np

def _arr(v: Any) -> np.ndarray:
    if v is None:
        return np.array([])
    if isinstance(v, np.ndarray):
        return v
    if hasattr(v, "detach"):
        return v.detach().cpu().numpy()
    if hasattr(v, "cpu") and hasattr(v, "numpy"):
        return v.cpu().numpy()
    return np.asarray(v)

def _depth2d(v: Any) -> np.ndarray:
    a = _arr(v).astype(np.float32, copy=False)
    while a.ndim > 2 and a.shape[0] == 1:
        a = a[0]
    if a.ndim != 2:
        raise ValueError(f"Expected HxW depth, got {a.shape}")
    return a

def _mask2d(v: Any, shape: tuple[int, int]) -> np.ndarray:
    if v is None:
        return np.ones(shape, dtype=bool)
    a = _arr(v)
    while a.ndim > 2 and a.shape[0] == 1:
        a = a[0]
    if a.shape != shape:
        raise ValueError(f"Mask shape {a.shape} != depth shape {shape}")
    return a.astype(bool, copy=False)

def _valid(depth: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    ok = np.isfinite(depth) & (depth > 0)
    if mask is not None:
        ok &= mask
    return ok

def _log_gradient(depth: np.ndarray, valid: np.ndarray) -> np.ndarray:
    safe = np.where(valid, np.maximum(depth, 1e-6), 1.0)
    ld = np.log(safe)
    gx = np.zeros_like(ld, dtype=np.float32)
    gy = np.zeros_like(ld, dtype=np.float32)
    gx[:, 1:-1] = 0.5 * (ld[:, 2:] - ld[:, :-2])
    gy[1:-1, :] = 0.5 * (ld[2:, :] - ld[:-2, :])
    z = np.sqrt(gx * gx + gy * gy)
    z[~valid] = 0.0
    return z

def normalize_metric_depths(sources: dict[str, tuple[np.ndarray, np.ndarray]]):
    names=list(sources)
    equations=[]; pairwise={}
    for i in range(len(names)):
        di,mi=sources[names[i]]; vi=_valid(di,mi)
        for j in range(i+1,len(names)):
            dj,mj=sources[names[j]]; vj=_valid(dj,mj)
            ov=vi & vj
            if int(ov.sum()) < 256:
                continue
            lr=np.log(np.maximum(di[ov],1e-6))-np.log(np.maximum(dj[ov],1e-6))
            qlo,qhi=np.quantile(lr,[0.05,0.95])
            lr=lr[(lr>=qlo)&(lr<=qhi)]
            if lr.size < 256:
                continue
            med=float(np.median(lr))
            pairwise[f"{names[i]}__vs__{names[j]}"]={"median_log_ratio":med,"overlap_pixels":int(ov.sum())}
            row=np.zeros(len(names),dtype=np.float64); row[i]=1.0; row[j]=-1.0
            equations.append((row,med))
    if not equations:
        raise RuntimeError("No pairwise overlap sufficient for dense-depth normalization")
    A=np.stack([r for r,_ in equations]+[np.ones(len(names),dtype=np.float64)],axis=0)
    b=np.asarray([v for _,v in equations]+[0.0],dtype=np.float64)
    bias,*_=np.linalg.lstsq(A,b,rcond=None)
    scales={names[i]:float(np.exp(-bias[i])) for i in range(len(names))}
    out={name:sources[name][0].astype(np.float32,copy=False)*np.float32(scales[name]) for name in names}
    return out,{"pairwise":pairwise,"source_scale_to_common":scales}

def fuse_dense_depth(moge_depth,moge_mask,depthpro_depth,depthpro_mask,depthanything_depth,depthanything_mask,*,inlier_relative_threshold=0.12,boundary_quantile=0.88):
    md=_depth2d(moge_depth); pd=_depth2d(depthpro_depth); ad=_depth2d(depthanything_depth)
    shape=md.shape
    native={"MoGe":(md,_mask2d(moge_mask,shape)),"DepthPro":(pd,_mask2d(depthpro_mask,shape)),"DepthAnything":(ad,_mask2d(depthanything_mask,shape))}
    aligned,_=normalize_metric_depths(native)
    names=["MoGe","DepthPro","DepthAnything"]
    stack=np.stack([aligned[n] for n in names],axis=0)
    valid=np.stack([_valid(aligned[n],native[n][1]) for n in names],axis=0)
    nan_stack=np.where(valid,stack,np.nan)
    with np.errstate(all="ignore"):
        pixel_median=np.nanmedian(nan_stack,axis=0)
    denom=np.maximum(np.abs(pixel_median),1e-6)
    rel=np.abs(stack-pixel_median[None,...])/denom[None,...]
    inlier=valid & (rel<=float(inlier_relative_threshold))
    valid_count=valid.sum(axis=0)
    inlier_count=inlier.sum(axis=0)
    closest=np.argmin(np.where(valid,rel,np.inf),axis=0)
    need_one=valid_count==1
    for i in range(len(names)):
        inlier[i]|=need_one & valid[i]
    no_inlier=(inlier_count==0)&(valid_count>=2)
    for i in range(len(names)):
        inlier[i]|=no_inlier & (closest==i) & valid[i]
    inlier_count=inlier.sum(axis=0)
    fused_mean=np.where(inlier,stack,0.0).sum(axis=0)/np.maximum(inlier_count,1)
    edges=[]; edge_thresholds={}
    for i,name in enumerate(names):
        g=_log_gradient(stack[i],valid[i])
        vals=g[valid[i]]
        positive=vals[np.isfinite(vals)&(vals>1e-6)]
        thr=float(np.quantile(positive,boundary_quantile)) if positive.size else float("inf")
        edge_thresholds[name]=thr
        edges.append(valid[i]&np.isfinite(g)&(g>1e-6)&(g>=thr))
    boundary=np.stack(edges,axis=0).sum(axis=0)>=2
    meddist=np.where(inlier,np.abs(stack-pixel_median[None,...]),np.inf)
    winner=np.argmin(meddist,axis=0)
    rows,cols=np.indices(shape)
    fused=np.where(boundary&(valid_count>=2),stack[winner,rows,cols],fused_mean).astype(np.float32)
    with np.errstate(all="ignore"):
        mad=np.nanmedian(np.where(inlier,np.abs(stack-fused[None,...]),np.nan),axis=0)
    agreement=1.0-np.clip(mad/np.maximum(np.abs(fused),1e-6)/max(inlier_relative_threshold,1e-6),0.0,1.0)
    coherent_availability=inlier_count.astype(np.float32)/float(len(names))
    rejection_penalty=np.divide(inlier_count.astype(np.float32),np.maximum(valid_count,1).astype(np.float32))
    confidence=(coherent_availability*np.nan_to_num(agreement,nan=0.0)*rejection_penalty).astype(np.float32)
    return {"depth_m":fused,"confidence":confidence},{"boundary_ratio":float(np.mean(boundary)),"edge_thresholds":edge_thresholds}
