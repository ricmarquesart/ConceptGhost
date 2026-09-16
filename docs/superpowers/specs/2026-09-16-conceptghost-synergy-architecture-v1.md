# ConceptGhost — Synergy Architecture v1

Date: 2026-09-16
Status: APPROVED architecture
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ FOR STAGES 6–8

This specification defines what "synergy" means in ConceptGhost and how the preserved upstream/reference code must cooperate to produce one final Ghost instead of several isolated outputs.

It does NOT change the approved geometry selector:

```text
Geometry = DA3
Geometry = MoGe
Compare Both = OFF/ON
```

DA3 and MoGe remain independently selectable. `Compare Both` remains a diagnostic/comparison mode and does NOT silently fuse the two geometry engines.

The synergy happens around and inside the selected path: camera constraints, confidence, masks, normals, edge/discontinuity logic, ground/gravity logic, canonical reconstruction, validation, and DCC handoff all cooperate to improve one final result.

## 1. Product rule

ConceptGhost must NOT behave like:

```text
Image
├── Atlas -> output A
├── DA3   -> output B
├── MoGe  -> output C
└── Maya  -> manual assembly
```

The intended architecture is:

```text
Image
  ↓
specialized components cooperate
  ↓
one canonical scene interpretation
  ↓
one final colored Ghost
  ↓
Maya
```

The normal user experience remains:

```text
load image
→ choose DA3 or MoGe (or Compare Both)
→ Run
→ receive final Ghost package
```

Internal complexity must not become manual assembly work for the artist.

## 2. Three participation classes

Every preserved code/reference must be classified as one of:

```text
RUNTIME CONTRIBUTOR
executes in normal production when its capability is required

CONDITIONAL / FALLBACK
executes only when a gate or scene condition requires it

IMPLEMENTATION REFERENCE
does not need to execute in production; proven logic is adapted into ConceptGhost
```

"Use all saved code intelligently" does NOT mean execute every repository on every run.

It means every retained reference has an explicit reason to exist and a defined integration role.

## 3. Source-of-truth model

```text
CAMERA / PROJECTION
Atlas Camera

GEOMETRY ENGINE
DA3 or MoGe, selected by the user
Both = independent comparison only

COLOR
original source image

FINAL SPACE
ConceptGhost Canonical Scene

FINAL ARTIST PRODUCT
Canonical Colored Ghost in Maya
```

Engine-native point clouds/meshes are evidence, not the final authoritative Ghost unless they have passed ConceptGhost adaptation and validation.

## 4. Stage 6 becomes the Synergistic Master Orchestrator

Stage 6 is not merely a visual collection of independent branches.

It orchestrates services:

```text
SOURCE IMAGE
    │
    ├── Camera Service
    ├── Geometry Service
    ├── Evidence Service
    ├── Refinement Service
    ├── Validation Service
    └── Export Service
```

User-facing controls remain intentionally small:

```text
Image
Preset = Max Reference
Camera = Auto
Geometry = DA3 or MoGe
Compare Both = OFF/ON
Run
```

Advanced controls may expose diagnostics but must not be required for a normal run.

## 5. Camera synergy — Atlas contributes before and after geometry

### 5.1 Atlas camera authority

Atlas remains the authoritative camera solver.

Auto policy:

```text
Atlas Learned / GeoCalib
        ↓
camera quality gate
        ├── PASS -> use
        └── FAIL -> Atlas VP
                      ↓
                  quality gate
```

Atlas VP is conditional fallback, not a second always-on solver.

### 5.2 DA3 conditioning

The official Depth Anything 3 API supports external:

```text
intrinsics
extrinsics
```

Therefore Stage 7 must support an Atlas-conditioned DA3 experiment/path where safe:

```text
Atlas CameraBundle
      │
      ├── intrinsics K
      └── extrinsics / pose
              ↓
        DA3 inference
```

This is stronger synergy than solving camera and depth independently and trying to reconcile them only afterward.

Baseline DA3 must remain available for comparison until Stage 9 evidence decides whether conditioning becomes the normal DA3 path.

### 5.3 MoGe conditioning

Atlas already supports feeding solved focal/FOV into MoGe using `fov_x`.

Therefore Stage 7 must support:

```text
Atlas solved focal/FOV
        ↓
MoGe fov_x
        ↓
MoGe geometry
```

MoGe Auto-FOV remains the baseline for Stage 9 comparison.

### 5.4 No silent camera disagreement

DA3/MoGe native camera estimates are diagnostics.

They never silently replace the Atlas camera.

## 6. Canonical ray reconstruction

The selected geometry engine may output different depth semantics.

ConceptGhost must explicitly declare and adapt:

```text
camera_z
ray_distance
inverse_depth
relative_depth
metric_depth
point_map_xyz
```

Never assume generic "depth" means the same thing across engines.

For image pixel center:

```text
p = [u + 0.5, v + 0.5, 1]^T
r = K^-1 p
```

For `camera_z`:

```text
P_camera = (z / r.z) * r
```

For ray distance:

```text
P_camera = d * normalize(r)
```

Then:

```text
P_world = CameraToWorld_Atlas * P_camera
```

This canonical reconstruction is the mathematical place where Atlas camera and the selected geometry engine truly meet.

## 7. Evidence Pack

Before producing final canonical points, ConceptGhost creates an engine-specific `EvidencePack`.

Possible fields:

```text
depth / point map
confidence
validity mask
sky mask
normals
native intrinsics/FOV
source UV/pixel relationship
engine/model/version
inference parameters
depth semantics
```

Not every engine must provide every field.

Missing data is explicit:

```text
available
not_available
not_requested
failed
```

No fake placeholders.

## 8. Geometry Reliability Map

Confidence should not be used only as a hard delete threshold.

ConceptGhost should derive a per-pixel/per-point reliability state from available evidence.

Conceptually:

```text
high depth confidence
+ valid camera ray
+ not sky
+ not near ambiguous discontinuity
= TRUST

medium confidence
+ boundary proximity
= CAUTION

sky / invalid / non-finite
= REJECT
```

Suggested canonical fields:

```text
xyz
rgb
uv
confidence
validity
boundary_weight
engine_provenance
```

The exact numeric policy is refined later, but the data model must support it now.

## 9. DA3-Blender-derived edge / streamer logic

DA3-Blender is an implementation reference, not a required runtime dependency.

Its proven idea that depth-discontinuity neighborhoods produce streamer artifacts should be adapted into the shared refinement layer.

Concept:

```text
raw depth
→ detect strong local depth change
→ mark ambiguous transition neighborhood
→ suppress or down-weight transition pixels
→ preserve foreground and background surfaces separately
```

This is preferred over solving every artifact only by raising a global confidence threshold.

Do not import Blender as a runtime intermediary.

## 10. MoGe depth + normal boundary logic

MoGe provides normals/masks/point/depth evidence.

Its meshing logic combines depth discontinuities with normal changes to avoid connecting surfaces that should remain separate.

ConceptGhost should adapt this idea into a reusable `SurfaceBoundaryMap`, even when no mesh is generated:

```text
large depth change
+
large normal change
→ strong likely surface boundary
```

Uses:

```text
prevent smoothing across object boundaries
prevent interpolation across occlusion edges
down-weight ambiguous edge points
guide later mesh segmentation
```

Normals must not be used blindly where they are absent or unreliable.

## 11. Normal-guided local refinement — deferred V0.2 capability

Surface normals can constrain local depth/surface consistency.

Potential future refinement:

```text
depth
+
normal
+
camera rays
+
reliability
→ local plane/surface stabilization
```

This is especially promising for:

```text
walls
floors
facades
large planar forms
```

But it must not block Synergy V0.1 / First Tangible Ghost.

V0.1 preserves normals and boundary evidence first.

V0.2 may use them for actual local depth optimization only if the first result justifies continued refinement.

## 12. Ground / gravity synergy from Atlas

Atlas contains ground/gravity/ground-consensus logic.

When evidence is strong, this can constrain large ground-like surfaces.

Policy:

```text
ground confidence high
→ allow robust ground-plane stabilization

ground confidence weak
→ do not flatten geometry
```

Never force all lower-image points to Y=0.

Ground evidence is conditional and confidence-gated.

Primary targets:

```text
roads
floors
architectural interiors
plazas
large horizontal surfaces
```

This capability is intended to improve the user's ability to estimate height and proportion for blockout.

## 13. Robust registration before using auxiliary geometry

ConceptGhost adopts a general rule inspired by Atlas hidden-geometry registration:

> Never combine auxiliary geometry merely because it exists. Register it against trusted visible geometry and measure agreement first.

For auxiliary depth `Za` and trusted visible depth `Zt` over valid overlapping pixels:

```text
ri = Zt(i) / Za(i)

scale s = median(ri)

relative_MAD =
median(|ri - s|)
----------------
       s
```

Only if registration quality is acceptable may the auxiliary evidence modify or extend the primary representation.

This pattern should become a reusable ConceptGhost service:

```text
RegisterAuxiliaryGeometry()
```

Possible future uses:

```text
hidden-surface hypotheses
alternative depth engines
metric reference depth
Stage 15 engines
specialized geometry helpers
```

No blind averaging.

## 14. Compare Both remains independent

`Compare Both` keeps its original meaning.

```text
same source
same Atlas camera
        │
   ┌────┴────┐
   ▼         ▼
  DA3       MoGe
   │         │
synergy     synergy
pipeline    pipeline
   │         │
   ▼         ▼
DA3 Ghost  MoGe Ghost
   └────┬────┘
        ▼
    comparison
```

No automatic DA3+MoGe fusion in V1.

The user explicitly chose comparison mode.

This distinction is mandatory.

## 15. Synergy V0.1 — required before First Tangible Ghost

To avoid replacing one delay with another, V0.1 must implement only high-value, low-risk synergy.

Required V0.1:

```text
Atlas Learned / GeoCalib
Atlas VP fallback
DA3 / MoGe / Both selector unchanged
Atlas-conditioned geometry hooks where supported
explicit depth semantics
canonical camera-ray reconstruction
confidence / masks / sky handling
edge-aware validity / streamer reduction
MoGe depth+normal boundary evidence when MoGe is selected
source RGB authority
reprojection consistency
basic geometry health
OpenUSD
MayaUSD
PLY
Maya wrapper
```

Conditional if already safely available:

```text
ground/gravity stabilization
```

Not required before first user judgment:

```text
normal-guided depth optimization
multi-model depth fusion
hidden-geometry synthesis
mesh fusion
complex hole reconstruction
```

## 16. Stage 7 becomes the Synergistic Integration Core

Stage 7 is no longer understood as "coordinate conversion only".

It owns:

```text
CameraBundle
GeometryEvidence
EvidencePack
depth semantics
camera conditioning adapters
canonical ray reconstruction
ReliabilityMap
SurfaceBoundaryMap
mask/sky validity
edge-aware cleanup
optional ground constraint
Integration Consistency Gate
Geometry Health Gate
CanonicalGeometry
SceneBundle
```

The output remains one authoritative `CanonicalGeometry` for the selected engine path.

## 17. Stage 8 remains one final handoff

Stage 8 consumes `SceneBundle`, not raw DA3/MoGe outputs.

Required final point-cloud outputs:

```text
pointcloud.ply
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.ma
```

FBX remains the camera/mesh compatibility companion.

OpenUSD is the dense Ghost carrier.

MayaUSD is the bridge into Maya.

No engine-specific manual import/setup should be required.

## 18. Reference-code role map

| Preserved reference | Role | Participation |
|---|---|---|
| Atlas Camera | authoritative camera/projection | Runtime |
| GeoCalib | learned camera solve inside Atlas | Runtime |
| Atlas VP | camera fallback | Conditional |
| official DA3 | depth/geometry semantics and camera-conditioned API | Runtime when DA3 selected |
| ComfyUI-DepthAnythingV3 | practical DA3 ComfyUI execution, confidence, intrinsics, sky, point utilities | Runtime/reference |
| MoGe | alternate geometry evidence, normals/masks/FOV | Runtime when MoGe selected |
| ComfyUI MoGe templates | official/native workflow wiring reference | Implementation Reference |
| DA3-Blender | confidence/edge/streamer cleanup concepts | Implementation Reference |
| Atlas hidden_geometry | robust registration and provenance discipline | Implementation Reference / future Conditional |
| Atlas ground/ground_consensus | ground/gravity stabilization | Conditional |
| Atlas exporters | camera/DCC/export logic | Runtime/reference |
| OpenUSD | canonical dense point scene carrier | Runtime |
| MayaUSD | Maya bridge | Runtime |
| fSpy | manual/advanced future camera fallback | Future Conditional |
| fSpy-Blender | DCC/camera conversion reference | Implementation Reference |
| ComfyUI workflow templates | one-click orchestration patterns | Implementation Reference |

This table must be extended whenever another upstream codebase is added.

No preserved code should remain an unexplained "archive item".

## 19. Forbidden integration patterns

Do NOT implement:

### Blind averaging

```text
depth_final = (DA3 + MoGe) / 2
```

without registration and evidence.

### Silent engine substitution

If DA3 is selected, MoGe does not silently replace it after failure.

### Native point-cloud passthrough as final Ghost

Engine-native point cloud must not bypass canonical camera reconstruction unless a proven equivalence is explicitly validated.

### All-tools-always-on

Do not execute every reference merely to claim synergy.

### Mesh-before-point-cloud

Optional mesh complexity must not delay the first usable canonical point cloud.

### Hidden coordinate fixes

Axis/scale/FOV conversions must be explicit and recorded.

## 20. Provenance

Manifest should preserve which synergistic components affected the result.

Example:

```json
{
  "camera": {
    "requested": "auto",
    "final_solver": "atlas_learned"
  },
  "geometry": {
    "engine": "da3",
    "camera_conditioned": true
  },
  "refinement": {
    "confidence_filter": true,
    "sky_filter": true,
    "edge_filter": true,
    "normal_boundary": false,
    "ground_stabilization": false
  }
}
```

For future auxiliary registration, also record:

```text
auxiliary source
registration scale
relative MAD
accepted/rejected
affected region
```

The artist must be able to tell what produced a run.

## 21. First Tangible Ghost success remains unchanged

Synergy is not permission to delay visible progress.

The immediate success criterion remains:

```text
one image
+ one Master run
+ valid Atlas camera
+ selected DA3 or MoGe path
+ synergistic Stage 7 integration
+ canonical colored point cloud
+ PLY
+ USDA
+ MA
= FIRST TANGIBLE GHOST
```

Then the user judges:

```text
PASS
MARGINAL
FAIL
```

based on blockout usefulness.

## 22. Post-first-result escalation

If PASS:

```text
Stage 9 refinement
then optional meshes
```

If MARGINAL:

prioritize only major defects, in this order:

```text
camera conditioning
depth semantics / canonical reconstruction
edge/streamer cleanup
confidence/mask policy
ground stabilization
normal-guided surface stabilization
```

If FAIL:

determine whether failure is:

```text
camera
depth inference
integration math
single-view information limit
```

before investing in mesh work or broad parameter tuning.

## 23. One-line architecture rule

> ConceptGhost synergy means specialized code contributes at the stage where it is strongest—camera, geometry, confidence, masks, normals, boundaries, ground constraints, validation, or export—to improve one canonical Ghost, while DA3 and MoGe remain independently selectable and `Compare Both` remains a comparison rather than hidden fusion.
