class AmbiguousTensor:
    def __bool__(self):
        raise RuntimeError("Boolean value of Tensor with more than one value is ambiguous")

def coalesce(primary, fallback):
    value = primary
    if value is None:
        value = fallback
    return value

a = AmbiguousTensor()
b = AmbiguousTensor()

# v0.41.1 must never evaluate tensor truthiness while selecting native/fallback MoGe depth/mask.
assert coalesce(a, b) is a
assert coalesce(None, b) is b

# Regression guard: the prohibited pattern is precisely Python boolean coalescing on tensors.
try:
    _ = a or b
except RuntimeError as e:
    assert "ambiguous" in str(e)
else:
    raise AssertionError("ambiguous tensor bool should have raised")

print("P9_V0411_DENSE_DEPTH_TENSOR_COALESCE_PASS")
