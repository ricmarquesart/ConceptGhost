import math
import numpy as np

def focal_for_fov(width, deg):
    return width/(2.0*math.tan(math.radians(deg)*0.5))

def rel(a,b):
    return abs(a-b)/max((abs(a)+abs(b))*0.5,1e-12)

def largest(obs,thr):
    best=[]
    best_spread=float("inf")
    for i in range(len(obs)):
        group=[j for j in range(len(obs)) if rel(obs[i][1],obs[j][1])<=thr]
        coherent=[j for j in group if all(rel(obs[j][1],obs[k][1])<=thr for k in group)] or [i]
        vals=np.asarray([obs[j][1] for j in coherent],dtype=float)
        spread=float(np.ptp(vals)/max(np.mean(vals),1e-12)) if len(vals)>1 else 0.0
        if len(coherent)>len(best) or (len(coherent)==len(best) and spread<best_spread):
            best=coherent; best_spread=spread
    return best

def solve(obs,strong=0.10):
    recovery=min(0.25,max(0.20,strong*2.0))
    g=largest(obs,strong)
    if len(g)>=2:
        vals=[obs[i][1] for i in g]
        return "STRONG_AGREEMENT",float(np.mean(vals)),0.82
    g=largest(obs,recovery)
    if len(g)>=2:
        vals=[obs[i][1] for i in g]
        return "RECOVERED_AGREEMENT",float(np.mean(vals)),0.62
    if not obs:
        raise RuntimeError("no valid focal witness")
    vals=np.asarray([v for _,v in obs],dtype=float)
    fx=float(np.exp(np.median(np.log(np.maximum(vals,1e-12)))))
    disp=float(np.median(np.abs(np.log(np.maximum(vals,1e-12))-math.log(fx)))) if len(vals)>1 else 1.0
    conf=float(np.clip(0.45-0.50*disp,0.15,0.45))
    mode="AMBIGUOUS_CONTINUE" if len(vals)>=2 else "SINGLE_WITNESS_CONTINUE"
    return mode,fx,conf

w=1448
obs=[
    ("Atlas",focal_for_fov(w,36.83175195590167)),
    ("MoGeIndependent",focal_for_fov(w,67.5001183691541)),
    ("DepthPro",focal_for_fov(w,54.9986956696813)),
]
mode,fx,conf=solve(obs)
fov=math.degrees(2.0*math.atan(w/(2.0*fx)))
assert mode=="AMBIGUOUS_CONTINUE"
assert abs(fx-1390.8297119140625)<1e-3
assert abs(fov-54.9986956696813)<1e-4
assert 0.15 <= conf <= 0.45

# Existing strong case remains strong.
m2,_,_=solve([("Atlas",1500.0),("MoGeIndependent",1530.0),("DepthPro",1490.0)])
assert m2=="STRONG_AGREEMENT"

# No focal at all is still fatal.
try:
    solve([])
except RuntimeError:
    pass
else:
    raise AssertionError("no focal witness must remain fatal")

print("P9_V0403_NONBLOCKING_FOCAL_PASS",{"mode":mode,"focal_px":fx,"fov":fov,"confidence":conf})
