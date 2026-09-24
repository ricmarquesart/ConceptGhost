# ConceptGhost — Visual Evidence & Comparison Contract

Date: 2026-09-24  
Status: AUTHORITATIVE PROJECT REQUIREMENT

## Decision

Every meaningful gate must expose a terminal visual-evidence branch so the artist can judge whether the gate is actually improving the scene without opening Maya.

A gate is not considered reviewable only because numerical tests pass.

The minimum visual contract is:

1. **State Preview** — show the gate's current result in a readable visual form.
2. **Comparison Output** — show BEFORE/AFTER or REFERENCE/RESULT using the same camera/projection/metric scale whenever possible.
3. **Diagnostics Manifest** — record exactly which inputs, views, scales and files were compared.

These branches are diagnostic only.

They MUST:
- terminate at the preview/comparison output;
- never feed geometry back into the authoritative pipeline;
- never modify P9;
- never promote a candidate;
- be deletable without changing the authoritative result.

## Comparison principle

The comparison must make the improvement visible rather than merely report that it happened.

Preferred presentation order:

1. same-camera BEFORE / AFTER replay;
2. static side-by-side using exactly the same projection and metric scale;
3. colored overlay;
4. delta / changed-region view;
5. focused problem-region crop when a global view hides the change.

For camera replays, both sides MUST use:
- identical qvec/tvec;
- identical intrinsics;
- identical frame selection;
- identical output resolution.

This allows a drone replay from an earlier stage to be reused later for a direct comparison against each refinement stage.

## Confidence visualization

Confidence should be visually readable without opening raw data.

Default diagnostic convention:
- **BLUE = high confidence**
- **RED = low confidence**
- intermediate confidence uses an interpolated red/blue scale.

The first implemented comparison is:

`G7.2C confidence BEFORE free-space coupling`
vs
`G7.3D confidence AFTER free-space coupling`

with a third DELTA panel.

Artifacts:
- `confidence_before_after_comparison.png`
- `confidence_before_after_comparison.json`

Source node:
- `P10 · Visual Evidence · Confidence BEFORE / AFTER`

## Same-camera drone replay

A reusable comparison renderer now replays any two mesh states through the exact Gate 6 known-camera sequence.

It produces:
- `drone_replay_before.gif`
- `drone_replay_after.gif`
- `drone_replay_before_after.gif`
- `drone_replay_before_after.json`

Source node:
- `P10 · Visual Evidence · Same-Camera BEFORE / AFTER GIF`

The current Gate 7 use can compare:
- BEFORE = P10 pre-fusion / earlier candidate;
- AFTER = protected fusion candidate.

Future Gate 8+ refinement stages should reuse the same renderer so a hole/opening can be inspected through the same drone trajectory:
- original hole/problem state;
- initial repair/fill candidate;
- later refined candidate;
- final refined geometry.

The visual branch is independent of the continuous geometry path.

## Gate-specific minimums

### G7.1 — Registration
Preview:
- P9/P10 registration overlay;
- camera/frustum context.

Comparison:
- P9 reference vs registered P10 in identical metric views.

### G7.2 — Provenance
Preview:
- source-protected / retained / multiview / generated / unknown / conflict classes.

Comparison:
- raw reconstructed geometry vs provenance-classified geometry.

### G7.2C — Confidence
Preview:
- blue/high to red/low confidence geometry.

Comparison:
- confidence before vs after subsequent evidence coupling.

### G7.3 — Free-Space
Preview:
- OCCUPIED / CONFIRMED_FREE / UNKNOWN / CONFLICT.

Comparison:
- surface candidate before constraints vs no-fill/no-bridge evidence.

### G7.4 — Protected Fusion
Preview:
- P9 preserved;
- P10 accepted;
- P10 rejected;
- reason/provenance.

Comparison:
- pre-fusion vs protected-fusion candidate;
- preferred dynamic comparison = same-camera drone GIF.

### G7.5 — Review
Preview:
- four-view registration/provenance review.

Comparison:
- consolidated Gate 7 evidence summary.

### G7.6 — Closeout
Preview:
- visual-evidence index / contact sheet.

Comparison:
- Gate 7 input-state vs Gate 7 protected candidate summary.

## Future gates

The requirement applies to future gates even if a gate-specific presentation has not yet been designed.

Any future gate that modifies, repairs, filters, fills, remeshes, textures or refines geometry MUST expose:
- a visual state preview;
- a BEFORE/AFTER comparison;
- and, when a camera sequence exists, a same-camera replay branch where useful.

For hole repair specifically, the expected visual sequence is:

`problem/hole BEFORE`
→ `first repair candidate`
→ `subsequent refinement`
→ `final refined state`

Each step should be visually comparable to the immediately preceding state and, where useful, to the original problem state.

## Source implementation

Project-wide contract:
- `p10_lab/visual_evidence_contract.py`

Comparison renderers:
- `p10_lab/visual_comparisons.py`

ComfyUI source nodes:
- `ConceptGhostP10ConfidenceComparison`
- `ConceptGhostP10DroneMeshComparisonReplay`

The currently published DR9R r15 bundle is not modified by this source work. These branches are intended for the next Gate 7 Preview package after runtime acceptance.

## Promotion rule

No gate may use a visual branch as authority.

Visual outputs exist for human review and diagnosis only.

A visual PASS is never a substitute for:
- identity/provenance checks;
- geometry-quality gates;
- free-space constraints;
- P9 immutability;
- runtime validation;
- explicit artist review where required.
