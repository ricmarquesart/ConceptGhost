# Gate 7 R6F9 — Triton 3.2 Annotation Sanitizer Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F8

R6F8 successfully removed explicit `tl.pointer_type` annotations and reached farther into the real ViT-L CUDA/refiner smoke test. The next failure occurred while Triton 3.2 parsed the inline helper:

`coord_stride_vec: tl.tensor | None`

The compiler raised a JIT-builder error before completing the sparse-refiner kernel compilation.

## Root cause

The pinned FlexGEMM source targets a newer Triton annotation surface. Triton 3.2 can infer runtime tensor/pointer argument types from actual JIT values, but walking explicit non-constexpr Triton-language annotations such as:

- `tl.pointer_type`
- `tl.tensor`
- `tl.const`
- optional unions using those types
- return annotations containing those types

can fail during AST/JIT parsing.

`tl.constexpr` is different: it controls compile-time specialization and must remain.

## R6F9 correction

R6F9 preserves the successful hashmap compatibility work and sanitizes only the ConceptGhost-private FlexGEMM Triton kernel tree:

`flex_gemm/kernels/triton/**/*.py`

It removes non-constexpr Triton-language parameter/return annotations:
- `: tl.pointer_type`
- `: tl.pointer_type | None`
- `: tl.tensor`
- `: tl.tensor | None`
- `: tl.const`
- `: tl.const | None`
- Triton-language return annotations including tuple returns

It explicitly preserves every `: tl.constexpr` occurrence.

## Deterministic validation

The private patcher self-test proves:
- pointer/tensor/const annotations are removed;
- optional variants are removed;
- Triton-language return annotations are removed;
- `tl.constexpr` count is unchanged;
- patching is idempotent;
- R6F7 hashmap token compatibility still passes LF and CRLF fixtures.

Every modified private FlexGEMM Python module is syntax-compiled before the patch reports PASS.

## Invariants

Unchanged:
- Python 3.11.9 private runtime;
- PyTorch 2.6.0 + cu124;
- torchvision 0.21.0;
- Triton Windows 3.2.x;
- `Ruicheng/moge-3-vitg`;
- High Fidelity `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 outputs;
- shared ComfyUI Python/Torch/CUDA;
- Gate 7 geometric-evidence thresholds.

Gate 8 remains source-only and absent from the target-PC validation bundle.
