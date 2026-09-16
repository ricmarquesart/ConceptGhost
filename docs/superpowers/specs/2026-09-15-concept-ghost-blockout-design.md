# Concept Ghost Blockout — Design Specification

Date: 2026-09-15
Status: Revised after prior mesh-failure review; written-spec re-approval pending
Target platform: Windows + ComfyUI + Autodesk Maya

## 1. Purpose

Build a repeatable single-image concept-art reconstruction pipeline that turns a city/village/environment image into the most useful possible 3D reference for manual blockout in Maya.

The project is not intended to promise a complete watertight scene from one image. Its primary success criterion is a camera-matched "ghost blockout" that gives the artist reliable spatial guidance: perspective, relative depth, proportions, major silhouettes, color reference, and optional 2.5D shell geometry.

Primary output hierarchy:
1. Matched camera / projection.
2. Dense colored point cloud / point map.
3. Diagnostics: depth, confidence, masks, normals, heatmap.
4. Maya import setup that preserves the projection relationship.
5. Reference shell mesh only after the camera + point-cloud pipeline passes its acceptance gates.

## 2. Architecture

Two independent engines are supported from the same configuration surface.

### Engine A — Depth Anything V3 (DA3)
Reference implementation:
- PozzettiAndrea/ComfyUI-DepthAnythingV3
- Reference workflows retained unmodified: advanced.json, advanced_3d.json, bas_relief.json

DA3 responsibilities:
- depth inference in Raw mode
- confidence
- camera intrinsics
- camera-related diagnostics
- dense RGB point cloud using geometric unprojection
- optional reference shell mesh using grid triangulation

DA3 point cloud is considered a core output.
DA3 mesh is NOT a V1 acceptance dependency. It remains disabled by default until the DA3 camera + point-cloud baseline passes reprojection and Maya validation. Only then may it be enabled as an experimental reference shell.

### Engine B — MoGe
Reference implementation:
- ComfyUI native MoGe integration
- Official Comfy-Org workflow template: 3d_moge_perspective_to_mesh.json
- Primary V1 checkpoint: moge_2_vitl_normal_fp16.safetensors

MoGe responsibilities:
- metric/relative geometry point map
- depth
- estimated intrinsics/FOV
- validity mask
- normals
- textured reference shell mesh
- standardized point-cloud export through the project adapter

MoGe point-map/depth/intrinsics outputs are core V1 outputs. Although native ComfyUI and Microsoft MoGe can triangulate the point map and export GLB/PLY, MoGe mesh is NOT treated as evidence of useful reconstruction quality and is disabled by default until the point-cloud/camera pipeline proves itself locally.

### Future engine slots
The adapter boundary must permit future engines without changing Maya integration. Candidates include MoGe-3, VGGT, or later DA3 variants. They are not mandatory V1 dependencies.

## 3. Key geometric principle

For a single source image, absolute world-space camera position is not treated as ground truth. The pipeline normalizes each engine into a canonical camera-space representation:

- X = right
- Y = up
- Z = backward
- canonical camera at origin
- camera looks toward -Z

What must remain invariant is the projective relationship among:
- source pixels
- camera intrinsics
- generated points/mesh

The standardized camera record preserves the full intrinsic matrix rather than only FOV:
- fx
- fy
- cx
- cy
- image_width
- image_height
- horizontal_fov
- vertical_fov
- projection convention
- source engine

This permits principal-point offsets to be reproduced in Maya instead of assuming a centered camera.

## 4. Mesh policy

### Historical-failure constraint
A previous local attempt to obtain useful meshes from single-image AI reconstruction produced results far below the user's practical target. That failure is treated as a project constraint, not as an anomaly to ignore. Therefore this project must not equate "the node exported a GLB" with "the mesh is useful".

The implementation order is deliberately point-cloud-first:
1. Camera/intrinsics must be useful.
2. Colored point cloud / point map must provide useful spatial guidance.
3. Reprojection in Maya must align acceptably with the source.
4. Only after those gates pass do we spend implementation/debugging time on shell meshes.

A generated single-view mesh, if later enabled, is a **reference shell / 2.5D reconstruction**, not a complete scene.

Expected useful behavior:
- front-visible surfaces follow inferred geometry
- foreground/background discontinuities are cut rather than bridged where possible
- source colors are preserved as UV texture or vertex color
- major buildings/terrain can become palpable surfaces for blockout reference

Expected limitations:
- unseen backsides are not reconstructed reliably
- occluded geometry is inferred or absent
- thin structures may break
- concept-art perspective can be intentionally non-physical
- scale may remain ambiguous unless metric inference or a manual scale anchor is supplied

### DA3 mesh
DA3_ToMesh uses K^-1 unprojection, confidence filtering, optional sky mask, relative depth-edge rejection, grid triangulation, UVs, normals, optional decimation, and GLB export.

Initial classification: DEFERRED_EXPERIMENTAL_REFERENCE. Disabled by default until the core point-cloud gates pass.

### MoGe mesh
MoGe converts its point map to a triangulated grid mesh with discontinuity rejection, UVs, texture, and GLB output.

Initial classification: DEFERRED_REFERENCE_SHELL. Technically supported upstream, but usefulness must be demonstrated locally before becoming part of the normal workflow.

## 5. Standard output bundle

Every run writes a self-contained bundle regardless of engine.

`<project_root>/output/<scene>/<run_id>/`

- `source/`
  - source image copy or link metadata
- `geometry/`
  - `pointcloud.ply`
  - `pointcloud.npz` where available
  - `shell.glb` when enabled/available
  - optional engine-native geometry
- `camera/`
  - `camera.json`
  - `intrinsics.json`
  - optional engine-native camera data
- `diagnostics/`
  - `depth_raw.*`
  - `depth_colored.png`
  - `confidence.png` when available
  - `mask.png` when available
  - `normal_opengl.png` when available
  - engine metadata/preview files
- `manifest/`
  - `run_manifest.json`
  - `versions.json`
  - `warnings.txt`

No engine is allowed to bypass the standardized bundle.

## 6. Maya bridge

The Maya bridge is engine-agnostic and consumes only the standardized bundle.

V1 target behavior:
1. Load point cloud as USD/Hydra points when MayaUSD support is available.
2. Preserve point RGB/displayColor and configurable point width.
3. Import/reference shell GLB/USD if requested.
4. Create a native Maya camera using the standardized intrinsics.
5. Match image aspect ratio and render resolution.
6. Apply principal-point offset via film offset / equivalent Maya camera controls.
7. Attach source image as camera image plane.
8. Lock the matched camera by default.
9. Leave normal `persp` free for blockout work.
10. Group reference data under a predictable namespace/group for one-click hide/delete.

Fallback if direct PLY display is unsuitable: convert project point data to USD `UsdGeomPoints` before Maya import.

## 7. Configuration

Main file: `config.yml`

Required conceptual sections:

```yaml
project:
  root: C:\\ConceptGhost
  output_root: C:\\ConceptGhost\\output

comfyui:
  root: auto

engine:
  active: da3   # da3 | moge

engines:
  da3:
    model: da3_base.safetensors
    normalization_mode: Raw
    confidence_threshold: 0.10
    downsample: 1
    filter_outliers: false
    outlier_percentage: 5.0
    mesh:
      enabled: false
      experimental: true
      depth_edge_threshold: 0.10
      target_faces: 100000

  moge:
    model: moge_2_vitl_normal_fp16.safetensors
    resolution_level: 9
    fov_x_degrees: 0.0
    apply_mask: true
    mesh:
      enabled: false
      decimation: 1
      discontinuity_threshold: 0.04
      texture: true

camera:
  mode: auto       # auto | override
  override_fov_x: null

maya:
  use_usd_points: true
  point_width: 1.0
  lock_camera: true
  create_image_plane: true

storage:
  track_every_write: true
  prevent_duplicate_models: true
  verify_hashes: true
```

Exact schema may gain versioning fields during implementation, but these semantics are fixed.

## 8. Default model choices and licensing safeguards

### MoGe V1
Default:
- `moge_2_vitl_normal_fp16.safetensors`
- known published size: approximately 662 MB
- SHA-256 must be pinned by installer

### DA3 V1
Default safest baseline:
- `da3_base.safetensors`
- published model file approximately 542 MB
- Apache 2.0 in the DA3 model-zoo table
- SHA-256 must be pinned by installer

Optional higher-quality preset:
- DA3 Large 1.1
- approximately 1.64 GB
- licensing metadata is treated conservatively because first-party surfaces have shown inconsistent labels; installer/config must display a warning and never silently switch from Base to Large.

The project does not provide legal advice. It records upstream license identifiers and source URLs in the install manifest.

## 9. Installation strategy

Primary entry point: `SETUP.bat`.

The installer must be idempotent. Running it twice must not duplicate models, repos, workflows, or project files.

### Detection before installation
- locate ComfyUI or read configured path
- identify Python used by that ComfyUI install
- detect existing DA3 custom node
- detect native MoGe nodes in current ComfyUI
- detect required model files at expected locations
- verify hashes where known
- detect reference workflows already present
- detect MayaUSD availability where possible without altering Maya
- detect legacy/existing copies before downloading duplicates

### Writes outside project root
Some files necessarily live under the user's existing ComfyUI tree:
- `ComfyUI/custom_nodes/ComfyUI-DepthAnythingV3/`
- `ComfyUI/models/depthanything3/...`
- `ComfyUI/models/geometry_estimation/...`
- optional ComfyUI workflow directory

Every external write must be recorded individually in the installation manifest.
Existing files are marked `preexisting=true` and are never deleted by project cleanup unless the user explicitly opts in.

### No hidden permanent environment changes
V1 avoids permanent system/user environment-variable edits unless a future dependency makes one unavoidable.
No PATH mutation without explicit user action.

## 10. Disk accounting

Disk transparency is a hard requirement.

The installer creates:
- `logs/install.log`
- `manifests/install_manifest.json`
- `manifests/disk_ledger.json`
- `manifests/disk_ledger.csv`
- `manifests/download_hashes.json`

For every managed asset, record:
- path
- category
- source URL/repository
- version/commit when available
- SHA-256 when available
- preexisting flag
- size_before
- size_after
- bytes_added
- timestamp
- owning component

Track at minimum:
- project root
- DA3 custom-node folder
- DA3 model folder
- MoGe model folder
- project workflows
- project outputs
- installer caches created by this project

Before and after each major setup phase, capture free-space snapshots for the target drive.

The final setup report prints:
- files downloaded
- paths touched
- total bytes added by category
- estimated reclaimable bytes
- preexisting assets reused
- assets intentionally not touched

### Cache policy
Downloads initiated by our scripts use a project-controlled temporary/cache location when possible. Temporary download artifacts are deleted after successful hash verification and final placement. Third-party package-manager caches that cannot be attributed safely are reported rather than blindly deleted.

## 11. Cleanup strategy

A future `UNINSTALL.bat` is part of V1, not an afterthought.

It must:
- read `install_manifest.json`
- delete only assets created by this project
- preserve `preexisting=true` assets
- remove project workflows and bridge scripts
- optionally preserve output bundles
- show exact bytes expected to be reclaimed
- write an uninstall report

If a tracked file changed after installation, cleanup must warn and avoid deleting it automatically unless forced.

## 12. Reference workflows retained verbatim

The setup keeps upstream workflows unchanged under:

`<project_root>/workflows/reference/da3/`
- `advanced.json`
- `advanced_3d.json`
- `bas_relief.json`

`<project_root>/workflows/reference/moge/`
- `3d_moge_perspective_to_mesh.json`

Project-derived workflows live separately under:
`<project_root>/workflows/project/`

This separation enables baseline-versus-project debugging.

## 13. Project-derived workflows

V1 intends two user-facing workflows:

### `concept_ghost_da3.json`
Input image -> DA3 Raw inference -> diagnostics -> point cloud -> optional DA3 shell -> standardized metadata outputs.

### `concept_ghost_moge.json`
Input image -> MoGe inference -> diagnostics -> point-map/point-cloud export -> textured shell -> standardized metadata outputs.

No V1 hybrid workflow. A hybrid is created only after A/B testing demonstrates a specific measurable advantage.

## 14. Quality presets

Config supports at least:
- `fast_test`
- `balanced`
- `max_reference`

`max_reference` prioritizes geometry fidelity and dense reference output, not runtime or file size.

The actual inference resolution is still bounded by engine/model behavior; merely exporting more points does not create information the network did not infer.

## 15. Validation gates

### Gate A — Installation
- all required nodes load without ComfyUI startup errors
- model hashes match pinned values
- no unexpected disk writes outside tracked paths

### Gate B — DA3 baseline
- upstream `advanced_3d.json` runs unchanged on a test image
- PLY produced
- point count > 0
- camera intrinsics present

### Gate C — MoGe baseline
- upstream official workflow runs unchanged far enough to verify model inference
- point map/depth/mask/normal available
- FOV/intrinsics recoverable
- GLB export may be observed for comparison but is not an acceptance requirement

### Gate D — Standardization
- both engines emit equivalent `camera.json` schema
- both engines emit point-cloud output
- both engines emit diagnostics
- mesh presence/status is declared explicitly

### Gate E — Reprojection
Render/project the generated 3D reference through the reconstructed camera and compare against source-image pixel positions. This is the primary camera/geometry consistency test.

### Gate F — Maya core acceptance
- camera image plane aligns to projected reference
- USD points display correctly in VP2
- point cloud provides usable depth/proportion guidance from a free perspective view
- free perspective view permits manual blockout

### Gate G — Mesh experiment (only after Gates A-F pass)
- enable MoGe shell first, then DA3 shell independently
- compare shell reprojection to the already-accepted point cloud
- reject meshes with severe depth bridges, collapsed planes, unusable silhouette distortion, or misleading spatial relationships
- record mesh as `useful`, `limited`, or `reject` for each test scene
- mesh failure must never block delivery of a successful camera + point-cloud pipeline

## 16. Success criteria

V1 is successful even if mesh quality is imperfect, provided:
- camera projection is useful and repeatable
- dense colored ghost geometry provides clear spatial guidance
- major depth relationships are understandable
- the source image overlays consistently from the matched camera
- Maya import requires minimal manual setup
- all installation/storage footprints are auditable and removable

Mesh success is a later bonus above the primary point-cloud/camera goal. DA3 and MoGe mesh paths will only be activated after the core pipeline passes Gates A-F. Upstream technical support for mesh export is treated as feasibility evidence, not quality evidence.

## 17. Non-goals for V1

- automatic semantic replacement of inferred surfaces with clean architectural primitives
- full hidden/backside reconstruction from one image
- production topology
- automatic final asset creation
- guaranteed real-world metric scale for arbitrary concept art
- automatic hybrid fusion before baseline comparison

## 18. Planned implementation deliverables after written-spec approval

1. Detailed implementation plan with test-first gates.
2. `SETUP.bat` and supporting PowerShell/Python helpers.
3. `UNINSTALL.bat`.
4. `config.yml` with documented presets.
5. pinned download/source manifest.
6. upstream reference-workflow downloader.
7. DA3 point-cloud-first project workflow.
8. MoGe point-map/point-cloud-first project workflow.
9. standardized bundle exporter/adapters.
10. Maya bridge for camera + image plane + USD points.
11. disk accounting and cleanup verification.
12. smoke-test checklist and A/B test scene protocol.
13. Only after Gates A-F pass: optional MoGe shell experiment.
14. Only after MoGe shell evaluation: optional DA3 shell experiment.
