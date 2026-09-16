# ConceptGhost Roadmap Addendum — Master Workflow Integration

Date: 2026-09-16
Status: Approved integration policy; updated through Stage 10 design plus post-V1 Stage 15 technology watch

This addendum clarifies how Stages 3-15 converge into one final user-facing workflow plus a post-V1 research stage.

## MANDATORY DEVELOPMENT READ GATE

Before implementing or modifying Stages 6-13, read and reconcile:

```text
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

Before Stage 8 Maya/export work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-output-handoff-contract.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
```

Before Stage 9 benchmark/preset work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-stage9-benchmark-preset-design.md
```

Before Stage 10 Atlas relief-mesh work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-stage10-atlas-relief-mesh-design.md
```

If older documentation conflicts with these files, stop and reconcile the conflict before implementation.

## Stages 3-5 — public baselines first

- Stage 3: Atlas camera baseline.
- Stage 4: DA3 upstream/public baseline unchanged.
- Stage 5: official/native MoGe baseline unchanged.

Do not hide an upstream failure behind ConceptGhost adapters.

## Stage 6 — Master Alpha

One `ConceptGhost_Master.json` with:
- one source image;
- Camera = Auto / Atlas Learned / Atlas VP;
- Geometry = DA3 / MoGe;
- Compare Both;
- presets.

Defaults:

```text
Preset = Max Reference
Camera = Auto
Geometry = DA3
Compare Both = OFF
```

No Geometry Auto.

## Stage 7 — canonical integration and refinement

Create CameraBundle, GeometryEvidence/GeometryBundle, CanonicalGeometry, SceneBundle, explicit coordinate/scale conventions, Integration Consistency Gate, and Geometry Health Gate.

Authority:

```text
Camera/projection = Atlas
Depth/shape evidence = DA3 or MoGe
Color = original image
Final 3D space = ConceptGhost Canonical Scene
```

Canonical convention:

```text
right-handed
Y-Up
camera local optical axis = -Z
```

Evaluate, without hiding baselines:
- DA3 current/public baseline vs Atlas-conditioned DA3 official API where safe;
- MoGe Auto FOV vs Atlas-FOV.

Reprojection validates integration consistency, not true depth accuracy.

## Stage 8 — first complete Maya artist handoff

Generate together:

```text
ConceptGhost_<scene>_Ghost.ma
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.fbx
pointcloud.ply
```

Roles:

```text
.ma   = artist entry point
.usda = dense Ghost carrier via UsdGeomPoints
.fbx  = camera + validated optional meshes
.ply  = portable Canonical Point Cloud
```

The `.ma` contains native matched camera, artist camera, source plate, and MayaUSD proxy/stage. Dense points live in the companion `.usda`.

Maya/FBX generation uses a separate Maya Worker. Prefer relative paths and test moving the entire run folder.

## Stage 9 — benchmark and preset freeze

Benchmark images are chosen by the user for each benchmark session. No permanent fixed corpus and no automatic public-image selection.

Within a session, every candidate uses the same selected images.

Compare:

```text
DA3 baseline
DA3 Atlas-conditioned
MoGe Auto FOV
MoGe Atlas FOV
```

Candidates must pass Stage 7/8 technical gates before artist comparison.

Automatic metrics are evidence only. Final practical usefulness is decided by the user in Maya, including:
- matched-camera agreement;
- foreground/background separation;
- ground continuity;
- architecture/large planes;
- thin structures;
- streamers;
- noise;
- occlusion boundaries;
- off-camera usefulness;
- blockout usefulness.

Freeze versioned per-engine presets:

```text
DA3 Fast Test v1
DA3 Balanced v1
DA3 Max Reference v1

MoGe Fast Test v1
MoGe Balanced v1
MoGe Max Reference v1
```

Parameter study is progressive, not brute-force.

Stage 9 decides:

```text
DA3 Atlas conditioning -> adopt | experimental | reject
MoGe Atlas FOV         -> adopt | experimental | reject
confidence policy
edge filtering
point density
processing resolution
```

Depth Anything V2 Metric Outdoor may remain a low-cost exterior reference baseline, not a hidden V1 engine switch.

## Stage 10 — Atlas relief mesh

Stage 10 is an OPTIONAL E1 branch. It does not replace the Canonical Point Cloud.

Reuse the pinned Atlas relief implementation first:

```text
mikejamesvfx/atlas-camera
commit 9f9ff4511154769aa2f8c0bd40387278a69b0078
```

Preserve:

```text
Atlas Native Relief
```

before creating derived variants:

```text
repair
retopo
decimation
```

Atlas deliberately tears triangles at depth discontinuities to avoid false foreground/background sheets. Do not automatically repair intentional occlusion tears.

Preserve projective UVs. If topology changes, regenerate projective UVs from the solved camera using the Atlas export-only pattern.

Optional cleanup dependencies must obey ConceptGhost's protected-environment policy.

Classify each result:

```text
useful | limited | reject
```

- `useful`: genuinely helps blockout;
- `limited`: useful mainly near the solved camera / known 2.5D limits;
- `reject`: misleading geometry, preserved only as evidence.

Maya integration:

```text
CG_OPTIONAL_MESH
└── Atlas_Relief
```

A rejected/failed Atlas relief must never invalidate:

```text
maya_ghost_ready
Canonical Point Cloud
matched camera
.usda Ghost
.ply point cloud
```

Read the Stage 10 spec for canonical-space adaptation, repair/retopo separation, UV validation, Maya evaluation, performance metrics, and FBX inclusion rules.

## Stage 11 — MoGe mesh

MoGe mesh remains an independent optional branch. Failure never invalidates the core Ghost.

## Stage 12 — DA3 mesh

DA3 mesh remains an independent optional branch. Failure never invalidates the core Ghost.

## Stage 13 — final packaging

Freeze:
- one production Master workflow;
- multi-format handoff contract;
- dependency-safe installer/uninstaller;
- documentation;
- acceptance tests;
- storage/non-overwrite policy.

## Stage 14 — future camera extension

PCS/fSpy/manual advanced camera path after core V1 is stable.

## Stage 15 — post-V1 alternative engine evaluation / technology watch

Starts only after Stages 3-14 are complete and does not alter V1.

Initial candidates:

```text
MoGe-3
VGGT
UniDepth V2
Depth Pro
Metric3D V2
GeoWizard
Depth Anything V2 Metric Outdoor reference baseline
newly released relevant systems
```

Any adopted candidate enters through a clean GeometryAdapter/CameraAdapter boundary and reuses Stages 7-9.

## Runtime rules that development must preserve

- Camera Auto = Atlas Learned first, Atlas VP only after camera-quality failure.
- DA3 default, MoGe selectable, no silent geometry fallback.
- Compare Both = independent comparison, never implicit fusion.
- Primary-fails/secondary-passes = PARTIAL; secondary is not promoted.
- Max Reference = default preset.
- Maya Ghost, Canonical Point Cloud, manifest, reprojection report, and reprojection overlay are mandatory.
- Extra diagnostics and optional meshes may remain optional.
- Every run gets a unique run ID.
- Never overwrite or automatically delete earlier runs.
- Disk-space preflight before expensive Max Reference processing.

## Production success semantics

The final package distinguishes:

```text
maya_ghost_ready
deliverable_package_complete
run.status
```

Core success targets:

```text
valid Atlas Camera
+ valid Canonical Geometry
+ Integration Consistency PASS
+ Geometry Health acceptable
+ usable .ma/.usda Maya Ghost
+ required .fbx companion
+ required .ply companion
= complete ConceptGhost production result
```

Optional mesh failure does not invalidate the core Ghost.
