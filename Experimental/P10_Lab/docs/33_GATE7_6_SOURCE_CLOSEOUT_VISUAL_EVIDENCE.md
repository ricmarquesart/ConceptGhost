# ConceptGhost P10 — Gate 7.6 Source Closeout & Preview Readiness

Date: 2026-09-24  
Status: **SOURCE COMPLETE / CI PASS / RUNTIME PROMOTION BLOCKED**

## Ordering decision

The project first implemented the new **Visual Evidence & Comparison Contract** and only then closed G7.6.

That ordering is intentional: Gate 7 cannot be considered source-complete if the artist has no direct way to inspect what each subgate changed.

Authoritative visual contract:

`docs/32_VISUAL_EVIDENCE_COMPARISON_CONTRACT.md`

## What G7.6 now validates

Source implementation:

`p10_lab/gate7_closeout.py`

G7.6 validates the complete runtime chain:

- G7.1 identity registration;
- G7.2 provenance;
- G7.2C confidence;
- G7.3 free-space constraints;
- G7.4 protected fusion candidate;
- G7.5 visual review;
- mandatory visual-evidence manifests for G7.1, G7.2, G7.2C, G7.3, G7.4 and G7.5.

It fails closed on:

- scene/run/attempt identity mismatch;
- non-identity registration;
- Sim(3) or scale changes;
- P9 authority mutation;
- confidence refinement silently enabled;
- official geometry mutated inside diagnostic gates;
- G7.4 candidate marked official;
- any P9 face removed or P9 vertex moved;
- missing per-gate visual preview;
- missing per-gate comparison output;
- visual branches that feed geometry back into the pipeline.

## Project-wide visual evidence rule

Every meaningful gate now requires:

1. **State Preview**
2. **BEFORE/AFTER or REFERENCE/RESULT comparison**
3. **diagnostic manifest**

Every visual branch is terminal:

- `feeds_geometry_pipeline = false`
- `may_modify_geometry = false`
- `may_modify_p9 = false`
- `may_promote_result = false`

This applies to future gates as well.

## Implemented comparison branches

### Confidence comparison

Source:

`p10_lab/visual_comparisons.py::render_confidence_before_after`

Output:

- `confidence_before_after_comparison.png`
- `confidence_before_after_comparison.json`

Presentation:
- BLUE = high confidence;
- RED = low confidence;
- BEFORE = G7.2C confidence;
- AFTER = G7.3D confidence after free-space evidence;
- DELTA = where confidence changed.

Source ComfyUI node:

`P10 · Visual Evidence · Confidence BEFORE / AFTER`

### Same-camera drone replay

Source:

`p10_lab/visual_comparisons.py::render_drone_mesh_before_after_replay`

Outputs:

- `drone_replay_before.gif`
- `drone_replay_after.gif`
- `drone_replay_before_after.gif`
- `drone_replay_before_after.json`

Both sides use the same:

- Gate 6 qvec/tvec;
- PINHOLE intrinsics;
- frame selection;
- resolution.

This branch is deliberately reusable by later repair/refinement gates. A future hole repair can therefore be reviewed as:

`original problem/hole`
→ `first repair candidate`
→ `later refinement`
→ `final refined state`

through the exact same drone-camera sequence.

Source ComfyUI node:

`P10 · Visual Evidence · Same-Camera BEFORE / AFTER GIF`

## G7.6 own visual output

Runtime G7.6 produces:

- `gate7_visual_evidence_index.png` — contact sheet across Gate 7 visual branches;
- `gate7_input_output_summary.png` — earlier/before comparison beside the G7.5 protected-result review;
- `gate7_closeout_manifest.json`.

This means G7.6 itself also obeys the visual-output rule.

## Source-side result

`audit_gate7_source_contract()` now reports:

- G7.1: IMPLEMENTED
- G7.2: IMPLEMENTED
- G7.2C: IMPLEMENTED
- G7.3: IMPLEMENTED
- G7.4: IMPLEMENTED
- G7.5: IMPLEMENTED
- G7.6: IMPLEMENTED
- source contract complete: TRUE
- preview package ready for build: TRUE
- preview package published: FALSE
- runtime Gate 7 accepted: FALSE
- ready for Gate 8: FALSE

## Why Gate 8 remains blocked

Source completion is not runtime acceptance.

Two explicit approvals remain mandatory:

1. **DR9R r15 runtime UX acceptance**
2. **artist visual review of the real Gate 7 Preview**

Runtime closeout only sets:

`ready_for_gate8 = true`

when both are explicitly true and the complete Gate 7 visual-evidence chain is present.

There is no automatic promotion from CI success.

## CI

Visual Evidence Contract focused suite:

- `35958717367` — SUCCESS
  - Ubuntu / Python 3.12
  - Windows / Python 3.12

General regression at the visual-contract checkpoint:

- `35958717335` — SUCCESS

Gate 7.6 focused suite:

- `35958902099` — SUCCESS
  - Ubuntu / Python 3.12
  - Windows / Python 3.12

General regression at G7.6 implementation:

- `35958901952` — SUCCESS

Source snapshot at G7.6 implementation:

- `35958901957` — SUCCESS

## Current boundary

**Gate 7 source implementation is complete.**

Not yet complete:

- runtime integration/package of the Gate 7 Preview;
- real Gate 7 execution on the user's current accepted P10 attempt;
- artist review;
- final Gate 7 runtime promotion;
- Gate 8 start.

The currently published DR9R r15 package remains unchanged by this source closeout.
