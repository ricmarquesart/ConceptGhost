# ConceptGhost — Optional Geometry Confidence Refinement Layer

Status: PLANNED — non-blocking, default OFF  
Roadmap placement: Gate 7, immediately after 7.1 P10→P9 registration and as an optional overlay for 7.2 authority-aware fusion.

## Decision

The existing P9→P10 path remains authoritative and unchanged by default.

Add one optional confidence-guided geometry refinement layer:

- `geometry_confidence_refine = OFF` by default.
- `show_geometry_confidence = OFF` by default.
- With both OFF, numerical/topological behavior must remain identical to the current Gate 7 plan.
- The layer may be enabled only by explicit artist choice.
- The confidence layer must never weaken original-source authority.

The current motivating failure class is local geometry ambiguity where the reference view is correct but side/back topology becomes fused or stretched (for example a foreground pot/plant cluster merging into neighboring geometry). High-confidence front-facing evidence must be preserved while low-confidence side/back continuation can become eligible for additional reconstruction/fusion work.

## Why Gate 7

Gate 7 is the first point where:
1. P9 geometry is in its canonical source-authority frame.
2. P10 reconstructed geometry has been registered into the same frame.
3. The system can compare source-facing P9 surfaces against independent multiview evidence.
4. Confidence can affect fusion without requiring the Baseline/P9 branch to change.

This is too late for Gate 4/5 hole generation if used as the primary path, but correct for an optional refinement because it can mark existing P9 faces as low-confidence and allow Gate 7/8 to repair them conservatively.

## Gate 7 optional overlay

### 7.2C-1 — Geometry Confidence Field

Compute a per-face confidence score in [0,1] without moving geometry.

Evidence may include:
- original-camera source visibility / exact source reprojection support;
- face normal vs original-camera viewing direction;
- distance to silhouette / occlusion / depth discontinuity boundaries;
- Split Clean boundary and rejected-neighbor evidence;
- triangle shape quality / local stretch / aspect irregularity;
- local normal variance and depth-gradient consistency;
- P9 solver confidence/evidence where available;
- registered P10 multiview support count and view-angle diversity;
- P10 reprojection/depth agreement across independent cameras;
- semantic/instance boundary evidence as a weak hint only, never sole authority.

Source-facing observed geometry gets a positive confidence prior. Side/back continuation that is weakly observed, boundary-adjacent, stretched or contradicted by P10 multiview evidence is reduced.

### 7.2C-2 — Confidence Classes

Initial policy:

- HIGH: confidence >= 0.75
- NEUTRAL: 0.40 <= confidence < 0.75
- LOW: 0.20 <= confidence < 0.40
- VERY_LOW: confidence < 0.20

Thresholds are internal/advanced initially and must not clutter the normal UI.

The normal artist-facing control is only:
- `geometry_confidence_refine` ON/OFF.
- `show_geometry_confidence` ON/OFF.

### 7.2C-3 — Source-Facing Protection

High-confidence source-facing P9 faces are locked.

Rules:
- Do not delete or move high-confidence faces merely because a later P10 surface exists.
- Preserve the original camera silhouette/reprojection unless a replacement passes a stricter regression gate.
- Foreground faces seen directly by the reference camera can remain card-like if their side/back continuation is uncertain.
- Confidence can differ within the same object/shell: front faces may be HIGH while lateral/back transition faces are LOW.

This is the core requirement for cases like pot + plant: preserve what the source camera actually sees, but do not give equal authority to uncertain geometry that stretches sideways/backward.

### 7.2C-4 — Optional Confidence-Guided Refinement

When `geometry_confidence_refine = OFF`:
- diagnostics only if requested;
- no geometry movement;
- no topology deletion;
- no change to Gate 7 fusion.

When ON:
- HIGH faces: locked/source-authoritative.
- NEUTRAL faces: unchanged by confidence alone.
- LOW faces: eligible for local replacement/remesh only when registered P10 evidence is stronger.
- VERY_LOW faces: may be treated as virtual-hole / replaceable geometry candidates, but only outside locked source-facing support.

A low-confidence score alone is not enough to destroy geometry.

Geometry may be replaced only when downstream evidence passes bounded conditions such as:
- support from multiple independent P10 views;
- adequate view-angle diversity;
- local geometric consistency;
- no regression of original-camera source reprojection beyond tolerance.

If replacement evidence is insufficient, preserve the current geometry and mark it LOW rather than inventing a correction.

### 7.2C-5 — Confidence-Aware Virtual Holes

Expose a P10 refinement mask:

`confidence_virtual_hole_mask`

This mask is separate from physical holes.

Candidate rule:
- physical hole OR
- VERY_LOW existing geometry that is outside protected original-source support and has evidence of contradiction/poor support.

The mask may be consumed later by Gate 8 local remesh/repair and by Gate 11 refinement experiments. It must not alter the original Gate 4 raw-hole contract when the feature is disabled.

### 7.2C-6 — 3D Confidence Visualization

Generate a 3D diagnostic representation without changing the official mesh.

Maya structure proposal:

`CG_DIAGNOSTICS/CG_GEOMETRY_CONFIDENCE`

Visual policy:
- HIGH confidence = BLUE
- LOW / VERY_LOW confidence = RED
- NEUTRAL = no overlay / transparent
- official source texture remains untouched

Prefer a diagnostic duplicate/overlay or face-set/material view rather than modifying the official material.

Add visibility control:
- `show_geometry_confidence = OFF` by default.

The user must be able to toggle the confidence visualization independently of confidence-guided refinement.

Also emit a lightweight machine-readable and shareable diagnostic:
- `geometry_confidence_manifest.json`
- `geometry_confidence_preview.ply` or equivalent colored 3D proxy when practical
- compact multi-angle preview PNG/SVG
- summary histogram of HIGH/NEUTRAL/LOW/VERY_LOW face area/count

### 7.2C-7 — A/B Safety Contract

Every run with confidence refinement ON must produce a paired comparison against the standard Gate 7 result.

Compare at minimum:
- original-camera reprojection error;
- protected-source coverage;
- number/area of modified faces;
- number/area of LOW/VERY_LOW faces;
- P10 multiview agreement;
- mesh health;
- new holes introduced;
- repaired/replaced regions;
- final Maya visual review.

Acceptance rule:
- confidence refinement is never allowed to silently become the default;
- it remains OFF until repeated A/B runs show benefit without reference-view regression.

## UI policy

Recommended artist-facing properties:

`Geometry Confidence Refinement: OFF / ON`
`Show Confidence Map: OFF / ON`

Default:
- Refinement = OFF
- Visualization = OFF

Advanced/debug-only values may expose thresholds later, but should not be required for normal operation.

## Provenance / authority

Confidence is evidence, not authority.

Authority order remains:
1. Original source-observed high-confidence P9 geometry.
2. Registered P10 multiview geometry when it is stronger than low-confidence P9 geometry.
3. Neutral P9 geometry when no stronger replacement exists.
4. Generated/repair geometry only for bounded low-confidence or hole regions.

Every modified face/region must record provenance:
- original P9;
- preserved high-confidence P9;
- low-confidence P9 retained;
- P10 replacement;
- Gate 8 local repair.

## Relationship to later gates

Gate 8:
- consumes LOW/VERY_LOW regions as bounded defect/repair candidates;
- local remesh must respect HIGH locks.

Gate 9:
- exports confidence diagnostic group/materials/sets to Maya;
- original-view regression is release-blocking for confidence-refined runs.

Gate 10:
- validates the optional mode under RTX 2080 Ti constraints;
- standard OFF path remains release baseline.

Gate 11:
- may use confidence to rank additional drone coverage or targeted revisits;
- low-confidence regions can influence route scoring, but only after the first end-to-end result exists.

Gate 12:
- standardizes confidence visual branches, logs, histograms and compact diagnostic package.

## Non-regression requirement

The OFF path is the contract.

With `geometry_confidence_refine = OFF` and `show_geometry_confidence = OFF`, outputs must remain equivalent to the already planned Gate 7/8/9 pipeline except for inert metadata needed to declare the feature disabled.
