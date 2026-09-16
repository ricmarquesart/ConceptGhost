# ConceptGhost Roadmap Addendum — Master Workflow Integration

Date: 2026-09-16
Status: Approved integration policy; updated with mandatory output/handoff gate

This addendum clarifies how Stages 3-14 converge into one final user-facing workflow.

## MANDATORY DEVELOPMENT READ GATE

Before implementing or modifying Stages 6-13, read and reconcile:

```text
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md
```

Before Stage 8 Maya/export work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-output-handoff-contract.md
```

If older documentation conflicts with these files, stop and reconcile the conflict before implementation.

## Stage convergence

### Stages 3-5 — public baselines first
- Stage 3: Atlas camera baseline.
- Stage 4: DA3 upstream `advanced_3d.json` unchanged.
- Stage 5: official/native MoGe baseline unchanged.

Do not hide an upstream failure behind ConceptGhost adapters.

### Stage 6 — Master Alpha
Create one `ConceptGhost_Master.json` with:
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

### Stage 7 — canonical integration
Create:
- CameraBundle;
- GeometryBundle;
- CanonicalGeometry;
- SceneBundle;
- coordinate/scale conventions;
- mandatory reprojection gate.

Atlas is camera authority.
DA3/MoGe supply depth/shape evidence.
Original image supplies color.
ConceptGhost Canonical Scene is final-space authority.

### Stage 8 — first complete artist handoff
Generate the Maya Ghost and all standard companion formats together:

```text
ConceptGhost_<scene>_Ghost.ma
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.fbx
pointcloud.ply
```

These are not mutually exclusive choices.

`.ma` is the normal Maya entry point.
`.usda` is the primary technical dense-Ghost representation.
`.fbx` is the camera/mesh portability companion.
`.ply` is the portable Canonical Point Cloud.

FBX point-cloud limitations must be respected; do not claim point-cloud equivalence with USD/PLY.

### Stage 9 — A/B benchmark
DA3 versus MoGe under the same Atlas camera and canonical conventions.

Use evidence to freeze Max Reference / Balanced / Fast Test values.

### Stages 10-12 — optional meshes
- Stage 10: Atlas relief mesh.
- Stage 11: MoGe mesh.
- Stage 12: DA3 mesh.

Classify each mesh `useful | limited | reject`.

Optional mesh failure does not invalidate a valid canonical Ghost.

### Stage 13 — final packaging
Freeze:
- one production Master workflow;
- multi-format handoff contract;
- dependency-safe installer/uninstaller;
- documentation;
- acceptance tests;
- storage/non-overwrite policy.

### Stage 14 — future camera extension
PCS/fSpy/manual advanced camera path after the core V1 is stable.

## Runtime rules that development must preserve

- Camera Auto = Atlas Learned first, Atlas VP only after quality-gate failure.
- DA3 default, MoGe selectable, no silent geometry fallback.
- Compare Both is independent comparison, never implicit fusion.
- Primary-fails/secondary-passes => PARTIAL; secondary is not promoted.
- Max Reference is the default preset.
- Maya Ghost, Canonical Point Cloud, manifest, reprojection report, and reprojection overlay are mandatory core outputs.
- Extra diagnostics and optional meshes may remain optional.
- Each run gets a unique run ID.
- Never overwrite or automatically delete earlier runs.
- Disk-space preflight before expensive Max Reference processing.

## Production success semantics

The final package distinguishes:

```text
maya_ghost_ready
deliverable_package_complete
run.status
```

A complete production result targets:

```text
valid Atlas Camera
+ valid Canonical Geometry
+ Reprojection PASS
+ usable .ma/.usda Maya Ghost
+ required .fbx companion
+ required .ply companion
= complete ConceptGhost production result
```
