# ConceptGhost v0.32 — Frozen Baseline

This branch freezes the pre-improvement v0.32 baseline.

## Complete installable bundle
Google Drive:
https://drive.google.com/file/d/1NhQ4Ui07MZ1Pmc6YUPMatogCrB50eSjf/view?usp=drivesdk

File:
`ConceptGhost_v0.32_COMPLETE.zip`

Bytes:
`11714746`

SHA-256:
`c89c542274d924d393dd529750ba3233aa4134a61b45dc2b17f335ec31298f3b`

## Local validation before freeze
- pytest: 64 PASS
- ZIP CRC: PASS
- bundle file/hash inventory: PASS
- pinned MoGe vendor present: 11,590,402 bytes
- MoGe vendor SHA-256: `b9a28e6a1aa86bd23399f995feb9d496a461405fe22b53b9878c21b48d46fe6d`
- no legacy v0.30/v0.31 filenames in the complete bundle
- no generated `__pycache__` / `.pytest_cache` directories in the complete bundle
- one current workflow: `ConceptGhost_Master_v0.32.json`

## Freeze scope
v0.32 includes the deduplicated-output architecture, fused-points preview, optional Light/Medium/Strong remesh branches, the complete pinned MoGe clean-machine source payload, and safe DA3 audit/removal tooling.

Fresh final Windows/ComfyUI/Maya acceptance is intentionally deferred until the remaining improvement gates are complete. This is a code/package freeze, not a claim that the deferred Maya gate has already been re-run.
