# ConceptGhost Roadmap Addendum — Master Workflow Integration

Date: 2026-09-16
Status: Approved integration policy; updated with Stage 7 refinement research and post-V1 Stage 15 technology watch

This addendum clarifies how Stages 3-15 converge into one final user-facing workflow plus a post-V1 research stage.

## MANDATORY DEVELOPMENT READ GATE

Before implementing or modifying Stages 6-13, read and reconcile:

```text
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

The consolidated research/guidance document is a required handoff to the programming chat. It contains current Stage 7 refinements, parameter-study guidance, alternative approaches, failure fallbacks, and future engine research.

Before Stage 8 Maya/export work, also read:

```text
docs/superpowers/specs/2026-09-16-conceptghost-output-handoff-contract.md
```

If older documentation conflicts with these files, stop and reconcile the conflict before implementation.

## Stage convergence

### Stages 3-5 — public baselines first

- Stage 3: Atlas camera baseline.
- Stage 4: DA3 upstream/public baseline unchanged.
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

### Stage 7 — canonical integration and camera-conditioned refinement study

Create:
- CameraBundle;
- GeometryEvidence / GeometryBundle;
- CanonicalGeometry;
- SceneBundle;
- explicit coordinate/scale conventions;
- Integration Consistency Gate;
- Geometry Health Gate.

Canonical convention:

```text
Right-handed
Y-Up
+X = right
+Y = up
-Z = camera forward
```

Authority:
- Atlas = camera/projection;
- DA3 or MoGe = depth/shape evidence;
- original image = color;
- ConceptGhost Canonical Scene = final 3D space.

Stage 7 must preserve unchanged public/native baselines first, then evaluate refinements independently:

```text
DA3:
A. public/current baseline
B. Atlas-conditioned official DA3 API using supplied intrinsics/extrinsics where safe

MoGe:
A. auto-FOV baseline
B. Atlas-FOV conditioned inference
```

Important:
- reprojection validates integration consistency, not true depth accuracy;
- Geometry Health is a separate gate;
- native evidence remains preserved separately from canonical/cleaned output;
- do not freeze parameter values from documentation or YouTube alone.

### Stage 8 — first complete artist handoff

Generate the Maya Ghost and all standard companion formats together:

```text
ConceptGhost_<scene>_Ghost.ma
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.fbx
pointcloud.ply
```

These are complementary outputs, not mutually exclusive choices.

- `.ma` = normal Maya artist entry point;
- `.usda` = primary technical dense-Ghost representation;
- `.fbx` = camera/mesh portability companion;
- `.ply` = portable Canonical Point Cloud.

Respect FBX point-cloud limitations.

### Stage 9 — controlled A/B benchmark and parameter freeze

Compare DA3 and MoGe under the same Atlas camera and canonical conventions.

Use evidence to freeze:
- Max Reference;
- Balanced;
- Fast Test.

Parameter policy:
1. upstream baseline;
2. documented/community high-quality candidate;
3. camera-conditioned candidate;
4. controlled ConceptGhost benchmark.

Also retain Depth Anything V2 Metric Outdoor as a low-cost/reference exterior baseline because Atlas itself reverted to it after a four-scene exterior A/B. Do not add it to the main V1 selector without evidence.

### Stages 10-12 — optional meshes

- Stage 10: Atlas relief mesh.
- Stage 11: MoGe mesh.
- Stage 12: DA3 mesh.

Classify each mesh:

```text
useful | limited | reject
```

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

### Stage 15 — post-V1 alternative engine evaluation / technology watch

Stage 15 starts only after Stages 3-14 are complete. It does not alter the current V1 path.

Mandatory research reference:

```text
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
```

Initial candidate queue:

```text
MoGe-3
VGGT
UniDepth V2
Depth Pro
Metric3D V2
GeoWizard
Depth Anything V2 Metric Outdoor reference baseline
newly released relevant monocular geometry systems
```

Research priority is not a quality ranking.

Each candidate must first run in isolation. If later adopted, it enters through:

```text
New Engine
→ GeometryAdapter / CameraAdapter
→ existing ConceptGhost contracts
```

Do not rewrite the V1 Normalizer or Maya/export architecture for a new model.

Evaluation includes:
- single-image suitability;
- stylized concept-art behavior;
- intrinsics/camera compatibility;
- geometry quality;
- thin structures;
- edge discontinuities;
- off-camera usefulness;
- Maya usefulness;
- VRAM/RAM/runtime;
- Windows/ComfyUI compatibility;
- license;
- dependency conflicts;
- measurable value over DA3/MoGe.

## Runtime rules that development must preserve

- Camera Auto = Atlas Learned first, Atlas VP only after camera-quality failure.
- DA3 default, MoGe selectable, no silent geometry fallback.
- Compare Both = independent comparison, never implicit fusion.
- Primary-fails/secondary-passes = PARTIAL; secondary is preserved but not promoted.
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

A complete production result targets:

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
