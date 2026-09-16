# ConceptGhost — Stage 10 Atlas Relief Mesh Design

Date: 2026-09-16
Status: APPROVED architecture for Stage 10
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ BEFORE STAGE 10 IMPLEMENTATION

This document defines the optional Atlas relief-mesh branch. Stage 10 is not part of the ConceptGhost core validity path and must never replace or invalidate the camera + Canonical Point Cloud + Maya Ghost pipeline.

Read together with:

```text
docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage9-benchmark-preset-design.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

Pinned Atlas reference:

```text
repository: mikejamesvfx/atlas-camera
commit: 9f9ff4511154769aa2f8c0bd40387278a69b0078
```

Primary upstream files:

```text
atlas_camera/core/relief_mesh.py
atlas_camera/core/mesh_repair.py
atlas_camera/core/mesh_retopo.py
atlas_camera/comfy/nodes_export.py
```

## 1. Goal

The ConceptGhost core remains:

```text
Atlas Camera
+ Canonical Point Cloud
+ Maya Ghost
```

Stage 10 adds only:

```text
OPTIONAL E1
Atlas Relief Mesh
```

Relief-mesh failure or rejection must never invalidate:
- `maya_ghost_ready`;
- the Stage 7 `SceneBundle`;
- `.usda` dense Ghost;
- canonical `.ply`;
- matched camera;
- source plate.

## 2. Reuse Atlas, do not reinvent depth-to-mesh

Atlas already implements a DCC relief path:

```text
depth
→ sample grid
→ back-project through solved camera
→ Atlas Y-up world
→ triangulate
→ tear at depth discontinuities
→ projective UVs from source pixels
```

ConceptGhost first reproduces this pinned upstream path unchanged.

Source:
https://github.com/mikejamesvfx/atlas-camera/blob/9f9ff4511154769aa2f8c0bd40387278a69b0078/atlas_camera/core/relief_mesh.py

Atlas explicitly describes the mesh as a triangulated depth map for DCC handoff, with deliberate tears at depth discontinuities so foreground silhouettes do not rubber-sheet onto the background.

## 3. Preserve native evidence before cleanup

Keep separate:

```text
A. NATIVE ATLAS RELIEF
B. DERIVED CONCEPTGHOST EXPORT VARIANTS
```

Suggested structure:

```text
meshes/
└── atlas_relief/
    ├── native/
    │   ├── atlas_relief_native.*
    │   ├── native_stats.json
    │   └── provenance.json
    ├── processed/
    │   ├── atlas_relief_processed.*
    │   └── processing_report.json
    └── evaluation/
        └── atlas_relief_evaluation.json
```

Never overwrite the native relief with repair/retopo output.

## 4. Canonical-space adapter

Atlas relief is produced in Atlas world space, but ConceptGhost must still validate conversion explicitly.

```text
Atlas ReliefMesh
→ AtlasMeshAdapter
→ ConceptGhost Canonical Scene
```

Validate:
- handedness;
- Y-up;
- camera-local forward convention;
- world transform;
- scale mode;
- origin;
- UV convention.

No exporter may hide axis fixes.

## 5. Upstream baseline parameters

At the pinned Atlas commit, `build_relief_mesh` exposes defaults including:

```text
grid_long_edge = 96
depth_edge_rel = 0.5
far_clip_percentile = 97.0
scale = 1.0
floor_clamp = -0.25
smooth_iterations = 2
max_edge_factor = 12.0
normal_edge_deg = None
```

It also exposes controls for horizon/bands/masks, sky heuristic, fill behavior, edge overhang, bevel behavior, quad coherence, and live hole/sawtooth filling.

These are baseline values, not frozen ConceptGhost presets.

## 6. Preserve projective UVs

Atlas maps vertices back to source-image pixels through projective UVs. Preserve this relationship.

For topology-changing processing:
- do not copy stale UVs;
- regenerate projective UVs from the solved camera.

Atlas already implements this in its export-only retopology path.

Source:
https://github.com/mikejamesvfx/atlas-camera/blob/9f9ff4511154769aa2f8c0bd40387278a69b0078/atlas_camera/core/mesh_retopo.py

## 7. Tears are often correct

Intentional discontinuity:

```text
foreground
████████

          gap

                 ███████ background
```

is often preferable to fake bridging:

```text
foreground
████████\
         \
          \
           ███████ background
```

Do not automatically repair every hole or open boundary.

Distinguish:
- accidental interior hole;
- intentional silhouette/depth tear.

## 8. Repair is a derived variant

Atlas contains mesh-repair logic. ConceptGhost may evaluate it, but only after preserving native output.

```text
native relief
├→ unmodified evaluation
└→ repair variant evaluation
```

Do not silently promote repaired output.

Source:
https://github.com/mikejamesvfx/atlas-camera/blob/9f9ff4511154769aa2f8c0bd40387278a69b0078/atlas_camera/core/mesh_repair.py

## 9. Retopology is export-only

Atlas's `mesh_retopo.py` explicitly separates retopology from the live relief used for projection.

The pinned module describes three guarded optional paths:
1. quad retopology via `pyinstantmeshes`;
2. quadric decimation via `fast-simplification` / `trimesh`;
3. smooth/relax via `trimesh` Taubin smoothing.

ConceptGhost preserves this rule:

```text
Atlas native relief
→ optional export cleanup
→ optional artist mesh
```

Never modify the live Atlas relief/camera solve merely to make export topology cleaner.

## 10. Dependency safety

Optional cleanup dependencies must not destabilize the protected ComfyUI environment.

Before enabling `pyinstantmeshes`, `fast-simplification`, `trimesh`, or any related package:
- inspect current package state;
- compare protected workflows;
- avoid automatic upgrades/downgrades;
- prefer additive/no-deps installation only when safe;
- stop rather than alter another working project.

If unsafe:

```text
cleanup_backend = unavailable
```

The native relief can still be evaluated.

## 11. Stage 10 comparison branches

At minimum:

```text
A. Atlas Native Relief
B. Atlas + safe Repair, if available
C. Atlas + safe Retopo/Decimation, if available
```

Each branch records:
- upstream parameters;
- repair parameters;
- retopo parameters;
- vertices;
- faces;
- UV status;
- bounding box;
- time;
- warnings;
- dependency availability.

## 12. Artist classification

Every result is classified:

```text
useful | limited | reject
```

### useful
- camera alignment is sound;
- major surfaces are useful;
- artifacts are understandable;
- it genuinely helps blockout.

### limited
- useful primarily near the solved camera;
- shows expected 2.5D limitations;
- still worth inspecting or tracing.

### reject
- geometry is misleading;
- stretched sheets or topology artifacts dominate;
- scale/orientation is wrong;
- it harms blockout decisions.

File generation alone does not imply `useful`.

## 13. Maya integration

Reuse Stage 8 hierarchy:

```text
ConceptGhost_<scene>
├── CG_CAMERAS
├── CG_SOURCE
├── CG_REFERENCE
│   └── Ghost_USD_Proxy
├── CG_OPTIONAL_MESH
│   └── Atlas_Relief
└── CG_METADATA
```

Recommended presentation:
- `useful`: include as normal optional artist asset;
- `limited`: preserve, hidden by default;
- `reject`: preserve evidence only, do not present as trusted artist geometry.

## 14. FBX behavior

If relief is `useful` (or deliberately approved), it may be included in the normal FBX companion.

Record:

```text
atlas_relief_included = true | false
atlas_relief_classification = useful | limited | reject
```

Rejected geometry must not appear in the standard FBX as if it were trusted.

## 15. Core Ghost independence

Stage 10 never replaces:

```text
maya/ConceptGhost_<scene>_Ghost.usda
geometry/canonical/pointcloud.ply
```

The point cloud remains the primary dense 3D reference.

## 16. Camera-view validation

Through `matchedCamera_LOCKED`, verify:
- silhouette;
- UV/source-image alignment;
- ground/facade placement;
- large surfaces;
- foreground/background separation.

Severe mismatch = Stage 10 integration failure.

## 17. Off-camera validation

Review small, medium, and large orbits.

Observe:
- stretching;
- deliberate tears;
- depth-sheet behavior;
- fake connections;
- wall/ground continuity;
- thin structures.

Do not reject simply because unseen back-side geometry does not exist. This branch is 2.5D by design.

## 18. Topology-health validation

Record:
- vertex count;
- face count;
- degenerate faces;
- non-finite vertices;
- invalid face indices;
- long-edge/stretched-triangle statistics;
- open boundaries where practical;
- UV validity;
- bounding box.

Compare before/after cleanup.

## 19. UV validation

Native and processed variants must retain correct source projection.

Topology-changing cleanup is not successful if it destroys projective UV behavior.

## 20. Performance validation

Record:
- file size;
- Maya load/import time;
- viewport responsiveness;
- vertex/face count;
- FBX size when included.

Highest triangle count is not a goal.

## 21. Progressive parameter study

Do not brute-force.

Recommended order:

```text
1. upstream defaults
2. grid density / grid_long_edge
3. depth-discontinuity sensitivity
4. smoothing
5. long-edge rejection
6. repair only if needed
7. retopo/decimation only if needed
```

Goal:

```text
maximum useful artist reference
with understandable artifacts
and acceptable Maya cost
```

## 22. Relationship to Stage 9 presets

Stage 10 may reuse the Stage 9 benchmark framework, but relief settings do not silently redefine DA3/MoGe core presets.

If useful, record separate optional mesh profiles later:

```text
atlas_relief.profile = native
atlas_relief.profile = cleaned
atlas_relief.profile = lightweight
```

## 23. Manifest

Suggested fields:

```text
mesh.engine = atlas_relief
mesh.source_commit = 9f9ff4511154769aa2f8c0bd40387278a69b0078
mesh.native_generated
mesh.processed_generated
mesh.repair_mode
mesh.retopology_mode
mesh.classification
mesh.maya_included
mesh.fbx_included
mesh.warnings
```

## 24. Status semantics

Core good + relief useful:

```text
maya_ghost_ready = true
atlas_relief.status = PASS
atlas_relief.classification = useful
```

Core good + relief limited:

```text
maya_ghost_ready = true
atlas_relief.status = PASS
atlas_relief.classification = limited
```

Core good + relief failed/rejected:

```text
maya_ghost_ready = true
atlas_relief.status = FAILED or GENERATED
atlas_relief.classification = reject when applicable
```

Core remains valid.

## 25. Stage 10 PASS

Stage 10 is complete when:

```text
pinned Atlas native relief reproduced
+ native evidence preserved
+ canonical conversion verified
+ camera/UV agreement verified
+ repair characterized
+ safe retopo/decimation characterized where available
+ Maya usefulness evaluated
+ useful|limited|reject contract implemented
+ optional Stage 8 handoff validated
= STAGE 10 PASS
```

Stage 10 does not require every image to produce a `useful` mesh.

## 26. Implementation priority

```text
P1 reproduce native Atlas relief
P2 preserve native provenance
P3 validate canonical-space adaptation
P4 load optional relief in Maya
P5 classify useful | limited | reject
P6 evaluate repair
P7 evaluate retopo/decimation only if safe/useful
P8 evaluate optional FBX inclusion
```

Do not begin with retopology.

## 27. One-line implementation instruction

> Reuse the pinned Atlas relief pipeline as the Stage 10 baseline, preserve the native torn/projective-UV mesh unchanged, adapt it explicitly into ConceptGhost canonical space, treat repair and export-only retopology as derived optional variants, classify the result `useful | limited | reject`, and never let optional relief failure invalidate the core camera + Canonical Point Cloud + Maya Ghost product.
