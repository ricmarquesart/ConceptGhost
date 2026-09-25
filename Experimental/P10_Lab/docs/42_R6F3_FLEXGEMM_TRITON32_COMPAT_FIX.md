# Gate 7 R6F3 — FlexGEMM / Triton 3.2 Compatibility Fix

Date: 2026-09-24 / 2026-09-25 UTC  
Status: SOURCE + PACKAGE CI PASS — RTX 2080 Ti TARGET-PC ACCEPTANCE PENDING

## Runtime evidence from R6F2

R6F2 correctly detected the old incompatible private runtime (Torch 2.14 + CUDA 13 + Triton Windows 3.8 on RTX 2080 Ti / sm75), rebuilt it as Torch 2.6.0 + CUDA 12.4 + Triton Windows 3.2.0.post21, and preserved the shared ComfyUI environment.

The next smoke test then failed inside MoGe-3's pinned FlexGEMM dependency:

`flex_gemm/kernels/triton/hashmap.py` used `keys_ptr.dtype.element_ty.itemsize`.

Triton 3.2 exposes `primitive_bitwidth` on its language dtype rather than the newer `itemsize` property. The failure was therefore a source/API compatibility mismatch between the pinned FlexGEMM commit used by MoGe-3 and the Turing-compatible Triton 3.2 runtime.

## R6F3 bounded repair

R6F3 keeps the Turing-safe private runtime matrix:

- Python 3.11.9 embedded
- PyTorch 2.6.0
- torchvision 0.21.0
- CUDA 12.4 wheels
- Triton Windows >=3.2,<3.3

It adds a ConceptGhost-owned, private-runtime-only compatibility bridge for the pinned FlexGEMM commit `b2fadb29d41846c7981ade6801ffc689fae119cf`.

The bridge rewrites only Triton compile-time dtype byte-width introspection in `flex_gemm/kernels/triton/hashmap.py`:

- `query_vec.dtype.itemsize` -> `query_vec.dtype.primitive_bitwidth // 8`
- `keys_ptr.dtype.element_ty.itemsize` -> `keys_ptr.dtype.element_ty.primitive_bitwidth // 8`
- `vec.dtype.itemsize` -> `vec.dtype.primitive_bitwidth // 8`

It validates expected source-shape counts, creates a private backup, writes `FLEXGEMM_TRITON32_PATCH.json`, and is idempotent.

## Cache isolation

The private installer now sets `TRITON_CACHE_DIR=<ConceptGhost-MoGeRuntime-v1>/cache/triton` and clears that private cache before the repaired smoke test so kernels compiled by a newer Triton version cannot be reused accidentally.

## Geometry authority unchanged

No geometry-quality parameter was lowered:

- High Fidelity model remains `Ruicheng/moge-3-vitg`
- `resolution_level=9`
- `refine_steps=7`
- P9 accepted outputs remain immutable
- no shared ComfyUI Python/Torch/CUDA mutation
- Gate 8 is not present in the runtime validation bundle

## CI/package evidence

- R6F3 workflow run: `36077852523` — SUCCESS
- General ConceptGhost Tests on the same source head: `36077852457` — SUCCESS
- Source snapshot: `36077852317` — SUCCESS
- Package SHA-256: `94a1a49e4c5641acd0a1fa680ab751c15801968389ae2f6c9fc58b11f80ef36c`
- Drive Evaluation_Builds file id: `11OFZbk-cM1Z1mOnYI5NQzqMkjlY4ppCp`

## Acceptance

The next target-PC test must run `03_INSTALL_ALL.bat` from R6F3, then `04_VERIFY_INSTALL.bat`. The installer must pass the Low Resolution ViT-L CUDA/refiner smoke and the ViT-G/Turing gate before the production workflow is rerun.

Gate 8 source work may continue in parallel under the user's explicit authorization, but Gate 8 promotion remains blocked until Gate 7 runtime/artist acceptance.
