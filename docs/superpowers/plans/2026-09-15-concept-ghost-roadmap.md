# Concept Ghost Blockout — Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows/ComfyUI/Maya pipeline that turns one concept-art environment image into staged, independently usable outputs: matched camera, diagnostics, colored point cloud, Maya ghost scene, and optional reference meshes.

**Architecture:** Atlas Camera is the camera/projection foundation. Depth Anything V3 and MoGe are independent geometry backends. Existing public workflows remain untouched as baselines; project workflows wrap them and normalize outputs. Mesh generation continues after the point-cloud stage, but camera + point cloud are the V1 success criteria.

**Tech Stack:** Windows batch/PowerShell, ComfyUI, Atlas Camera, GeoCalib, Depth Anything V3, MoGe-2, Maya/MayaUSD, Python, YAML/JSON, USD/PLY/GLB.

**Spec:** `docs/superpowers/specs/2026-09-15-concept-ghost-blockout-design.md`

## Global Constraints

- Do not reimplement camera solving, depth inference, monocular geometry, or mesh triangulation when a validated public implementation exists.
- Keep upstream reference workflows verbatim and separate from project-derived workflows.
- Detect and reuse existing installs/models before downloading anything.
- Track every managed write and every byte added outside `C:\ConceptGhost`.
- Never modify PATH or permanent user/system environment variables silently.
- Never let mesh failure block a successful camera + point-cloud deliverable.
- Treat single-image meshes as 2.5D/reference shells unless proven otherwise.
- Primary platform: Windows + existing ComfyUI + Autodesk Maya.

---

## Final stage order

0. Inventory and freeze current machine state
1. Project root, manifests, disk ledger, and safe installer framework
2. Atlas Camera core installation
3. Atlas camera-solve baseline and camera Output A
4. DA3 baseline and DA3 diagnostic/point-cloud branch
5. MoGe baseline and MoGe diagnostic/point-map branch
6. Unified `config.yml` and staged output contract
7. Standardized geometry bundles and Output B/C
8. Maya handoff and Output D
9. A/B validation and engine presets
10. Mesh Track 1 — Atlas relief mesh
11. Mesh Track 2 — official MoGe mesh
12. Mesh Track 3 — DA3 mesh
13. Packaging, uninstall, documentation, and final acceptance
14. Future/optional PCS hybrid camera-validation track

---

## Stage 0 — Inventory / no installation yet

**Purpose:** Know exactly what is already on disk before touching the machine.

### Inspect
- Existing ComfyUI root(s).
- Whether ComfyUI is portable (`python_embeded`) or venv-based.
- Exact ComfyUI Python executable.
- Git availability.
- Current torch, torchvision, numpy, transformers, kornia, OpenCV versions.
- Existing Atlas Camera clone.
- Existing `ComfyUI-DepthAnythingV3` clone.
- Existing DA3 model files and their paths/sizes/hashes.
- Existing native MoGe nodes and model files.
- Existing Microsoft MoGe Python package/cache.
- Maya version.
- MayaUSD / `mayaUsdPlugin` availability.
- Available disk space on every drive that contains ComfyUI, project root, models, and Maya assets.

### Produce
- `C:\ConceptGhost\manifests\preinstall_inventory.json`
- `C:\ConceptGhost\manifests\preinstall_python_packages.txt`
- `C:\ConceptGhost\manifests\preinstall_disk.json`

### Gate 0
Proceed only when every detected pre-existing component is marked `preexisting=true` and has a canonical path.

**Can test now?** Yes. This stage itself is testable and must make zero permanent installation changes.

---

## Stage 1 — Safe project/install framework

**Purpose:** Build the safety layer before downloading models or custom nodes.

### Create under `C:\ConceptGhost`
- `SETUP.bat`
- `UNINSTALL.bat`
- `config.yml`
- `scripts\`
- `logs\`
- `manifests\`
- `workflows\reference\`
- `workflows\project\`
- `output\`
- `cache\downloads\`
- `maya\`

### Implement first
- Path discovery.
- File hashing.
- File/folder size measurement.
- Free-space snapshots.
- Download-to-temp then atomic move.
- Pre-existing asset detection.
- Idempotent install records.
- `install_manifest.json`.
- `disk_ledger.json` and `.csv`.
- Install log.
- Dry-run mode.

### Gate 1
Running setup in `--dry-run` must list intended operations and estimated known model sizes without downloading or overwriting anything.

**Can test now?** Yes. Test idempotence and dry-run before installing Atlas.

---

## Stage 2 — Atlas Camera core

**Public base:** `mikejamesvfx/atlas-camera`.

**Why first:** Atlas already provides the most complete public camera/projection/Maya foundation and has real DCC validation.

### Install/reuse
1. If an Atlas clone already exists and is compatible, reuse it.
2. Otherwise clone Atlas into `<COMFYUI_ROOT>\custom_nodes\atlas-camera`.
3. Do not pip-install the full project merely to register core nodes; upstream supports clone-and-go.
4. Start with core nodes only and verify ComfyUI launches.

### Camera extras, in this order
1. Vision prerequisites for classical vanishing-point solve.
2. GeoCalib learned solve dependencies.
3. Pin `kornia<0.8.3` when using the upstream-safe recipe to avoid breaking LTXVideo-class consumers.
4. Verify torch/numpy versions before and after installation.

### Do not install yet
- DA3 extras.
- MoGe package.
- SAM3.
- inpainting stacks.
- Qwen/edit models.
- experimental hidden-geometry systems.

### Reference workflow copied verbatim
- `examples/atlas_input_quickstart_workflow.json`
- `examples/atlas_quickstart_solve_project_export_workflow.json`
- `examples/atlas_export_fanout_workflow.json`
- `examples/atlas_hero_02_photo_to_editable_scene_workflow.json`

### Gate 2
- ComfyUI starts with Atlas loaded.
- `AtlasInput` appears.
- Quickstart JSON loads without missing Atlas nodes.
- No unrelated custom node breaks after dependency changes.

**Can test now?** Yes. This is the first meaningful user-visible test point.

---

## Stage 3 — Camera baseline / Output A

**Purpose:** Prove the camera path before introducing DA3 or MoGe geometry.

### Test two Atlas camera modes
- `AtlasLearnedSolveFromImage` / GeoCalib — default candidate for concept art.
- `AtlasSolveFromImage` / vanishing points — comparison/fallback for strong architectural perspective.

### Input set
Use at least three images:
1. rectilinear architecture;
2. stylized city/village concept;
3. difficult image with weak or inconsistent perspective.

### Output A — Camera Package
For each solve preserve:
- focal/intrinsics available from Atlas;
- horizon/gravity/orientation;
- confidence/report;
- source image size;
- source solver;
- review overlay/diagnostics;
- Atlas native solve JSON.

### Decision rule
The project camera default becomes the Atlas solve mode that performs best on the concept-art test set; the other stays selectable in `config.yml`.

### Gate 3
At least one camera mode must be plausibly usable on the main concept test image before depth geometry work begins.

**Can test now?** Yes. Camera-only output is already a deliverable.

---

## Stage 4 — DA3 baseline

**Public bases:**
- `PozzettiAndrea/ComfyUI-DepthAnythingV3`
- official ByteDance Depth Anything 3 code where Atlas needs its DA3 backend.
- `xy-gao/DA3-blender` as practical reference for filtering and point-cloud presentation.

### Installation strategy
- Detect existing `ComfyUI-DepthAnythingV3` before cloning.
- Detect existing DA3 model files before downloading.
- Keep the upstream custom-node workflows verbatim.
- For Atlas DA3 support in an existing ComfyUI environment, use the upstream safe `--no-deps` approach rather than letting DA3 re-resolve torch/numpy/xformers/export stacks.
- Never install heavyweight DA3 export-only packages unless a later proven feature explicitly requires them.

### Reference workflows
- `advanced.json`
- `advanced_3d.json`
- `bas_relief.json` (reference only at this stage)

### Baseline run
Run `advanced_3d.json` unchanged on the same camera-test concept.

### Validate
- Raw depth exists.
- confidence exists.
- intrinsics exist where the chosen DA3 model supports them.
- colored PLY point cloud is produced.
- point count > 0.
- test edge/confidence filtering based on existing DA3-Blender practices; do not invent a new algorithm first.

### Gate 4
Unmodified public DA3 point-cloud workflow must run successfully before project wrapping begins.

**Can test now?** Yes. Compare point cloud visually against the source and Atlas camera.

---

## Stage 5 — MoGe baseline

**Public bases:**
- native ComfyUI MoGe nodes.
- `Comfy-Org/workflow_templates/templates/3d_moge_perspective_to_mesh.json`.
- `microsoft/MoGe`.

### Installation strategy
- Detect whether current ComfyUI already has native MoGe nodes.
- Detect/reuse `moge_2_vitl_normal_fp16.safetensors` in `models\geometry_estimation`.
- If Atlas's MoGe backend needs the Python package separately, install Microsoft MoGe with the safe `--no-deps` recipe and pin the upstream `utils3d` commit used by Atlas.
- Do not duplicate model weights if the same compatible file can be reused.

### Reference workflow
- `3d_moge_perspective_to_mesh.json` unchanged.

### Baseline run
Run official MoGe workflow unchanged.

### Validate
- point map/geometry exists;
- depth exists;
- mask exists;
- normals exist with the selected MoGe-2 normal model;
- FOV/intrinsics are recoverable;
- official GLB may be generated, but mesh quality is not yet an acceptance criterion.

### Gate 5
Official public MoGe workflow must run successfully before project wrapping begins.

**Can test now?** Yes. DA3 versus MoGe geometry can already be inspected side-by-side.

---

## Stage 6 — Unified `config.yml` and staged outputs

**Purpose:** Configure existing systems rather than replacing them.

### Configuration split
- `camera.engine`: `atlas_learned | atlas_vp`
- `geometry.engine`: `da3 | moge`
- optional later `geometry.compare_both: true`

### Output switches
- `output.camera: true`
- `output.diagnostics: true`
- `output.pointcloud: true`
- `output.maya: true`
- `output.atlas_relief_mesh: false`
- `output.moge_mesh: false`
- `output.da3_mesh: false`

### Presets
- `fast_test`
- `balanced`
- `max_reference`

### Gate 6
Changing the config must switch backends/presets without editing upstream workflows or model code.

**Can test now?** Yes. Config-only switching should be testable before output standardization is complete.

---

## Stage 7 — Output B/C: diagnostics + standardized point geometry

### Output B — Diagnostics Package
Normalize available outputs into one folder structure:
- raw depth;
- display depth/heatmap;
- confidence when present;
- valid/sky mask when present;
- normals when present;
- solver/depth reports.

### Output C — Point Geometry Package
DA3:
- reuse DA3 point-cloud node/output directly;
- retain RGB and confidence;
- preserve engine-native PLY.

MoGe:
- reuse point map/native geometry;
- use the smallest adapter necessary to emit the same standard point format;
- do not replace MoGe's own point-map inference or geometry math.

### Standard manifest
Every run records:
- camera source;
- geometry source;
- model/checkpoint;
- resolution;
- filtering parameters;
- point count;
- coordinate convention;
- files produced;
- warnings.

### Gate 7
Both DA3 and MoGe produce equivalent directory/schema contracts even when their internal data differs.

**Can test now?** Yes. This is the primary V1 geometry checkpoint.

---

## Stage 8 — Output D: Maya ghost scene

**Reuse first:** Atlas Maya exporters/bridge.

### Camera path
- Use Atlas's Maya camera/export logic wherever possible.
- Preserve recovered projection and source image.
- Keep a locked matched camera plus a free artist perspective camera.

### Point-cloud path
Preferred order:
1. Use an existing Maya/MayaUSD point representation if the produced format is directly accepted.
2. Otherwise make the minimal glue conversion to USD `UsdGeomPoints` and let MayaUSD/Hydra display the points.
3. Do not instantiate one Maya transform per point.

### Reference hierarchy
- one predictable group/namespace;
- source plate/image plane;
- camera;
- point cloud;
- optional diagnostics/reference geometry.

### Gate 8
In Maya:
- matched camera view aligns with the source;
- colored points are visible;
- orbiting in `persp` reveals meaningful relative depth;
- reference can be hidden/deleted cleanly;
- no catastrophic viewport slowdown at chosen balanced preset.

**Can test now?** Yes. This is the main V1 acceptance gate.

---

## Stage 9 — A/B benchmark and preset selection

### Benchmark matrix
For each test concept run:
- Atlas learned camera + DA3 geometry;
- Atlas learned camera + MoGe geometry;
- Atlas VP camera + DA3 geometry where VP solve is valid;
- Atlas VP camera + MoGe geometry where VP solve is valid.

### Score only measurable/useful properties
- camera/source alignment;
- horizon/orientation plausibility;
- point-cloud silhouette fidelity;
- relative depth readability;
- edge-streamer/noise severity;
- foreground/background separation;
- Maya usability;
- VRAM/RAM/runtime notes;
- output size.

### Gate 9
Choose default `balanced` combination from evidence, while keeping both geometry engines selectable.

**Can test now?** Yes. This is the point where the user should choose the preferred engine on real concepts.

---

# Mesh tracks — workflow continues after successful point output

These are independent outputs. Failure of one track does not invalidate Stages 0–9.

## Stage 10 — Output E1: Atlas relief mesh

**Why first:** This is the most directly proven mesh path for our intended 2.5D camera-projection use, and Atlas documents imports into Maya/Nuke/Blender.

### Reuse
- `AtlasDeriveProjectionGeometry`
- `AtlasExportReliefMesh`
- Atlas hole-fill/export logic where useful
- Atlas Maya handoff

### Evaluate
- reprojection from solved camera;
- torn silhouettes at true discontinuities;
- UV/projected texture alignment;
- whether the surface helps manual blockout from side views.

### Gate 10
Classify per scene: `useful | limited | reject`.

**Can test now?** Yes. First mesh experiment.

---

## Stage 11 — Output E2: official MoGe mesh

### Reuse unchanged first
- official `3d_moge_perspective_to_mesh.json`.
- `MoGePointMapToMesh`.
- native discontinuity threshold, decimation, normals, texture.

### Only tune existing parameters first
- resolution level;
- decimation;
- discontinuity threshold;
- known/Atlas FOV when supported.

### Do not add custom repair algorithms until the stock public workflow has been measured.

### Gate 11
Compare MoGe shell against accepted MoGe point geometry and source camera. Classify `useful | limited | reject`.

**Can test now?** Yes. Second mesh experiment.

---

## Stage 12 — Output E3: DA3 mesh

### Reuse unchanged first
- public `bas_relief.json`.
- `DA3_ToMesh`.
- existing confidence filtering, depth-edge threshold, grid triangulation, UVs, normals, decimation.

### Compare against
- accepted DA3 point cloud;
- Atlas relief mesh;
- MoGe mesh.

### Gate 12
Classify `useful | limited | reject`. DA3 mesh is never promoted to default merely because it exports successfully.

**Can test now?** Yes. Third mesh experiment.

---

## Stage 13 — Packaging, uninstall, and final acceptance

### Installer finalization
`SETUP.bat` must:
- detect first;
- reuse compatible existing assets;
- install in staged order;
- log every write;
- measure sizes before/after;
- hash managed downloads;
- stop cleanly on unsafe dependency changes;
- produce final report.

### Uninstall
`UNINSTALL.bat` must:
- read manifest;
- preserve `preexisting=true` assets;
- warn on changed files;
- optionally preserve outputs;
- report expected/reclaimed bytes.

### Documentation
- installation map;
- exact file locations;
- disk footprint report;
- user workflow;
- output-stage explanation;
- troubleshooting;
- cleanup procedure;
- license/source inventory.

### Final acceptance
A fresh run should be able to stop at any of these useful outputs:
- A: camera;
- B: diagnostics;
- C: point cloud;
- D: Maya ghost scene;
- E1/E2/E3: independent optional mesh outputs.

**Can test now?** Yes. Full regression test and clean uninstall/reinstall cycle.

---

## Stage 14 — Future optional PCS integration

Not required for V1.

Potential role:
- manual/artist-guided vanishing-line correction;
- known-height metric anchor;
- explicit X/Y/Z world frame;
- compare Atlas learned/VP camera with PCS solve;
- feed a confirmed FOV/world orientation back into MoGe or downstream geometry.

Only start this after the Atlas-based camera + point-cloud pipeline is proven useful in Maya.

---

# Installation dependency order summary

1. **No downloads:** machine inventory + disk snapshot.
2. **Project safety framework:** manifests/ledger/dry-run.
3. **Atlas Camera core clone.**
4. **Atlas vision/GeoCalib camera dependencies** using the environment-safe upstream recipe.
5. **Camera baseline test.**
6. **DA3 custom node / DA3 minimal backend dependencies**, reusing existing assets first.
7. **DA3 point-cloud baseline test.**
8. **MoGe native workflow + MoGe-2 model**, reusing existing assets first.
9. **MoGe baseline test.**
10. **Unified config/output adapters.**
11. **Maya bridge/point display.**
12. **A/B validation.**
13. **Atlas relief mesh experiment.**
14. **MoGe mesh experiment.**
15. **DA3 mesh experiment.**
16. **Package/uninstall/final documentation.**

# Disk policy

Known large weights should be presented before download; actual disk usage is authoritative and measured by the installer.

Expected large categories include:
- DA3 checkpoint(s): model-dependent; use one V1 checkpoint first rather than downloading the entire model zoo.
- MoGe-2 checkpoint: one V1 checkpoint first.
- Hugging Face caches created by first-use downloads.
- Python packages installed into the existing ComfyUI interpreter.
- generated PLY/GLB/USD outputs, which can become much larger than the model code when dense/full-resolution.

The installer must report both:
- **managed project bytes** — safe to reclaim automatically;
- **shared/pre-existing bytes** — reused but not owned by ConceptGhost.

# Stop rules

- If Atlas camera baseline fails badly on the target concept set, stop before building the geometry integration and diagnose camera first.
- If an upstream DA3/MoGe reference workflow does not run unchanged, do not build our wrapper around it yet.
- If a dependency install would replace/downgrade ComfyUI's torch/numpy unexpectedly, abort and switch to an isolated/safe installation approach.
- If point-cloud output is not useful in Maya, do not spend time on mesh until that core problem is resolved.
- If one mesh path fails, continue testing the other public mesh paths independently.
