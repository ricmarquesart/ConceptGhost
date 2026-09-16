# ConceptGhost Roadmap Addendum — Master Workflow Integration

Date: 2026-09-16
Status: Approved integration policy; updated through Stage 10 design plus post-V1 Stage 15 technology watch

This addendum clarifies how Stages 3-15 converge into one final user-facing workflow plus a post-V1 research stage.

## MANDATORY DEVELOPMENT READ GATE

Before implementing or modifying Stages 6-13, read and reconcile:

```text
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/specs/2026-09-16-conceptghost-execution-priority-first-tangible-ghost.md
docs/superpowers/plans/2026-09-16-conceptghost-stage6-8-vertical-slice-plan.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

Drive mirror of the Stage 6–8 execution plan:

```text
G:\My Drive\ConceptGhost\Documentation\Roadmap\2026-09-16-conceptghost-stage6-8-vertical-slice-plan.md
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

Before Stage 11 MoGe mesh work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-stage11-moge-mesh-design.md
```

If older documentation conflicts with these files, stop and reconcile the conflict before implementation.

## EXECUTION PRIORITY RESET — FIRST TANGIBLE GHOST

Implementation priority is now explicitly different from architecture-detail priority.

Immediate objective:

```text
one image
-> one integrated Master workflow run
-> Atlas camera
-> DA3/MoGe geometry evidence
-> ConceptGhost Normalizer
-> canonical colored point cloud
-> Maya Ghost package
```

This is the **FIRST TANGIBLE GHOST** milestone and it is the next decisive gate for the project. The user's decision to continue investing in ConceptGhost depends primarily on judging this first integrated point-cloud result.

Therefore, the effective implementation order is:

```text
Stage 6
-> Stage 7
-> Stage 8
-> FIRST TANGIBLE GHOST GATE
-> only then heavy Stage 9 refinement and serious Stage 10-12 mesh work
```

Use **best-known defaults** derived from upstream/public references now. Do not block the first integrated Ghost on a full benchmark campaign.

The primary evaluation gate is:

```text
POINT CLOUD USABILITY GATE
```

Question:

> Is the point cloud useful enough to estimate distance, proportion, shape, and relative height for manual blockout in Maya?

Possible outcomes:

```text
PASS     -> continue and refine
MARGINAL -> continue, but focus only on major defects
FAIL     -> user decides whether the project still deserves continuation
```

Before that first tangible Ghost exists, do not let the following dominate project time unless they block execution or validity:

```text
fine threshold tuning
mesh repair/retopo detail
large parameter sweeps
full benchmark campaigns
small-quality polishing
```

Stages 10-12 remain approved architecture, but they are blocked behind point-cloud usefulness in practical implementation priority.

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

Implementation note for current priority: the first user-visible Ghost should not be delayed by non-critical FBX polish if `.ma`, `.usda`, and `.ply` are already sufficient to let the user inspect the point cloud in Maya. FBX remains part of the Stage 8/production contract, but the first tangible point-cloud judgment comes first.

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

Timing note: Stage 9 remains approved, but it must not block the first integrated Ghost. Before the first tangible Ghost exists, use best-known defaults. Run the full benchmark/preset-freeze effort only after the user has judged the first integrated point-cloud result as promising enough to continue.

## Stage 10 — Atlas relief mesh

Stage 10 is an OPTIONAL E1 branch. It does not replace the Canonical Point Cloud. In current execution priority, Stage 10 is architecturally approved but practically deferred until the core point-cloud Ghost has passed the first tangible usability gate.

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

MoGe mesh remains an independent optional branch. Failure never invalidates the core Ghost. Practical implementation priority is deferred until the core point-cloud Ghost has proven useful enough to justify serious mesh work.

Approved Stage 11 architecture:
- preserve MoGe native mesh independently from the normalized point-cloud path;
- obey the Stage 9 Auto-FOV vs Atlas-FOV decision rather than making a second camera-policy decision;
- canonicalize the native mesh into the same ConceptGhost scene space;
- add a Mesh-to-Ghost Consistency Gate distinct from reprojection and Geometry Health;
- characterize discontinuity behavior without brute-force parameter sweeps;
- classify `useful | limited | reject`;
- include in Maya/FBX only when classification permits it.

See `docs/superpowers/specs/2026-09-16-conceptghost-stage11-moge-mesh-design.md`.

## Stage 12 — DA3 mesh

DA3 mesh remains an independent optional branch. Failure never invalidates the core Ghost. Practical implementation priority is deferred until the core point-cloud Ghost has proven useful enough to justify serious mesh work.

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
- Max Reference = default preset, interpreted for now as the best-known upstream/public default rather than a fully benchmark-frozen optimum.
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
