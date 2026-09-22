# ConceptGhost — Free-Space / Visibility Carving Policy

Status: PLANNED — Gate 7.3 integration, generated from Gate 6 dense evidence.
Purpose: distinguish true observed empty space from unknown/disoccluded regions so later meshing/fusion does not seal legitimate openings such as table-leg gaps, fences, arches, railings, door openings or visible foliage gaps.

## Why this structure is required

The P10 pipeline must distinguish a **true opening** from a **missing reconstruction**.

Examples:
- the gap between table legs is valid empty space and must remain open;
- a fence or railing contains repeated valid openings;
- the center of an arch or doorway is valid empty space;
- a missing back wall caused by disocclusion is UNKNOWN and may require generation/reconstruction;
- a false Poisson bridge across an observed opening is an invalid surface, not a hole to fill.

Without explicit free-space evidence, downstream meshing can confuse these cases because a surface reconstructor usually receives points/surfaces but does not automatically retain every empty ray volume that produced them.

The design therefore treats **empty space as first-class evidence** rather than as the absence of geometry.

This is intentionally geometric rather than semantic. The system does not need to know that an object is a table, chair, fence, arch or tree. It only needs to know whether multiple cameras can see through a region to a farther supported surface.

## Architectural principle

P10 will track two complementary kinds of evidence:

1. **Surface evidence** — where reliable geometry is observed.
2. **Visibility/free-space evidence** — where camera rays were observed to travel before reaching a reliable surface.

The combination allows the fusion stage to distinguish:
- “there should be a surface here”;
- “there must NOT be a surface here”;
- “we do not know yet”;
- “our evidence disagrees”.

The free-space field is therefore a constraint layer for fusion/topology, not a replacement for P9, COLMAP, Poisson, WAN or the geometry-confidence layer.

## Full insertion point in the P10 roadmap

Primary implementation home: **Gate 7.3 — Narrow Transition Geometry Handling**.

Supporting producer/consumer hooks:
- **Gate 6.4** produces depth/normal/consistency evidence.
- **Gate 6.5** adds the Delaunay visibility-aware mesh candidate alongside Poisson.
- **Gate 7.2C** consumes free-space conflict as one input to geometry confidence.
- **Gate 7.3** is the main authority point where CONFIRMED_FREE becomes a no-fill/no-bridge constraint.
- **Gate 8.1/8.2** uses FREE/UNKNOWN/CONFLICT to classify and repair defects safely.
- **Gate 11** may use UNKNOWN/CONFLICT for targeted route spending after the first complete result.
- **Gate 12** owns standardized visualization, diagnostics and retained evidence.

Important scheduling rule:
- current completed Gate 6.4/6.5 work is **not reopened as a blocker**;
- the new producer extensions are implemented when Gate 7 work begins, using the already-created Gate 6 dense workspace;
- first end-to-end progress remains protected.

## End-to-end data flow

```text
P9 authoritative geometry + source image
        |
Gate 4 exact virtual cameras
        |
Gate 5 source-preserved / WAN-completed views
        |
Gate 6 known-camera COLMAP
        |
        +--> geometric depth maps
        +--> normal maps
        +--> consistency graphs
        +--> sparse/dense points
        |
        +--> Poisson mesh candidate
        +--> Delaunay visibility-aware mesh candidate
        |
        +--> Free-Space Evidence Builder
                |
                +--> FREE votes
                +--> OCCUPIED votes
                +--> UNKNOWN
                +--> CONFLICT
                |
Gate 7.2C Geometry Confidence
        |
Gate 7.3 Free-Space-Aware Fusion
        |
Gate 8 bounded repair / local remesh
        |
Gate 9 original-view regression
        |
final Maya/export
```

## Core decision

Do not solve this primarily with semantic object recognition.

Use geometric visibility evidence from known cameras + per-view depth:
- if a camera ray reaches a valid surface at depth D, the segment from the camera to just before D is observed free space;
- a narrow band around D is occupied/surface evidence;
- space behind D remains unknown;
- no valid depth => UNKNOWN, never FREE by assumption.

Represent four states:
- OCCUPIED
- FREE
- UNKNOWN
- CONFLICT

## Existing ConceptGhost inputs

Gate 4/6 already provide:
- exact P9-derived per-frame PINHOLE camera poses/intrinsics;
- source-preserved drone images;
- COLMAP dense workspace;
- geometric PatchMatch depth maps / normal maps;
- geometric consistency graphs;
- fused dense cloud.

No new generative model is required for first implementation.

## Two-layer implementation

### Layer A — COLMAP visibility-aware meshing branch

Keep the current Poisson mesh for smoothness, but add a second mesh candidate using COLMAP Delaunay meshing from the existing dense workspace.

Reason:
- Poisson can bridge/close holes;
- COLMAP Delaunay meshing uses visibility voting/graph-cut and is therefore a useful free-space-aware structural candidate.

Artifacts:
- dense/pre_fusion_mesh_poisson.ply
- dense/pre_fusion_mesh_delaunay.ply
- dense/free_space_meshing_comparison.json
- lightweight three-view comparison preview.

Delaunay is evidence/constraint, not automatic final authority.

### Layer B — Explicit sparse free-space field

Create a ConceptGhost-native sparse visibility volume.

Suggested module:
Experimental/P10_Lab/p10_lab/free_space_evidence.py

Inputs:
- Gate 6 camera manifest;
- COLMAP undistorted camera model;
- dense/stereo/depth_maps/*.geometric.bin;
- dense/stereo/consistency_graphs/*.geometric.bin;
- Scene Contract / canonical transform.

For every selected valid depth pixel:
1. Camera origin C.
2. Ray direction R from exact camera intrinsics/extrinsics.
3. Surface endpoint P = C + depth * R.
4. Mark voxels before P - surface_margin as FREE evidence.
5. Mark a narrow band around P as OCCUPIED evidence.
6. Never mark voxels behind P as free.
7. Invalid/no-depth pixels contribute UNKNOWN only.

Accumulate per sparse voxel:
- free_vote_count;
- occupied_vote_count;
- contributing_frame_ids;
- contributing_route_ids;
- angular diversity;
- source type/provenance;
- consistency support.

## Independence policy

Adjacent frames from the same drone are correlated and must not count as fully independent votes.

First policy:
- require evidence across at least 2 separated camera viewpoints or route families for CONFIRMED_FREE;
- enforce a minimum angular/baseline diversity;
- use COLMAP consistency-graph support to reject weak depth pixels;
- cap repeated votes from neighboring frames of the same route.

For the initial 7-route / 30-frame target, route diversity matters more than raw frame count.

## Proposed state logic

Thresholds are implementation defaults subject to A/B tuning.

CONFIRMED_FREE:
- free evidence from >=3 selected views;
- >=2 independent route/view groups;
- adequate baseline/view-angle diversity;
- strong free/(free+occupied) ratio;
- no strong source-authority contradiction.

OCCUPIED:
- stable surface-depth evidence from >=2 views or protected P9 source surface.

UNKNOWN:
- insufficient valid depth / visibility evidence.

CONFLICT:
- meaningful FREE and OCCUPIED evidence coexist.
- never hard-carve automatically;
- route to geometry-confidence layer / Gate 8 repair analysis.

## Authority weighting

Do not treat all observations equally.

Suggested provenance tiers:
1. protected original-source/P9 observed surface: highest authority;
2. source-authority HiRes Composite pixels / reprojected known source: high;
3. P10 multiview geometry with strong COLMAP consistency: medium-high;
4. WAN-only generated regions: lower;
5. single-view or low-consistency generated depth: diagnostic only.

Free-space evidence from generated views is therefore probabilistic, not ground truth.

## Gate placement

### Gate 6.4 producer extension

After PatchMatch depth/normal generation and before/alongside stereo fusion:
- preserve geometric depth maps and consistency graphs as explicit evidence;
- optionally generate the sparse free-space field;
- record free_space_manifest.json.

Do not block current Gate 6 runtime path until Gate 7 implementation starts.

### Gate 6.5 meshing extension

Run both:
- current Poisson mesh;
- new Delaunay visibility-voting mesh.

Do not replace Poisson automatically.

### Gate 7.2C confidence integration

Feed FREE/UNKNOWN/CONFLICT classification into the existing geometry-confidence field:
- confirmed free-space conflict lowers confidence of a surface that occupies that volume;
- UNKNOWN does not lower confidence solely because it is unknown;
- CONFLICT remains diagnostic/repair candidate.

### Gate 7.3 — Free-Space-Aware Transition Geometry

This is the main consumer.

Before final P9/P10 fusion:
- reject or mark candidate faces that occupy CONFIRMED_FREE volume;
- preserve legitimate holes/openings;
- never fill UNKNOWN simply because it lacks geometry;
- do not carve protected original-camera HIGH-confidence surfaces;
- CONFLICT regions remain bounded candidates for Gate 8, not destructive edits.

### Gate 8.1/8.2

Defect analysis distinguishes:
- MISSING_SURFACE_UNKNOWN
- FALSE_SURFACE_IN_CONFIRMED_FREE
- CONFLICT_REGION
- VALID_OPENING

Local remesh/cleanup must honor CONFIRMED_FREE as a no-fill constraint unless stronger evidence explicitly reverses it.

### Gate 11

Adaptive drone planning may prioritize UNKNOWN/CONFLICT regions where an extra camera could convert uncertainty into FREE or OCCUPIED evidence.

### Gate 12

Add a dedicated ComfyUI 3D diagnostic preview:
P10 · Free-Space 3D Preview

Suggested display:
- FREE = cyan/green translucent volume or points;
- OCCUPIED/surface = neutral/white;
- UNKNOWN = hidden;
- CONFLICT = magenta/yellow.

This preview is diagnostic-only and not exported to Maya.

## Required components

### Existing components reused

No new generative model is required for the first implementation.

Reuse:
- ConceptGhost authoritative camera manifest;
- ConceptGhost Scene Contract;
- Gate 5 source-preserved composite frames;
- COLMAP 4.2.0 CUDA runtime already required by Gate 6;
- COLMAP PatchMatch geometric depth maps;
- COLMAP normal maps;
- COLMAP consistency graphs;
- COLMAP sparse/dense reconstruction;
- current Poisson mesher;
- current Gate 7 geometry-confidence plan;
- current TEMP workspace / auto-clean policy.

### New ConceptGhost-native components

1. **COLMAP dense evidence reader**
   - proposed file: `p10_lab/colmap_dense_io.py`;
   - reads `*.geometric.bin` depth maps, normal maps and consistency graphs;
   - validates image identity, dimensions, camera mapping and Scene Contract;
   - converts COLMAP camera/depth convention into ConceptGhost canonical world coordinates.

2. **Free-space evidence builder**
   - proposed file: `p10_lab/free_space_evidence.py`;
   - performs ray traversal from camera to supported depth;
   - accumulates sparse FREE/OCCUPIED evidence;
   - records route/view provenance and angle diversity.

3. **Free-space state classifier**
   - proposed file: `p10_lab/free_space_constraints.py`;
   - converts raw votes into CONFIRMED_FREE / OCCUPIED / UNKNOWN / CONFLICT;
   - applies source-authority protection and conservative thresholds;
   - exposes no-fill constraints to Gate 7.3.

4. **Delaunay mesher adapter**
   - extend `p10_lab/prefusion_mesh.py`;
   - invoke COLMAP `delaunay_mesher` from the same dense workspace;
   - retain both Poisson and Delaunay outputs for comparison/fusion evidence.

5. **Free-space 3D preview**
   - proposed file: `p10_lab/free_space_preview.py`;
   - creates a lightweight temporary colored proxy / point-volume representation;
   - surfaced through a dedicated ComfyUI node;
   - never exported to Maya.

6. **Runtime/checkpoint integration**
   - extend `reconstruction_runtime.py`, `preview_nodes.py`, `workflow_integration.py`;
   - support resumable free-space stage manifests;
   - avoid rerunning WAN/COLMAP upstream work when valid checkpoints exist.

### Optional future component

Open3D TSDF/VoxelBlockGrid may be evaluated later if it materially improves sparse volumetric fusion or implementation simplicity.

It is **not required** for the first implementation and must not become a dependency without an A/B justification.

## Exact ray-carving logic

For a selected geometrically-consistent depth sample:

```text
C = camera center
R = world-space ray direction
D = reliable first-surface depth
P = C + D * R
```

Apply:

```text
[C, P - surface_margin]  -> FREE evidence
[P - band, P + band]     -> OCCUPIED evidence
behind P                 -> UNKNOWN from this observation
invalid/no depth         -> UNKNOWN
```

Critical rule: a camera ray never claims that volume behind its first reliable surface is free.

The surface margin prevents numerical noise from carving the actual surface.

## Vote and independence model

Raw frame count must not dominate the decision.

Each evidence sample stores:
- frame ID;
- route/drone ID;
- camera center;
- viewing direction;
- depth consistency support;
- source provenance;
- confidence weight.

Frames are grouped so that adjacent frames from the same route do not behave like independent cameras.

Initial conservative aggregation:
- cap repeated contributions from neighboring frames;
- require >=2 independent route/view groups for confirmed free-space;
- prefer >=3 selected supporting views;
- require minimum parallax / angular diversity;
- reject low-consistency depth observations;
- protect source-observed surfaces even if generated views disagree.

The exact numeric thresholds remain implementation-tunable, but the independence requirement is architectural and must remain.

## Proposed evidence weights

Suggested initial conceptual order:

```text
P9/source observed surface                  weight 1.00
HiRes source-authority reprojection         weight 0.90
P10 COLMAP geometric support                weight 0.65-0.85
WAN-only generated multiview evidence       weight 0.35-0.60
single-view / low-consistency evidence      <=0.25 diagnostic only
```

These are initial implementation weights, not hard physical probabilities.

The rule that matters is monotonic authority: generated content cannot overrule strong original-source evidence on its own.

## Free-space state machine

Each sparse cell/block resolves to one of four primary states:

### OCCUPIED
Stable supported surface exists.

Typical evidence:
- protected P9/source surface;
- consistent P10 depth endpoint support;
- multiple views agreeing on a surface.

### CONFIRMED_FREE
Multiple independent camera rays pass through the volume to a farther supported surface, with no stronger occupied contradiction.

This becomes a Gate 7.3 **NO_FILL** constraint.

### UNKNOWN
Insufficient evidence.

UNKNOWN must remain editable/reconstructable. It is not a no-fill region and it is not automatically a hole that must be filled.

### CONFLICT
Substantial FREE and OCCUPIED evidence coexist.

CONFLICT is fail-safe:
- never auto-delete;
- never auto-fill merely because one branch wins weakly;
- lower geometry confidence;
- forward to Gate 8 defect analysis / possible extra drone coverage.

## Relationship with physical holes and confidence virtual holes

Three concepts remain separate:

1. **Physical hole**
   - no current surface exists.

2. **Confidence virtual hole**
   - a surface exists but confidence is very low and it may be eligible for replacement.

3. **Confirmed free space**
   - evidence says a surface should NOT exist in this volume.

This separation prevents a valid table-leg gap from being interpreted as a missing surface.

## Meshing policy: Poisson + Delaunay, not Poisson vs Delaunay

The final design should not blindly replace Poisson.

Poisson strengths:
- smooth surface reconstruction;
- good closure where surface evidence is continuous;
- useful final-quality candidate.

Poisson risk:
- can bridge/close sparse openings or holes.

Delaunay strengths:
- uses visibility information and graph-cut/voting;
- useful structural evidence for openings and free-space boundaries.

Delaunay risk:
- may be noisier / less smooth and should not automatically become the final mesh.

Policy:
- produce both;
- compare them against explicit FREE/OCCUPIED evidence;
- Gate 7 fusion decides which local surface is admissible;
- CONFIRMED_FREE vetoes any candidate surface occupying that volume unless stronger protected evidence proves otherwise.

## Gate 7.2C confidence coupling

Free-space does not replace the confidence system.

It adds strong evidence:

- a P9/P10 face crossing CONFIRMED_FREE -> confidence sharply reduced;
- face supported by original source -> protected/high;
- face in UNKNOWN -> no penalty solely for being unknown;
- face in CONFLICT -> mark low/uncertain, not auto-remove;
- face supported consistently across independent routes -> confidence raised.

The dedicated Confidence 3D Preview and the Free-Space 3D Preview remain separate diagnostic views because one displays **belief in surfaces** while the other displays **belief about empty volume**.

## Gate 7.3 fusion rules

Before accepting a candidate triangle/patch:

1. Test whether it intersects protected source-authority geometry.
2. Test whether it enters CONFIRMED_FREE.
3. Test local P9/P10 confidence/provenance.
4. Compare Poisson and Delaunay candidate support.
5. Keep/open/replace the region according to evidence.

Rules:
- protected HIGH source geometry wins;
- CONFIRMED_FREE rejects generated bridges/walls;
- UNKNOWN may be filled only by supported reconstruction/repair evidence;
- CONFLICT is preserved as unresolved or sent to bounded Gate 8 repair;
- no global destructive carving.

## Gate 8 defect taxonomy

Add explicit defect labels:

- `VALID_OPENING`
- `FALSE_SURFACE_IN_CONFIRMED_FREE`
- `MISSING_SURFACE_UNKNOWN`
- `LOW_CONFIDENCE_SURFACE`
- `CONFLICT_REGION`
- `SUPPORTED_SURFACE`

Gate 8.2 local remesh must honor FREE cells as hard/near-hard exclusion constraints depending on provenance strength.

## ComfyUI user-facing diagnostics

Add a dedicated node:

`P10 · Free-Space 3D Preview`

Default visualization proposal:
- FREE / CONFIRMED_FREE = cyan or green translucent samples/volume;
- OCCUPIED = neutral/white surface;
- CONFLICT = magenta/yellow;
- UNKNOWN = hidden.

Node requirements:
- orbit/zoom/pan 3D inspection;
- show current counts/volume percentages;
- show contributing routes/views for a selected region when practical;
- expose manifest/temp-path for diagnostics;
- diagnostic only;
- no Maya data pollution.

The confidence viewer stays separate:
- confidence answers: “how much do we trust this surface?”;
- free-space viewer answers: “where do cameras provide evidence that no surface should exist?”.

## TEMP workspace and cleanup

Recommended run layout:

```text
<ComfyUI output>/conceptghost/_temp/<run_id>/free_space/
    evidence/
    sparse_volume/
    previews/
    delaunay/
    manifests/
```

Keep:
- compact manifest;
- summary metrics;
- lightweight preview(s) in the retained diagnostic package when useful.

Auto-clean:
- delete heavy sparse volume / temporary Delaunay intermediates after successful downstream validation;
- retain everything on failure/cancel according to existing preserve-on-failure policy.

## Runtime and memory strategy

Target hardware remains RTX 2080 Ti 11 GB.

Requirements:
- never construct a dense full-world 3D array at render resolution;
- use sparse/hash/chunked cells;
- sequentially process cameras;
- downsample depth rays for the first pass;
- allow a refinement pass only near candidate openings/conflicts;
- CPU processing is acceptable for ray voting when it avoids VRAM pressure;
- reuse COLMAP outputs instead of recomputing depth.

First target:
- approximately 256-384 sparse cells across the useful scene span;
- adaptive/sparse occupancy rather than fixed dense cube;
- confidence/free-space resolution independent from final mesh triangle density.

## Failure and recovery behavior

Each stage writes a manifest and checkpoint.

Suggested states:
- NOT_STARTED
- BUILDING_EVIDENCE
- EVIDENCE_READY
- CLASSIFIED
- DELAUNAY_READY
- CONSTRAINTS_READY
- PREVIEW_READY
- FAILED_RETAINED

If the free-space stage fails:
- do not corrupt or overwrite the proven Poisson result;
- do not modify P9;
- retain diagnostic workspace;
- allow standard Gate 7 path to remain available until free-space mode is proven.

## Implementation sequence

### FS-1 — Dense evidence contract
- implement `colmap_dense_io.py`;
- validate depth/normal/consistency file parsing;
- bind every map to exact camera/frame identity;
- tests for axes/depth convention.

### FS-2 — Ray evidence accumulator
- implement sparse ray traversal;
- FREE before surface, OCCUPIED around endpoint, UNKNOWN behind;
- route/view provenance;
- sequential/chunked execution.

### FS-3 — Independence and classification
- frame clustering / route diversity;
- confidence weighting;
- FREE/OCCUPIED/UNKNOWN/CONFLICT classifier;
- manifest/histograms.

### FS-4 — Delaunay branch
- integrate COLMAP `delaunay_mesher`;
- keep Poisson untouched;
- generate comparison metrics/previews.

### FS-5 — Gate 7.2C confidence coupling
- surface/free-space contradiction score;
- no geometry edits yet;
- verify confidence visualization.

### FS-6 — Gate 7.3 no-fill enforcement
- face/patch intersection against free-space constraints;
- reject false bridge surfaces;
- preserve source-authority locks;
- forward conflicts to Gate 8.

### FS-7 — ComfyUI 3D preview
- interactive diagnostic proxy;
- FREE/OCCUPIED/CONFLICT display;
- TEMP path and manifest visibility.

### FS-8 — A/B validation fixtures
Test at minimum:
- four-leg table/open underside;
- picket fence / railing;
- arch/door opening;
- chair structure;
- foliage/tree canopy;
- solid wall control scene where no opening should be created.

### FS-9 — Hardware/storage validation
- 7 routes x 30 frames target;
- RTX 2080 Ti 11 GB;
- record runtime, peak RAM/VRAM, sparse volume size, TEMP peak disk use.

### FS-10 — Promotion decision
- compare free-space OFF vs ON;
- require no original-camera regression;
- promote no-fill constraints only after repeatable benefit.

## Acceptance criteria

The feature is accepted when:
- true observed openings remain open;
- FALSE_SURFACE_IN_CONFIRMED_FREE bridges are reduced materially;
- protected source-facing geometry is unchanged;
- UNKNOWN is not accidentally carved;
- foliage/conflict regions fail conservatively;
- output remains resumable;
- runtime fits hardware target;
- diagnostics make failures traceable;
- free-space OFF path remains available during rollout.

## Files / code paths

Existing files to extend:
- p10_lab/dense_reconstruction.py
- p10_lab/prefusion_mesh.py
- p10_lab/reconstruction_runtime.py
- p10_lab/preview_nodes.py
- p10_lab/workflow_integration.py

New proposed modules:
- p10_lab/free_space_evidence.py
- p10_lab/free_space_constraints.py
- p10_lab/free_space_preview.py

Potential future helper:
- p10_lab/colmap_dense_io.py
  Reads COLMAP geometric depth maps and consistency graphs in one tested place.

## Storage

Use sparse voxel/block storage; never allocate one giant dense world grid.

Store under TEMP workspace:
<ComfyUI output>/conceptghost/_temp/<run_id>/free_space/

Suggested:
- free_space_volume.npz or chunked sparse representation;
- free_space_manifest.json;
- free_space_preview.ply (temporary);
- comparison previews.

Auto-clean follows the existing TEMP lifecycle.

## Resolution / hardware policy

Start with conservative occupancy resolution independent of render pixels.

Suggested first pass:
- derive voxel size from scene scale / robust median depth;
- target roughly 256–384 cells across the useful scene span, sparse/hashed rather than dense;
- downsample depth evidence for ray traversal;
- use only geometrically consistent depth pixels;
- process views sequentially/chunked for RTX 2080 Ti 11 GB.

If Open3D is later useful for a TSDF/VoxelBlockGrid implementation, treat it as an optional implementation dependency, not required for the first native prototype.

## Acceptance examples

TABLE:
- rays through the gap hit floor/background behind;
- multiple independent views mark the gap FREE;
- any Poisson face sealing that gap becomes FALSE_SURFACE_IN_CONFIRMED_FREE;
- Gate 7.3 removes/rejects that face while preserving legs/tops that are OCCUPIED.

FENCE:
- repeated rays pass through openings to background;
- openings become FREE corridors;
- mesher is prevented from sealing them.

ARCH:
- wall/arch is OCCUPIED;
- central opening has rays continuing to rear wall/background;
- opening becomes CONFIRMED_FREE.

TREE/FOLIAGE:
- use soft thresholds; porous foliage can generate mixed FREE/OCCUPIED evidence;
- CONFLICT rather than aggressive carving is preferred unless multi-view evidence is strong.

## Limitation

This detects observed empty space, not objective real-world truth.

If WAN consistently hallucinates a solid panel where the real table had an opening, the synthetic views can support the wrong surface. Therefore:
- generated free-space/occupied evidence must remain lower authority than source-observed evidence;
- multi-route consistency and angle diversity are mandatory;
- CONFLICT must fail safe;
- no semantic assumption like “tables have four legs” is required or trusted.

## First implementation recommendation

1. Add Delaunay mesher branch first — zero new model/download and immediate visibility-aware A/B evidence.
2. Add explicit free-space field from COLMAP geometric depth maps + known cameras.
3. Feed field into Gate 7.2C confidence.
4. Enforce CONFIRMED_FREE as a no-fill constraint in Gate 7.3.
5. Add ComfyUI Free-Space 3D Preview.
6. A/B on table/fence/arch/foliage fixtures before any default promotion.
