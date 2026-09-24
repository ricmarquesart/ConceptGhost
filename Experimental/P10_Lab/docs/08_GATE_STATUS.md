# P10-Lab Gate Status

## Authoritative reconciliation — 2026-09-24 Gate 7.4 source checkpoint

- DR9R r15 remains under user runtime UX testing; Gate 7 source work remains isolated from that published runtime.
- **G7.1 registration authority: COMPLETE / CI PASS.**
- **G7.2 authority-aware provenance: COMPLETE / CI PASS.**
- **G7.2C geometry confidence: COMPLETE / CI PASS.**
- **G7.3 free-space / visibility no-fill authority: COMPLETE / CI PASS.**
- **G7.4 protected fusion candidate: COMPLETE / CI PASS at source level.**
- G7.4 is additive only: all P9 faces are retained unchanged and no P9 vertices are moved.
- P10 faces are admitted only with `P10_MULTIVIEW_SUPPORTED` provenance, sufficient confidence and bounded support distance.
- `CONFIRMED_FREE` and free-space `CONFLICT` veto P10 face admission; protected P9 source overlap also vetoes P10 admission.
- When Delaunay evidence is available, local Delaunay agreement is additionally required.
- Every P10 input face receives an explicit accept/reject provenance reason.
- The fused PLY is a disposable Gate 7 candidate, **not official geometry**.
- Destructive cleanup/remesh remains Gate 8 work.
- Focused G7.4 run `35954991624`: SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.
- General regression run `35954991620`: SUCCESS across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.
- Source snapshot run `35954991565`: SUCCESS.
- Formal closeout: `Experimental/P10_Lab/docs/30_GATE7_4_PROTECTED_FUSION_SOURCE_CLOSEOUT.md`.
- Next bounded source work: **G7.5 — Registration / Provenance Visual Review**.
- User-facing Gate 7 promotion remains blocked until the current DR9R r15 runtime UX acceptance is reviewed.

## Authoritative reconciliation — 2026-09-24 Gate 7.3 source checkpoint

- DR9R r15 remains under user runtime UX testing; Gate 7 source work remains isolated from the published runtime.
- **G7.1 registration authority: COMPLETE / CI PASS.**
- **G7.2 authority-aware provenance: COMPLETE / CI PASS.**
- **G7.2C geometry confidence: COMPLETE / CI PASS.**
- **G7.3 free-space / visibility no-fill authority: COMPLETE / CI PASS at source level.**
- G7.3 consumes the existing Gate 6 geometric depth maps and consistency graphs; camera/depth calibration mismatch fails closed.
- Sparse visibility evidence records camera-to-first-surface FREE votes and first-surface OCCUPIED votes; space behind the first surface stays UNKNOWN.
- `CONFIRMED_FREE` requires >=3 effective views, >=2 authored routes, angular diversity and a strong free-vote ratio.
- `CONFIRMED_FREE` is a future `NO_FILL / NO_BRIDGE` constraint; `UNKNOWN` is never treated as FREE.
- P9 source-protected evidence is forced OCCUPIED and cannot be carved by generated P10 evidence.
- COLMAP Delaunay meshing is now available as a separate visibility-aware structural candidate beside Poisson; no automatic winner is selected.
- Free-space is coupled back into confidence diagnostics: CONFIRMED_FREE/CONFLICT lower P10 confidence; UNKNOWN has no penalty; P9 confidence is unchanged.
- Official geometry changed: **NO**. Destructive fusion enabled: **NO**.
- General CI run `35953822364`: SUCCESS.
- Focused Gate 7.3 runtime-format/free-space run `35953822402`: SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.
- Source snapshot run `35953822367`: SUCCESS.
- Formal closeout: `Experimental/P10_Lab/docs/29_GATE7_3_FREE_SPACE_SOURCE_CLOSEOUT.md`.
- Next bounded source work: **G7.4 — Protected Fusion Candidate**.
- User-facing Gate 7 promotion remains blocked until the current DR9R r15 runtime UX acceptance is reviewed.

## Authoritative reconciliation — 2026-09-24 Gate 7.2C source checkpoint

- DR9R r15 remains under user runtime UX testing; current Gate 7 source development is isolated from that published runtime.
- **Gate 7.1 registration authority: COMPLETE / CI PASS.**
- **Gate 7.2 authority-aware provenance: COMPLETE / CI PASS.**
- **Gate 7.2C geometry confidence field: COMPLETE / CI PASS at source level.**
- Confidence analysis is ON, confidence diagnostic evidence is produced, and confidence-guided refinement remains **OFF**.
- Thresholds remain HIGH >= 0.75, NEUTRAL >= 0.40, LOW >= 0.20 and VERY_LOW < 0.20.
- G7.2C writes a diagnostic NPZ plus a colored PLY point proxy for later ComfyUI visualization; it never changes official geometry and is never exported to Maya.
- UNKNOWN receives no free-space penalty before G7.3. CONFLICT is low-confidence evidence, not an automatic deletion instruction.
- `ready_for_destructive_fusion` remains false.
- GitHub Actions run `35946720027` completed SUCCESS on Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.
- Next source-only bounded work: **Gate 7.3 — Free-Space / Visibility No-Fill Authority**.
- User-facing Gate 7 promotion remains blocked until DR9R r15 runtime UX acceptance is reviewed.

## Authoritative reconciliation — 2026-09-24 Gate 7.2 source checkpoint

- DR9R r15 remains under user runtime UX testing; its published bundle is not modified by this source work.
- **Gate 7.1 — P10→P9 registration authority: COMPLETE / CI PASS.**
- G7.1 validates that current known-camera Gate 6 geometry is already in the P9 canonical metric world and therefore uses an identity transform: scale 1, translation 0, no Sim(3) refit.
- **Gate 7.2 — authority-aware geometry provenance: COMPLETE / CI PASS at source level.**
- G7.2 writes diagnostic-only provenance evidence/classes without mutating P9 or official P10 geometry.
- Provenance classes are `P9_SOURCE_PROTECTED`, `P9_RETAINED`, `P10_MULTIVIEW_SUPPORTED`, `P10_GENERATED_ONLY`, `UNKNOWN`, and `CONFLICT`.
- Independent multiview support requires sparse support across at least two images from at least two authored missions.
- `P10_GENERATED_ONLY` is conservative diagnostic evidence and cannot authorize deletion/replacement.
- `ready_for_destructive_fusion` remains false until G7.2C confidence, G7.3 free-space/no-fill, and G7.4 protected fusion are implemented.
- GitHub Actions run `35946502650` completed SUCCESS on Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.
- Next source-only bounded work: **Gate 7.2C — Geometry Confidence Field**.
- User-facing Gate 7 promotion remains blocked until DR9R r15 runtime UX acceptance is reviewed.

## Authoritative reconciliation — 2026-09-23 DR9R-F r7 ready for runtime acceptance

- P9 remains the accepted immutable upstream authority.
- DR9R-F F1–F8 implementation/static-package work is complete.
- Current package: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r7.zip`.
- Current user workflows are numbered and current-only: `01_ConceptGhost_P10_ROUTE_SETUP_r7.json` and `02_ConceptGhost_P10_PRODUCTION_r7.json`.
- r7 fixes the destructive route reset, frozen Perspective duplicate, missing all-view zoom/pan, route visibility overflow, hidden AUTO_LATEST resolution, P10 storage lifecycle ambiguity, and split-workflow P9-dependency uncertainty.
- P10 cleanup is explicitly scoped to P10-owned paths and cannot delete P9.
- P9 Maya remains immutable; future P10 refined Maya is a separate non-overwriting deliverable.
- Runtime source commit: `2b35f61057c1131520d21059c183ab02fbdca635`; CI run `35897710951` SUCCESS.
- r7 ZIP SHA-256: `0e38a75b5b4736a6b09e99fcfe71f3a361cf03946ac0bed0ef47eed889d8f756`.
- Google Drive file id: `1hAp4qqbCVxUyHLXrKuWQUPHERLcFNFWR`; GitHub release tag: `p10-dr9r-r7`.
- User runtime acceptance is PENDING. Gate 7 remains blocked until r7 is tested and reviewed.


## Authoritative reconciliation — 2026-09-23 DR9R r6 ready for runtime acceptance

- P9 remains accepted immutable upstream authority; P10 must operate on that geometry as delivered.
- DR9R-A and DR9R-B1..B6 are COMPLETE / CI PASS.
- DR9R-C explicit two-stage handoff is COMPLETE / CI PASS.
- DR9R-D immutable P10 attempts is COMPLETE / CI PASS.
- DR9R-E implementation/package work is COMPLETE; one real user runtime acceptance pass remains.
- Final package: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r6.zip`.
- Normal new-scene execution is three Queue Prompt clicks: Route Setup #1 -> edit -> Route Setup #2 commit -> Production #1.
- Only the first Route Setup queue performs the expensive P9 solve; Route Setup commit should reuse cached P9; Production contains no P9 solver.
- r6 ZIP SHA-256: `be3e3fc5ef84f404a41cd7177b16a5aa9331ba0420c6013397a4f641413226d5`.
- Gate 7 must not start until this runtime acceptance is reviewed.


## Authoritative reconciliation — 2026-09-23 DR9R r5 published

- P9 remains the accepted immutable upstream authority.
- DR9R-A, B1-B6, C and D are COMPLETE / CI PASS.
- DR9R-E final two-workflow package is PUBLISHED.
- Bundle: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r5.zip`.
- SHA-256: `63ec487e3a73e98018cb72d5d27472ada3e33ccbd450ebf964028e558420be1d`.
- Google Drive file id: `1qr3iAHlRRlgRHsqRF1zwULlfNikhTwyH`.
- GitHub release: `p10-dr9r-r5`.
- New-scene flow is three Queue Prompt clicks but only one expensive P9 solve and one P10 Production execution.
- User runtime acceptance is PENDING. Gate 7 must not begin until r5 runtime evidence is reviewed.
- Detailed closeout: `Experimental/P10_Lab/docs/18_DR9R_RUNTIME_FINDINGS_REFINEMENT_PLAN.md`.


This is the persistent execution board for ConceptGhost v1.54 P10. It maps the
16 ordered implementation items in `01_MASTER_IMPLEMENTATION_PLAN.md` to ten
development gates. A gate is complete only when its acceptance evidence is
recorded and its checkpoint is mirrored to GitHub and Google Drive.

## Authoritative reconciliation — 2026-09-23 DR8 complete

This is the newest authoritative development status.

- **DR8A–DR8E are COMPLETE at code/CI level.**
- A dedicated aggregate closeout suite now validates the entire artist-route diagnostic/preview contract rather than relying only on isolated tests.
- Baseline/P9 isolation is explicitly regression-tested: the original workflow object and Baseline export node remain unchanged.
- Two-drone PATH + SPIN_360 identity, exact frame sampling, diagnostics, split-WAN reassembly, preview freshness and frontend controls are covered.
- GitHub Actions has an explicit DR8 closeout gate in addition to the complete P10 test suite.
- Closeout run `35818321869` completed SUCCESS on `de1201374c7a633dbdb1ff7654520cb79d08212d` across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.
- Formal closeout matrix: `Experimental/P10_Lab/docs/15_DR8_FINAL_REGRESSION_CLOSEOUT.md`.
- **Next bounded development: DR9 — Preview Package + User Runtime Acceptance.**
- DR9 must produce the next complete installer/workflow, pass extracted-bundle/release-integrity checks, synchronize GitHub/Google Drive, then be exercised in real ComfyUI with at least one curved/descending PATH plus one SPIN_360 mission and per-drone GIF inspection.
- Required Gate 7 fusion/free-space work remains after this bounded route-authoring runtime acceptance.

## Authoritative reconciliation — 2026-09-23 DR8D complete

This is the newest authoritative development status.

- DR8A route diagnostics remains COMPLETE / CI PASS.
- DR8B per-drone final-composite GIFs remains COMPLETE / CI PASS.
- DR8C formal preview index/output surfacing remains COMPLETE / CI PASS.
- **DR8D — Preview Invalidation / Freshness — is COMPLETED / CI PASS.**
- Preview authority now requires matching route-plan hash, control-manifest hash, WAN-generation-context hash, GIF bytes and exact final-composite source bytes.
- The prior preview package is explicitly classified before regeneration; missing/tampered prior index bytes are distinguished from route/control/settings changes.
- Gate 5 removes the previous ConceptGhost-owned preview package before writing the next one, preventing stale GIF/index state from surviving as current authority.
- Post-generation source-composite mutation now fails freshness validation instead of leaving an apparently valid GIF.
- The WAN manifest and diagnostics record the preview invalidation reason and freshness policy.
- CI run `35817845135` completed SUCCESS on implementation commit `5ee52c8edf0b84ecbaec0c3f3458fb6543ef8e2e`.
- CI run `35817871526` completed SUCCESS on regression commit `1dc4c5c44b88cd313adf48ae0da92e8bb96b5c3d`.
- **Next bounded development: DR8E — Final Regression Closeout.**

## Authoritative reconciliation — 2026-09-23 DR8C complete

This is the newest authoritative development status.

- The pre-DR8 DR7 recovery checkpoint remains frozen in GitHub and Google Drive.
- DR8A pre-WAN route diagnostics remains COMPLETE / CI PASS.
- DR8B per-drone final-composite GIF generation remains COMPLETE / CI PASS.
- **DR8C — Preview Index / Output Surfacing — is COMPLETED / CI PASS.**
- `drone_preview_index.json` is now schema `ConceptGhost.P10DronePreviewIndex.v0.2` with scene/run/route/control/WAN-generation identity.
- Every GIF entry carries exact mission/frame range, dimensions, fps, ordered source-frame-set SHA-256 and GIF SHA-256.
- Formal validation fails closed on stale/missing/tampered preview bytes or identity/order mismatch.
- WAN manifest and diagnostics surface preview-index path/hash plus per-drone preview metadata.
- Gate 5 WAN sampler now exposes `drone_preview_index_path` as an additional output without changing the existing WAN manifest output used by Gate 6.
- GIFs are surfaced through ComfyUI standard output-image metadata for direct artist inspection.
- CI runs `35817184829` and `35817189070` both completed SUCCESS.
- **Next bounded development: DR8D — Preview Invalidation / Freshness.**

## Authoritative reconciliation — 2026-09-23 DR8B complete

This is the newest authoritative development status.

- The pre-DR8 DR7 recovery checkpoint remains frozen in GitHub and Google Drive.
- DR8A pre-WAN route diagnostics remains COMPLETE / CI PASS.
- **DR8B — per-drone final-composite GIF previews — is COMPLETED / CI PASS.**
- Gate 5 now emits one GIF per authored drone from final source-preserving/WAN composite frames.
- Split WAN windows belonging to the same drone are reassembled into one exact global-frame sequence before preview creation.
- All mission frames are included; missing/duplicate/cross-mission frames fail closed.
- Default preview profile is max width 640 px, aspect preserved, 10 fps, infinite loop.
- GIF filenames are Windows-safe.
- Each GIF carries a SHA-256 and an ordered source-frame-set SHA-256.
- `drone_preview_index.json` is already produced and surfaced in Gate 5 diagnostics; DR8C will formalize/finish that output-index contract.
- GitHub Actions run `35816862522` completed SUCCESS on `6c9931c63ed18ad3d6c3ad97b59175b44a4bad22`.
- **Next bounded development: DR8C — Preview Index / Output Surfacing.**

## Authoritative reconciliation — 2026-09-23 DR8A complete

This is the newest authoritative development status.

- Pre-DR8 recovery checkpoint is frozen in GitHub branch `checkpoint/p10-dr7-complete-20260923` at commit `8d15f63d24fff023bec47eeccb334beb4e615e90`; its GitHub Actions run `35815637530` is SUCCESS.
- A matching Google Drive checkpoint folder exists under the P10 Lab with the r10 installer baseline, DR7 plan snapshot and checkpoint manifest.
- DR8A — deterministic pre-WAN route diagnostics — is COMPLETED / CI PASS.
- Gate 4 now writes `diagnostics/drone_route_diagnostics.json` before WAN.
- The manifest includes mission order, active drone count, route/movement lengths, exact frame counts, collision hold/resume statistics, clearance and P9 coverage/hole metrics.
- Status semantics are deterministic: PASS for an exact route/frame contract without collision hold; WARN for a valid route requiring collision hold or having no P9 coverage; FAIL for route/frame/diagnostic contract mismatch.
- Low P9 coverage alone is not treated as failure because Gate 5/WAN is explicitly the missing-region completion stage.
- GitHub Actions run `35816433877` completed SUCCESS on `efb7a39b0a53c2035ab8ae58ca34a26c339ea92a`.
- **Next bounded development: DR8B — per-drone final-composite GIF previews.**

## Authoritative reconciliation — 2026-09-23 DR7 complete

This is the newest authoritative development status.

- Gate 6 first-pass remains PASS and is not reopened.
- Gate 4R remains the active bounded refinement before required Gate 7.
- DR0–DR2 are complete.
- DR3–DR5 are implemented/CI-green with user runtime acceptance deferred to DR9.
- DR6 artist-route Gate 4 → WAN → Gate 6 integration is complete at code/CI level.
- **DR7 persistence / resume / deterministic identity is COMPLETED at code/CI level.**
- Routes are now bound to `scene_contract_id + source_run_id + route_authority` and carry a deterministic SHA-256.
- An artist-authored route cannot be silently reused on another scene/run. An untouched editable seed may be regenerated instead.
- Gate 4 persists `control_sequence/route_plan.json`; control/camera manifests bind that file/hash to the source scene/run.
- Gate 5 verifies the persisted route before generation and invalidates prior WAN output when route/control/WAN settings change.
- Gate 6 resume verifies WAN/camera manifests plus hashes of every source composite image and the ordered image set; changed/missing image bytes force rebuild.
- Editor changes deliberately invalidate the previous route hash; the next execution rebinds the edited plan. `Resetar cena` explicitly discards saved route state.
- GitHub Actions run `35813649004` completed SUCCESS on `02c72585a312e26fda011e128e27dd9eae4f1cc2`.
- **Next bounded development: DR8 — diagnostics / quality controls / final regression coverage.**
- DR9 remains the complete installer/workflow + real ComfyUI user acceptance.

## Authoritative reconciliation — 2026-09-23 DR6 complete

This is the newest authoritative development status.

- Gate 6 first-pass remains PASS.
- Gate 4R artist-route refinement remains the active bounded work before required Gate 7.
- DR0–DR2 are complete.
- DR3 interactive tri-view editor is implemented/CI-green; user runtime pending.
- DR4 1–7 drones + PATH/SPIN_360 UX is implemented/CI-green; user runtime pending.
- DR5 surface-aware collision preflight + hold/resume protection is implemented/CI-green; user runtime pending.
- **DR6 route editor → Gate 4 → Gate 5 WAN → Gate 6 known-camera reconstruction integration is COMPLETED at code/CI level.**
- DR6 now enforces exact mission/frame identity, no silent WAN frame loss, preserved mission identity across split windows, and route-authority/hash parity at the Gate 6 boundary.
- GitHub Actions run `35811855641` completed SUCCESS on all active Python/OS test jobs.
- Next bounded development is **DR7 — scene-bound persistence / deterministic route identity / checkpoint invalidation**.
- DR8 diagnostics remains partial.
- DR9 produces the complete preview bundle and performs the real ComfyUI user acceptance of DR3–DR6.

## Authoritative reconciliation — 2026-09-23 Gate 4R artist route authoring

This is the newest authoritative development boundary.

- Gate 6 first-pass runtime acceptance remains PASS and is not reopened.
- Before starting required Gate 7 fusion work, a user-requested P10 camera-evidence refinement is active at the Gate 4 boundary: **Gate 4R — Artist Drone Route Authoring**.
- The refinement replaces automatic route authority with artist-authored missions while retaining the automatic planner only as an editable seed/fallback.
- Total bounded work: **10 subgates DR0–DR9**.
- DR0 planning, DR1 route contract/sampling and DR2 tri-view projection backend are completed.
- DR3 interactive ComfyUI editor is implemented and under CI/runtime validation.
- DR4 multi-drone/PATH/SPIN_360 controls are implemented in backend and frontend but still require runtime validation.
- DR5 collision hold-and-resume backend exists; visualization and stronger scene-surface validation remain.
- DR6 authored-route Gate 4→5→6 integration is partially wired.
- DR7 deterministic persistence/resume is pending.
- DR8 diagnostics/tests are partial.
- DR9 packaged user runtime acceptance is pending.
- The final UI target is one synchronized TOP/SIDE/FRONT scene editor, 1–7 drones, click/drag 3D waypoints, PATH or SPIN_360 per drone, shared capture settings and collision protection.
- Gate 7 required implementation waits until this bounded camera-authoring refinement is accepted, because the quality of Gate 7 fusion depends on the evidence cameras selected here.

## Authoritative reconciliation — 2026-09-23 r9 runtime PASS

This is the newest authoritative status. Older reconciliations below are historical checkpoints.

- User runtime r9 completed the integrated P10 path through the **Gate 6.6 reconstructed pre-fusion mesh preview** with no runtime exception.
- The r9 viewport/intrinsics correction is therefore runtime-validated: Gate 6.3 accepted the known-camera database, Gate 6.4 dense reconstruction completed, Gate 6.5 produced a non-empty pre-fusion mesh, and Gate 6.6 rendered the final three-view mesh diagnostic.
- **Gate 6.6 functional runtime acceptance is PASS. Gate 6 first-pass path is COMPLETED.**
- The source Refined/P9 run used for this validation was `20260923T001018_212752Z_21246d71`. Its production export manifest reports PASS, but it was executed with **Fast Test / Low Resolution**; therefore it validates pipeline structure and runtime plumbing, not final-quality geometry.
- P10 release workflows now default `geometry_profile` to **High Fidelity Split Clean**. Artist override remains allowed.
- Several secondary `PreviewImage` nodes may appear blank even when their tensors are valid. These nodes are diagnostic-only parallel consumers: Gate 5 receives flight images/hole masks/control manifest directly from the evidence node, and Gate 6 receives the camera manifest directly. The successful WAN and Gate 6 reconstruction therefore prove the blank panels are not blocking the data path.
- To make diagnostics robust against ComfyUI temp-preview/cache behavior, the Gate 4 evidence node now persists compact output previews for source authority, source-lock mask, representative drone views, representative raw holes and camera trajectory in addition to the existing P9 ERP preview.
- The new Free-Space/Delaunay producer extensions remain scheduled as Gate 7 prerequisites/consumers per the existing policy; they do not invalidate the completed Gate 6 first-pass acceptance.
- Next required development gate is **Gate 7.1 — P10 reconstruction → P9 coordinate registration**, but project-control rules still require explicit user approval before starting the next gate.

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
