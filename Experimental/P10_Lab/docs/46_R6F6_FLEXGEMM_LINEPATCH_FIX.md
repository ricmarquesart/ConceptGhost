# Gate 7 R6F6 — FlexGEMM Line-Based Patch Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F5

R6F5 reached the ConceptGhost-private FlexGEMM compatibility script but the patcher exited with code 4 before the MoGe smoke test.

The runtime itself remained correct:
- RTX 2080 Ti / Turing sm75;
- Python 3.11 private runtime;
- PyTorch 2.6.0 + cu124;
- torchvision 0.21.0;
- Triton Windows 3.2.0.post21;
- shared ComfyUI environment untouched.

The R6F5 failure was in the ConceptGhost patcher's own source matching. Its generated matcher encoded multi-line source fragments with escaped "\\n" sequences and compared those literal characters against real newlines in `hashmap.py`. The expected callsites were therefore not found and the patcher failed closed with exit code 4.

## R6F6 correction

R6F6 removes all brittle multi-line source matching.

The compatibility bridge now edits only individual active FlexGEMM source lines using anchored regular expressions and validates exact occurrence counts:

- two build/unique byte-width assertions are replaced by an explanatory no-op comment;
- two build/unique `D_32` expressions become `D_32 = D`;
- the active lookup converts `query_vec` directly to `tl.int32`;
- the lookup `D_32` expression becomes `D_32 = D`.

Both pristine `dtype.itemsize` callsites and the earlier R6F3 `primitive_bitwidth` callsites are accepted.

The generic helper function may remain in the FlexGEMM file, but the active hashmap lookup no longer calls it.

## Why D_32 = D is valid here

The pinned FlexGEMM Python host wrappers already:
1. flatten key/query data;
2. byte-pad to a power-of-two 32-bit width;
3. view keys/queries as `torch.int32`;
4. pass `D_32` to Triton as kernel argument `D`.

R6F6 consumes that existing host contract instead of rediscovering dtype width inside Triton 3.2 JIT.

## Invariants

No quality or authority changes:
- `Ruicheng/moge-3-vitg`;
- High Fidelity `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 outputs remain immutable;
- shared ComfyUI Python/Torch/CUDA remains read-only;
- Gate 7 geometric evidence thresholds remain unchanged;
- Gate 8 remains source-only and absent from this validation package.

## Acceptance

The R6F6 installer must first show the FlexGEMM compatibility report as PASS, then pass the CUDA/refiner smoke test and the ViT-G/Turing verification on the RTX 2080 Ti.
