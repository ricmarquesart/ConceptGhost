# ConceptGhost Code Usage Map

Date: 2026-09-17
Status: Project control / reference-use audit

## Purpose

This document makes the preserved upstream code visibly auditable inside the ConceptGhost architecture.

It answers four questions for every preserved code family:

1. where it enters the pipeline;
2. whether it directly runs, contributes algorithms/contracts, or is only planned;
3. which ConceptGhost output it influences;
4. why a preserved reference is not active when applicable.

The goal is **functional reuse**, not maximizing the number of repositories executed on every run. A reference counts as useful only when it contributes runtime computation, proven upstream logic, a stable interface/contract, an export path, or a validation method that affects the same ConceptGhost result.

## Numbering note

The frozen machine-readable `references/SOURCE_LOCK.json` contains **11 distinct upstream source families**. The Google Drive `References/Upstream_Code` archive visibly contains both the live `atlas-camera` mirror and the separately pinned `atlas-camera-pinned-9f9ff451` snapshot. To preserve the user's requested 1–12 visual legend, this map assigns separate visual codes to those two Atlas folders while explicitly treating them as one upstream technology lineage.

## Pipeline map

```text
[INPUT IMAGE]
     |
     +------------------------------------------------------------------+
     |                                                                  |
     v                                                                  v
[1][2][11]                                                       source RGB
Atlas Camera + GeoCalib                                             authority
camera / FOV / gravity / pose / intrinsics                              |
     |                                                                  |
     +--------------------------+---------------------------------------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
             [3][4][5]                       [6][12]
             DA3 route                       MoGe route
             raw depth                       point map
             confidence                      mask
             sky/validity                    depth
             camera params                   normals
             edge logic                      FOV-conditioned inference
                 |                             |
                 +--------------+--------------+
                                |
                                v
                         Geometry Router
                    DA3 | MoGe | Compare Both
                  (comparison is not implicit fusion)
                                |
                                v
                           [1][2][11]
                   Atlas camera authority returns
                                |
                                v
                      ConceptGhost Normalizer
                         [5][6][11]
             Canonical Point Cloud / SceneBundle
                                |
           +--------------------+----------------------+
           |                    |                      |
           v                    v                      v
      diagnostics          [7] OpenUSD          [8] MayaUSD
 depth/conf/mask/       UsdGeomPoints /         Maya Ghost
 normals/evidence         .usda handoff         / DCC handoff
           |                    |                      |
           +--------------------+----------------------+
                                |
                                v
                       standard run package
                                |
        +-----------------------+------------------------+
        |                       |                        |
        v                       v                        v
   Stage 10                Stage 11                 Stage 12
 [1][2] Atlas          [6][12] MoGe            [3][4][5][12]
 relief mesh            native mesh             DA3/bas-relief mesh
        \                       |                        /
         +----------------------+-----------------------+
                                |
                                v
                           Stage 13
                    packaging / documentation
                                |
                                v
                           Stage 14
                           [9][10]
                    fSpy / fSpy-Blender
                    camera validation branch
                                |
                                v
                           Stage 15+
                    future solver evaluation
```

## Code legend 1–12

### [1] `atlas-camera`

**Upstream:** `mikejamesvfx/atlas-camera`

**Role:** active camera/projection runtime foundation.

**Used for:**
- Atlas Learned / Atlas VP camera solves;
- camera intrinsics/extrinsics/FOV;
- gravity/horizon/ground support exposed through Atlas;
- conditioning geometry routes where supported;
- Stage 10 native relief mesh and export logic;
- Maya/DCC camera/export patterns.

**Status:** `ACTIVE`

**Primary outputs influenced:** Camera Package, Canonical Scene, Atlas Relief, Maya handoff.

---

### [2] `atlas-camera-pinned-9f9ff451`

**Upstream lineage:** same Atlas Camera repository as [1], frozen at commit `9f9ff4511154769aa2f8c0bd40387278a69b0078`.

**Role:** immutable implementation/audit baseline, not a second competing camera solver.

**Used for:**
- reproducible reference behavior;
- exact relief-mesh defaults/algorithms;
- pinned Maya/export behavior;
- preventing documentation/runtime drift during ConceptGhost adaptation.

**Status:** `STRUCTURAL / PINNED REFERENCE`

**Why it does not run as an independent branch:** doing so would duplicate Atlas rather than add information.

---

### [3] `ComfyUI-DepthAnythingV3`

**Upstream:** `PozzettiAndrea/ComfyUI-DepthAnythingV3`

**Role:** active ComfyUI DA3 integration.

**Used for:**
- model loading;
- raw DA3 inference;
- confidence/sky/camera outputs;
- DA3 point-cloud/viewer behavior;
- Stage 12 DA3 mesh/bas-relief workflow references.

**Status:** `ACTIVE`

**Primary outputs influenced:** DA3 GeometryEvidence, Canonical Point Cloud, DA3 diagnostics, optional DA3 mesh.

---

### [4] `Depth-Anything-3`

**Upstream:** `ByteDance-Seed/Depth-Anything-3`

**Role:** official research/inference authority behind the DA3 route.

**Used for:**
- official input/output semantics;
- external camera-conditioning contract where supported;
- raw depth/camera interpretation;
- Stage 12 upstream geometry behavior.

**Status:** `STRUCTURAL + RUNTIME REFERENCE`

**Why it is not exposed as a second user-facing DA3:** [3] is the ComfyUI execution surface; [4] defines official model behavior and contracts.

---

### [5] `DA3-blender`

**Upstream:** `xy-gao/DA3-blender`

**Role:** geometry-processing algorithm donor.

**Used for now:**
- depth-edge / streamer suppression logic before canonical point creation;
- practical DA3-to-3D processing conventions.

**Planned/ongoing use:**
- Stage 12 DA3 mesh evaluation and geometry-processing comparison.

**Status:** `ACTIVE — PARTIAL`

**Gap:** only selected proven logic has been adapted; not every Blender-side operation is meaningful inside ComfyUI/ConceptGhost.

---

### [6] `MoGe`

**Upstream:** `microsoft/MoGe`

**Role:** active independent geometry route.

**Used for now:**
- point map / native geometry;
- validity mask;
- Atlas-FOV-conditioned inference;
- canonical MoGe point reconstruction.

**Available evidence not yet fully exploited:**
- raw depth;
- native normals;
- boundary/reliability evidence.

**Stage 11 use:** native MoGe mesh branch.

**Status:** `ACTIVE — PARTIAL`

**Primary outputs influenced:** MoGe GeometryEvidence, Canonical Point Cloud when selected, diagnostics, native MoGe mesh.

---

### [7] `OpenUSD-selected`

**Upstream:** selected Pixar OpenUSD PLY-to-USD / UsdGeomPoints example.

**Role:** dense point transport / USD authoring reference.

**Used for:**
- `.usda` canonical Ghost representation;
- `UsdGeomPoints` authoring conventions;
- preserving a scalable dense reference for MayaUSD/Hydra.

**Status:** `ACTIVE / STRUCTURAL`

**Primary output influenced:** `ConceptGhost_<scene>_Ghost.usda`.

---

### [8] `maya-usd-reference`

**Upstream:** `Autodesk/maya-usd`

**Role:** official Maya/USD handoff reference.

**Used for:**
- MayaUSD proxy/stage architecture;
- camera/viewport/USD integration conventions;
- Stage 8 Maya Ghost handoff.

**Status:** `ACTIVE / STRUCTURAL`

**Primary output influenced:** `.ma` artist entry point + companion `.usda`.

---

### [9] `fSpy`

**Upstream:** `stuffmatic/fSpy`

**Role:** camera-matching comparison/validation reference.

**Roadmap location:** Stage 14.

**Status:** `PLANNED — STAGE 14`

**Why not active earlier:** ConceptGhost V1 camera authority is Atlas; fSpy is valuable as an advanced/manual/validation path, not as an additional mandatory solver in every run.

---

### [10] `fSpy-Blender`

**Upstream:** `stuffmatic/fSpy-Blender`

**Role:** DCC interpretation / coordinate and camera-transfer reference for fSpy data.

**Roadmap location:** Stage 14.

**Status:** `PLANNED — STAGE 14`

**Why not active earlier:** it only becomes causally useful when the Stage 14 fSpy/PCS validation branch is exercised.

---

### [11] `GeoCalib`

**Upstream:** `cvg/GeoCalib`

**Role:** learned camera calibration used through Atlas Learned.

**Used for:**
- focal/intrinsic prior;
- gravity/horizon orientation;
- camera solve evidence passed through Atlas.

**Status:** `ACTIVE THROUGH ATLAS`

**Why it is not a separate geometry branch:** its specialty is camera calibration, not depth/mesh generation.

---

### [12] `ComfyUI-workflow-templates`

**Upstream:** `Comfy-Org/workflow_templates`

**Role:** official known-good workflow/wiring baseline.

**Used for:**
- native MoGe perspective-to-mesh workflow;
- `MoGeInference -> MoGePointMapToMesh -> SaveGLB` structure;
- proven parameter/default wiring before ConceptGhost adapters;
- Stage 11 native mesh baseline.

**Status:** `STRUCTURAL + ACTIVE WORKFLOW BASELINE`

**Why it is not a solver:** it is the official integration/template source for already-existing algorithms.

## Status matrix

| Code | Reference | Status | Runtime on normal run? | Main contribution |
|---:|---|---|---|---|
| 1 | atlas-camera | ACTIVE | yes | camera/projection + relief/export services |
| 2 | atlas-camera pinned | STRUCTURAL | no duplicate branch | reproducible Atlas baseline |
| 3 | ComfyUI-DepthAnythingV3 | ACTIVE | yes when DA3 selected | DA3 ComfyUI inference/evidence |
| 4 | Depth-Anything-3 | STRUCTURAL/RUNTIME REFERENCE | through [3]/adapter | official DA3 semantics/API |
| 5 | DA3-blender | ACTIVE-PARTIAL | adapted logic | edge/geometry processing |
| 6 | MoGe | ACTIVE-PARTIAL | yes when MoGe/compare selected | point map/depth/mask/normals/mesh |
| 7 | OpenUSD-selected | ACTIVE/STRUCTURAL | export stage | dense USD points |
| 8 | MayaUSD | ACTIVE/STRUCTURAL | Maya handoff | Maya/USD integration |
| 9 | fSpy | PLANNED | Stage 14 only | camera validation/manual match |
| 10 | fSpy-Blender | PLANNED | Stage 14 only | DCC interpretation of fSpy |
| 11 | GeoCalib | ACTIVE | through Atlas Learned | learned camera calibration |
| 12 | ComfyUI workflow templates | STRUCTURAL/ACTIVE BASELINE | baseline/mesh branch | known-good native wiring |

## Output-to-code matrix

| Output | Main upstream contributors |
|---|---|
| Camera Package | [1], [2], [11] |
| DA3 diagnostics/evidence | [3], [4], [5] |
| MoGe diagnostics/evidence | [6], [12] |
| Canonical Colored Point Cloud | [1], [3]/[6], [5] where applicable, [11], source RGB |
| `.usda` Ghost | [7] + Canonical Geometry |
| Maya `.ma` Ghost | [8] + Atlas camera + `.usda` |
| Atlas Relief Mesh | [1], [2] |
| MoGe Native Mesh | [6], [12] |
| DA3/Bas-Relief Mesh | [3], [4], [5] + preserved DA3 workflows |
| PCS/fSpy validation | [9], [10] + Atlas comparison |

## Audit rule for future development

For every release/build report, ConceptGhost should record each reference as one of:

```text
ACTIVE_RUNTIME
ACTIVE_ALGORITHM_DONOR
ACTIVE_EXPORT_CONTRACT
PINNED_REFERENCE
PLANNED
REJECTED
```

For `PLANNED` or `REJECTED`, record a reason. Merely storing a repository in `References/Upstream_Code` does **not** count as integration.

## Current gaps worth revisiting after structural end-to-end completion

1. MoGe raw depth + normals should contribute more directly to boundary/reliability refinement when MoGe is the selected route.
2. DA3-Blender contribution can be expanded only where a proven operation improves the same canonical result; do not port Blender-specific code merely to increase reference count.
3. fSpy/fSpy-Blender become active only at Stage 14.
4. Stage 10–12 mesh branches must reuse their official/native upstream paths first and remain separate optional 2.5D products.
5. Stage 15/16 may add new references, but new engines must enter through existing ConceptGhost adapter contracts rather than replacing the core architecture.

## One-line policy

> ConceptGhost measures reference-code reuse by causal contribution to the same artist result, not by the number of repositories executed: every preserved code family must either run where it is the appropriate specialist, donate proven upstream logic/contracts to that stage, or remain explicitly PLANNED/REJECTED with a documented reason.
