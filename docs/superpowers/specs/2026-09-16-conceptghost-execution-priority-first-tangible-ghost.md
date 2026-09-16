# ConceptGhost — Execution Priority Reset and First Tangible Ghost Gate

Date: 2026-09-16
Status: APPROVED execution-priority directive
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ BEFORE NEW IMPLEMENTATION WORK

This document changes execution priority. It does not replace the approved technical architecture, but it changes what must be implemented first and what must wait until the first tangible result is judged by the user.

Read together with:

```text
docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md
docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md
docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage9-benchmark-preset-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage10-atlas-relief-mesh-design.md
```

---

## 1. Why this directive exists

ConceptGhost has accumulated enough approved architecture, upstream reference code, and documentation. The immediate problem is no longer lack of design detail.

The immediate problem is lack of one integrated, user-judgable result.

The user has explicitly stated that the next critical milestone is **not perfection**. It is a working end-to-end run that generates a usable point-cloud-based Ghost from one image with the best-known defaults already configured.

The user's decision to continue or stop investing in this project depends on evaluating that first integrated result.

Therefore the project must now optimize for:

```text
first tangible result
before
fine refinement
```

## 2. New top priority milestone

Create:

```text
MILESTONE A — FIRST TANGIBLE GHOST
```

Definition:

```text
one image
-> one production-style Master workflow run
-> Atlas camera
-> DA3 or MoGe geometry evidence
-> ConceptGhost normalizer
-> canonical colored point cloud
-> artist-usable Maya Ghost package
```

This is the first milestone that the user will judge as either:

```text
promising enough to continue
or
too weak to justify more refinement
```

## 3. User experience target

The immediate target experience is:

```text
Load Image
-> leave best-known defaults in place
-> click Run
-> get result package
-> open .ma in Maya
-> inspect camera + point cloud Ghost
```

The user must not need to manually assemble Atlas, DA3, MoGe, normalization, PLY, USDA, or Maya handoff.

The complexity belongs inside the workflow, not in the user's operation.

## 4. Best-known defaults now, benchmark refinement later

For the first tangible result, the project should use **best-known defaults** based on:

```text
upstream official workflows
upstream official code
preserved public reference code
already-researched practical usage notes
```

Do NOT block the first integrated Ghost on a full benchmark campaign.

The first integrated Ghost does not require the mathematically optimal final preset values. It requires stable, reasonable, defensible, reproducible values. Later benchmark work may refine them.

## 5. New implementation order

The effective critical path is now:

```text
Stage 6  Master Workflow
-> Stage 7  Canonical Integration / Normalizer
-> Stage 8  Maya / PLY / USDA first artist handoff
-> FIRST TANGIBLE GHOST GATE
```

Only after the user judges this result do we spend serious time on:

```text
Stage 9  benchmark/preset refinement
Stage 10 Atlas relief mesh
Stage 11 MoGe mesh
Stage 12 DA3 mesh
```

## 6. What MUST happen before the first user judgment

Immediate required deliverables:

```text
P0 one integrated ConceptGhost_Master.json
P1 canonical colored point cloud
P2 pointcloud.ply + Ghost.usda + Ghost.ma
P3 Maya usability for artist judgment
```

The `.fbx` companion remains part of Stage 8 and the production package, but it must not delay the first visual judgment of the point-cloud Ghost if camera + PLY + USDA + MA are already functioning.

## 7. Point Cloud Usability Gate

The core go/no-go criterion is:

```text
POINT CLOUD USABILITY GATE
```

Question:

> Can this Ghost point cloud help estimate distance, proportion, shape, scale relationship, and height well enough to support manual blockout in Maya?

Possible outcomes:

```text
PASS     -> continue project and refine
MARGINAL -> continue, prioritize only major defects
FAIL     -> user decides whether the project still deserves continuation
```

This gate is artist-judged, not automatically scored.

## 8. What should NOT block the first tangible result

Do not delay the first integrated Ghost for:

```text
small threshold optimization
hole-count polishing
mesh retopology
repair variants
optional mesh cleanup
full A/B benchmark campaigns
extensive parameter sweeps
non-critical UI polish
```

Do not optimize the last 10% before proving the first 60–80% is useful.

## 9. Test policy before Milestone A

Necessary tests only:

```text
node/code loads
workflow executes without exception
required files are generated
camera and point cloud share the expected space
Maya handoff opens
```

Defer multi-image benchmark sessions, fine preset calibration, mesh quality comparisons, and parameter-grid experiments.

## 10. Stage 9 role is deferred, not removed

Before Milestone A, use best-known defaults. After Milestone A, if the Ghost is promising, run controlled benchmark/refinement and freeze better presets.

Stage 9 is no longer a blocker for the first user-visible Ghost.

## 11. Mesh stages are blocked behind point-cloud usefulness

Stages 10-12 remain architecturally approved, but they are no longer implementation-priority work until the point cloud proves useful enough.

```text
No serious mesh implementation effort
until the core point-cloud Ghost passes the usability gate
or is at least clearly promising.
```

## 12. Programming-chat directive

> Stop spending primary effort on fine refinement, benchmark depth, or optional mesh implementation before the first end-to-end Ghost exists. Use the preserved upstream/public code and the approved ConceptGhost specifications to build one integrated `ConceptGhost_Master.json` that runs from one image to one aligned canonical point-cloud Ghost with best-known defaults. The immediate success criterion is not perfection; it is producing a point cloud the user can judge in Maya for manual blockout usefulness.

## 13. Required implementation focus

```text
Atlas Camera Auto
Geometry = DA3 first
Normalizer
PLY
USDA
MA
```

Keep advanced controls secondary, preserve all dependency-safety/non-overwrite rules, and use saved upstream/reference code as implementation sources rather than research-only archives.

## 14. Concrete immediate target configuration

```text
Preset   = Max Reference (best-known default, not benchmark-perfect)
Camera   = Auto
Geometry = DA3
Compare Both = OFF
```

MoGe remains selectable or available for later comparison, but it must not delay the first DA3-based integrated Ghost unless DA3 is blocked.

## 15. Minimal first-result success definition

Milestone A succeeds when:

```text
one image can be loaded
one integrated run can be executed
Atlas camera resolves
geometry is normalized into canonical space
a colored point cloud is generated
pointcloud.ply is generated
Ghost.usda is generated
Ghost.ma is generated
the Maya scene opens
the user can inspect the Ghost and judge usefulness
```

It does not require perfect presets, best-in-class mesh, all optional branches, full benchmark evidence, or final production polish.

## 16. After Milestone A

If promising:

```text
refine point cloud quality first
then benchmark/preset freeze
then optional mesh branches
then final packaging freeze
```

If too weak, evaluate whether a major blocker is fixable, whether the project should stop, or whether future Stage 15 alternatives deserve a later trial.

## 17. One-line directive

> ConceptGhost must now prioritize one integrated, user-judgable, image-to-point-cloud Maya Ghost result above further refinement detail; benchmark depth and mesh work are real but deferred until the first tangible Ghost proves the project is worth continuing.
