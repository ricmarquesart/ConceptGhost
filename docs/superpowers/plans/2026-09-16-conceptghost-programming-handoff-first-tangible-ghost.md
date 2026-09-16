# ConceptGhost — Programming Handoff: First Tangible Ghost

Date: 2026-09-16
Status: IMMEDIATE EXECUTION PRIORITY

Read first:

```text
docs/superpowers/specs/2026-09-16-conceptghost-execution-priority-first-tangible-ghost.md
G:\My Drive\ConceptGhost\Documentation\Roadmap\2026-09-16-conceptghost-stage6-8-vertical-slice-plan.md
docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
```

## One instruction

Build the first integrated Ghost before refining it.

Immediate target:

```text
one image
-> ConceptGhost_Master.json
-> Atlas Camera Auto
-> DA3
-> ConceptGhost Normalizer
-> Canonical Colored Point Cloud
-> pointcloud.ply
-> Ghost.usda
-> Ghost.ma
-> user opens Maya and judges usefulness
```

Default first-run settings:

```text
Preset = Max Reference
Camera = Auto
Geometry = DA3
Compare Both = OFF
```

For now, `Max Reference` means the best-known stable upstream/public configuration already supported by the preserved references. It does not mean "wait until Stage 9 proves every number".

Do not spend primary time before the first Ghost on:
- mesh generation;
- mesh repair/retopo;
- full Stage 9 benchmark;
- broad threshold sweeps;
- cosmetic UI polish.

Tests before the user judgment should answer only:
- does the code/node load?
- does the workflow run?
- is camera space coherent?
- are PLY/USDA/MA generated?
- does the Maya scene open and show the Ghost?

When the first Ghost is ready, STOP and present it for:

```text
PASS | MARGINAL | FAIL
```

The user's criterion is whether the point cloud helps estimate distance, proportion, shape, relative height, and blockout placement.

Stages 10-12 remain designed but implementation-deferred until that judgment.

## Existing detailed execution plan

Do not create a competing Stage 6–8 plan. The detailed vertical-slice plan already exists on Google Drive:

```text
G:\My Drive\ConceptGhost\Documentation\Roadmap\2026-09-16-conceptghost-stage6-8-vertical-slice-plan.md
```

Drive file ID:

```text
1PLQF7cZx11y5_m2YbqaQF7jwyxX8-4R-
```

Use that plan as the detailed implementation checklist, with the new First Tangible Ghost priority directive taking precedence on sequencing: get the point-cloud Ghost in front of the user before fine benchmark or mesh work.
