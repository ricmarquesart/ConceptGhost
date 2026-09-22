# P10-Lab Gate Status

This is the persistent execution board for ConceptGhost v1.54 P10. It maps the
16 ordered implementation items in `01_MASTER_IMPLEMENTATION_PLAN.md` to ten
development gates. A gate is complete only when its acceptance evidence is
recorded and its checkpoint is mirrored to GitHub and Google Drive.

## Authoritative reconciliation — 2026-09-22 r8 runtime + free-space update

This is the newest authoritative status. Older reconciliation/current-summary sections below are retained only as historical checkpoints.

- Current active boundary remains **Gate 6.6 — integrated reconstruction preview/runtime validation**.
- Gates 1–4 are functionally completed for the first end-to-end pass.
- Gate 5.1–5.4 are completed; Gate 5.5 runtime evidence is exercised through the integrated Gate 6 preview.
- Gate 6.1–6.5 have completed first-pass implementations; Gate 6.6 remains OPEN because real runtime acceptance has not yet passed end-to-end.
- The latest r8 runtime progressed through P9, WAN generation and into Gate 6 reconstruction, then failed in Gate 6.3 with a real camera calibration mismatch between the pre-WAN Gate 4 camera viewport and the saved Gate 5 WAN composite viewport.
- The correction maps fx/fy/cx/cy through the exact ComfyUI center-crop + resize transform, versions the reconstruction dataset as v0.2 with source digests, invalidates stale datasets, and rebuilds the Gate-6-owned COLMAP database on sparse retry.
- This runtime correction is separate from the new Free-Space design.
- Free-Space / Visibility Carving is now an authoritative **planned Gate 7.3 feature generated from Gate 6 evidence**. Gate 6.4 is the producer/retention point for geometric depth, normals and consistency graphs; Gate 6.5 gains a Poisson + Delaunay dual-mesh producer extension when Gate 7 work begins.
- Gate 7.2C uses CONFIRMED_FREE/UNKNOWN/CONFLICT as confidence evidence; Gate 7.3 enforces CONFIRMED_FREE as no-fill/no-bridge; Gate 8 distinguishes VALID_OPENING, MISSING_SURFACE_UNKNOWN, FALSE_SURFACE_IN_CONFIRMED_FREE and CONFLICT_REGION.
- Free-space uses a sparse/chunked visibility field with route/view independence rather than a giant dense world grid. Adjacent frames from one route are correlated; initial CONFIRMED_FREE policy requires multiple useful views, at least two independent route/view groups and useful angular diversity.
- `UNKNOWN != FREE`; no observation is never treated as proof of empty space.
- Dedicated ComfyUI `P10 · Free-Space 3D Preview` remains diagnostic-only and is planned under Gate 12 standardization.
- Gate 7 required implementation does not begin until the corrected Gate 6 runtime preview is accepted, although its design documents are already authoritative.

## Authoritative reconciliation — 2026-09-22 r7

This section supersedes the stale Gate 2 summary below. Historical Gate 2 details are intentionally retained for audit.

- Current active development boundary: **Gate 6.6 — integrated reconstruction preview/runtime validation**.
- Gates 1–4: **FUNCTIONALLY COMPLETED** for first end-to-end development.
- Gate 5: **5.1–5.4 COMPLETED; 5.5 runtime acceptance is exercised through the integrated Gate 6 preview**.
- Gate 6: **6.1–6.5 COMPLETED; 6.6 PREVIEW READY / USER RUNTIME PENDING**.
- Gate 7: next required development gate after Gate 6 runtime acceptance.
- Gates 11–12 remain deferred until the first complete Gates 4–10 end-to-end result, except their cross-cutting policies already recorded.
- Required roadmap size: **66 bounded subgates**, plus optional non-blocking Gate **7.2C** geometry-confidence refinement.
- Current Gate 7.2C policy: confidence analysis **ON**, dedicated ComfyUI 3D confidence preview **ON/available**, geometry refinement **OFF** by default; confidence visualization is diagnostic-only and must not alter Maya deliverables.
- Current Gate 11 final-quality defaults: **7 geometry-adaptive routes × 30 configurable frames**, HiRes Composite **ON**, HiRes Views **ON**, **4K default** with 6K/8K presets.
- Current release test artifact: `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r7.zip`.
- r7 supersedes r6 and fixes the real WAN VAE decode/Pillow shape failure by normalizing 5D decoded video to a 4D IMAGE batch before frame accounting, composite and save.
- r7 implementation commit: `a5c9383990f5e3f4ad55f7ec1b2474be2a505a3a`.
- r7 regression commit: `87c56a0644cb1983882264062268596d7e0f97c4`.
- GitHub Actions for the r7 regression head: run `35771754630` — SUCCESS.
- Current branch head after confidence-policy documentation: `81d2716285d0719fb4496b2a29c2fc43583e6ced`; Actions run `35772121481` — SUCCESS.
- r7 ZIP: **12,102,618 bytes**, SHA-256 `c921fd235ca54b61ab807cf6e94764073b7a818b8079f7c537331c9723f8325c`.
- Evaluation_Builds Drive ZIP ID: `18VJ3Kn5LU1wPJ4dJsF_DZvxIHVutEBE5`.
- P10 recovery mirror ZIP ID: `1VMxkp9ohh4tLe9-6j5TmsHGeDQBpalx-`.
- Expanded Evaluation_Builds r7 folder ID: `1RYy_gkp83lcIFHHGgwG00t1DpEPXf4PU`; verified complete at **155 files** with the expected `Installer`, `Payload` and `Runtime` structure.


## Current summary

- Current gate: **Gate 2 — Completion Bundle and P9 identity boundary**
- State: **PREVIEW READY / USER RUNTIME CONFIRMATION PENDING**
- Completed gates: **1 / 10**
- Gate currently in progress: **2 / 10**
- Gates remaining after the current gate: **8**
- Gate 3: **BLOCKED / NOT STARTED until Gate 2 is reported and approved**
- Current branch: `work/v1.54-p10-multiview-completion`
- Latest cross-platform verified Gate 2 head: `6280fe844f5d822ebfee95ac627548db88e089c1`
- GitHub Actions proof: run `35682140166` — SUCCESS on Windows/Python 3.12,
  Windows/Python 3.14 and Ubuntu/Python 3.12
- Baseline rule: the standalone Baseline remains unchanged
- Current Preview Version: **Gate 2 Preview r2**
- Preview r1: **SUPERSEDED FOR USER TESTING / retained as engineering checkpoint**

## Gate board

| Gate | State | Scope | Completion evidence |
|---|---|---|---|
| 1. Foundation contracts and visible checkpoints | **COMPLETED** | Raw-hole policy; configurable 3+1 flight plan; reusable flight data; control/mask/WAN/composite checkpoint contract; digest-safe resume; safety validation | 22/22 P10 tests at closure; 111/111 repository tests; GitHub Actions success on three matrix jobs; GitHub and Drive mirrors |
| 2. Completion Bundle and P9 identity boundary | **PREVIEW READY / USER CONFIRMATION PENDING** | Real Completion Bundle; loader/validator; Baseline-equivalent P9 adapter; identity regression; first ComfyUI preview | v0.3 contract; real v1.53 Baseline run PASS; SHA/tamper/stale/path-traversal rejection; Baseline-vs-P9 comparator; visible ComfyUI diagnostics; 33/33 P10 tests and 111/111 repository tests in CI; Preview r2 on Drive |
| 3. Temporary panorama and completion envelope | **BLOCKED / NOT STARTED** | Perspective-to-ERP placement; lock original pixels; panorama preview; bounded local exploration envelope | Starts only after Gate 2 closure/approval |
| 4. Automatic paths, collision, raw controls and masks | **PLANNED** | Scene-relative paths; collision adaptation; raw-hole control renderer; disocclusion masks; per-flight previews | Left/right/forward-elevated paths execute safely and expose unsupported regions without compensation |
| 5. WAN completion and source-preserving composite | **PLANNED** | Quantized masked WAN; sequential 11 GB execution; generated preview; high-resolution source composite | Missing regions are generated while observed source/P9 pixels remain locked |
| 6. SphereSfM and COLMAP reconstruction | **PLANNED** | Generated-view collection; SphereSfM; sparse reconstruction; dense stereo/fusion; triangle mesh | Cameras, sparse cloud, dense cloud and pre-fusion mesh pass reconstruction health checks |
| 7. Registration, fusion and provenance | **PLANNED** | Register P10 reconstruction to P9 coordinates; known/generated fusion; transition handling; provenance | Observed geometry wins; generated geometry fills unknown regions; origin remains selectable/auditable |
| 8. Geometry cleanup and texture recovery | **PLANNED** | Local remesh; defect cleanup; UV/texture recovery; texel provenance | Healthy editable mesh with source-preserving texture coverage and bounded repairs |
| 9. Original-view regression and Maya export | **PLANNED** | Canonical-camera regression; rejection thresholds; editable `.ma`; diagnostic groups/sets | Original view remains within tolerance and Maya scene contains camera, mesh, materials and provenance |
| 10. Adaptive quality, hardware compliance and Refined integration | **PLANNED** | Spend adaptive flights only on useful defects; restart/cache cleanup; RTX 2080 Ti 11 GB compliance; Refined = P9 + P10; release validation | One queued run reaches validated Maya output without manual handoff; Baseline remains untouched |

## Gate 2 implementation checkpoint

Gate 2 is implemented against the real ConceptGhost v1.53 official run-pack
shape rather than against invented P10-only filenames.

The current source authority is:

- `source/source.png`;
- `camera/camera.json`;
- one official `maya/ConceptGhost_*_PrimaryMesh.npz`;
- `maya/primary_mesh_payload.json`;
- `manifest.json`;
- `output_index.json`;
- `package/official_outputs_contract.json`.

The authoritative P9/Baseline PrimaryMesh remains NPZ at this boundary. P10
does not require P9 to replace it with OBJ/PLY merely for the laboratory.

Completion Bundle v0.3 records source stage, Baseline equivalence, branch mode,
Scene Contract identity, source manifest schema and SHA-256 for every packaged
required/optional artifact. The loader rehashes the bytes and fails closed on
stale or modified data.

`p10_lab/p9_boundary.py` now provides:

- official-run validation;
- Completion Bundle creation;
- Completion Bundle safe loading/extraction;
- Baseline-vs-Refined/P9 runtime identity comparison.

`p10_lab/preview_nodes.py` now exposes:

- `P10 P9 Completion Bundle Builder`;
- `P10 P9 Bundle Loader / Validator`.

Both Preview r2 nodes publish their diagnostic JSON in ComfyUI's visible UI
response while keeping machine-readable STRING outputs.

## Gate 2 TDD / automated evidence

The Gate 2 tests were introduced RED before the implementation. They cover:

- real official-run shape ingestion;
- Baseline/P9 stage labeling;
- Scene Contract identity mismatch rejection;
- unsupported branch rejection;
- byte/hash tamper rejection;
- Baseline-vs-P9 PrimaryMesh divergence;
- ZIP traversal rejection;
- ComfyUI node registration;
- visible ComfyUI diagnostic output.

Cross-platform GitHub Actions run `35682140166` passed every P10 and repository
step on the three supported matrix jobs. The preceding full log recorded
111/111 repository tests and 33/33 P10 laboratory tests; the r2 UI change kept
the P10 suite green on all three platforms.

## Gate 2 real-run evidence

Validated real v1.53 run:

`20260921T194812_539232Z_366c63df`

Observed authority:

- branch mode: `Baseline / P9`;
- Scene Contract: `cgsc_legacy_8f72c73ab923f5801558`;
- identity chain: PASS;
- official core-output contract: PASS;
- authoritative PrimaryMesh: NPZ.

The Gate 2 adapter validated the run, created Completion Bundle v0.3, reopened
it, rehashed its files and preserved the source/camera/PrimaryMesh identity.

Real validation bundle:

- `ConceptGhost_v1.54_P10_Gate2_REAL_BASELINE_CompletionBundle.zip`
- SHA-256: `45b927fbcbc363ab0109fdc6089c454b8b1e5711a5b51c88667d36759e2ecc6b`
- Google Drive file id: `1bwtR_dteShynPihyt2ihPKimqIrfl_SH`

## Gate 2 Preview r2 publication evidence

- Preview: `ConceptGhost_v1.54_P10_Gate02_PREVIEW_r2.zip`
- SHA-256: `8a7e80afd95a7399ba1b6fe169901739255fca74ae38852c44f8862affa0fb47`
- Google Drive file id: `1MPd5eNLsTVQri7RDqStW9B2fdRgs-hT9`
- Preview source/workflow/instructions/validation evidence are mirrored in
  `Experimental/P10_Lab/previews/Gate02/`.
- r2 package smoke test imported the package as a custom node, registered both
  nodes, and executed Builder + Loader against the real v1.53 run with visible
  `PASS` diagnostics.
- r1 remains on Drive as a recovery checkpoint but is superseded for user testing.

## Gate 2 closure checklist

- [x] Completion Bundle v0.3 contract implemented.
- [x] Real v1.53 official-run adapter implemented.
- [x] Current authoritative PrimaryMesh NPZ supported directly.
- [x] Manifest/camera/PrimaryMesh Scene Contract identity enforced.
- [x] Required and optional bundle bytes SHA-256 validated.
- [x] Mixed/stale/tampered bundle data fails closed.
- [x] Safe ZIP extraction rejects traversal/non-portable/symlink entries.
- [x] Baseline-vs-Refined/P9 identity comparator implemented and regression-tested.
- [x] Gate 2 ComfyUI Preview nodes implemented.
- [x] Preview r2 publishes visible diagnostics in the ComfyUI node UI.
- [x] Real v1.53 Baseline run validated and converted/reloaded successfully.
- [x] GitHub Actions matrix is green.
- [x] GitHub and Google Drive mirrors exist.
- [ ] Preview r2 confirmed in the user's actual ComfyUI Desktop/runtime.
- [ ] If a current matched `Refined / P9 Clone` run is available, record direct
      runtime identity evidence with the comparator; a successful user test
      using that matched run can satisfy this item.

Until the pending runtime evidence is recorded, Gate 2 is not marked COMPLETED
and Gate 3 must not start.

## Gate 1 closure record

Gate 1 established raw-hole policy, scalable flight configuration, visible
checkpoint contracts and digest-safe resume. The final review also hardened
checkpoint filesystem handling against linked-directory and malformed-path
cases. The Gate 1 recovery bundle remains mirrored in Google Drive.

Deferred Gate 1 Minor findings remain:

- extremely large integer scale inputs can surface `OverflowError` instead of
  `ContractError`;
- full per-flight enforcement belongs to the later executable flight-runner gate.

## Update rule

Every progress report must state:

1. current gate and state;
2. completed work in that gate;
3. remaining closure items;
4. gates completed out of ten;
5. gates remaining after the current gate;
6. latest verified commit and mirror state.

No implementation work begins on the next gate until the current gate is
reported complete and the user explicitly approves continuation.

## Preview Version rule

When a gate or completed sub-stage becomes meaningfully executable or visible,
deliver `ConceptGhost_v1.54_P10_GateXX_PREVIEW_rN.zip` before advancing. The
package must include the relevant workflow and nodes, installation/update
instructions, `README_TEST_PREVIEW.md`, expected node outputs, known
limitations, validation evidence, and SHA-256.

Gate 1 contained only contracts and checkpoint infrastructure, so it had no
honest node-level visual preview. Gate 2 Preview r2 is the first user-facing
preview and exposes the Completion Bundle boundary with visible validation
diagnostics.
