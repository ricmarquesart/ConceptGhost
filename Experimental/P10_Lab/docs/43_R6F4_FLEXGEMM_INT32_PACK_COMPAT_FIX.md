# Gate 7 R6F4 — FlexGEMM int32-pack / Triton 3.2 Compatibility Fix

Date: 2026-09-24 / 2026-09-25 UTC  
Status: SOURCE FIX IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F3

R6F3 correctly preserved the Turing-safe private runtime:
- PyTorch 2.6.0 + cu124;
- torchvision 0.21.0;
- Triton Windows 3.2.0.post21;
- RTX 2080 Ti / sm75 target;
- shared ComfyUI environment untouched.

R6F3 also successfully applied the first FlexGEMM compatibility bridge before the smoke test.

The smoke test then failed at the next compiler boundary in the same pinned FlexGEMM hashmap kernel:

`D * (keys_ptr.dtype.element_ty.primitive_bitwidth // 8)`

On Triton 3.2 this pointer/JIT dtype introspection does not resolve to a usable compile-time integer in this context; it produced `NotImplementedType`.

## Root correction

The pinned FlexGEMM host wrappers already establish a stronger contract before any Triton kernel call:

1. coordinates/keys are flattened and viewed as bytes;
2. byte width is padded to a power-of-two number of 32-bit words;
3. keys and queries are explicitly viewed as `torch.int32`;
4. the kernel argument `D` is already the number of int32 words (`D_32`).

Therefore the Triton kernels do not need to rediscover byte width from their JIT pointer/tensor dtypes.

## R6F4 bounded bridge

R6F4 changes only the ConceptGhost-private copy of
`flex_gemm/kernels/triton/hashmap.py`:

- build kernel: `D_32 = D`;
- unique kernel: `D_32 = D`;
- lookup inline: `query_vec_32 = query_vec.to(tl.int32)`, `D_32 = D`;
- the little-endian helper becomes a direct int32 cast for this prepacked path.

The runtime patch accepts either the pristine pinned FlexGEMM source or the R6F3 partially patched source, validates the expected source shape, preserves a backup, compiles the patched Python source, and writes `FLEXGEMM_TRITON32_PATCH.json`.

## Invariants

Unchanged:
- `Ruicheng/moge-3-vitg`;
- High Fidelity `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 geometry and outputs;
- shared ComfyUI Python/Torch/CUDA;
- Gate 7 geometry/evidence thresholds.

Gate 8 remains source-only in parallel and is not present in the validation bundle.

## Acceptance

The R6F4 installer must pass the ViT-L CUDA/refiner smoke test and the ViT-G/Turing verifier on the RTX 2080 Ti before the production workflow is considered ready for another Gate 7 runtime attempt.
