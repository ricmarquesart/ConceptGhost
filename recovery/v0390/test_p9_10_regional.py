import numpy as np

def p9_10_refine(depth, confidence, boundary, normals):
    depth=np.asarray(depth,np.float32)
    confidence=np.asarray(confidence,np.float32)
    boundary=np.asarray(boundary,bool)
    normals=np.asarray(normals,np.float32)
    h,w=depth.shape
    # 4-neighbor normal boundary
    n=normals/np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-6)
    nb=np.zeros((h,w),bool)
    cos_thr=np.cos(np.deg2rad(22.0))
    for a,b in [((slice(None),slice(1,None)),(slice(None),slice(None,-1))),
                ((slice(1,None),slice(None)),(slice(None,-1),slice(None)))]:
        dot=np.abs(np.sum(n[a]*n[b],axis=-1))
        hit=dot<cos_thr
        nb[a]|=hit; nb[b]|=hit
    protected=boundary|nb
    # one-pixel halo
    halo=protected.copy()
    halo[1:]|=protected[:-1]; halo[:-1]|=protected[1:]
    halo[:,1:]|=protected[:,:-1]; halo[:,:-1]|=protected[:,1:]
    protected=halo
    eligible=(confidence>=0.72)&~protected
    out=depth.copy()
    total=np.zeros_like(depth); weight=np.zeros_like(depth)
    for dst,src in [((slice(None),slice(1,None)),(slice(None),slice(None,-1))),
                    ((slice(None),slice(None,-1)),(slice(None),slice(1,None))),
                    ((slice(1,None),slice(None)),(slice(None,-1),slice(None))),
                    ((slice(None,-1),slice(None)),(slice(1,None),slice(None)))]:
        d0=depth[dst]; d1=depth[src]
        rel=np.abs(d1-d0)/np.maximum(np.minimum(np.abs(d0),np.abs(d1)),1e-6)
        ok=(rel<=0.035)&~protected[dst]&~protected[src]
        dot=np.abs(np.sum(n[dst]*n[src],axis=-1))
        ok &= dot>=np.cos(np.deg2rad(14.0))
        wgt=np.where(ok,np.maximum(confidence[src],0.05),0.0).astype(np.float32)
        total[dst]+=d1*wgt; weight[dst]+=wgt
    mean=np.divide(total,np.maximum(weight,1e-6))
    alpha=np.clip((confidence-0.72)/(1.0-0.72),0,1)*0.28
    use=eligible&(weight>0)
    out[use]=(1-alpha[use])*depth[use]+alpha[use]*mean[use]
    return out,protected,use

h,w=64,96
x=np.arange(w,dtype=np.float32)[None,:]
y=np.arange(h,dtype=np.float32)[:,None]
base=np.where(x<48,10.0,20.0).astype(np.float32)
base=np.repeat(base,h,axis=0)
ripple=0.025*np.sin(x*0.47)+0.018*np.cos(y*0.39)
depth=(base+ripple).astype(np.float32)
confidence=np.ones((h,w),np.float32)
confidence[18:34,12:28]=0.20
boundary=np.zeros((h,w),bool); boundary[:,47:49]=True
normals=np.zeros((h,w,3),np.float32)
normals[:,:48,2]=1.0
normals[:,48:,0]=1.0
refined,protected,use=p9_10_refine(depth,confidence,boundary,normals)
changed=np.abs(refined-depth)>1e-7
assert changed.any()
assert not changed[protected].any()
assert not changed[18:34,12:28].any()
assert np.mean(np.abs(refined[:,:40]-10.0)) < np.mean(np.abs(depth[:,:40]-10.0))
assert np.mean(np.abs(refined[:,56:]-20.0)) < np.mean(np.abs(depth[:,56:]-20.0))
assert float(np.median(refined[:,46])) < 10.1
assert float(np.median(refined[:,49])) > 19.9
assert np.isfinite(refined).all()
print("P9_10_GITHUB_STATIC_PASS",{"changed_ratio":float(changed.mean()),"protected_changed":int((changed&protected).sum()),"low_conf_changed":int(changed[18:34,12:28].sum())})
