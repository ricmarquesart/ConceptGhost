# ConceptGhost Gate 7 R6F13 — v0.36 Runtime Compatibility + Run-Local Audit

Date: 2026-09-25

## Purpose

R6F13 preserves the latest R6F12 P9/P10 graph, Route Editor, Gate 7 implementation and the restored v0.36 fixed-depth PrimaryMesh topology policy, while changing only the private MoGe execution lane and audit ZIP placement.

The runtime experiment is intentionally in-place: it uses the existing stable ConceptGhost-owned MoGe runtime root `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`. It must not create a second versioned MoGe runtime.

## v0.36 compatibility lane

Archived pre-R6F2 environment evidence is reproduced in the stable runtime:

- Python 3.11.9
- PyTorch 2.14.0+cu130
- torchvision 0.29.0+cu130
- triton-windows 3.8.0.post28
- MoGe 3.0.0
- FlexGEMM commit `b2fadb29d41846c7981ade6801ffc689fae119cf`
- MoGe source SHA-256 `b9a28e6a1aa86bd23399f995feb9d496a461405fe22b53b9878c21b48d46fe6d`

The compatibility worker keeps current heartbeat/diagnostic transport but removes the later R6F2 hard requirement that Turing must use Torch 2.6.x + Triton 3.2.x. The current P9 request and R6F12-restored v0.36 fixed PrimaryMesh depth-edge rule remain unchanged.

This is an experimental target-PC runtime test. Static validation does not prove that the archived dependency matrix will execute successfully on the target RTX 2080 Ti.

## One runtime only

The installer switches the existing private runtime in place and preserves its model/cache root. Before the switch it stores the previous pip freeze, worker payload and readiness manifests under `%LOCALAPPDATA%\ConceptGhost\backups`.

`07_RESTORE_R6F12_TURING_RUNTIME.bat` restores the R6F12 Torch 2.6/cu124 + Triton 3.2 compatibility matrix in the same stable runtime root.

## RUN_AUDIT_BUNDLE storage correction

The Master node supplies `output_root` and `scene_name`, and the P9 export produces the dynamically-created `run_dir`. R6F13 treats that resolved P9 `run_dir` as the audit storage authority.

The bundle becomes:

`<output_root>\<scene_name>\<run_id>\RUN_AUDIT_BUNDLE.zip`

Its manifest and latest-audit pointer files sit beside it in the same run folder. There is no hard-coded project path and no extra `P10_AUDIT\<attempt>` nesting for the bundle itself. Immutable P10 attempt evidence remains in the existing P10 attempt tree and is collected into the run-local ZIP.

## Acceptance

Gate 8 remains blocked until the target PC installs/verifies R6F13 and the same source image is rerun with High Fidelity Split Clean so the P9 PrimaryMesh can be compared with the degraded current result.
