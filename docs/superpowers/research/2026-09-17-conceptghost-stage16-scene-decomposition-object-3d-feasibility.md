# ConceptGhost — Stage 16 Scene Decomposition + Object 3D Reconstruction Feasibility

Date: 2026-09-17
Status: APPROVED RESEARCH GATE — implementation deferred until Stage 15 is complete
Project: ConceptGhost

## 1. Purpose

Stage 16 is a post-Stage-15 feasibility gate. It does **not** alter Stages 0–15 and does not replace the existing camera + point-cloud + 2.5D mesh pipeline.

The question is narrower:

> Can ConceptGhost take a complete scene image, identify/separate several visible objects, generate a finite 3D object for each selected instance, and place/scale those objects back into the ConceptGhost Canonical Scene strongly enough to improve blockout beyond the existing 2.5D outputs?

The target is useful blockout, not perfect hidden-side reconstruction and not production topology.

## 2. Hard constraints approved by the user

Hardware target:

```text
GPU: NVIDIA RTX 2080 Ti
physical VRAM: 11 GB
safe planning target: <= ~9–9.5 GB peak whenever practical
OS: Windows
orchestration: ComfyUI preferred/required for normal adoption
```

A candidate remains eligible only if:

1. it fits realistically on the 11 GB card, or has a documented low-VRAM/offload mode that plausibly fits;
2. public source code exists on GitHub;
3. a ComfyUI implementation/workflow already exists, or integration is unusually small and well documented;
4. there is concrete evidence of output: official/project demo, video, published examples, paper/project page, or reproducible workflow;
5. it contributes to a plausible chain of `scene -> instances/masks -> object 3D -> position/scale in scene`.

Research papers that require 24–32 GB+ are architectural references only, not runtime candidates.

## 3. Important VRAM policy

The full Stage 16 pipeline must be **sequential**, not resident-at-once:

```text
segmentation/detection
-> save masks/crops
-> unload segmentation models
-> load one 3D reconstruction model
-> reconstruct object A
-> save/unload temporary state
-> reconstruct object B
-> ...
-> ConceptGhost alignment/assembly
```

Do not budget VRAM as if GroundingDINO/SAM2, DA3/MoGe, and an object generator must coexist simultaneously.

## 4. Candidate matrix

| Candidate | Function | Public GitHub | ComfyUI workflow | VRAM evidence | Real output evidence | Stage16 status |
|---|---|---:|---:|---|---:|---|
| GroundingDINO + SAM2 (`ComfyUI-SAM2`) | scene/object masks | yes | yes | lightweight model family; explicit unload support | example workflow/public repo | **GO — front end** |
| PartCrafter-Scene | scene -> multiple object/part meshes | yes | yes, ComfyUI-3D-Pack | official minimum 8 GB; reduce parts/tokens | NeurIPS project + repo + scene workflow + video | **EXPERIMENTAL / PRIORITY BASELINE** |
| Stable Fast 3D (SF3D) | masked/cropped object -> finite GLB | yes | official nodes + example workflow | ~6 GB single image | official project/video/examples | **GO — object generator** |
| SPAR3D | masked/cropped object -> finite textured mesh | yes | official nodes + example workflow | ~7 GB low-VRAM mode; default higher | official project/examples | **GO/EXPERIMENTAL** |
| TripoSR | masked/cropped object -> finite mesh | yes | community workflow | ~6 GB | official repo/examples + ComfyUI workflows | **GO — fallback** |
| Hunyuan3D-2 / 2mini | object -> finite mesh | yes | native/community ComfyUI workflows | official low-VRAM mode; GP forks report 6–9 GB | official repo + ComfyUI examples | **EXPERIMENTAL** |
| TRELLIS.2 / Pixal3D via ComfyUI-Trellis2 | object generation | yes | yes | low-VRAM paths exist on newer GPUs | examples/issues | **NO-GO on RTX 2080 Ti for now** |
| SAM 3D Objects | masked object -> 3D with pose/layout | yes | community wrappers | official requirement >=32 GB VRAM | official code/demo/paper | **NO-GO on current hardware** |
| SceneConductor / 3D-Fixer / similar 24 GB+ research stacks | full-scene research precedent | yes | not suitable as normal ComfyUI baseline | exceeds user hardware | papers/demos/code | **REFERENCE ONLY** |

## 5. Candidate details

### 5.1 GroundingDINO + SAM2 — GO for instance/mask front end

Public ComfyUI implementation:

- https://github.com/neverbiasu/ComfyUI-SAM2

Useful properties:

- text-prompted GroundingDINO detection;
- SAM2 masks;
- multiple SAM2 checkpoint sizes;
- `keep_model_loaded` / model offload behavior in the node implementation;
- public example workflow.

Published model sizes in the wrapper include GroundingDINO SwinT at roughly 694 MB and SAM2.1 checkpoints from tiny through large. Stage 16 should begin with SwinT + SAM2.1 tiny/small, then unload them before 3D generation.

Role:

```text
source image
-> candidate object boxes
-> per-instance masks/crops
```

This component does not generate 3D. It solves the decomposition front-end.

### 5.2 PartCrafter-Scene — EXPERIMENTAL / first direct-scene baseline

Official source:

- https://github.com/wgsxm/PartCrafter

ComfyUI implementation and exact scene workflow:

- https://github.com/MrForExample/ComfyUI-3D-Pack
- `example_workflows/PartCrafter/PartCrafter-Scene.json`

The official PartCrafter repository states:

- scene-level PartCrafter is released;
- it is trained on 3D-Front;
- CUDA GPU minimum is 8 GB VRAM;
- reducing number of parts or tokens reduces memory;
- Windows installation guidance exists through a community fork.

The ComfyUI-3D-Pack workflow is a real one-shot scene baseline:

```text
LoadImage
-> Load PartCrafter Scene Pipeline
-> PartCrafter Generate
   -> parts_zip_path
   -> merged scene GLB
```

The pack documents a `PartCrafter-Scene.mp4` demonstration and produces a ZIP of individual object meshes plus a merged scene mesh.

Why it is not classified unconditional GO:

- scene model training is 3D-Front-oriented, therefore indoor/furniture biased;
- ConceptGhost target images include outdoor/stylized streets, trees, cars and architecture;
- existing result evidence does not prove robust outdoor concept-art reconstruction.

Therefore PartCrafter-Scene is the **first unchanged baseline to test**, not an assumed production solution.

### 5.3 Stable Fast 3D — GO as primary modular object generator

Official source:

- https://github.com/Stability-AI/stable-fast-3d

Evidence:

- official repo reports about 6 GB VRAM for one image;
- official ComfyUI custom nodes and example workflow are included;
- Windows support is documented as experimental;
- Stability AI publishes examples/video and describes output as UV-unwrapped mesh + material information.

ConceptGhost role:

```text
instance mask/crop
-> isolated object image
-> SF3D
-> finite object GLB
```

This is currently the cleanest low-VRAM candidate for the modular branch.

### 5.4 SPAR3D — GO/EXPERIMENTAL second object generator

Official source:

- https://github.com/Stability-AI/stable-point-aware-3d

Evidence:

- official low-VRAM mode reduces usage to roughly 7 GB according to the project code/docs;
- official ComfyUI loader/sampler/save nodes are present;
- example workflow is provided;
- Windows support is experimental;
- output is a finite textured/UV-unwrapped 3D object.

Stage16 role: A/B against SF3D only if installation is dependency-safe.

### 5.5 TripoSR — GO fallback

Official source:

- https://github.com/VAST-AI-Research/TripoSR

ComfyUI wrapper:

- https://github.com/flowtyone/ComfyUI-Flowty-TripoSR

Evidence:

- official repo reports about 6 GB VRAM;
- community ComfyUI wrapper includes `workflow_simple.json` and `workflow_rembg.json`;
- simple image/mask -> mesh path.

Role: lower-risk fallback if newer object generators conflict with the protected ComfyUI environment.

### 5.6 Hunyuan3D-2 / 2mini — EXPERIMENTAL

Official source:

- https://github.com/Tencent-Hunyuan/Hunyuan3D-2

Evidence:

- official code supports `--low_vram_mode`;
- ComfyUI has Hunyuan3D-2 single-view/multiview example workflows;
- GPU-poor community forks document memory profiles in the ~6–9 GB range.

Why experimental rather than GO:

- the exact low-memory community path and the normal/native ComfyUI path are not identical;
- dependency/runtime compatibility must be proven on the protected RTX 2080 Ti machine before adoption.

Stage16 may test **shape generation only** first. Texture is not needed to decide blockout feasibility.

### 5.7 TRELLIS.2 / Pixal3D — NO-GO on current machine for Stage16 baseline

ComfyUI wrapper exists:

- https://github.com/visualbruno/ComfyUI-Trellis2

However, current evidence shows substantial CUDA-extension/architecture sensitivity. The project depends on components such as FlexGEMM/o-voxel/nvdiffrast, and compatibility discussions center on rebuilding for specific compute capabilities. An open ComfyUI-Trellis2 issue specifically requests SM 7.5 support after an RTX 2060/Turing card fails with `CUDA error: no kernel image is available for execution on the device`. The RTX 2080 Ti is also Turing / SM 7.5, so this is not a safe protected-machine baseline even if low-memory configurations work on newer GPUs.

Decision:

```text
NO-GO for initial Stage16 on RTX 2080 Ti.
Revisit only if an SM 7.5/Turing path is explicitly demonstrated and reproducible.
```

Do not spend Stage16 time creating a custom CUDA port just to reach the baseline.

### 5.8 SAM 3D Objects — NO-GO current hardware

Official source:

- https://github.com/facebookresearch/sam-3d-objects

Official setup prerequisites require Linux x64 and an NVIDIA GPU with at least **32 GB VRAM**.

ComfyUI/community wrappers do not change the official hardware fact sufficiently for the 11 GB target.

Decision: **NO-GO**. It may remain an architectural reference because its masked-object/layout formulation is relevant, but it is not a runtime candidate on this machine.

## 6. Stage 16 recommended experiment architecture

Do not start with a new large custom system. Test two branches.

### Branch A — direct scene baseline

```text
source image
-> PartCrafter-Scene unchanged ComfyUI example
-> individual object meshes ZIP
-> merged scene GLB
-> inspect camera-view + free-view usefulness
```

Why first:

- shortest proof/disproof;
- already a complete ComfyUI workflow;
- minimum VRAM claim fits the machine;
- gives immediate evidence whether one-shot scene decomposition has any value on our concepts.

Test three image categories:

1. indoor/furniture scene similar to 3D-Front — control;
2. outdoor street image with car/tree/building;
3. stylized concept-art scene.

If it only succeeds on the first category, keep it as research evidence but do not integrate it into ConceptGhost production.

### Branch B — modular general scene decomposition

```text
ConceptGhost source image
        |
        +-> GroundingDINO + SAM2
        |      -> per-instance masks/crops
        |
        +-> existing Canonical Point Cloud + Atlas Camera
               -> spatial evidence per mask

for each selected instance, sequentially:
mask/crop
-> SF3D primary
   or SPAR3D A/B
   or TripoSR fallback
-> finite generated object
-> unload generator state as needed

object + masked canonical point subset
-> ConceptGhost Object Anchor Fit
-> position / uniform scale / optional orientation
-> matched-camera silhouette check
-> canonical scene
```

The essential ConceptGhost-specific contribution is **not** another 3D generator. It is the anchoring layer:

```text
2D instance mask
-> select Canonical Point Cloud points whose source_uv is inside mask
-> robust 3D centroid / depth median
-> ground contact if available
-> robust extent/PCA evidence
-> fit generated object's bbox to the observed fragment
-> project candidate object through Atlas camera
-> compare projected silhouette to mask
```

This uses the existing 2.5D Ghost as the spatial scaffold rather than throwing it away.

## 7. What Stage 16 does not promise

Even if Stage 16 receives GO:

- generated backsides are hypotheses;
- generated object identity can be wrong;
- trees/foliage remain difficult;
- buildings are not guaranteed to become architectural CAD blocks;
- overlapping objects may segment incorrectly;
- object generator canonical orientation may differ from source orientation;
- exact metric scale is not guaranteed without the ConceptGhost anchor;
- scene-wide consistency is not automatic merely because every object looks good independently.

## 8. Feasibility test set

Minimum test uses one image for each:

```text
A. indoor scene / furniture control
B. outdoor street with obvious car + tree + building
C. stylized concept environment
```

For B/C select 3–5 objects, not every visible object.

Suggested initial target classes:

```text
car
large tree
street furniture / lamp / sign
isolated building mass when segmentation is clean
one medium foreground prop
```

Do not begin with foliage clusters, crowds, tiny props, or transparent objects.

## 9. Stage 16 acceptance gate

### Hardware gate

PASS only if the tested workflow can complete repeatedly on the RTX 2080 Ti without OOM under a documented profile. Target peak should leave practical headroom rather than using all physical VRAM.

### ComfyUI gate

PASS only if the normal experiment can be run from ComfyUI. Separate helper scripts may perform deterministic alignment/export, but the user-facing orchestration remains ComfyUI.

### Scene-decomposition gate

On at least one B/C test scene:

```text
>= 3 useful instance masks
>= 3 finite object meshes attempted
>= 2 object meshes visually recognizable enough for blockout
```

### Spatial reassembly gate

For at least two generated objects:

- object location is anchored by the corresponding ConceptGhost masked point subset;
- scale is bounded/plausible relative to that subset;
- matched-camera projection overlaps the source object enough for practical placement;
- objects do not simply sit at arbitrary generator origin/scale.

### Artist-value gate

The user must judge at least one assembled scene as providing **meaningfully more free-view blockout information** than the existing point cloud + 2.5D meshes.

## 10. Decision semantics

### GO

Use only when:

- hardware gate passes;
- ComfyUI gate passes;
- decomposition + object generation works on relevant concept scenes;
- spatial anchoring works well enough to preserve scene relationships;
- free-view blockout value is clearly above the 2.5D baseline.

GO means Stage 16 may become an optional post-V1 subsystem. It does not replace the core pipeline.

### EXPERIMENTAL

Use when:

- some candidates work;
- hardware fits;
- but domain generalization, object placement or installation reliability is inconsistent.

Keep it as an optional lab branch with no production promise.

### NO-GO

Use when:

- practical RTX 2080 Ti execution is not stable;
- ComfyUI integration requires a fragile parallel environment;
- scene decomposition/generation is poor on outdoor/stylized concepts;
- generated meshes cannot be anchored reliably;
- result does not provide clear blockout value over current 2.5D outputs.

## 11. Current research recommendation — 2026-09-17

Current classification before local testing:

```text
GO TO BASELINE TEST
- GroundingDINO + SAM2 front end
- Stable Fast 3D per-object generator
- TripoSR fallback

GO / EXPERIMENTAL
- SPAR3D low-VRAM

EXPERIMENTAL / FIRST DIRECT-SCENE BASELINE
- PartCrafter-Scene

EXPERIMENTAL
- Hunyuan3D-2mini / low-VRAM shape-only path

NO-GO ON CURRENT RTX 2080 Ti BASELINE
- SAM 3D Objects (official >=32 GB)
- TRELLIS.2 / Pixal3D until an explicit stable SM 7.5/Turing path exists
- research stacks that require 24 GB+ VRAM
```

The recommended first Stage16 experiment sequence is:

```text
1. PartCrafter-Scene unchanged ComfyUI baseline
2. GroundingDINO+SAM2 -> masks
3. SF3D -> per-object finite meshes
4. ConceptGhost masked point-cloud anchoring
5. A/B SPAR3D only if SF3D shows value
6. TripoSR as compatibility fallback
7. Hunyuan3D low-VRAM only if additional quality is justified
```

Do not install/test any Stage16 candidate until Stage15 is complete unless the user explicitly reorders priorities.

## 12. Evidence links

PartCrafter / PartCrafter-Scene:
- https://github.com/wgsxm/PartCrafter
- https://github.com/MrForExample/ComfyUI-3D-Pack
- https://github.com/MrForExample/ComfyUI-3D-Pack/blob/main/example_workflows/PartCrafter/PartCrafter-Scene.json

GroundingDINO + SAM2 in ComfyUI:
- https://github.com/neverbiasu/ComfyUI-SAM2

Stable Fast 3D:
- https://github.com/Stability-AI/stable-fast-3d
- https://stability.ai/news-updates/introducing-stable-fast-3d

SPAR3D:
- https://github.com/Stability-AI/stable-point-aware-3d
- https://stability.ai/stable-3d

TripoSR:
- https://github.com/VAST-AI-Research/TripoSR
- https://github.com/flowtyone/ComfyUI-Flowty-TripoSR

Hunyuan3D-2:
- https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- low-memory reference only: https://github.com/ovidVR/Hunyuan3D-2GP

TRELLIS.2 ComfyUI compatibility evidence:
- https://github.com/visualbruno/ComfyUI-Trellis2
- https://github.com/visualbruno/ComfyUI-Trellis2/issues/109

SAM 3D Objects official setup:
- https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md

## 13. One-line Stage 16 instruction

> After Stage 15, evaluate scene decomposition plus per-object finite 3D reconstruction on the RTX 2080 Ti using only public, evidence-backed, ComfyUI-compatible or near-ComfyUI candidates; test PartCrafter-Scene as the one-shot baseline and GroundingDINO+SAM2 -> SF3D/SPAR3D/TripoSR as the modular path, anchor generated objects back into the Atlas/Canonical Point Cloud scene, and classify the entire Stage 16 effort GO, EXPERIMENTAL, or NO-GO based on hardware fit and real blockout value rather than paper claims.
