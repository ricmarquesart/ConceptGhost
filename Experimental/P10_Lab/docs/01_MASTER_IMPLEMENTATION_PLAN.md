> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. The purchased/original reference files remain Google Drive only and must **not** be copied to GitHub or release bundles. Concept Art + accepted P9 camera/source authority remain the product authority. Current gate progression follows the result-first reset in `61_RESULT_FIRST_ROADMAP_RESET_PRIVATE_REFERENCE_POLICY.md`.

# P10-Lab Master Implementation Plan — P9 (= Baseline) + P10

## Decision

The Refined Solver Fusion architecture is now defined as **P9 + P10**.

P9 is intentionally a functionally identical copy of Baseline. It has no separate refined-solver behavior of its own. P10 is appended immediately after P9 and is the first stage that adds multiview completion, geometry recovery and scene completion.

## Non-negotiables

- The standalone Baseline branch remains untouched.
- P9 must remain functionally equivalent to Baseline before the P10 handoff.
- Original source pixels and the P9/Baseline camera are highest authority where observed.
- Generated content is allowed only in unseen or demonstrably defective regions.
- No manual drone piloting.
- Initial scope is local completion, not full 360 world generation.
- Final product remains editable Maya geometry.
- First target is an RTX 2080 Ti with 11 GB VRAM.
- P10 control rendering exposes unsupported holes without compensating for them.
- Control, mask, generated and source-composite previews are visible per flight.
- Flight count is configuration, with a default of three plus one adaptive slot.

## Ordered implementation

1. P9 Completion Bundle contract and dry-run validator.
2. P9/Baseline-equivalent adapter.
3. Automatic scene-relative camera-path planner with configurable flight count.
4. Raw-hole control-frame and disocclusion-mask generation.
5. Quantized WAN masked completion.
6. Source-preserving high-resolution composite.
7. SphereSfM reconstruction.
8. COLMAP dense stereo/fusion and mesh.
9. Registration to P9/Baseline coordinates.
10. Known/generated fusion.
11. Local remesh/geometry cleanup.
12. Texture recovery.
13. Original-camera regression.
14. Maya export.
15. Spend configurable adaptive path budget only where important defects remain.
16. Refined-branch integration as P9 (= Baseline) + P10.

## Authoritative reconstruction refinement — 2026-09-22

The ordered implementation list above records the original plan, but the implemented Gate 6 architecture has been refined:

- **Known-camera COLMAP is the primary P10 reconstruction path** because every virtual P10 perspective camera is already derived from P9 authority.
- **SphereSfM is optional validation/fallback**, especially for ERP/spherical experiments; it does not replace known P9 camera authority in the current perspective path.
- Gate 6.4 retains geometric depth maps, normal maps and consistency graphs as downstream evidence.
- Gate 6.5 keeps Poisson and gains a planned Delaunay visibility-aware candidate when Gate 7 implementation begins.
- Gate 7.2C consumes geometry confidence plus free-space conflict evidence.
- Gate 7.3 owns explicit free-space/no-fill fusion constraints.
- Gate 8 distinguishes valid openings, unknown missing surfaces, false surfaces inside confirmed free space and conflict regions.
- Gate 12 owns the standardized Free-Space 3D diagnostic surface.

This refinement preserves the official topology `P9 (= Baseline) → P10` and does not reopen completed Gate 6.4/6.5 first-pass work as a blocker.

## P9 acceptance lock and DR9R execution rule — 2026-09-23

The current P9 output is accepted as the authoritative upstream scene for P10, including its monocular depth span and disconnected-shell structure. P10 must adapt to that world without reshaping P9 merely to simplify downstream reconstruction.

DR9R therefore focuses on camera authoring, orientation authority, reconstruction diagnostics, multi-mission preservation, quality gates, explicit P9→P10 handoff and immutable P10 attempts.

User runtime testing is deferred until the entire DR9R improvement set is complete. Every bounded DR9R subgate is still checkpointed to GitHub and Google Drive for recovery, but intermediate checkpoints are not user-test releases.

## Promotion gates

- Baseline protection.
- P9 identity with Baseline.
- Original-view fidelity.
- Reduced disocclusion holes.
- Healthy completed mesh.
- Identifiable provenance.
- Maya usability.
- 11 GB hardware compliance.

## Official topology

`Baseline` → Baseline output.

`Refined Solver Fusion` → P9 (same behavior/output contract as Baseline) → P10 completion → refined Maya result.

P10 must be developed so that it can be tested using Baseline-equivalent input, but its official integrated upstream stage is P9.

## Checkpoint contract

For each flight the workflow publishes previews after control render,
disocclusion mask, WAN completion and source-preserving composite. The same
artifacts are restart points. Resume requires a validated manifest and matching
artifact digests.

## Preview Version delivery contract

Whenever a completed gate or bounded sub-stage produces a meaningful result
that the user can execute, inspect in ComfyUI, or open in Maya, development
must publish a testable Preview Version before the next gate begins.

Preview packages use this naming convention:

`ConceptGhost_v1.54_P10_GateXX_PREVIEW_rN.zip`

Every Preview Version contains:

- the relevant workflow JSON;
- the required project-owned nodes and scripts;
- installation or update instructions;
- `README_TEST_PREVIEW.md` with numbered test steps;
- expected visible output for each exposed node;
- known limitations and intentionally unfinished downstream stages;
- validation results and a SHA-256 digest.

Preview packages remain isolated from the stable standalone Baseline. They may
extend the Refined/P10 laboratory, but must not overwrite or silently promote a
preview into the protected Baseline path.

A gate that only establishes non-visual contracts is marked `NO VISUAL PREVIEW`
rather than receiving a misleading workflow. Gate 1 is such a gate. Its git
checkpoint and recovery bundle are engineering evidence, not a user-facing node
preview.

Expected user-facing previews:

| Gate | Preview result |
|---|---|
| 2 | Completion Bundle loader/validator diagnostics |
| 3 | Temporary panorama, locked source region and observed/unknown map |
| 4 | Raw virtual-camera control video and disocclusion mask |
| 5 | WAN proposal and source-preserving composite |
| 6 | Recovered cameras, sparse cloud, dense cloud and pre-fusion mesh |
| 7 | P9/P10 registration overlay and geometry provenance |
| 8 | Geometry cleanup comparison and recovered texture |
| 9 | Original-camera regression and preliminary editable Maya scene |
| 10 | Complete integrated v1.54 preview |

The preview is a review gate: test findings are corrected in the current gate.
The next gate starts only after the current result is reported and approved.
