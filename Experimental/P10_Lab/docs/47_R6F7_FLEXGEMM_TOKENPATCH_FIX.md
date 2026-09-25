# Gate 7 R6F7 — FlexGEMM Token-Patch Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F6

R6F6 again stopped before MoGe smoke inference. The target runtime remained healthy:
- RTX 2080 Ti / Turing sm75;
- private Python 3.11;
- PyTorch 2.6.0 + cu124;
- torchvision 0.21.0;
- Triton Windows 3.2.0.post21;
- shared ComfyUI environment unchanged.

The private compatibility script still exited with code 4. The line-regex strategy was therefore still too brittle for the installed FlexGEMM source shape on the target PC.

## R6F7 correction

R6F7 removes line matching entirely.

The bridge now patches only semantic tokens in the private FlexGEMM `hashmap.py`:
- `keys_ptr.dtype.element_ty.itemsize` or the prior `primitive_bitwidth` equivalent -> literal width `4`;
- `query_vec.dtype.itemsize` or the prior `primitive_bitwidth` equivalent -> literal width `4`;
- active lookup call `_vec_pack_little_endian_to_int32(query_vec)` -> `query_vec.to(tl.int32)`;
- resulting active `D * 4 // 4` expressions normalize to `D`.

This is independent of LF vs CRLF, indentation and surrounding source formatting.

## New deterministic self-test

The runtime patcher now supports `--self-test` and CI executes it before release against four fixtures:
- pristine FlexGEMM / LF;
- pristine FlexGEMM / CRLF;
- prior R6F3 primitive-bitwidth form / LF;
- prior R6F3 primitive-bitwidth form / CRLF.

The self-test also reapplies the patch and requires idempotence.

If target-PC patching still fails, the report now includes a `source_probe` with exact token counts so the next diagnosis is based on the target file rather than another inferred source shape.

## Invariants

No quality or authority changes:
- `Ruicheng/moge-3-vitg`;
- High Fidelity `resolution_level=9`;
- `refine_steps=7`;
- accepted P9 outputs remain immutable;
- shared ComfyUI Python/Torch/CUDA remains read-only;
- Gate 7 geometric evidence thresholds remain unchanged;
- Gate 8 remains source-only and absent from this validation package.
