# ConceptGhost — Integrated Architecture v2

Date: 2026-09-16
Status: Consolidated approved architecture and development guidance
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ
>
> This document consolidates the approved architecture decisions made after the earlier `2026-09-16-conceptghost-master-workflow-design.md`. When the older design conflicts with this document, this document plus the Runtime Behavior Policy and Output/Handoff Contract are authoritative.

## 1. Product goal

ConceptGhost converts one 2D concept-art image into a locally generated 3D reference package for Maya.

The primary artist experience is:

```text
Concept image
-> ConceptGhost runs locally
-> one self-contained run folder
-> open one .ma file in Maya
-> matched camera + source plate + colored 3D Ghost already assembled
-> orbit away from the camera
-> model normal Maya geometry against the Ghost
```

The artist must not be required to manually rebuild the camera, import DA3/MoGe outputs, align a point cloud, or pass through Blender before using Maya.

## 2. Technology responsibilities

### ComfyUI
Role: orchestration and user-facing workflow.

It coordinates:
- the single source image;
- preset;
- camera mode;
- geometry engine;
- Compare Both;
- Atlas, DA3, MoGe, normalization, reprojection, and export branches.

ComfyUI is not the authority for camera or depth.

### Atlas Camera
Role: authoritative camera/projection solution.

Camera modes:
- Auto;
- Atlas Learned / GeoCalib;
- Atlas VP.

Approved Auto policy:

```text
Atlas Learned
-> camera quality gate
   -> PASS: authoritative camera
   -> FAIL: Atlas VP fallback
             -> PASS: authoritative camera
             -> FAIL: camera stage fails
```

Manual selection of Atlas Learned or Atlas VP remains literal; it is not silently replaced by another solver.

### Depth Anything V3 / DA3
Role: primary/default geometry and depth evidence.

DA3 may provide:
- depth;
- confidence;
- estimated intrinsics;
- native point cloud;
- other engine-native evidence.

DA3 native camera information is diagnostic evidence, not the final ConceptGhost camera authority.

### MoGe
Role: independent alternate geometry reconstruction.

MoGe may provide:
- point map;
- depth;
- mask;
- normals;
- estimated FOV/intrinsics;
- native mesh/geometry where available.

MoGe native camera/FOV remains diagnostic. Atlas remains the final camera authority.

### DA3-Blender
Role: proven workflow reference, not a mandatory runtime dependency.

ConceptGhost may adapt validated ideas such as:
- confidence filtering;
- depth-discontinuity / edge filtering;
- streamer reduction;
- point-size / point-presentation strategies;
- optional mesh cleanup.

### ConceptGhost Normalizer
Role: the key integration layer owned by this project.

It combines:
- authoritative Atlas CameraBundle;
- DA3 or MoGe GeometryBundle;
- source pixels/color;
- explicit coordinate conventions.

It produces ConceptGhost Canonical Geometry / Canonical Point Cloud.

### Reprojection Gate
Role: mathematical consistency validation.

Canonical 3D points are projected back through the authoritative Atlas camera and compared with their source-image pixel positions.

A significant mismatch blocks publication of an authoritative Maya Ghost.

### OpenUSD
Role: preferred high-density scene/point interchange.

The primary technical Ghost representation is expected to use USD point primitives such as `UsdGeomPoints`, subject to Stage 8 validation.

### MayaUSD / Maya
Role: primary artist handoff and working environment.

Maya receives:
- matched camera;
- artist camera;
- source plate;
- canonical colored Ghost points;
- optional validated meshes;
- metadata.

The point cloud must not be represented as one Maya transform per point.

### FBX
Role: automatic compatibility companion output.

FBX is not the authoritative Ghost carrier because standard FBX interoperability does not reliably carry point-cloud geometry.

FBX is valuable for:
- matched camera;
- artist camera where useful;
- coordinate/transform context;
- validated optional meshes when available.

Point-cloud data remains authoritative in USD/PLY unless Stage 8 testing proves a stable FBX-compatible representation. A workaround must never silently replace or degrade the canonical USD/PLY Ghost.

### PLY
Role: simple portable canonical point-cloud copy.

PLY preserves the canonical point positions and colors for debugging, inspection, interchange, and recovery.

### fSpy / PCS
Role: future advanced/manual camera validation or fallback.

They are not required in the automatic V1 path. Stage 14 may add them after the core V1 is stable.

## 3. Authority model

```text
CAMERA / PROJECTION
Atlas = source of truth

DEPTH / SHAPE EVIDENCE
DA3 or MoGe = source of truth

COLOR
Original concept image = source of truth

FINAL 3D COORDINATE SYSTEM
ConceptGhost Canonical Scene = source of truth
```

The project must not simply route an engine-native point cloud directly to Maya and call it the final Ghost.

## 4. Stage integration

### Stage 3 — Atlas camera baseline
Validate camera solving independently:
- Atlas Learned / GeoCalib;
- Atlas VP;
- camera-quality acceptance evidence.

No geometry integration yet.

### Stage 4 — DA3 baseline
Run upstream `advanced_3d.json` unchanged.

Prove DA3 can produce the required native evidence before any ConceptGhost adapter is blamed or trusted.

### Stage 5 — MoGe baseline
Run the official/native MoGe workflow unchanged.

Prove the native MoGe evidence independently.

### Stage 6 — Master Alpha
Create the first `ConceptGhost_Master.json`.

One input image fans out to:
- Atlas camera branch;
- DA3/MoGe Geometry Router.

Initial production defaults:

```text
Preset = Max Reference
Camera = Auto
Geometry = DA3
Compare Both = OFF
```

There is no `Geometry = Auto`.

### Stage 7 — Canonical integration
Create and enforce:
- CameraBundle;
- GeometryBundle;
- CanonicalGeometry;
- SceneBundle;
- explicit coordinate convention;
- mandatory reprojection gate.

DA3 path conceptually:

```text
source pixels
+ DA3 depth/confidence
+ Atlas camera
-> Canonical Point Cloud
```

MoGe path conceptually:

```text
MoGe point/depth evidence
+ source-pixel relationship
+ Atlas camera
+ canonical coordinate conversion
-> Canonical Point Cloud
```

### Stage 8 — Maya Ghost and multi-format handoff
This is the first artist-usable V1 milestone.

A valid run automatically attempts to generate all required deliverables:

```text
ConceptGhost_<scene>_Ghost.ma
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.fbx
pointcloud.ply
```

The `.ma` file is the normal artist entry point.

The `.usda` file is the primary technical Ghost scene/point representation used behind or alongside the Maya wrapper.

The `.fbx` file is a compatibility companion carrying the matched camera and exportable validated meshes. It must be generated automatically; the user does not choose FBX instead of MA/USD.

The `.ply` file is the portable canonical point-cloud copy.

See the mandatory `2026-09-16-conceptghost-output-handoff-contract.md`.

### Stage 9 — controlled A/B benchmark
Compare DA3 and MoGe under:
- the same source image;
- the same authoritative Atlas camera;
- the same canonical conventions;
- controlled preset settings.

Benchmark:
- depth continuity;
- edge streamers;
- noise;
- occlusion;
- foreground/background separation;
- architecture fidelity;
- behavior when orbiting away from the matched camera;
- Maya usefulness.

The measured evidence defines the final values of Max Reference, Balanced, and Fast Test.

### Stage 10 — Atlas relief mesh
Optional mesh branch only.

Classify output as:
- useful;
- limited;
- reject.

Mesh failure never invalidates a good camera + canonical Ghost.

### Stage 11 — MoGe mesh
Optional mesh branch.

A generated GLB/mesh is not automatically considered useful.

### Stage 12 — DA3 mesh
Optional mesh branch using validated DA3/DA3-Blender ideas where justified.

### Stage 13 — packaging and production freeze
Freeze:
- one user-facing Master workflow;
- output contract;
- presets;
- dependency-safe install/uninstall;
- documentation;
- acceptance tests;
- non-interference rules.

### Stage 14 — future advanced/manual camera path
Potential PCS/fSpy integration after V1.

## 5. Runtime behavior already approved

### Camera
`Auto` tries Atlas Learned first, then Atlas VP only when the primary camera fails the quality gate.

### Geometry
- DA3 default;
- MoGe selectable;
- no Geometry Auto;
- no silent geometry fallback.

### Compare Both
Runs DA3 and MoGe independently.

If selected primary geometry fails and the comparison engine passes:

```text
run = PARTIAL
secondary output is preserved
secondary is not promoted
no authoritative Maya Ghost is silently rebuilt from it
```

### Presets
- Max Reference = default;
- Balanced;
- Fast Test.

Presets control validated quality/cost parameters and never silently switch Camera, DA3/MoGe, or Compare Both.

### Mandatory outputs
The production Master has no ON/OFF controls for:
- Maya Ghost;
- Canonical Point Cloud;
- manifest;
- reprojection report;
- reprojection overlay.

Heavy extra diagnostics and optional mesh branches may remain optional.

## 6. Required artist-facing result

Expected run layout:

```text
ConceptGhost_Output\
└── <scene>\
    └── <run_id>\
        ├── source\
        ├── camera\
        ├── diagnostics\
        ├── geometry\
        │   ├── native\
        │   └── canonical\
        │       ├── pointcloud.ply
        │       └── geometry.json
        ├── maya\
        │   ├── ConceptGhost_<scene>_Ghost.ma
        │   ├── ConceptGhost_<scene>_Ghost.usda
        │   ├── ConceptGhost_<scene>_Ghost.fbx
        │   └── maya_manifest.json
        ├── meshes\
        ├── compare\
        ├── logs\
        └── manifest.json
```

The `.ma` wrapper should use portable/relative paths to the companion USD whenever technically feasible so the entire run folder can be moved without manually rebuilding links.

## 7. Maya scene goal

Conceptual hierarchy:

```text
ConceptGhost_<scene>
├── CG_CAMERAS
│   ├── matchedCamera_LOCKED
│   └── artistCamera
├── CG_SOURCE
│   └── sourcePlate
├── CG_REFERENCE
│   └── <engine>_Ghost
├── CG_OPTIONAL_MESH
└── CG_METADATA
```

Artist workflow:

```text
open .ma
-> inspect matched camera
-> confirm concept/Ghost agreement
-> switch to artist/perspective camera
-> orbit freely
-> create normal Maya primitives
-> block/model against the Ghost
```

Blender is not a required intermediate stage.

The user may optionally import/open the USD/FBX/PLY in other software for inspection or compatibility.

## 8. FBX contract and limitation

The project must generate FBX as a standard companion deliverable, but must not misrepresent its capabilities.

Autodesk documents FBX camera support, including camera field-of-view and clipping-plane data, but FBX does not provide a reliable standard point-cloud interchange path.

Therefore Stage 8 must validate the FBX export with this minimum contract:

```text
REQUIRED IN FBX
matched camera
camera projection/FOV information supported by FBX
scene transforms/axis/scale context
validated exportable mesh geometry when generated

NOT REQUIRED TO CLAIM FBX SUCCESS
full Canonical Point Cloud
```

If a stable point representation can be proven across Maya/Blender without corrupting performance or semantics, it may be added later. It must not replace `.usda` or `.ply`.

## 9. Output completeness and status

For the production output package:

```text
Primary artist file: .ma
Primary technical Ghost: .usda
Portable camera/mesh companion: .fbx
Portable point-cloud companion: .ply
```

All four are generated automatically when their upstream requirements are met.

Recommended status separation:

```text
maya_ghost_ready = true|false
deliverable_package_complete = true|false
run.status = PASS|PARTIAL|FAIL
```

A working `.ma/.usda` Ghost can be artist-usable while an FBX exporter problem is diagnosed, but the final production package is not considered complete until the required FBX and PLY companions are also produced.

## 10. Non-overwrite and disk policy

Every execution gets a new unique `run_id`.

ConceptGhost must:
- never overwrite an earlier run;
- never automatically delete an earlier run;
- preserve failed/partial evidence when useful for diagnosis;
- perform a local disk-space preflight;
- warn before a high-cost Max Reference run when available storage is below the documented safe threshold.

No cloud upload or remote compute is required for the normal image-processing path.

## 11. Development gates

Before Stage 6 integration work, read:
1. this document;
2. Runtime Behavior Policy;
3. UI Layout Policy;
4. Roadmap Addendum.

Before Stage 8 export/Maya work, also read:
- Output/Handoff Contract.

Implementation must not infer different output semantics from older docs without first reconciling the conflict.

## 12. Core acceptance equation

```text
valid Atlas Camera
+ authoritative Canonical Geometry
+ Reprojection PASS
+ usable Maya Ghost
+ required multi-format deliverables
= complete ConceptGhost production result
```
