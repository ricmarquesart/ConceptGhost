# ConceptGhost — Free-Space / Visibility Carving Policy

Status: PLANNED — Gate 7.3 integration, generated from Gate 6 dense evidence.
Purpose: distinguish true observed empty space from unknown/disoccluded regions so later meshing/fusion does not seal legitimate openings such as table-leg gaps, fences, arches, railings, door openings or visible foliage gaps.

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
