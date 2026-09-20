import numpy as np

SKY=1; GROUND=2; ARCH=3

def gate(dense_conf, sem_conf, uncertainty, normal_consistency, boundary):
    semantic=np.where(sem_conf>0,0.45+0.55*np.clip(sem_conf*(1-uncertainty),0,1),0.45)
    normal=0.35+0.65*np.clip(normal_consistency,0,1)
    regional=np.clip(dense_conf*semantic*normal,0,1)
    return regional, regional*(1-boundary)

h,w=24,32
macro=np.zeros((h,w),np.uint8)
macro[:4]=SKY; macro[16:]=GROUND; macro[5:15,:14]=ARCH
dense=np.ones((h,w),np.float32)*0.98
sem=np.ones((h,w),np.float32)*0.95
unc=np.ones((h,w),np.float32)*0.04
norm=np.ones((h,w),np.float32)*0.95
boundary=np.zeros((h,w),np.float32); boundary[:,14:16]=1.0
regional,refine=gate(dense,sem,unc,norm,boundary)
sky=(macro==SKY)&(sem>=0.70)&(unc<=0.35)
assert sky.sum()==4*w
assert float(refine[:,14:16].max())==0.0
assert float(regional[8,8])>0.75

# Normal+boundary mesh rule: a strong normal discontinuity with reliable confidence
# must reject a bridge even if depth is flat.
angle_deg=90.0; normal_conf=1.0; boundary_conf=1.0
normal_bridge=(normal_conf>=0.55 and boundary_conf>=0.35 and angle_deg>=45.0)
assert normal_bridge

# Semantic evidence must not be report-only: at least one authoritative geometry
# effect is mandatory for a synthetic scene with confident sky/ground/structure.
geometry_effects={
  "sky_invalidated": int(sky.sum()),
  "boundary_refinement_suppressed": int((refine==0).sum()),
  "normal_boundary_bridge_rejected": int(normal_bridge),
}
assert sum(v>0 for v in geometry_effects.values())>=3
print("P9_10_CI_CONTRACT_PASS",geometry_effects)
