# Gate 7 R6F8 — Triton 3.2 Pointer Annotation Compatibility Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F7

R6F7 succeeded in applying the private FlexGEMM token patch and advanced into the real Low Resolution ViT-L CUDA/refiner smoke test. This is the first package in the R6F2–R6F7 sequence that passed the compatibility-patcher stage.

The smoke test then failed during Triton JIT signature compilation with:

`KeyError: 'ier_type'`

The failing FlexGEMM kernel explicitly annotates runtime pointer arguments with `tl.pointer_type`. Triton 3.2 has a known signature-parser incompatibility with explicit `tl.pointer_type` parameter annotations; the public Triton issue for the same traceback reports that removing those annotations fixes the problem.

## R6F8 correction

R6F8 preserves the successful R6F7 hashmap token bridge and additionally scans only the ConceptGhost-private FlexGEMM Triton kernel tree:

`flex_gemm/kernels/triton/**/*.py`

It removes:
- `: tl.pointer_type`
- `: tl.pointer_type | None`

It deliberately preserves:
- `: tl.constexpr`
- model code;
- model weights;
- geometry settings;
- shared ComfyUI runtime.

Triton infers the runtime pointer type from the actual tensor arguments. The explicit annotation is unnecessary for execution and is the source of the Triton 3.2 parser failure.

## Deterministic validation

The private patcher self-test now proves:
- plain pointer annotations are removed;
- optional pointer annotations are removed;
- `tl.constexpr` survives untouched;
- reapplying the patch is idempotent;
- the R6F7 hashmap token bridge still works with LF and CRLF fixtures.

The target patcher also compiles every modified Python module and refuses PASS if any `: tl.pointer_type` annotation remains.

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

Gate 8 remains source-only and is not included in this target-PC validation bundle.
