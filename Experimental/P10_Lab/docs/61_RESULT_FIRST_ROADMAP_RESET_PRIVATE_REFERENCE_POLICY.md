> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. The purchased/original reference files remain Google Drive only and must **not** be copied to GitHub or release bundles. Concept Art + accepted P9 camera/source authority remain the product authority. Current gate progression follows the result-first reset in `61_RESULT_FIRST_ROADMAP_RESET_PRIVATE_REFERENCE_POLICY.md`.

# ConceptGhost P10 — Result-First Roadmap Reset

**Status:** AUTHORITATIVE PROJECT DIRECTION  
**Effective:** 2026-09-25

## Private implementation reference

P10 design work must consult the private implementation-reference library before changing camera coverage, generated-view production, source-preserving composition, multi-view dataset construction, reconstruction, splat/surface extraction, fusion, or Maya integration:

`G:\My Drive\ConceptGhost\Drones\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`

The folder is private/purchased source material. **Do not upload, mirror, vendor, copy, or embed its contents in GitHub or release bundles.**

Private ConceptGhost-derived notes are stored separately under:

`G:\My Drive\ConceptGhost\Drones\90_CONCEPTGHOST_DERIVED_NOTES_PRIVATE`

This public repository may record ConceptGhost-specific engineering decisions, but not reproduce the private source materials.

## Why the roadmap is reset

The prior P10 implementation progressed through reconstruction runtime, Gate 7 filtering and Gate 8 source planning before the target-PC result had proven useful aligned novel geometry.

That is no longer accepted as meaningful gate closure.

The rejected reconstruction demonstrated:

- runtime success is not reconstruction success;
- CI success is not artist-visible success;
- a non-empty mesh can still be useless for the actual P9 holes;
- downstream cleanup must not be used to compensate for missing core reconstruction.

Historical gate records remain audit evidence, but do not override the result-first acceptance model below.

## Product authority

The final product remains anchored to:

1. original Concept Art;
2. accepted P9 source/camera authority;
3. ConceptGhost project contracts.

The original concept-camera appearance must remain unchanged.

## Revised proof order

### R0 — Freeze acceptance scene

Freeze one accepted P9 run and exact source camera for all reconstruction comparisons.

### R1 — Persistent output tree

Every new P10 attempt creates its official output hierarchy from the beginning. Normal new runs must not require a later backfill BAT.

### R2 — Camera rails and coverage

Produce persistent camera rails and direct evidence that intended missing/occluded regions are observed from multiple useful trajectories.

### R2-PANO — Mandatory shared 360 world prior

Before R3, every normal P10 result-first run converts the original concept into a seam-corrected 2:1 equirectangular 360 world prior. P9 remains authoritative for the original concept view. The panorama is mandatory lower-authority generated context for unseen directions.

Do **not** feed the flat equirectangular image into the existing perspective MoGe path as if it were a normal camera frame. When panorama-derived depth/proxy geometry is needed, project the ERP into ordinary known-yaw/pitch/FOV perspective views first and align those views to P9 overlap.

Acceptance condition: the mandatory panorama stage must preserve the exact original concept-camera result and provide a valid continuous world prior for all downstream routes. The project does not fall back to a panorama-free production path; failures are fixed at this stage.

Private source for this lane:
`G:\My Drive\ConceptGhost\360\00_ORIGINAL_READ_ONLY`

### R3 — Source-authority generated views

Preserve source/P9-supported pixels where trustworthy and use generative completion only for genuinely unknown/disoccluded content. Persist provenance and coverage.

### R4 — Extendable multi-view dataset

Produce a standard perspective/pinhole multi-view dataset with camera evidence and an extension path for additional trajectories.

### R5 — Explorable-world proof

Before polygon cleanup/fusion, prove that the exact ConceptGhost dataset can produce a coherent explorable 3D world representation.

**R5 is a hard blocker.**

### R6 — Useful polygonal surface reconstruction

From validated multi-view/world evidence, produce polygonal geometry that:

- matches P9 metric scale and coordinate space;
- occupies intended missing/occluded regions;
- does not require manual transform guessing;
- is visibly useful in Maya.

**R6 is a hard blocker.**

### R7 — Protected comparison/fusion

The Maya diagnostic must expose independently toggleable:

- P9 original;
- complete P9 + accepted-P10 candidate;
- raw P10 reconstruction;
- accepted P10 fill;
- rejected/low-confidence P10;
- cameras/rails.

### R8 — Cleanup/regularization

Only clean an already valid reconstruction. Do not use cleanup as a substitute for reconstruction.

### R9 — Texture/provenance/original-view regression

Verify source dominance on observed surfaces, generated-region traceability, and original concept-camera equivalence.

### R10 — Final Maya + COMPLETE release

Deliver the editable Maya scene, diagnostics, rails, automatic outputs, and a complete repeatable installer/bundle.

### R11 — Adaptive expansion/optimization

Only after core reconstruction works: add routes for weak areas, expand explorable volume, optimize runtime/storage, and run final regressions.

## Gate status contract

Every gate reports three independent states:

- runtime;
- functional;
- artist-visible quality.

A gate is CLOSED only when the functional result passes and the artist-visible result is accepted.

## Immediate acceptance test

The current high-overlap short-scene/five-drone test is the primary A/B scene.

The existing reconstruction path and the reference-aligned multi-view/world-proof path are compared using the same generated views and camera evidence.

Success is measured by:

- P9 metric alignment;
- useful missing-region support;
- agreement across independent routes;
- preservation of the original concept view;
- coherent nearby parallax/explorability.

## Packaging

The next user-facing package must be a **COMPLETE ConceptGhost bundle** carrying the accepted automatic-output and Maya-unit corrections directly in normal runtime.

Historical backfill helpers may remain recovery-only, but they must not be required for normal new runs.

Gate 8 remains blocked until R5/R6 produce a useful aligned result.
