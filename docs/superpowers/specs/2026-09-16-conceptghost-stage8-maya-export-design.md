# ConceptGhost — Stage 8 Maya Ghost / Export Layer Design

Date: 2026-09-16
Status: APPROVED architecture for Stage 8
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ BEFORE STAGE 8 IMPLEMENTATION

This document defines the approved handoff from Stage 7 `SceneBundle` to the artist-facing Maya Ghost package.

It must be read together with:

```text
docs/superpowers/specs/2026-09-16-conceptghost-output-handoff-contract.md
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

---

# 1. Stage 8 goal

Stage 8 converts a validated Stage 7 `SceneBundle` into a practical, portable Maya reference package.

The normal artist workflow is:

```text
Run ConceptGhost
-> open the generated run folder
-> double-click ConceptGhost_<scene>_Ghost.ma
-> matched camera, source plate, and Ghost are already assembled
-> orbit with artist camera / Maya perspective
-> create normal Maya geometry and model against the Ghost
```

The artist must not be required to:

- manually import the PLY;
- manually import/reconstruct DA3 or MoGe data;
- rebuild the Atlas camera;
- manually align the source concept;
- pass through Blender;
- manually attach the USD point cloud to the Maya scene.

---

# 2. Input contract

Stage 8 consumes only the stable ConceptGhost `SceneBundle`.

Conceptually:

```text
SceneBundle
├── CameraBundle
├── CanonicalGeometry
├── SourceImage
├── GeometryHealth
├── Reprojection / Integration Consistency Report
├── CoordinateConvention
├── ScaleConvention
├── EngineMetadata
└── Manifest
```

Stage 8 must not depend directly on engine-private DA3/MoGe ComfyUI node sockets.

This keeps the export architecture stable if future engines are added.

---

# 3. Approved standard output set

Every valid Stage 8 run automatically attempts to generate all standard outputs:

```text
maya/ConceptGhost_<scene>_Ghost.ma
maya/ConceptGhost_<scene>_Ghost.usda
maya/ConceptGhost_<scene>_Ghost.fbx
geometry/canonical/pointcloud.ply
```

These files are complementary, not user-selectable alternatives.

Their roles are:

```text
.ma   = PRIMARY ARTIST ENTRY POINT
.usda = PRIMARY TECHNICAL DENSE-GHOST / POINT-CLOUD CARRIER
.fbx  = PORTABLE CAMERA + VALIDATED MESH COMPANION
.ply  = PORTABLE CANONICAL POINT-CLOUD COPY
```

---

# 4. Where the point cloud lives

The dense Canonical Point Cloud does not need to be embedded directly as native Maya point objects inside the `.ma`.

Approved structure:

```text
ConceptGhost_<scene>_Ghost.ma
        |
        `-- MayaUSD proxy / USD stage
                  |
                  v
ConceptGhost_<scene>_Ghost.usda
                  |
                  `-- UsdGeomPoints
                        |
                        `-- Canonical Point Cloud
```

The `.ma` scene therefore shows the point cloud normally inside Maya, but the dense point data is stored in the companion USD.

The same canonical points are also exported to:

```text
geometry/canonical/pointcloud.ply
```

for portability, inspection, recovery, and independent verification.

## Why not embed one Maya object per point?

Do not create:

```text
point_000001 transform
point_000002 transform
...
point_800000 transform
```

This would create unacceptable scene and viewport overhead.

Use a dense point representation appropriate to USD/Hydra.

---

# 5. USDA / OpenUSD structure

The primary technical Ghost representation uses OpenUSD.

Target concept:

```text
/ConceptGhost_<scene>
    /CG_REFERENCE
        /<engine>_Ghost
```

The Ghost should be represented using:

```text
UsdGeomPoints
```

At minimum preserve:

```text
points XYZ
display color RGB
point width / display radius
coordinate convention metadata
scale mode metadata
source engine metadata
```

Where practical, preserve additional non-render-critical metadata outside the heavy point arrays rather than overloading per-point attributes unnecessarily.

## Point width

Point display width is a visualization parameter, not geometry.

Changing point width must not move or rescale canonical XYZ.

This enables future artist-side controls such as:

```text
Ghost Point Size
```

without rerunning DA3/MoGe.

---

# 6. Maya `.ma` wrapper

The `.ma` is the normal artist file.

Target hierarchy:

```text
ConceptGhost_<scene>
├── CG_CAMERAS
│   ├── matchedCamera_LOCKED
│   └── artistCamera
├── CG_SOURCE
│   └── sourcePlate
├── CG_REFERENCE
│   └── Ghost_USD_Proxy
├── CG_OPTIONAL_MESH
└── CG_METADATA
```

The `.ma` should contain:

- native Maya matched camera;
- optional free artist camera;
- source image plane/reference;
- MayaUSD proxy/stage that loads the companion `.usda`;
- optional validated mesh nodes when appropriate;
- minimal metadata needed for traceability.

The `.ma` should not duplicate the entire dense point cloud as Maya-native per-point scene objects.

---

# 7. Matched camera

`CameraBundle` is converted into a native Maya camera.

The generated camera must preserve, as applicable:

```text
projection
focal / FOV
aspect relationship
camera transform
orientation
principal-point handling
near/far clipping
```

Target node:

```text
CG_CAMERAS/matchedCamera_LOCKED
```

The matched camera should be locked against accidental artist edits after generation, while still allowing deliberate unlock if the artist explicitly chooses to do so.

## Single camera authority

Do not independently recalculate a second camera for FBX.

Approved path:

```text
CameraBundle
    |
    v
native Maya matchedCamera
    |
    +-- saved in .ma
    |
    `-- exported to .fbx
```

This reduces drift between Maya and FBX cameras.

---

# 8. Artist camera

Create:

```text
CG_CAMERAS/artistCamera
```

Purpose:

- start near or at the matched camera;
- remain unlocked;
- allow orbiting, inspection, and modeling;
- preserve `matchedCamera_LOCKED` unchanged.

The source plate belongs to the matched camera, not necessarily the free artist camera.

---

# 9. Source plate

The source image must be copied into the run bundle.

Example:

```text
source/source.png
```

The Maya scene should reference the run-local copy, not the original arbitrary source path.

Approved relationship:

```text
matchedCamera
    |
    `-- imagePlane / sourcePlate
             |
             `-- relative path to ../source/source.png
```

This makes the run portable and auditable.

---

# 10. Relative-path requirement

The `.ma` should use relative paths for companion assets wherever technically reliable.

Especially:

```text
.usda
source image
optional mesh/textures
```

Required portability test:

```text
1. Generate run
2. Open .ma successfully
3. Close Maya
4. Move the whole run folder to another local path
5. Re-open the .ma
6. Source plate and USD Ghost still resolve
```

If MayaUSD does not reliably preserve a relative path in the selected Maya version, Stage 8 may include a lightweight ConceptGhost rebinder/loader.

That helper is a fallback, not the preferred normal artist workflow.

---

# 11. Compare Both behavior in Maya

If:

```text
Geometry = DA3
Compare Both = ON
```

then preserve independent Ghosts:

```text
CG_REFERENCE
├── DA3_Ghost
└── MoGe_Ghost
```

Default visibility:

```text
primary selected engine = visible
secondary comparison engine = hidden
```

No geometry fusion occurs.

PLY output should likewise preserve separate comparison branches when Compare Both is enabled.

Example:

```text
geometry/
├── da3/canonical/pointcloud.ply
├── moge/canonical/pointcloud.ply
└── canonical/pointcloud.ply
```

`geometry/canonical/pointcloud.ply` corresponds to the authoritative selected engine.

---

# 12. Optional meshes

Stages 10–12 may later populate:

```text
CG_OPTIONAL_MESH
├── Atlas_Relief
├── MoGe_Mesh
└── DA3_Mesh
```

Mesh classification remains:

```text
useful
limited
reject
```

Export behavior recommendation:

```text
useful  -> normal optional scene/export inclusion
limited -> preserve but mark clearly
reject  -> retain only as evidence when useful; do not present as primary good geometry
```

Optional mesh status never changes the Canonical Point Cloud.

---

# 13. FBX companion

FBX is generated automatically.

Approved approach:

```text
SceneBundle
   |
   v
Maya Worker
   |
   +-- native matchedCamera
   +-- artistCamera if validated/useful
   +-- transforms / coordinate context
   `-- validated optional meshes
             |
             v
ConceptGhost_<scene>_Ghost.fbx
```

Minimum FBX contract:

```text
matched camera
supported FOV/projection data
scene transform / axis / scale context
validated optional meshes when available
```

The Canonical Point Cloud is not required inside the FBX.

USD/PLY remain authoritative for dense points.

---

# 14. Separate Maya Worker

Maya/FBX generation must run outside the ComfyUI Python process.

Reason:

```text
ComfyUI environment:
Torch
CUDA
NumPy
DA3
MoGe
Atlas
...

Maya environment:
Maya Python
Maya API
MayaUSD
FBX plugin
Maya libraries
```

Do not contaminate the protected ComfyUI environment by forcing Maya runtime dependencies into it.

Approved architecture:

```text
ComfyUI / ConceptGhost
        |
        | writes validated SceneBundle / export inputs
        v
separate ConceptGhost Maya Worker
        |
        +-- creates .ma
        `-- creates .fbx
```

USD and PLY may be generated by the general ConceptGhost export layer without importing Maya runtime dependencies.

The worker may use Maya batch / standalone / headless mode only after Stage 8 validation determines the stable approach.

---

# 15. Maya version support must be evidence-based

Do not assume identical support across all installed Maya versions.

Characterize:

```text
Maya 2026
Maya 2024
Maya 2018
```

Validate per version:

```text
MayaUSD availability
MayaUSD load
FBX plugin
.ma open/save
native camera conversion
source image plane
USD point rendering
viewport performance
relative path behavior
```

Final documentation may classify versions as:

```text
FULL
LIMITED
UNSUPPORTED
```

based only on fresh Stage 8 evidence.

---

# 16. Validation Gate 8A — USDA

Before relying on `.ma`, validate the `.usda` directly.

Check:

```text
point count
XYZ values
RGB values
bounding box
up axis
orientation
scale
point widths
USD stage validity
MayaUSD loading
viewport performance
```

If explicit decimation is used, it must be recorded in the manifest.

---

# 17. Validation Gate 8B — Maya camera

Stage 7 already validates ConceptGhost's math.

Stage 8 must independently validate the Maya implementation.

Concept:

```text
Canonical XYZ
   |
   v
generated native Maya camera
   |
   v
project to Maya image/screen
   |
   v
compare against expected source UV
```

This catches exporter/camera-conversion mistakes that Stage 7 cannot detect.

---

# 18. Validation Gate 8C — `.ma`

Real open test:

```text
open .ma
-> no missing required references
-> matchedCamera exists
-> artistCamera exists
-> sourcePlate resolves
-> USD Ghost loads
-> colors visible
-> point display usable
-> hierarchy correct
-> source/Ghost alignment correct
```

Then run the move-folder portability test.

---

# 19. Validation Gate 8D — FBX round trip

Test:

```text
export FBX
-> new empty scene
-> import FBX
```

Compare:

```text
camera transform
FOV
projection behavior
orientation
axis conversion
scale
optional mesh extents
optional mesh vertex count
```

Record deviations explicitly.

---

# 20. Validation Gate 8E — PLY

Export and parse/reopen:

```text
point count
XYZ
RGB
bounding box
```

The PLY must match the authoritative Canonical Point Cloud subject only to explicitly recorded filtering/decimation.

---

# 21. Artist usability validation

Mathematical/export correctness is not sufficient.

Required artist test:

```text
open .ma
-> look through matched camera
-> concept/Ghost composition agrees
-> switch away from matched camera
-> orbit freely
-> Ghost provides useful spatial guidance
-> create normal Maya primitives
-> model/block against Ghost
```

The product fails its practical goal if the Ghost is not useful for modeling, even if files are technically valid.

---

# 22. Approved run layout

Example:

```text
ConceptGhost_Output/
└── <scene>/
    └── <run_id>/
        ├── source/
        │   └── source.png
        ├── camera/
        │   └── camera.json
        ├── diagnostics/
        │   ├── reprojection_report.json
        │   └── geometry_health.json
        ├── geometry/
        │   ├── native/
        │   └── canonical/
        │       ├── pointcloud.ply
        │       └── geometry.json
        ├── maya/
        │   ├── ConceptGhost_<scene>_Ghost.ma
        │   ├── ConceptGhost_<scene>_Ghost.usda
        │   ├── ConceptGhost_<scene>_Ghost.fbx
        │   └── maya_manifest.json
        ├── meshes/
        ├── compare/
        ├── logs/
        └── manifest.json
```

---

# 23. Status semantics

Keep separate:

```text
maya_ghost_ready
deliverable_package_complete
run.status
```

Example:

```text
.ma works
.usda works
.ply works
.fbx fails
```

Then:

```text
maya_ghost_ready = true
deliverable_package_complete = false
run.status = PARTIAL
```

Never delete successful upstream outputs because one companion exporter failed.

---

# 24. Stage 8 PASS

Target acceptance:

```text
valid SceneBundle
+
valid USDA dense Ghost
+
native Maya camera matches CameraBundle
+
source plate resolves
+
.ma opens without manual assembly
+
Ghost usable in viewport
+
FBX camera round-trip acceptable
+
PLY verified
=
STAGE 8 PASS
```

For full production package completeness:

```text
.ma
+ .usda
+ .fbx
+ .ply
all generated and validated
```

---

# 25. One-line implementation instruction

> Build Stage 8 around a `.ma` artist wrapper that contains a native matched camera, source plate, hierarchy, and a MayaUSD proxy to the companion `.usda`; keep the dense Canonical Point Cloud in `UsdGeomPoints`, export a matching `.ply`, generate camera/mesh `.fbx` through a separate Maya Worker, prefer relative paths, and validate USD, Maya camera, `.ma`, FBX round-trip, PLY, portability, and artist usability independently.
