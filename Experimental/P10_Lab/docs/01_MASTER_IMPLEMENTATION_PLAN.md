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
