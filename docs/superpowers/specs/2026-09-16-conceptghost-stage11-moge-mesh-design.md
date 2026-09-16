# ConceptGhost — Stage 11 MoGe Mesh Design

Date: 2026-09-16
Status: APPROVED architecture, IMPLEMENTATION DEFERRED behind Point Cloud Usability Gate
Project: ConceptGhost

> Stage 11 is architecturally defined now so the roadmap is complete, but serious implementation work must wait until the first tangible point-cloud Ghost has been judged useful enough to justify mesh work.

Read together with:

```text
docs/superpowers/specs/2026-09-16-conceptghost-execution-priority-first-tangible-ghost.md
docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage9-benchmark-preset-design.md
```

## 1. Goal

Stage 11 evaluates MoGe's native mesh as OPTIONAL E2 geometry.

Core product remains:

```text
Atlas Camera
+ Canonical Colored Point Cloud
+ Maya Ghost
```

Stage 11 may later add:

```text
OPTIONAL E2
MoGe Mesh
```

A MoGe mesh must never replace or invalidate a good point-cloud Ghost.

## 2. Preserve two independent MoGe products

MoGe can contribute two different geometry paths:

```text
MoGe depth/point map
-> ConceptGhost Normalizer
-> Canonical Point Cloud

MoGe native mesh
-> MoGe Mesh Adapter
-> Optional Canonical MoGe Mesh
```

Do not generate the Stage 11 mesh by triangulating the ConceptGhost point cloud and call it "MoGe native mesh".

Preserve native provenance.

## 3. Respect the Stage 9 FOV/camera policy

Stage 11 does not independently decide whether MoGe should use Auto FOV or Atlas FOV. It obeys the Stage 9 decision.

If Stage 9 adopts Atlas-FOV conditioning:

```text
Atlas camera/FOV
-> MoGe inference
   ├-> point/depth evidence
   └-> native mesh
```

Both products must come from the same camera interpretation.

Avoid:

```text
point cloud = Atlas-FOV-conditioned MoGe
mesh = Auto-FOV MoGe
```

unless explicitly generated as a diagnostic comparison.

## 4. Native mesh first

First baseline is the official/native MoGe mesh workflow already preserved by the project.

Preserve:

```text
meshes/
└── moge/
    ├── native/
    │   ├── moge_native.glb
    │   ├── native_parameters.json
    │   └── native_report.json
    ├── canonical/
    │   ├── moge_mesh.*
    │   └── conversion_report.json
    └── evaluation/
        └── moge_mesh_evaluation.json
```

Exact native file extension may follow the proven upstream workflow.

## 5. Canonical-space conversion

The native MoGe mesh must be adapted into ConceptGhost Canonical Scene space.

Validate:

```text
handedness
axis convention
camera orientation
scale mode
world transform
source-image relationship
```

No silent axis flip inside the final exporter.

## 6. Mesh-to-Ghost Consistency Gate

Stage 11 introduces a separate validation question:

```text
Does the canonicalized MoGe mesh occupy approximately
the same scene structure as the canonical MoGe point cloud?
```

This is not the same as reprojection.

Three distinct checks exist:

```text
Reprojection
-> integration math

Geometry Health
-> point-cloud health

Mesh-to-Ghost Consistency
-> native mesh and canonical point cloud spatial agreement
```

Large disagreement indicates likely transform, scale, FOV, projection, or normalization error before artistic evaluation.

## 7. Discontinuity behavior

Foreground/background discontinuities must not become long artificial sheets.

Study only a small progressive set:

```text
native/default
slightly more conservative
slightly more aggressive
```

Do not run broad brute-force sweeps.

Record holes, stretched triangles, streamers, silhouette behavior, foreground/background separation, and large-surface continuity.

## 8. Decimation is optional

Start from the native mesh. Only test decimation after proving the native mesh is useful enough to justify it.

Measure triangle count, file size, Maya load time, viewport responsiveness, and visual change for blockout. Do not simplify merely to hit an arbitrary polygon target.

## 9. Texture/material role

If the upstream MoGe workflow produces texture/material data, preserve it as a visual reference. Its purpose is identifying which mesh region corresponds to which concept region, not production LookDev.

## 10. Normals

Preserve useful native normals where available. Do not add an automatic normals-correction subsystem in Stage 11 unless evidence shows it is necessary.

## 11. Maya integration

Reuse Stage 8 hierarchy:

```text
CG_REFERENCE
└── MoGe_Ghost

CG_OPTIONAL_MESH
└── MoGe_Mesh
```

Default presentation:

```text
useful  -> normal optional artist asset
limited -> preserved, hidden by default
reject  -> evidence only, not trusted scene geometry
```

## 12. Classification

Use:

```text
useful | limited | reject
```

`useful`: aligns with Ghost/camera, helps blockout, and major artifacts are not misleading.

`limited`: useful in some regions/angles while known 2.5D/topology limitations remain.

`reject`: misleading topology/depth, severe scale/axis/FOV mismatch, or more harmful than helpful.

Generated is not equivalent to useful.

## 13. Failure isolation

If the point cloud is good but the mesh is bad, investigate meshing, discontinuity threshold, topology generation, and mesh export.

If both point cloud and mesh are bad, investigate earlier depth/FOV/camera conditioning/inference.

This separation is one of the main diagnostic values of Stage 11.

## 14. FBX behavior

Only include the MoGe mesh in normal FBX when its classification permits it.

Record:

```text
moge_mesh_included
moge_mesh_classification
moge_mesh_source_mode
```

Rejected mesh must not masquerade as normal deliverable geometry.

## 15. Performance evidence

Record native/canonical vertex and face counts, file size, Maya load time, viewport responsiveness, and decimated values if tested.

## 16. Stage 11 PASS

Stage 11 development passes when:

```text
official/native MoGe mesh is reproduced
+ native evidence is preserved
+ Stage 9 FOV/camera policy is respected
+ canonical conversion is verified
+ Mesh-to-Ghost consistency is characterized
+ discontinuity behavior is characterized
+ Maya performance is characterized
+ useful|limited|reject classification works
= STAGE 11 PASS
```

Stage 11 PASS does not mean every image must produce a useful mesh.

## 17. Execution priority

```text
DO NOT IMPLEMENT STAGE 11 SERIOUSLY
until FIRST TANGIBLE GHOST has been judged promising.
```

The point cloud is the decision gate.

## 18. One-line implementation instruction

> Preserve MoGe native mesh as a separate optional product, canonicalize it under the same Stage 9 camera/FOV policy as the point-cloud path, validate Mesh-to-Ghost consistency, classify it `useful | limited | reject`, and defer serious Stage 11 implementation until the core point-cloud Ghost has proved useful enough to justify mesh work.
