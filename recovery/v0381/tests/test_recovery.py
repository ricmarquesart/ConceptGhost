import importlib.util
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("dense", root/"conceptghost_dense_depth.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

h,w=40,80
base=np.full((h,w),10.0,np.float32); base[:,40:]=20.0
m=base.copy(); da=base*1.02; dp=base.copy(); dp[10:30,10:30]=100.0
mask=np.ones_like(base,dtype=bool)
c,r=mod.fuse_dense_depth(m,mask,dp,mask,da,mask)
assert 0.005 <= r["boundary_ratio"] <= 0.08, r
assert float(np.mean(c["confidence"][10:30,10:30])) < 0.75
assert float(np.mean(c["confidence"][:10,:10])) > 0.9

patch=(root/"p9_recovery_v0381.patch").read_text()
for token in ['allowed_engines = {"moge", "p9_solver_fusion"}','"source_engine": geometry_engine','"geometry_engine": str(canonical.get("engine") or "unknown")']:
    assert token in patch, token
print("P9_RECOVERY_ACTION_PASS")
