# ConceptGhost v0.31.2 RC5 — Runtime acceptance procedure

## Before running
1. Run `INSTALL_CONCEPTGHOST.bat`.
2. Run `VERIFY_CONCEPTGHOST.bat`.
3. Fully close and restart ComfyUI Desktop.
4. Close any restored older ConceptGhost tab.
5. Explicitly open `ConceptGhost_Master_v0.31.2_DEDUP_REMESH.json`.

## Run A — Remesh OFF
- Geometry profile: `High Fidelity`.
- `Generate Remesh Variants = OFF`.
- Execute to completion.
- Run `VERIFY_V0312_RUNTIME_OUTPUT.bat -RemeshMode OFF`.
- Expected: PrimaryMesh Master + fused-points output; no Light/Medium/Strong files; no COMPLETE.zip.

## Run B — Remesh ON
- In the same v0.31.2 workflow set `Generate Remesh Variants = ON`.
- Execute to completion; this must create a new run folder.
- Run `VERIFY_V0312_RUNTIME_OUTPUT.bat -RemeshMode ON`.
- Expected: Master + Light + Medium + Strong as separate outputs.

## Acceptance
The verifier requires all Maya/normal gates PASS, `CG_FUSED_POINTS` observed after `.ma` reopen, one canonical USDA only, source texture reuse, no persistent `.fbm`, exact FBX alias payload, no `*_COMPLETE.zip`, and the requested remesh state.

Do not execute DA3 removal during Gate 10. DA3 cleanup remains a separate audited Gate 11 action.

RC5 source SHA-256: `9d7dc41e4a8bcc58b664943dac7edf9c5d9ccdbcfe546d56639a7934c7e2b670`.
Local regression suite: **64 PASS**.
