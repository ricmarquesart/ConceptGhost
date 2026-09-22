# Gate 2 Preview r2 — Validation Evidence

## State

Gate 2 is **PREVIEW READY / USER RUNTIME CONFIRMATION PENDING**.
Gate 3 has not started.

## Preview artifact

- File: `ConceptGhost_v1.54_P10_Gate02_PREVIEW_r2.zip`
- SHA-256: `8a7e80afd95a7399ba1b6fe169901739255fca74ae38852c44f8862affa0fb47`
- Google Drive file id: `1MPd5eNLsTVQri7RDqStW9B2fdRgs-hT9`
- r1 is superseded for user testing; it remains an engineering checkpoint.

## Real v1.53 boundary proof

Validated source run:

`20260921T194812_539232Z_366c63df`

Observed production authority:

- branch mode: `Baseline / P9`
- Scene Contract: `cgsc_legacy_8f72c73ab923f5801558`
- authoritative PrimaryMesh: NPZ
- identity chain: PASS
- official core-output contract: PASS

Gate 2 successfully validated the run, created Completion Bundle v0.3, reloaded
it, rehashed its artifacts and preserved the source/camera/PrimaryMesh identity.

Real validation bundle:

- file: `ConceptGhost_v1.54_P10_Gate2_REAL_BASELINE_CompletionBundle.zip`
- SHA-256: `45b927fbcbc363ab0109fdc6089c454b8b1e5711a5b51c88667d36759e2ecc6b`
- Google Drive file id: `1bwtR_dteShynPihyt2ihPKimqIrfl_SH`

## TDD proof

RED tests were committed before implementation for:

- real official-run ingestion;
- P9/Baseline stage labeling;
- Scene Contract mismatch rejection;
- unsupported branch rejection;
- bundle-byte tamper rejection;
- Baseline-vs-P9 PrimaryMesh divergence;
- ZIP traversal rejection;
- ComfyUI preview nodes;
- visible ComfyUI UI diagnostics.

The implementation then made those tests GREEN.

## Automated validation

At the r1 checkpoint, GitHub Actions run `35681531094` passed on:

- Windows / Python 3.12;
- Windows / Python 3.14;
- Ubuntu / Python 3.12.

That run recorded:

- repository suite: 111/111 PASS;
- P10 laboratory suite: 33/33 PASS.

The r2 code additionally passed focused local preview tests and an installable
package smoke test against the real v1.53 run. The final r2 branch-head Actions
run is recorded in `docs/08_GATE_STATUS.md` after completion.

## Remaining closure evidence

The gate remains open until the Preview Version is confirmed in the user's
actual ComfyUI Desktop/runtime. A current matched v1.53 Refined/P9 runtime pair
may also be used to produce direct runtime identity evidence; the comparator is
already implemented and tested.

No Gate 3 implementation is authorized before Gate 2 is reported and approved.
