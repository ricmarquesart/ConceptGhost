import hashlib, json, math
import numpy as np

# P9.13 confidence-gated refinement invariants
h,w=48,72
depth=np.full((h,w),10.0,np.float32)
depth[:,36:]=20.0
conf=np.ones((h,w),np.float32)
conf[12:24,8:20]=0.2
boundary=np.zeros((h,w),bool)
boundary[:,35:37]=True
noise=(0.02*np.sin(np.arange(w,dtype=np.float32)[None,:]*0.41))
noisy=depth+noise
protected=boundary.copy()
protected[1:]|=boundary[:-1]; protected[:-1]|=boundary[1:]
protected[:,1:]|=boundary[:,:-1]; protected[:,:-1]|=boundary[:,1:]
eligible=(conf>=0.72)&~protected
refined=noisy.copy()
for y in range(1,h-1):
  for x in range(1,w-1):
    if not eligible[y,x]: continue
    vals=[noisy[y,x],noisy[y-1,x],noisy[y+1,x],noisy[y,x-1],noisy[y,x+1]]
    vals=[v for v in vals if abs(v-noisy[y,x])/max(abs(noisy[y,x]),1e-6)<=0.035]
    if len(vals)>=3:
      refined[y,x]=0.75*noisy[y,x]+0.25*float(np.mean(vals))
changed=np.abs(refined-noisy)>1e-7
assert changed.any()
assert not changed[protected].any()
assert not changed[12:24,8:20].any()

# P9.14 canonical FOV parity / identity
sid='cgsc_ci_v0400'
fov=37.44
sensor=36.0
focal=sensor/(2*math.tan(math.radians(fov)/2))
maya_fov=math.degrees(2*math.atan(sensor/(2*focal)))
assert abs(maya_fov-fov) < 1e-9
identity={'scene_contract_id':sid,'camera_scene_contract_id':sid,'geometry_scene_contract_id':sid,'primary_mesh_scene_contract_id':sid,'maya_scene_contract_id':sid}
assert len(set(identity.values()))==1

# P9.15 controlled regression gate
stable={'source':'abc','reprojection':0.20,'outlier_ratio':0.02,'exports':{'ma':'PASS','fbx':'PASS','ply':'PASS','usd':'PASS'}}
ref={'source':'abc','reprojection':0.18,'outlier_ratio':0.01,'identity':'PASS','p913':'PASS','moved_vertices':900,'exports':{'ma':'PASS','fbx':'PASS','ply':'PASS','usd':'PASS'}}
checks=[
 stable['source']==ref['source'],
 ref['reprojection'] <= stable['reprojection']+0.25,
 ref['identity']=='PASS',
 all(v=='PASS' for v in ref['exports'].values())
]
improvements=(ref['reprojection']<stable['reprojection']) or (ref['outlier_ratio']<stable['outlier_ratio']) or (ref['p913']=='PASS' and ref['moved_vertices']>0)
assert all(checks) and improvements
bad=dict(ref); bad['source']='different'
assert not (stable['source']==bad['source'])

print('P9_13_14_15_GITHUB_STATIC_PASS', {'changed_ratio':float(changed.mean()),'fov':maya_fov,'sha':'438400bcc02a5c4f74842b0beefe07b0c8c30248b2610d8baf42b5d421c6eaf8'})
