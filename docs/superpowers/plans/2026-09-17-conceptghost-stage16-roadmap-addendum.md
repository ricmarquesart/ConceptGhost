# ConceptGhost Roadmap Addendum — Stage 16 Scene Decomposition + Object 3D Feasibility

Date: 2026-09-17
Status: APPROVED ROADMAP EXTENSION

This document extends `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md` directly **after Stage 15**. It does not modify Stages 0–15 and does not change the V1 camera, point-cloud, Maya or 2.5D mesh goals.

## Stage order extension

```text
Stage 14 — PCS/fSpy/manual camera extension
Stage 15 — alternative geometry/camera engine evaluation / technology watch
Stage 16 — scene decomposition + per-object finite 3D reconstruction feasibility
```

## Stage 16 — Scene Decomposition + Object 3D Reconstruction Feasibility

Stage 16 starts only after Stage 15 is complete unless the user explicitly reorders priorities.

Purpose:

```text
existing ConceptGhost source image
+ Atlas camera
+ Canonical Point Cloud / 2.5D scene evidence
        ↓
scene/object decomposition
        ↓
finite 3D object generation per selected instance
        ↓
position / scale / optional orientation anchored back to ConceptGhost
        ↓
assembled optional 3D blockout scene
```

Stage 16 is a **feasibility gate**, not a promised production subsystem.

### Hard machine constraints

Target machine:

```text
GPU = RTX 2080 Ti
physical VRAM = 11 GB
OS = Windows
orchestration = ComfyUI
```

Candidate inclusion requires:

1. realistic operation within 11 GB VRAM, or a documented low-VRAM/offload mode that plausibly fits;
2. public GitHub code;
3. existing ComfyUI workflow/nodes preferred; non-Comfy candidates survive only when integration is small and well documented;
4. real result evidence: video/demo/project page/paper examples/reproducible workflow;
5. a plausible contribution to `image -> instances/masks -> per-object 3D -> scene placement/scale`.

Any 24–32 GB+ system remains research evidence only unless a credible low-memory path is later demonstrated on comparable hardware.

### Current candidate queue

```text
GO TO BASELINE TEST
- GroundingDINO + SAM2 via ComfyUI-SAM2 — instance masks
- Stable Fast 3D — primary low-VRAM per-object generator
- TripoSR — compatibility fallback

GO / EXPERIMENTAL
- SPAR3D low-VRAM

EXPERIMENTAL / FIRST DIRECT-SCENE BASELINE
- PartCrafter-Scene through ComfyUI-3D-Pack

EXPERIMENTAL
- Hunyuan3D-2mini / low-VRAM shape-only path

NO-GO ON CURRENT RTX 2080 Ti BASELINE
- SAM 3D Objects — official >=32 GB VRAM
- TRELLIS.2 / Pixal3D until explicit stable Turing / SM 7.5 support is demonstrated
- SceneConductor / 3D-Fixer / other 24 GB+ research stacks as runtime candidates
```

### Required execution strategy

Run heavy systems sequentially:

```text
segment/detect
-> save masks/crops
-> unload detector/segmenter
-> load one object generator
-> reconstruct selected objects one at a time
-> unload as needed
-> align/assemble from saved outputs
```

Do not require segmentation + DA3/MoGe + object generator to coexist in VRAM.

### First baseline sequence

```text
A. PartCrafter-Scene unchanged ComfyUI example
   -> indoor control
   -> outdoor street
   -> stylized concept

B. Modular branch
   GroundingDINO + SAM2
   -> per-instance masks
   -> SF3D
   -> masked Canonical Point Cloud anchoring
   -> scene assembly

C. Only if B shows value
   -> SPAR3D A/B
   -> TripoSR fallback
   -> Hunyuan3D low-VRAM experiment if justified
```

### ConceptGhost anchoring rule

Generated object geometry must not be accepted at arbitrary generator origin/scale.

For every selected object:

```text
instance mask
-> use source_uv to select matching Canonical Point Cloud fragment
-> robust 3D centroid / depth / extents / ground contact
-> fit generated object translation + scale (+ orientation where justified)
-> project through Atlas camera
-> compare against source instance mask
```

The existing ConceptGhost 2.5D result is therefore retained as the spatial scaffold for Stage 16.

### Stage 16 test set

Minimum:

```text
A. indoor/furniture control
B. outdoor street: car + tree + building
C. stylized concept environment
```

For B/C, begin with 3–5 clear objects rather than every visible element.

### Stage 16 decision

Every Stage 16 research cycle ends with exactly one status:

```text
GO
EXPERIMENTAL
NO-GO
```

#### GO

Requires:
- repeated execution without OOM on RTX 2080 Ti;
- ComfyUI orchestration works;
- useful masks and finite meshes for multiple objects;
- object placement/scale can be anchored to ConceptGhost scene evidence;
- free-view blockout value is materially better than the existing 2.5D outputs.

#### EXPERIMENTAL

Hardware fits and some objects/scenes work, but outdoor/stylized generalization, placement, dependency safety or reliability remains inconsistent.

#### NO-GO

Use when hardware/integration is impractical, object reconstruction is too unreliable, spatial anchoring fails, or the result adds no meaningful blockout value above the canonical point cloud + 2.5D meshes.

## Mandatory Stage 16 research document

Before any implementation work, read:

```text
docs/superpowers/research/2026-09-17-conceptghost-stage16-scene-decomposition-object-3d-feasibility.md
```

No Stage 16 production code should be written before running the unchanged public baselines selected by that research.
