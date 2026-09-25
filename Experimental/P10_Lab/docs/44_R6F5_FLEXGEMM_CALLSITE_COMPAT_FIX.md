# Gate 7 R6F5 — FlexGEMM Active Callsite Compatibility Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F4

R6F4 reached the ConceptGhost-private FlexGEMM compatibility patch, but that patch exited with code 4 before the MoGe smoke test. The failure was inside the patcher's source-shape assumption, not inside MoGe inference.

The previous bridge tried to locate and replace the entire generic helper function boundary. That is unnecessarily brittle because the only path used by the failing MoGe sparse refiner is the hashmap build/lookup callsite.

## R6F5 repair

R6F5 patches only active callsites in the private FlexGEMM hashmap implementation.

FlexGEMM's host wrappers already:
- flatten keys/queries;
- pad them to a power-of-two width in 32-bit words;
- view the tensors as `torch.int32`;
- pass `D_32` into Triton as `D`.

Therefore:
- build/unique kernels use `D_32 = D`;
- lookup uses `query_vec.to(tl.int32)` and `D_32 = D`;
- the generic dtype-introspection helper is allowed to remain in source but is no longer called by the hashmap lookup path.

The patch accepts pristine `dtype.itemsize` callsites and R6F3 `primitive_bitwidth` callsites, and is idempotent if the safe callsites are already present.

## Invariants

Unchanged:
- private runtime: Python 3.11.9, Torch 2.6.0, torchvision 0.21.0, cu124, Triton Windows 3.2.x;
- High Fidelity model: `Ruicheng/moge-3-vitg`;
- `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 outputs;
- shared ComfyUI environment;
- Gate 7 evidence thresholds.

Gate 8 remains source-only in parallel and is not included in this runtime validation package.
