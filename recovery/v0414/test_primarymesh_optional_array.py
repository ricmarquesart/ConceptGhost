import numpy as np

def aligned_optional(value, expected_len, dtype):
    if value is None:
        return None
    raw = np.asarray(value)
    if raw.ndim < 1 or raw.shape[0] != expected_len:
        return None
    return np.asarray(raw, dtype=dtype)

n=16
# Baseline/runtime-style scalars and None must be ignored, never len()-checked.
for value in [None, 0.73, np.asarray(7), np.asarray(2,dtype=np.uint8)]:
    assert aligned_optional(value,n,np.float32) is None

# Correct per-point arrays remain legal.
arr=np.linspace(0.1,0.9,n,dtype=np.float32)
out=aligned_optional(arr,n,np.float32)
assert out is not None and out.shape==(n,)

# Wrong-length vectors remain excluded.
assert aligned_optional(np.ones(3,np.float32),n,np.float32) is None

print("P9_V0414_PRIMARYMESH_OPTIONAL_ARRAY_PASS",{"points":n})
