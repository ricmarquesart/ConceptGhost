import numpy as np

def positive_threshold(values, q=85.0):
    v=np.asarray(values,float)
    v=v[np.isfinite(v)&(v>1e-6)]
    return float(np.percentile(v,q)) if len(v) else float("inf")

def region_score(solver_conf, normal_conf, boundary_strength, boundary_ratio):
    safety=np.clip(1.0-max(float(boundary_strength),float(boundary_ratio)),0.0,1.0)
    return float(np.clip(0.65*solver_conf+0.25*normal_conf+0.10*safety,0.0,1.0))

def gate(score, high=0.75, medium=0.55):
    if score>=high: return "HIGH",0.25,0.020,True
    if score>=medium: return "MEDIUM",0.08,0.005,False
    return "LOW",0.0,0.0,False

# Sparse boundary must remain detectable instead of collapsing to an all-zero percentile.
b=np.zeros(1000,np.float32); b[490:510]=1.0
thr=positive_threshold(b)
assert thr>0 and thr<=1.0,thr

hi=region_score(.95,.95,.02,.03)
med=region_score(.62,.70,.05,.05)
lo=region_score(.20,.20,.10,.10)
assert gate(hi)[0]=="HIGH"
assert gate(med)[0]=="MEDIUM"
assert gate(lo)[0]=="LOW"
assert gate(lo)[1:]==(0.0,0.0,False)

# P9.13 topology policy: removals only in HIGH; no new faces.
labels=np.array([0,0,1,1,2,2],dtype=np.int32)
remove=np.array([1,0,1,0,1,0],dtype=bool)
states={0:"HIGH",1:"MEDIUM",2:"LOW"}
high_face=np.array([states[int(x)]=="HIGH" for x in labels],dtype=bool)
gated=remove&high_face
assert gated.tolist()==[True,False,False,False,False,False]

# Regional rollback: worsening plane RMS zeroes the region strength.
strengths={0:.25,1:.08}
before={0:.010,1:.020}; after={0:.008,1:.021}
rollback=[r for r in strengths if after[r]>before[r]+max(1e-9,abs(before[r])*1e-6)]
for r in rollback: strengths[r]=0.0
assert rollback==[1] and strengths[1]==0.0 and strengths[0]>.0

# Global reprojection gate.
rmse_before=.001
rmse_after=.011
assert rmse_after <= rmse_before + .25
assert not (.40 <= rmse_before + .25)

print("P9_13_GITHUB_STATIC_PASS",{"boundary_threshold":thr,"high":hi,"medium":med,"low":lo,"regional_rollback":rollback})
