# Gate 7 R6F10 — Triton 3.2 reduce_or Compatibility Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F9

R6F9 successfully passed the private annotation sanitizer and advanced farther through the real ViT-L CUDA/refiner smoke test.

The next failure occurred inside:

`flex_gemm/kernels/triton/neighbor_cache/post_process.py`

at:

`tl.reduce_or(gray_code, axis=0)`

The installed Triton Windows 3.2 runtime does not expose `triton.language.reduce_or`, so the sparse-refiner path stopped with:

`AttributeError: module 'triton.language' has no attribute 'reduce_or'`

## Compatibility bridge

Triton 3.2 does provide the generic reduction primitive `tl.reduce` with a JIT combine function. R6F10 therefore adds a private helper:

`@triton.jit`
`def _conceptghost_or_combine(a, b): return a | b`

and replaces the unsupported call with:

`tl.reduce(gray_code, axis=0, combine_fn=_conceptghost_or_combine)`

This preserves the intended bitwise-OR reduction exactly; it is not replaced by sum/max or another approximate operation.

## Retained compatibility fixes

R6F10 also keeps all previously validated private-runtime bridges:
- Turing-safe Torch 2.6.0 + cu124 + Triton Windows 3.2.x;
- FlexGEMM hashmap int32 packing bridge;
- non-constexpr Triton annotation sanitizer;
- isolated Triton cache;
- runtime capability telemetry.

## Deterministic validation

The patcher self-test now validates:
- annotation sanitizer;
- LF/CRLF hashmap compatibility;
- reduce_or replacement;
- helper insertion;
- idempotence.

## Invariants

Unchanged:
- `Ruicheng/moge-3-vitg`;
- High Fidelity `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 outputs;
- shared ComfyUI Python/Torch/CUDA;
- Gate 7 geometric-evidence thresholds.

Gate 8 remains source-only and absent from the target-PC validation bundle.
