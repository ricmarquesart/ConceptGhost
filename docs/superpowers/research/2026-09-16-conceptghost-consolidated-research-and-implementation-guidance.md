# ConceptGhost — Consolidated Research, Current Integration Guidance, and Future Technology Plan

**Date:** 2026-09-16  
**Project:** ConceptGhost  
**Status:** Mandatory design/research handoff for the programming chat  
**Scope:** What must be considered **now** in Stages 3–14, what must be tested before freezing parameters, and what must be considered **later** in a post-V1 Stage 15 without changing the current architecture.

---

# 0. READ THIS FIRST — HANDOFF FOR THE PROGRAMMING CHAT

This document is a **mandatory development reference**.

Do **not** interpret the new research below as permission to redesign the current ConceptGhost architecture.

The current architecture remains:

```text
SOURCE IMAGE
   ├── ATLAS CAMERA BRANCH
   │      └── CameraBundle
   │
   └── GEOMETRY BRANCH
          ├── DA3
          └── MoGe
               ↓
        GeometryAdapter
               ↓
      CONCEPTGHOST NORMALIZER
               ↓
        CanonicalGeometry
               ↓
   Integration Consistency Gate
      + Geometry Health Gate
               ↓
           SceneBundle
               ↓
          STAGE 8 EXPORT
               ↓
       .ma + .usda + .fbx + .ply
```

## 0.1 What changes NOW

The new research adds **refinement experiments and implementation guidance**, not a new main architecture.

The programming chat should now explicitly consider:

1. **MoGe should be tested with Atlas-derived FOV**, not only with MoGe auto-FOV.
2. **DA3 should be tested in two modes**:
   - current/public baseline;
   - Atlas-conditioned inference using supplied intrinsics/extrinsics where the official DA3 API supports it safely.
3. **Depth semantics must be explicit** before converting any engine output into XYZ.
4. **Reprojection is an integration-consistency test, not a depth-accuracy test.**
5. Stage 7 must also include a separate **Geometry Health Gate**.
6. Parameter defaults are **not frozen from documentation or YouTube**; upstream defaults and community settings are benchmark candidates.
7. Atlas already contains useful prior art that should be inspected/reused before writing custom logic:
   - solved focal supplied to MoGe-2 as `fov_x`;
   - DA3 depth path tied to solved focal;
   - Depth Anything V2 Metric Outdoor retained/reverted as a strong exterior reference in Atlas after its own A/B.
8. The official/native engine outputs must remain preserved separately from cleaned ConceptGhost canonical outputs.
9. The current V1 stays DA3/MoGe + Atlas. **Do not add VGGT, UniDepth, Depth Pro, Metric3D, GeoWizard, or MoGe-3 into the production path now.**
10. Add a future **Stage 15 — Alternative Engine Evaluation / Technology Watch** after Stages 3–14.

## 0.2 What does NOT change NOW

Do not change these approved decisions:

```text
Preset = Max Reference
Camera = Auto
Geometry = DA3
Compare Both = OFF
```

- Atlas remains camera authority.
- DA3 remains default geometry engine.
- MoGe remains selectable.
- No `Geometry = Auto`.
- No hidden DA3↔MoGe fallback.
- Compare Both remains comparison, not fusion.
- Canonical coordinate system remains:

```text
Right-handed
Y-Up
+X = right
+Y = up
-Z = camera forward
```

- Maya Ghost remains the primary product.
- Standard output package remains:

```text
ConceptGhost_<scene>_Ghost.ma
ConceptGhost_<scene>_Ghost.usda
ConceptGhost_<scene>_Ghost.fbx
pointcloud.ply
```

---

# 1. WHY THIS RESEARCH MATTERS

The risk in a single-image 3D pipeline is not only that a depth model produces a bad depth map.

A pipeline can fail even when every individual component appears to work because:

- the camera assumed by one model differs from the camera solved by another;
- one engine outputs camera-Z depth while another outputs ray distance or scale-invariant depth;
- image resizing changes intrinsics but the downstream unprojection keeps old values;
- coordinate conventions change between OpenCV, glTF/USD, Maya, and engine-native spaces;
- normalized/display depth is accidentally used as 3D depth;
- edge discontinuities create long “streamers” between foreground and background;
- a reprojection check passes while the actual depth is still wrong.

The core ConceptGhost value therefore remains:

```text
GOOD CAMERA AUTHORITY
+
GOOD GEOMETRY EVIDENCE
+
EXPLICIT GEOMETRIC SEMANTICS
+
CANONICAL NORMALIZATION
+
VALIDATION
=
USEFUL MAYA GHOST
```

---

# 2. CURRENT TECHNOLOGY STACK — REFINED UNDERSTANDING

# 2.1 Atlas Camera — camera authority

## Current role

Atlas remains the source of truth for:

- projection;
- focal/FOV;
- principal point / intrinsics;
- orientation;
- camera transform;
- learned solve vs VP fallback.

## Important new finding: Atlas already contains camera-conditioned depth prior art

The current Atlas documentation is especially valuable because it already implements two ideas closely related to the ConceptGhost design.

### MoGe-2 inside Atlas

Atlas documents that its MoGe-2 backend receives the **solved focal as `fov_x`**.

That means the idea:

```text
Atlas solves camera
      ↓
Atlas FOV
      ↓
MoGe geometry
```

is not merely theoretical. There is already upstream implementation prior art to inspect.

**Programming instruction:** before writing our own Atlas→MoGe FOV adapter, inspect the Atlas implementation and reuse the mathematical convention or adapter logic when compatible.

Source:
- https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md

### DA3 inside Atlas

Atlas also documents a DA3 path in which solved focal is threaded into the DA3 metric-depth process.

This is not identical to supplying DA3's official API with the full Atlas intrinsics/extrinsics, but it proves that Atlas's authors already found value in explicitly coupling the camera solve and DA3 depth interpretation.

**Programming instruction:** inspect the Atlas DA3 backend before creating duplicate focal/depth conversion logic.

Sources:
- https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md
- https://github.com/mikejamesvfx/atlas-camera/blob/main/CHANGELOG.md

## Important secondary finding: Atlas reverted exterior default to Depth Anything V2 Metric Outdoor

Atlas's changelog/installation guide states that its main branch reverted the default exterior depth backend from DA3 to **Depth Anything V2 Metric Outdoor** after a four-scene A/B in which V2 was best or tied for exteriors.

This does **not** mean ConceptGhost should replace DA3 now.

It means:

```text
Depth Anything V2 Metric Outdoor
```

is valuable as a **reference baseline / fallback research candidate**, particularly for exterior concept environments.

Recommended use:
- keep it out of the current Geometry selector;
- include it in future reference benchmarks if DA3/MoGe outputs are unexpectedly poor;
- consider it in Stage 15 or a Stage 9 diagnostic benchmark.

Sources:
- https://github.com/mikejamesvfx/atlas-camera/blob/main/CHANGELOG.md
- https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md
- https://github.com/DepthAnything/Depth-Anything-V2/blob/main/metric_depth/README.md

---

# 2.2 Depth Anything V3 — current primary/default geometry engine

## Native ComfyUI behavior worth preserving

The current native ComfyUI DA3 integration exposes distinct model capabilities:

```text
DA3 Small/Base:
- depth
- confidence
- camera decoder

DA3 Mono/Metric:
- depth
- sky estimate
- no camera decoder in the same sense
```

The point-cloud conversion path:

- uses raw model depth;
- reconstructs points with intrinsics;
- can exclude sky;
- can threshold confidence;
- supports point downsampling;
- explicitly converts OpenCV camera convention to glTF-like orientation.

Source:
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_depth_anything_3.py

## Important rule: RAW depth for 3D

The public ComfyUI DA3 workflows distinguish depth intended for display/ControlNet from raw geometric depth.

For 3D reconstruction, use raw depth.

Do not do:

```text
pretty normalized grayscale depth
→ unproject to 3D
```

Do:

```text
raw DA3 depth
→ explicit depth semantics
→ Atlas camera
→ canonical XYZ
```

Community/ComfyUI wrapper reference:
- https://github.com/chettilaura/ComfyUI-DepthAnythingV3

## Official DA3 API supports external camera inputs

The official API accepts:

```text
extrinsics: (N, 4, 4)
intrinsics: (N, 3, 3)
```

and forwards those into model inference/alignment.

Official API defaults also currently include:

```text
process_res = 504
conf_thresh_percentile = 40
num_max_points = 1,000,000
```

These are **baseline values**, not ConceptGhost final presets.

Source:
- https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/src/depth_anything_3/api.py

## REQUIRED Stage 7 DA3 experiment

Compare:

```text
PATH A — PUBLIC/UNCHANGED BASELINE
image
→ existing DA3 workflow
→ raw depth / native evidence
→ ConceptGhost Normalizer
→ Atlas reconstruction

PATH B — ATLAS-CONDITIONED DA3 EXPERIMENT
Atlas CameraBundle
→ convert to DA3 intrinsics/extrinsics convention
→ official DA3 API with supplied camera
→ depth / geometry
→ ConceptGhost Normalizer
```

Do not promote Path B until:
- environment-safe;
- no protected packages drift;
- math conventions verified;
- measurable improvement exists.

## Candidate parameter study

Do not freeze these yet. Benchmark:

```text
process_res candidates:
504
intermediate validated value (~700–800 range if supported cleanly)
1024

point downsample:
1 for Max Reference candidate
2/4 only for lower-cost presets if visually acceptable

confidence:
0.10 native ComfyUI normalized threshold as one candidate
official percentile-based filtering as another candidate

sky mask:
ON where model actually supplies a trustworthy sky output
```

The final `Max Reference` parameter set must come from Stage 9 evidence.

---

# 2.3 MoGe — current alternate geometry engine

## Native outputs

Current MoGe APIs/nodes expose combinations of:

- point map;
- depth;
- mask;
- intrinsics;
- normals on supported variants;
- FOV.

The native coordinate system is OpenCV-style camera coordinates:

```text
X right
Y down
Z forward
```

ConceptGhost must explicitly convert this to:

```text
X right
Y up
Z back / camera looks -Z
```

Sources:
- https://github.com/microsoft/MoGe
- https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_moge.py

## Resolution control

MoGe documents:

```text
resolution_level = 0..9
9 = highest normal inference detail
```

The model also supports direct `num_tokens`; current v1 documentation describes a suggested approximate range of 1200–2500 when overriding the level.

Source:
- https://github.com/microsoft/MoGe/blob/main/moge/model/v1.py

## Critical finding: known FOV is a supported accuracy path

MoGe explicitly supports external horizontal FOV:

```text
fov_x
```

and the project states that providing true FOV can improve accuracy.

Native ComfyUI exposes:

```text
fov_x_degrees
0.0 = auto
```

Sources:
- https://github.com/microsoft/MoGe
- https://github.com/Comfy-Org/embedded-docs/blob/main/comfyui_embedded_docs/docs/MoGeInference/en.md

## REQUIRED Stage 7 MoGe A/B

Compare:

```text
A. MoGe Auto FOV
B. MoGe with Atlas horizontal FOV
```

Same:
- input image;
- model;
- resolution;
- masking;
- downstream canonicalization.

Measure:
- depth/point shape;
- edge artifacts;
- canonical Geometry Health;
- off-camera usefulness;
- Maya usefulness in Stage 8/9.

## Candidate current Max Reference settings

Initial candidate only:

```text
resolution_level = 9
force_projection = true
apply_mask = true
fov_x = Atlas FOV for conditioned experiment
```

For mesh experiments:

```text
decimation = 1
discontinuity threshold = test around upstream/reference defaults
texture = true
```

Official ComfyUI template currently documents auto-resize for large inputs:
- width > 2048 → working long edge 2048;
- otherwise keep original.

Source:
- https://github.com/Comfy-Org/workflow_templates/blob/main/templates/3d_moge_perspective_to_mesh.json

This 2048 policy is a benchmark candidate, not automatically the ConceptGhost final rule.

---

# 2.4 MoGe-3 — status changed; FUTURE candidate

A previous assumption that MoGe-3 was only a distant future item is now partly outdated.

The current repository includes:

```text
MoGe v3 code
package version 3.0.0
refine_steps
default refine_steps = 3
```

The CLI currently requires an explicit pretrained checkpoint for v3.

So the correct status is:

```text
CODE PATH: present
REFINEMENT SUPPORT: present
CHECKPOINT AVAILABILITY / PRODUCTION READINESS: verify at implementation/research time
CURRENT CONCEPTGHOST V1: do not switch now
FUTURE STAGE 15: high-priority evaluation
```

Sources:
- https://github.com/microsoft/MoGe
- https://github.com/microsoft/MoGe/blob/main/moge/scripts/infer.py
- https://github.com/microsoft/MoGe/blob/main/pyproject.toml

---

# 3. STAGE 7 — REQUIRED NORMALIZER DESIGN

# 3.1 Canonical coordinate system

Approved:

```text
Right-handed
Y-Up

+X = right
+Y = up
-Z = camera forward
```

Image UV:

```text
U = right
V = down
origin = upper-left
```

No engine or exporter may guess this convention.

---

# 3.2 CameraBundle

Normalize Atlas into a stable contract.

Minimum fields:

```text
CameraBundle
{
    source_width
    source_height

    fx
    fy
    cx
    cy
    K[3x3]

    projection_type

    camera_to_world
    world_to_camera

    solver_requested
    solver_used
    solver_confidence
    quality_status

    coordinate_convention
}
```

Downstream code must not depend on Atlas private node wiring.

---

# 3.3 GeometryEvidence / GeometryBundle

Every engine adapter must explicitly declare what it produced.

Minimum:

```text
GeometryEvidence
{
    engine
    model
    model_version

    raw_depth
    point_map

    depth_semantics

    confidence
    mask
    sky_mask
    normals

    native_intrinsics
    native_camera

    source_pixel_mapping

    inference_parameters
    native_coordinate_convention
}
```

## depth_semantics is mandatory

Examples:

```text
camera_z
ray_distance
inverse_depth
relative_depth
metric_depth
point_map_xyz
```

Never infer semantics from the filename or variable name alone.

---

# 3.4 Canonical point construction

For each retained source pixel:

```text
source UV
+
geometry evidence
+
Atlas CameraBundle
→ canonical XYZ
```

Color:

```text
RGB = original concept image at source UV
```

Canonical point metadata should retain:

```text
X Y Z
R G B
confidence
validity
source_u
source_v
source_engine
depth_semantics
provenance
```

This makes each point traceable back to its source pixel and engine.

---

# 3.5 Filtering

Never destroy native evidence.

Keep:

```text
geometry/native/<engine>/
```

Produce cleaned:

```text
geometry/canonical/
```

Candidate filtering pipeline:

```text
raw evidence
→ finite / positive validity
→ engine mask / sky mask
→ confidence filtering
→ depth discontinuity filter
→ outlier / streamer rejection
→ canonical point cloud
```

DA3-Blender remains a practical reference for:
- confidence filtering;
- depth-discontinuity cleanup;
- streamer reduction;
- point display strategy.

Do not make Blender a mandatory runtime dependency.

---

# 3.6 Reprojection correction — IMPORTANT

Reprojection validates **integration**, not actual scene depth.

Example:

```text
same source pixel
      │
      ├── near 3D point
      ├── medium 3D point
      └── far 3D point

all can project to the same pixel
```

Therefore a reprojection PASS tells us:

```text
camera intrinsics are being used coherently
image resolution mapping is coherent
principal point is coherent
axis conversion is coherent
handedness is coherent
world/camera transform is coherent
```

It does NOT prove:

```text
the wall is at the correct distance
DA3 estimated true depth
MoGe estimated true geometry
```

Rename conceptually:

```text
Integration Consistency Gate
```

rather than treating reprojection as a depth-quality proof.

---

# 3.7 Geometry Health Gate

Add a second Stage 7 gate.

Track at minimum:

```text
valid coverage
point count
non-finite points
confidence distribution
depth min/max
depth percentiles
mask coverage
sky coverage
edge rejection ratio
outlier rejection ratio
large depth-jump statistics
```

Purpose:
detect structurally broken output that could still pass reprojection.

Do not turn this into an unsupported “artistic quality score”.

---

# 3.8 Scale

V1:

```text
scale_mode = relative
```

Even when an engine returns metric depth, the manifest must record the provenance and must not imply physical accuracy for stylized concept art without validation.

Future:

```text
scale_mode = anchored
known measurement → scene scale
```

---

# 3.9 SceneBundle

Stage 8 should consume only a stable ConceptGhost contract:

```text
SceneBundle
{
    CameraBundle
    CanonicalGeometry
    SourceImage
    GeometryHealth
    ReprojectionReport
    EngineMetadata
    CoordinateConvention
    ScaleConvention
    Manifest
}
```

Stage 8 should not need to know which ComfyUI DA3 output socket produced a tensor.

---

# 4. PARAMETER POLICY — HOW TO FIND THE “BEST” SETTINGS

Do not copy one creator’s values and call them optimal.

Use four layers:

## Layer 1 — upstream baseline

Run official/native defaults unchanged.

This answers:

```text
Does the original tool work?
```

## Layer 2 — documented high-quality candidate

Examples:

DA3:
```text
process_res 504 baseline
process_res 1024 high-quality candidate
raw depth
full-resolution point sampling candidate
```

MoGe:
```text
resolution_level 9
mask enabled
projection constraint enabled
```

## Layer 3 — camera-conditioned candidate

DA3:
```text
Atlas K / extrinsics → DA3 official API
```

MoGe:
```text
Atlas FOV → MoGe fov_x
```

## Layer 4 — ConceptGhost benchmark

Use same scenes to compare:

```text
detail preservation
edge streamers
noise
foreground/background separation
thin structures
coverage
point count
VRAM
runtime
Maya viewport usability
off-camera usefulness
```

Only after that freeze:

```text
Fast Test
Balanced
Max Reference
```

---

# 5. EXISTING PRIOR ART WE SHOULD REUSE BEFORE INVENTING

## 5.1 Atlas solved-focal → MoGe

Before writing custom FOV-conditioning logic, inspect Atlas's MoGe backend.

Source:
https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md

## 5.2 Atlas solved-focal → DA3 metric path

Inspect Atlas's DA3 focal/depth conversion before duplicating it.

Sources:
https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md
https://github.com/mikejamesvfx/atlas-camera/blob/main/CHANGELOG.md

## 5.3 Native ComfyUI DA3 unprojection

Reuse/verify:
- intrinsics scaling during downsample;
- invalid-depth handling;
- OpenCV→glTF axis conversion;
- sky/confidence masks.

Source:
https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_depth_anything_3.py

## 5.4 Native ComfyUI MoGe

Reuse/verify:
- FOV control;
- native point/depth/mask/intrinsics;
- coordinate semantics.

Source:
https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_moge.py

## 5.5 DA3-Blender

Use as workflow/design reference for filtering and presentation, not as a mandatory bridge.

---

# 6. COMMUNITY / VIDEO RESEARCH POLICY

Videos are valuable because they show:

- real workflows;
- practical parameter choices;
- failure modes;
- performance;
- visual result quality.

But:

```text
VIDEO = workflow evidence / idea source
OFFICIAL CODE = semantic source of truth
CONCEPTGHOST BENCHMARK = final parameter authority
```

Examples already identified in research:
- Depth Anything V3 in ComfyUI with 3D reconstruction / PLY / GLB workflows.
- DA3 ComfyUI demonstrations emphasizing raw depth for 3D rather than display-normalized depth.

The research pass should continue collecting creator workflows, but no YouTube value should become a production default without a controlled local benchmark.

---

# 7. ALTERNATIVE TECHNOLOGIES — DO NOT ADD TO CURRENT V1

These are future candidates only.

# 7.1 VGGT — very high priority future study

Official VGGT predicts:

- camera extrinsics;
- camera intrinsics;
- depth;
- point maps;
- confidence;
- tracks.

It supports direct single-view inference even though monocular reconstruction was not its dedicated training target.

The official project notes a particularly relevant result:

```text
depth + predicted camera → unprojected points
```

usually produces more accurate 3D points than using its direct point-map branch.

That strongly validates the ConceptGhost architecture:

```text
geometry evidence
+
camera authority
→ canonical reconstruction
```

Potential future role:
- new GeometryAdapter;
- camera cross-check;
- independent point/depth comparator.

Source:
https://github.com/facebookresearch/vggt

Priority:
**HIGH for Stage 15.**

---

# 7.2 UniDepth V2 — high-priority metric alternative

Outputs/architecture include:

- metric depth;
- points;
- confidence;
- rays;
- intrinsics.

It also supports supplied cameras/intrinsics.

This matches the ConceptGhost GeometryBundle extremely well.

V2 adds:
- resolution control;
- confidence;
- sharper edges;
- broader camera model support.

Potential role:
- third geometry engine;
- metric cross-check;
- camera-conditioned benchmark.

Caution:
- current documented reference environment is Linux/Python/CUDA-oriented;
- do not install into protected ComfyUI without an isolated compatibility plan.

Sources:
https://github.com/lpiccinelli-eth/UniDepth
https://github.com/lpiccinelli-eth/UniDepth/blob/main/assets/docs/V2_README.md

Priority:
**HIGH/MEDIUM for Stage 15.**

---

# 7.3 Apple Depth Pro — sharp-boundary specialist candidate

Depth Pro provides:
- metric depth;
- sharp boundaries / high-frequency detail;
- focal length estimate in pixels;
- optional use of externally supplied focal length.

Particularly interesting for:
- architecture;
- thin silhouette boundaries;
- foreground/background edges.

Potential ConceptGhost use:
- specialist depth engine;
- boundary benchmark;
- focal/depth diagnostic.

Source:
https://github.com/apple-aiml-research/ml-depth-pro

Priority:
**MEDIUM for Stage 15.**

---

# 7.4 Metric3D V2 — depth + surface normals

Metric3D V2 targets:
- metric depth;
- surface normals.

Its own documentation explicitly warns that point clouds can look distorted when focal length is wrong.

That independently supports the ConceptGhost decision:

```text
camera solve must be explicit
```

rather than letting depth geometry use an unrelated assumed focal.

Potential use:
- geometry adapter;
- normal-map evidence;
- planar orientation diagnostics.

Source:
https://github.com/YvanYin/Metric3D

Priority:
**MEDIUM for Stage 15.**

---

# 7.5 GeoWizard — diffusion geometry alternative

GeoWizard estimates:
- depth;
- normals.

It uses a diffusion-based approach and documents different domains:
- indoor;
- outdoor;
- object.

V2 reports improvements on rare images including cartoon-style imagery.

This makes it especially interesting for ConceptGhost because our input may be:

```text
concept art
stylized environment
matte painting
illustration
```

There is also a public ComfyUI wrapper.

Sources:
https://github.com/fuxiao0719/GeoWizard
https://github.com/kijai/ComfyUI-Geowizard

Potential downside:
- heavier/slower iterative inference;
- dependency stack different from current protected environment.

Priority:
**MEDIUM/LOW for Stage 15, but potentially important for stylized-art failure cases.**

---

# 7.6 Depth Anything V2 Metric Outdoor — reference/fallback benchmark

Not new, but newly important because Atlas itself returned to it for exteriors.

Potential role:
- controlled exterior reference baseline;
- inexpensive fallback research;
- sanity check when DA3/MoGe disagree strongly.

Keep out of V1 user-facing Geometry selector unless later evidence justifies expansion.

Priority:
**LOW-COST BENCHMARK candidate.**

---

# 7.7 Lotus-2 / other diffusion depth backends

Atlas also exposes/references diffusion-depth alternatives such as Lotus-2.

These may be worth future study, but licensing, gated weights, runtime cost, and dependency impact make them lower priority for ConceptGhost than VGGT / UniDepth / MoGe-3.

Do not introduce them now.

---

# 8. FUTURE STAGE 15 — ALTERNATIVE ENGINE EVALUATION / TECHNOLOGY WATCH

Stage 15 starts **only after Stages 3–14 are complete**.

It must not destabilize the frozen V1.

## Initial queue

```text
1. MoGe-3
2. VGGT
3. UniDepth V2
4. Depth Pro
5. Metric3D V2
6. GeoWizard
7. Depth Anything V2 Metric Outdoor benchmark
8. newly released relevant systems at that future date
```

This order is research priority, not a quality ranking.

## Stage 15 rules

Each candidate must first run independently.

Then, if useful:

```text
New Engine
→ GeometryAdapter
→ GeometryBundle
→ existing ConceptGhost Normalizer
→ existing gates
→ existing SceneBundle
```

Never rewrite the entire Maya/export stack for a new model.

## Evaluation matrix

```text
single-image behavior
stylized concept-art behavior
camera/intrinsics compatibility
depth semantics clarity
metric/relative scale behavior
edge quality
thin structures
occlusion boundaries
streamers
point-cloud cleanliness
off-camera usefulness
Maya usefulness
VRAM/RAM
runtime
Windows compatibility
ComfyUI compatibility
license
dependency conflicts
value over DA3/MoGe
```

---

# 9. FAILURE FALLBACK MAP

If Atlas Learned fails:

```text
→ Atlas VP
```

If both Atlas camera modes fail:

```text
→ stop authoritative Ghost
→ preserve diagnostics
→ future Stage 14 PCS/fSpy/manual solve
```

If DA3 baseline fails:

```text
→ do not hide failure with ConceptGhost code
→ inspect upstream workflow
→ explicit MoGe run if user chooses it
→ preserve evidence
```

If DA3 produces poor geometry but executes:

```text
→ test camera-conditioned DA3
→ compare MoGe Atlas-FOV path
→ Stage 9 benchmark
→ optional DAv2 Metric Outdoor reference baseline
```

If MoGe auto-FOV is poor:

```text
→ use Atlas-FOV experiment
```

If both DA3 and MoGe are poor on stylized art:

```text
→ do not silently add another engine in V1
→ preserve case for Stage 15
→ prioritize GeoWizard / VGGT / Depth Pro / UniDepth research depending failure mode
```

If point cloud has streamers:

```text
→ confidence/mask checks
→ depth-discontinuity filtering
→ DA3-Blender-style cleanup reference
→ do not modify native evidence
```

If reprojection fails:

```text
→ investigate coordinate/intrinsics/resolution/transform bug
→ do not blame depth accuracy first
```

If reprojection passes but geometry looks wrong:

```text
→ Geometry Health / actual depth quality problem
→ compare engine/conditioning
```

---

# 10. SAFE IMPLEMENTATION ORDER

The programming chat should not jump directly to the “best” experimental path.

Use:

```text
1. Public/native baseline passes
2. Capture native evidence
3. Implement canonical adapter
4. Pass Integration Consistency Gate
5. Pass Geometry Health Gate
6. Add one refinement experiment at a time
7. Compare to baseline
8. Keep only measured improvements
9. Stage 9 freezes presets
```

This prevents a complex hybrid from becoming impossible to debug.

---

# 11. ENVIRONMENT / NON-INTERFERENCE REQUIREMENT

All research is subordinate to the existing ConceptGhost environment-safety rules.

Do not:

- upgrade/downgrade Torch automatically;
- replace NumPy;
- reinstall CUDA stack;
- edit unrelated `custom_nodes`;
- overwrite protected working workflows;
- install a new research engine into the production ComfyUI environment without a dependency-impact review.

When a future engine has risky dependencies:

```text
isolated environment / worker
→ test
→ adapter boundary
```

is preferred over contaminating the current ComfyUI environment.

Use the project's source lock / reference verifier before relying on moving upstream `main` content.

---

# 12. SOURCE / REFERENCE INDEX

## Current stack

Atlas Camera  
https://github.com/mikejamesvfx/atlas-camera

Atlas install/dependency/depth notes  
https://github.com/mikejamesvfx/atlas-camera/blob/main/INSTALL.md

Atlas changelog / backend A/B history  
https://github.com/mikejamesvfx/atlas-camera/blob/main/CHANGELOG.md

Depth Anything 3  
https://github.com/ByteDance-Seed/Depth-Anything-3

DA3 official API  
https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/src/depth_anything_3/api.py

ComfyUI native DA3  
https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_depth_anything_3.py

ComfyUI DA3 workflow/reference implementation  
https://github.com/chettilaura/ComfyUI-DepthAnythingV3

MoGe  
https://github.com/microsoft/MoGe

ComfyUI native MoGe  
https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_moge.py

ComfyUI MoGe documentation  
https://github.com/Comfy-Org/embedded-docs/blob/main/comfyui_embedded_docs/docs/MoGeInference/en.md

Official MoGe template  
https://github.com/Comfy-Org/workflow_templates/blob/main/templates/3d_moge_perspective_to_mesh.json

Depth Anything V2 Metric  
https://github.com/DepthAnything/Depth-Anything-V2/blob/main/metric_depth/README.md

## Future engines

VGGT  
https://github.com/facebookresearch/vggt

UniDepth V2  
https://github.com/lpiccinelli-eth/UniDepth

Depth Pro  
https://github.com/apple-aiml-research/ml-depth-pro

Metric3D V2  
https://github.com/YvanYin/Metric3D

GeoWizard  
https://github.com/fuxiao0719/GeoWizard

ComfyUI GeoWizard  
https://github.com/kijai/ComfyUI-Geowizard

---

# 13. MINIMAL RESEARCH PSEUDOCODE FOR THE PROGRAMMING CHAT

These snippets express the intended integration, not copy-pasted upstream code.

## MoGe with Atlas FOV

```python
camera = atlas_camera_bundle
fov_x = camera.horizontal_fov_degrees

moge_result = run_moge(
    image=source_image,
    fov_x=fov_x,
    resolution_level=9,
    apply_mask=True,
    force_projection=True,
)

evidence = moge_adapter.to_geometry_evidence(moge_result)
canonical = normalizer.build(camera, evidence, source_image)
```

## DA3 baseline

```python
da3_result = run_existing_da3_workflow(source_image)

evidence = da3_adapter.to_geometry_evidence(
    raw_depth=da3_result.raw_depth,
    confidence=da3_result.confidence,
    sky_mask=da3_result.sky_mask,
    native_intrinsics=da3_result.intrinsics,
)

canonical = normalizer.build(atlas_camera_bundle, evidence, source_image)
```

## DA3 Atlas-conditioned experiment

```python
camera = atlas_camera_bundle

da3_conditioned = da3_official_api.inference(
    image=[source_image],
    intrinsics=camera.as_da3_intrinsics(),
    extrinsics=camera.as_da3_extrinsics(),
    process_res=experiment.process_res,
)

evidence = da3_adapter.to_geometry_evidence(da3_conditioned)
canonical = normalizer.build(camera, evidence, source_image)
```

## Integration Consistency

```python
uv_expected = canonical.source_uv
uv_projected = project(canonical.xyz, camera)

error_px = distance(uv_expected, uv_projected)
```

## Geometry Health

```python
health = {
    "valid_coverage": valid_points / source_pixels,
    "point_count": valid_points,
    "nonfinite_count": nonfinite_points,
    "depth_percentiles": percentiles(depth),
    "edge_rejection_ratio": edge_rejected / candidates,
    "outlier_rejection_ratio": outliers / candidates,
}
```

---

# 14. FINAL CURRENT VS FUTURE DECISION TABLE

| Topic | Consider NOW | Consider LATER |
|---|---|---|
| Atlas learned + VP | Yes, core | PCS/fSpy extension |
| DA3 current workflow | Yes, baseline + default | newer variants as research |
| DA3 with Atlas intrinsics/extrinsics | Yes, controlled Stage 7 experiment | promote only if benchmark wins |
| MoGe current | Yes | MoGe-3 |
| MoGe with Atlas FOV | Yes, high-priority Stage 7 A/B | make default only after evidence |
| Reprojection | Yes, integration consistency | keep permanently |
| Geometry Health | Yes, add Stage 7 | refine metrics over time |
| DAv2 Metric Outdoor | benchmark/reference only | possible fallback |
| DA3-Blender logic | use as reference | more cleanup ideas |
| VGGT | No production integration | Stage 15 high priority |
| UniDepth V2 | No | Stage 15 |
| Depth Pro | No | Stage 15 |
| Metric3D V2 | No | Stage 15 |
| GeoWizard | No | Stage 15, especially stylized failures |
| MoGe-3 | No current V1 switch | Stage 15 high priority |
| Blender intermediate | No | optional inspection only |
| Maya .ma/.usda/.fbx/.ply | Yes, Stage 8 | expand formats only later |

---

# 15. ONE-SENTENCE INSTRUCTION TO THE OTHER CHAT

> **Keep the current Atlas + DA3/MoGe + Canonical Normalizer architecture unchanged, but add Stage-7 research gates for Atlas-conditioned MoGe FOV and Atlas-conditioned DA3 intrinsics/extrinsics, separate reprojection consistency from geometry-quality validation, benchmark parameters instead of assuming defaults are optimal, preserve all native evidence, and defer VGGT/UniDepth/Depth Pro/Metric3D/GeoWizard/MoGe-3 to a post-V1 Stage 15.**
