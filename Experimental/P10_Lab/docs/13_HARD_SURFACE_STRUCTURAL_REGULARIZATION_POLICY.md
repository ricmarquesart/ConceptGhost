# ConceptGhost — Hard-Surface / Structural Regularization Policy

Status: PLANNED — primary integration in Gate 8.2, after Gate 7 registration/fusion/confidence/free-space and before UV/texture recovery.
Feature type: optional geometry polish with always-available analysis/preview.
Default application state: OFF.

## Why this structure is required

The current P9/P10 reconstruction can be geometrically plausible and still be structurally weak in man-made regions.

Typical failure classes:
- a concrete canopy or overhang that should be planar becomes slightly bowed or rounded;
- two sides that appear intended to be parallel become skewed;
- a nominally rectangular architectural block loses orthogonality;
- repeated structural offsets lose proportional consistency;
- a sharp hard-surface crease becomes soft;
- one side of a visually balanced structure becomes longer/deeper than the other because monocular/multiview depth is uncertain;
- a locally distorted surface remains closed and therefore is not detected by hole-filling logic.

These are not primarily hole problems. They are **structural regularity problems**.

The purpose of this stage is to generate a conservative local hard-surface candidate that:
1. improves planarity/sharpness/structural consistency where evidence is strong;
2. preserves original-camera appearance;
3. respects CONFIRMED_FREE no-fill volumes;
4. respects HIGH-confidence/protected source geometry;
5. never globally forces symmetry or architectural assumptions;
6. remains fully optional for official geometry.

## Primary roadmap placement

Primary implementation home: **Gate 8.2 — Local Remesh / Cleanup / Hard-Surface Structural Regularization**.

Why Gate 8.2:
- Gate 7.1 has already registered P9 and P10 in one coordinate frame.
- Gate 7.2/7.2C has fused authority/provenance and produced geometry confidence.
- Gate 7.3 has classified free-space constraints.
- Gate 8.1 has identified bounded defect/repair regions.
- Gate 8.2 is therefore the first point where the system has enough information to polish geometry without asking MoGe/WAN to hallucinate a new object.
- Gate 8.3/8.4 occur afterward, so UV/texture recovery can adapt to the final selected topology.
- Gate 9 original-view regression is available immediately downstream to reject structural edits that hurt the reference view.

Supporting gates:
- Gate 7.2C supplies per-face confidence/protection.
- Gate 7.3 supplies CONFIRMED_FREE / UNKNOWN / CONFLICT constraints.
- Gate 8.1 supplies bounded candidate repair regions.
- Gate 9.1/9.2 validates original-camera reprojection and observed-region preservation.
- Gate 12 owns standardized A/B visualization, logs and retained diagnostics.

## Core operating contract

Three states are separated:

1. **Analysis/impact map**
   - runs by default;
   - does not change official geometry;
   - identifies where regularization would be allowed/useful.

2. **Regularized candidate**
   - generated as a diagnostic candidate when practical so A/B can be inspected quickly;
   - is not authoritative while application is OFF.

3. **Official selected geometry**
   - standard Gate 8 geometry when the switch is OFF;
   - regularized candidate only when the switch is ON and safety guards pass.

Primary artist-facing switch:

`Apply Structural Regularization: OFF / ON`

Default: **OFF**.

With OFF:
- analysis is still performed;
- the 3D affected-region preview is still available;
- candidate metrics/diff may still be generated;
- downstream official mesh remains the standard existing flow.

With ON:
- only bounded approved regions may be modified;
- source/projection/free-space/confidence guards remain mandatory;
- failed safety checks fall back region-by-region to the unmodified geometry.

## ComfyUI node/group design

### Node group: P10 · Structural Regularization Analysis

Purpose:
- inspect fused Gate 7 geometry;
- detect hard-surface candidate regions;
- calculate structural constraints;
- calculate protected/rejected regions;
- build the impact map.

Inputs:
- fused Gate 7 mesh;
- original source image;
- authoritative original camera;
- P9/P10 provenance;
- geometry confidence field;
- free-space constraints;
- Gate 8.1 defect/repair regions.

Outputs:
- structural_region_manifest;
- planar patch set;
- candidate constraint set;
- impact mask / per-face classification;
- analysis diagnostics.

This group does not modify official geometry.

### Node: P10 · Structural Regularization 3D Preview

This viewer is present/active by default regardless of the application switch.

Display proposal:
- GRAY = unaffected;
- BLUE/CYAN = protected source/high-confidence region;
- ORANGE = eligible candidate region;
- RED = vertices/faces that the candidate would actually move/remesh;
- MAGENTA = conflict/rejected candidate due to free-space/source/regression constraints.

Viewer modes:
- Standard Mesh;
- Candidate Mesh;
- Impact Map;
- Difference Magnitude.

User controls:
- orbit;
- zoom;
- pan;
- display-mode selector when supported.

Diagnostic only:
- no Maya materials;
- no Maya selection sets;
- no Maya groups;
- no modification to artist deliverables.

### Node group: P10 · Structural Regularization Candidate

Purpose:
- create a bounded candidate geometry using the detected structural relationships.

Outputs:
- unmodified_standard_mesh;
- regularized_candidate_mesh;
- regularization_manifest;
- per-region before/after metrics;
- candidate regression preview.

### Node: P10 · Structural Regularization Selector

Input switch:
`Apply Structural Regularization = OFF / ON`

OFF:
- pass standard mesh downstream unchanged.

ON:
- pass only the safety-approved regularized candidate downstream.

The selector must make A/B runs reproducible and explicit in the manifest.

## Mandatory node/group Notes policy

This project now requires visible explanatory notes for every meaningful P10 node or visual node group.

Every group must include a visible workflow note containing at least:

- **Purpose** — why this node/group exists.
- **Inputs** — the authoritative information it consumes.
- **What it does** — concise algorithm/stage description.
- **Outputs** — what downstream nodes receive.
- **Authority** — whether it is diagnostic, candidate, or official geometry authority.
- **Geometry impact** — NONE / OPTIONAL / REQUIRED.
- **Default switch state** — where applicable.
- **Failure behavior** — fail closed, fallback, or retain previous official output.
- **TEMP/retention** — whether outputs are temporary or retained.
- **Next stage** — which gate/group consumes it.

The notes must be visible in the shipped Refined workflow, not only in source-code comments or external documentation.

Group titles must also identify gate/subgate, for example:
`G8.2 · Structural Regularization — Optional Polish (OFF by default)`.

This applies going forward to new P10 groups and should be backfilled onto existing P10 visual lanes during Gate 12 observability cleanup.

## Evidence used to detect hard-surface candidate regions

No single signal is allowed to decide that a surface should be regularized.

Candidate score may combine:

### 1. Planarity evidence
- local point-to-plane residual;
- normal variance;
- planar patch support;
- patch area/extent;
- multi-view depth consistency.

### 2. Sharp-edge evidence
- strong normal discontinuity;
- source image edge/line support;
- geometric boundary support;
- repeated linear crease support across views.

### 3. Structural relation evidence
- near-parallel plane pairs;
- near-orthogonal plane pairs;
- near-coplanar patches;
- repeated offsets/thickness;
- shared principal directions.

### 4. Soft symmetry/proportionality evidence
- paired patches approximately mirrored around a detected local axis;
- repeated architectural modules;
- similar offsets/lengths around a doorway/window/covering structure.

Symmetry/proportion is always a **soft candidate constraint**, never a hard assumption.

### 5. Protection/rejection evidence
- original-source visibility;
- HIGH geometry confidence;
- CONFIRMED_FREE intersections;
- CONFLICT regions;
- semantic/instance boundaries where available;
- original-camera reprojection/silhouette guard.

## Structural relation hierarchy

Apply from safest to most speculative:

1. local planarization;
2. crease/sharp-edge recovery;
3. parallelism;
4. orthogonality;
5. coplanarity/alignment;
6. repeated thickness/offset consistency;
7. soft symmetry/proportionality.

Later items require stronger evidence and stricter original-view validation.

## Tooling plan

### Required first-pass geometry toolkit: Open3D

Use in an isolated ConceptGhost geometry runtime.

Primary uses:
- point-cloud/mesh sampling;
- RANSAC plane segmentation;
- robust planar patch detection;
- normals/neighborhood support;
- geometric diagnostics.

Open3D is preferred for first-pass detection because it exposes both RANSAC plane segmentation and robust planar-patch detection and is straightforward to automate from Python.

### Native ConceptGhost constraint solver

Do not require CGAL initially.

Implement the first production regularizer with NumPy/SciPy-style linear algebra / bounded least-squares:
- plane normal targets;
- parallel/orthogonal constraints;
- plane offset constraints;
- vertex-to-plane penalties;
- source reprojection penalties;
- confidence/free-space locks;
- displacement regularization.

This keeps the core behavior inspectable and avoids adding a heavy compiled C++ dependency to the normal Windows installer.

### Optional source-image line evidence: OpenCV headless

Use conservative 2D edges/line segments to support, not dictate, hard-surface creases.

Potential operations:
- Canny/gradient edge confidence;
- line-segment/Hough support;
- alignment of projected candidate creases to source-image line evidence.

This is advisory evidence only.

### CGAL: optional validation/reference path

CGAL Shape Regularization supports plane parallelism, orthogonality, coplanarity and axis symmetry.

Do not make CGAL a required dependency in the first implementation.

Possible later use:
- compiled isolated helper binary;
- A/B comparison against native regularizer;
- validation of plane-relationship clustering.

Promote only if it provides measurable quality benefit worth the Windows packaging complexity.

## Installation architecture

Do not modify the protected shared ComfyUI Python environment.

Create a new isolated runtime:

`%LOCALAPPDATA%\ConceptGhost\GeometryRegularizationRuntime-v1`

Recommended runtime:
- isolated CPython 3.11 x64;
- Open3D pinned after Windows/RTX compatibility test;
- NumPy/SciPy pinned inside the isolated runtime;
- OpenCV headless pinned if source-line evidence is enabled;
- no mutation of `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`;
- no mutation of protected shared ComfyUI packages.

Installer files planned:
- `Scripts/install_geometry_regularization_runtime.ps1`;
- `Scripts/verify_geometry_regularization_runtime.ps1`;
- root installer invokes them through the existing `03_INSTALL_ALL.bat`;
- `04_VERIFY_INSTALL.bat` verifies imports/versions and runs a tiny plane-fit smoke test.

The installer should:
1. discover/reuse an exact valid runtime;
2. download/install only missing or invalid components;
3. verify package versions/hashes where feasible;
4. keep install logs under ConceptGhost runtime logs;
5. fail without damaging the existing ComfyUI/MoGe runtime;
6. support uninstall/repair independently.

Exact package versions are frozen only after compatibility testing; the architecture must not pin an unverified wheel version prematurely.

## New/extended code modules

New modules proposed:
- `p10_lab/structural_analysis.py`
  Candidate region scoring and planar/crease/relationship detection.

- `p10_lab/planar_patch_adapter.py`
  Isolated runtime adapter for Open3D plane/patch detection.

- `p10_lab/structural_constraints.py`
  Plane groups, parallelism, orthogonality, coplanarity, repeated offset and soft symmetry constraints.

- `p10_lab/structural_optimizer.py`
  Bounded local vertex/patch optimizer with confidence/source/free-space locks.

- `p10_lab/structural_remesh.py`
  Local topology cleanup / crease recovery where vertex projection alone is insufficient.

- `p10_lab/structural_preview.py`
  Temporary 3D impact/candidate proxy and visualization manifest.

- `p10_lab/structural_regression.py`
  Before/after source-camera and geometry metrics.

Existing modules likely extended:
- Gate 7 fusion output adapter;
- Gate 8 defect analysis;
- preview nodes;
- workflow integration;
- reconstruction/runtime manifest plumbing;
- Gate 9 original-view regression.

## Candidate optimization objective

For a bounded candidate region, minimize a weighted objective conceptually containing:

```text
E =
  w_shape      * displacement_from_input
+ w_plane      * point_to_regularized_plane
+ w_parallel   * parallel_relation_error
+ w_orthogonal * orthogonality_error
+ w_coplanar   * coplanarity_error
+ w_offset     * repeated_offset_error
+ w_symmetry   * soft_symmetry_error
+ w_reproject  * original_camera_reprojection_error
+ w_edge       * projected_source_edge_misalignment
+ hard/large penalties for protected confidence + free-space violations
```

Weights vary by evidence strength.

The solver is local, bounded and reversible. No full-scene global architectural straightening.

## Original-camera preservation guard

Every candidate region is reprojected through the authoritative source camera before promotion.

Reject/revert a regional edit when it materially worsens:
- source silhouette;
- source-facing edge alignment;
- protected observed-region reprojection;
- foreground/background ordering.

Initial A/B target may use sub-pixel to ~1 px tolerances in protected areas, but exact thresholds are tuned against real ConceptGhost fixtures before being frozen.

Key principle:
**a 3D cleanup is not an improvement if the reference camera becomes visibly worse.**

## Confidence-aware deformation budget

Per-region movement allowance depends on geometry confidence:

- HIGH: locked or near-zero displacement.
- NEUTRAL: small planar/sharpness correction only.
- LOW: larger bounded structural correction if multiview support exists.
- VERY_LOW: eligible for local remesh/replacement only when Gate 7/8 evidence supports it.

Confidence never alone proves that a regularized shape is correct.

## Free-space-aware guard

Before moving/remeshing candidate geometry:
- test the proposed surface against CONFIRMED_FREE;
- reject an extrusion/bridge that seals an observed opening;
- preserve UNKNOWN as uncertain, not as forced empty space;
- forward CONFLICT to conservative handling.

This is critical for overhangs, railings, canopies, doorways and table-like structures.

## Planarity and sharpness strategy

### Planarization
For a strong planar patch:
- fit robust plane;
- identify protected anchor vertices;
- project only eligible vertices toward the plane;
- use falloff near patch boundaries;
- preserve source-facing silhouette anchors.

### Sharp-edge recovery
Where two reliable planar patches meet:
- estimate their plane intersection line;
- identify the current soft transition;
- move/remesh only eligible transition vertices toward a crisp crease;
- preserve UV recovery for Gate 8.3/8.4.

Do not sharpen organic/foliage regions merely because local normals vary.

## Parallelism / orthogonality

Detect plane relationships only inside spatially/semantically/local-context related groups.

Examples:
- two sides of one architectural canopy;
- wall vs underside plane;
- repeated facade elements.

Do not make every wall in the scene globally parallel.

Use angular tolerance + local adjacency/proximity + source evidence.

## Soft symmetry / proportionality

Symmetry is the riskiest regularity and must be last.

Candidate symmetry requires:
- a plausible local axis;
- corresponding structural patches;
- similar source appearance / projected endpoints;
- no conflict with original source;
- no free-space violation;
- adequate confidence/multiview support.

The regularizer may reduce an accidental asymmetry caused by reconstruction, but it may not invent symmetry simply because architecture often looks symmetric.

## Affected-region 3D map

The impact map must be generated even with `Apply Structural Regularization = OFF`.

Per-face/vertex labels:
- UNAFFECTED;
- PROTECTED;
- CANDIDATE;
- WOULD_MOVE;
- WOULD_REMESH;
- REJECTED_SOURCE_GUARD;
- REJECTED_FREE_SPACE;
- CONFLICT.

The viewer should also expose, when practical:
- maximum predicted displacement;
- median predicted displacement;
- affected face count/area;
- detected plane IDs;
- relation types;
- reason each region is eligible/rejected.

## A/B comparison contract

Every run can preserve two candidate references:

A — Standard Gate 8 mesh.
B — Structural-regularized candidate.

When switch OFF:
- A is official;
- B remains diagnostic/temp.

When switch ON and guards pass:
- B becomes selected downstream mesh;
- A remains available for regression/diagnostics until final validation.

Metrics:
- source-camera reprojection;
- silhouette/edge delta;
- planar residual before/after;
- normal variance before/after;
- parallel/orthogonal relation error;
- vertex displacement;
- triangle/mesh health;
- FREE-space violations (must be zero in strong free regions);
- changed surface area;
- runtime/storage.

## ComfyUI workflow Notes standard for this group

Visible note text should explain, in plain language:

**G8.2 Structural Regularization Analysis**
“Finds man-made regions that appear planar/sharp/parallel/orthogonal or locally symmetric. Diagnostic only. Does not change official geometry.”

**G8.2 Structural Candidate**
“Builds a bounded cleanup candidate. Source-facing/high-confidence surfaces and confirmed free-space are protected.”

**G8.2 Structural 3D Preview**
“Shows where the candidate would change geometry even when Apply Structural Regularization is OFF.”

**G8.2 Structural Selector**
“OFF passes the existing Gate 8 mesh unchanged. ON uses only safety-approved regularized regions.”

## Internal implementation steps

### HS-1 — Runtime + dependency proof
- isolated geometry runtime;
- Open3D import/plane-fit smoke;
- optional OpenCV line-evidence smoke;
- no shared Comfy mutation.

### HS-2 — Structural analysis contract
- input/output schemas;
- per-region IDs;
- provenance;
- deterministic candidate scoring.

### HS-3 — Planar patch detector
- RANSAC / robust planar patches;
- local normal/residual metrics;
- bounded candidate regions.

### HS-4 — Sharp-edge/crease detector
- plane intersections;
- source-image edge support;
- geometric boundary support.

### HS-5 — Structural relation graph
- parallel;
- orthogonal;
- coplanar;
- repeated offsets;
- soft symmetry candidate relationships.

### HS-6 — Protected-region policy
- confidence locks;
- source-camera anchors;
- free-space constraints;
- conflict handling.

### HS-7 — Candidate optimizer/remesher
- bounded local solve;
- region falloff;
- crease recovery;
- no global scene warp.

### HS-8 — Original-view candidate regression
- reproject candidate;
- reject unsafe regions individually;
- record reason codes.

### HS-9 — 3D impact/candidate preview
- always available;
- OFF still shows affected map;
- Standard/Candidate/Difference display.

### HS-10 — ON/OFF selector + provenance
- deterministic switch;
- standard path byte/geometry-equivalent when OFF where practical;
- explicit selected-output provenance.

### HS-11 — A/B fixture matrix
Test:
- concrete canopy/door overhang;
- rectangular facade block;
- repeated windows/columns;
- intentionally asymmetric stylized architecture;
- curved/organic control object;
- railing/fence with FREE-space constraints;
- source-visible sharp edge;
- low-confidence side/back deformation.

### HS-12 — RTX/storage/performance validation
- 7-route final-quality geometry where available;
- measure CPU/RAM/VRAM/runtime;
- verify TEMP cleanup;
- compact diagnostic package.

### HS-13 — Promotion decision
- compare OFF vs ON across fixtures;
- keep OFF as release default until repeated gains are proven;
- never silently change default.

## Gate 8.2 acceptance criteria

Analysis/preview acceptance:
- candidate regions are explainable;
- protected/source regions are visibly distinguished;
- impact viewer works with application OFF;
- no official geometry change when OFF.

Refinement acceptance:
- planar residual improves where expected;
- accidental rounding is reduced on hard-surface fixtures;
- sharp edges improve without source-camera regression;
- parallel/orthogonal relationships improve only where supported;
- symmetry corrections remain conservative;
- confirmed free-space is never sealed;
- organic/stylized controls are not globally straightened;
- failure reverts affected region rather than corrupting full mesh;
- standard OFF path remains available.

## TEMP / retention

Use:
`<ComfyUI output>/conceptghost/_temp/<run_id>/structural_regularization/`

Suggested subfolders:
- analysis/
- candidate/
- previews/
- regression/
- manifests/

Keep permanently only compact diagnostics when useful.

Heavy candidate meshes/intermediate patch data are cleanup-eligible after final downstream validation.

Failure/cancel retains the workspace under existing preserve-on-failure policy.

## Maya policy

No structural-analysis colors, preview materials or diagnostic groups are required in Maya.

Only the selected final geometry reaches the normal Maya export path.

The diagnostic map remains a ComfyUI/run-time visualization.

## Scheduling rule

Do not implement this before the required Gate 7 registration/fusion path and Gate 8.1 defect analysis are functional.

Implementation order:
Gate 7 complete enough for stable fused geometry
→ Gate 8.1 defect regions
→ Gate 8.2 HS analysis/preview
→ candidate optimizer
→ OFF/ON selector
→ Gate 8.3/8.4 UV/texture recovery
→ Gate 9 source regression
→ later Gate 12 diagnostic standardization.

The required roadmap subgate count remains unchanged. HS-1..HS-13 are bounded internal steps inside Gate 8.2.

## Technical reference rationale

Open3D is the first-pass detector for planar geometry.
CGAL Shape Regularization is retained as a technical reference/optional validation path for plane parallelism, orthogonality, coplanarity and axis symmetry.
The production first pass should prefer an isolated Python-native implementation to keep installation automatic and reversible.
