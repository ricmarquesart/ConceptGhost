# Gate 7 R6F2 — MoGe-3 Turing Runtime Compatibility Fix

Date: 2026-09-24  
Status: SOURCE FIX IMPLEMENTED — TARGET-PC ACCEPTANCE PENDING

## Runtime evidence

The R6F target-PC run failed before Gate 7. `ConceptGhostMoGe3Inference` loaded `Ruicheng/moge-3-vitg`, prepared the 1448x1086 source image, entered `INFERENCE_START` with `resolution_level=9` and `refine_steps=7`, then remained there until the 1500-second worker hard timeout terminated the process.

This is a P9 / Stage68 MoGe runtime failure, not a Gate 7 COLMAP/fusion failure.

## Root compatibility finding

The ConceptGhost private MoGe installer previously installed current `torch>=2.4` / `torchvision>=0.19` and allowed FlexGEMM's `triton-windows>=3.2.0` dependency to resolve without an upper bound.

The project target GPU is RTX 2080 Ti / Turing sm75. Triton Windows supports Turing only through the 3.2 minor. R6F2 therefore freezes the ConceptGhost-owned private runtime to:

- Python 3.11.9 embedded;
- PyTorch 2.6.0;
- torchvision 0.21.0;
- CUDA 12.4 PyTorch wheels;
- Triton Windows >=3.2,<3.3.

The shared ComfyUI Python/Torch/CUDA environment remains untouched.

## Geometry authority is unchanged

R6F2 does **not** lower the High Fidelity geometry settings:

- model remains `Ruicheng/moge-3-vitg`;
- `resolution_level` remains 9;
- `refine_steps` remains 7;
- FP16/mixed precision, force projection, mask application and Split Clean behavior remain unchanged.

Existing accepted P9 outputs are never rewritten by this runtime repair.

## Fail-fast and diagnostics

The MoGe worker now emits `RUNTIME_CAPABILITY` before model loading, including GPU, compute capability, Torch version, CUDA runtime and Triton version.

On Turing/sm75, an incompatible Torch/Triton matrix fails immediately with a repair instruction instead of spending 1500 seconds in `INFERENCE_START`.

The ViT-G verifier records compute capability and runtime versions and rejects an incompatible Turing matrix before the package is considered healthy. The full installer runs the ViT-G compatibility gate after private-runtime repair.

## Acceptance

Source/package validation must prove the R6 route-editor and Gate 7 repair contracts remain intact, the P9 High Fidelity model/resolution/refinement contract is unchanged, the private runtime is frozen to the Turing-safe matrix, the shared ComfyUI environment stays protected, and package manifests/checksums remain valid.

Real RTX 2080 Ti runtime acceptance remains required. Gate 8 may continue source-only in parallel, but promotion remains dependent on Gate 7/R6F2 runtime acceptance.
