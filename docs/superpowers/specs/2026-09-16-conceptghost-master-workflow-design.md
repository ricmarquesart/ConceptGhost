# ConceptGhost Master Workflow Architecture

Date: 2026-09-16
Status: Approved architecture sections 1-4
Project: ConceptGhost

> This document supersedes the old V1 workflow split described in Section 13 of `2026-09-15-concept-ghost-blockout-design.md`. The final user-facing architecture is one master workflow, not separate DA3 and MoGe production workflows.

## 1. Final user-facing architecture

ConceptGhost will have one primary user-facing ComfyUI workflow:

`ConceptGhost_Master.json`

The user provides one source concept image. The workflow fans out internally into camera, geometry, diagnostics, point-cloud, Maya handoff, and optional mesh branches.

The workflow is modular internally even though it is presented as one workflow externally.

### Primary flow

```text
SOURCE IMAGE (single input)
        |
        +------------------------------+
        |                              |
        v                              v
ATLAS CAMERA                     GEOMETRY ROUTER
Learned / VP                           |
        |                  +-----------+-----------+
        |                  |                       |
        |                 DA3                    MoGe
        |                  |                       |
        |                  +-----------+-----------+
        |                              |
        |                    Compare Both optional
        |                              |
        +---------------+--------------+
                        v
             CONCEPTGHOST NORMALIZER
                        |
        +---------------+----------------+
        |               |                |
        v               v                v
     CAMERA         DIAGNOSTICS      POINT CLOUD
    Output A          Output B        Output C
        |                                 |
        +---------------+-----------------+
                        v
                MAYA GHOST ASSEMBLER
                        |
                        v
                 PRIMARY OUTPUT
                MAYA GHOST SCENE
                    Output D
```

Optional mesh branches are attached later and are not part of the mandatory success path:

- Output E1 — Atlas relief mesh
- Output E2 — MoGe mesh
- Output E3 — DA3 mesh

Mesh failure must never invalidate a successful camera + point-cloud + Maya Ghost result.

## 2. Geometry engine selection and Compare Both

Normal operation runs one geometry engine only.

```text
Compare Both = OFF + geometry.engine = DA3
-> run DA3 only

Compare Both = OFF + geometry.engine = MoGe
-> run MoGe only

Compare Both = ON
-> run DA3 and MoGe independently
-> keep their native outputs separate
-> normalize both into ConceptGhost canonical geometry
-> provide side-by-side comparison
-> do not fuse their geometry automatically
```

DA3+MoGe hybrid fusion is explicitly out of scope until A/B evidence demonstrates a measurable advantage.

The final user should not have to choose among multiple final workflows such as `Atlas_DA3.json` or `Atlas_MoGe.json`. Those may exist only as internal development/test fixtures. The intended production interface is one `ConceptGhost_Master.json`.

## 3. How the master workflow grows by stage

### Stage 3 — Atlas camera baseline
- Test Atlas independently.
- Prove learned camera / GeoCalib and VP fallback behavior.
- No master integration yet.

### Stage 4 — DA3 baseline
- Run upstream `advanced_3d.json` unchanged.
- Prove raw depth, confidence, intrinsics, and point cloud.
- No master integration yet.

### Stage 5 — MoGe baseline
- Run official MoGe workflow unchanged.
- Prove point map/depth/mask/normals/FOV or intrinsics.
- No master integration yet.

### Stage 6 — Master Alpha
Create the first `ConceptGhost_Master.json` shell.

Responsibilities:
- one source-image input;
- camera engine selection: `atlas_learned | atlas_vp`;
- geometry engine selection: `da3 | moge`;
- `geometry.compare_both: true | false`;
- output switches;
- presets;
- branches remain engine-native internally.

At this stage outputs are not yet fully normalized.

### Stage 7 — Master Beta / canonical contracts
Create explicit internal contracts:

#### CameraBundle
- source image resolution;
- focal/FOV;
- principal point;
- full intrinsic matrix K when available;
- orientation;
- camera transform/projection;
- solver source;
- confidence/diagnostics.

#### GeometryBundle
- engine source (`da3 | moge`);
- raw depth or point information;
- confidence where available;
- valid/sky mask where available;
- normals where available;
- native intrinsics/FOV;
- native point cloud/point map;
- filtering parameters;
- model/checkpoint identity.

#### CanonicalGeometry
- XYZ points;
- RGB;
- confidence/validity;
- original source-pixel coordinate where retained;
- source geometry engine;
- canonical camera reference;
- canonical coordinate convention.

#### SceneBundle
`SceneBundle = CameraBundle + CanonicalGeometry + Source Image + Manifest`

The downstream Maya bridge and optional mesh/export consumers must use the standardized SceneBundle rather than engine-specific internals.

### Stage 8 — First usable V1 product
CameraBundle and CanonicalGeometry converge into the Maya Ghost package.

Primary V1 product:

`ConceptGhost Maya Ghost Scene`

Expected Maya hierarchy conceptually:

```text
ConceptGhost_<scene>
|-- CG_CAMERAS
|   |-- matchedCamera_LOCKED
|   `-- artistCamera
|-- CG_REFERENCE
|   |-- sourcePlate
|   `-- ghostPoints
|-- CG_OPTIONAL_MESH
`-- CG_METADATA
```

### Stage 9 — A/B benchmark
Compare combinations under the same camera authority:
- Atlas learned + DA3;
- Atlas learned + MoGe;
- Atlas VP + DA3 where valid;
- Atlas VP + MoGe where valid.

Use evidence to choose balanced defaults. Both geometry engines remain selectable.

### Stages 10-12 — optional mesh branches
- Stage 10: Atlas relief mesh E1
- Stage 11: MoGe mesh E2
- Stage 12: DA3 mesh E3

Each is independent and classified per scene as `useful | limited | reject`.

### Stage 13 — final packaging
Freeze the user-facing master workflow, presets, output contract, installer/uninstaller, documentation, and acceptance tests.

## 4. Camera authority and geometry authority

ConceptGhost uses a clear hierarchy of authority:

```text
CAMERA / PROJECTION
Atlas = source of truth

DEPTH / SHAPE
DA3 or MoGe = source of truth

COLOR
Original concept = source of truth

FINAL SCENE SPACE
ConceptGhost Canonical Scene = source of truth
```

The final Maya Ghost must not blindly reuse each engine's native camera-space point cloud as the only authoritative representation.

Native outputs are preserved for diagnostics and comparison, but the primary ConceptGhost ghost geometry is normalized against the selected Atlas camera.

### DA3 path

Preserve native evidence:
- raw depth;
- confidence;
- DA3-estimated intrinsics;
- native DA3 point cloud.

Primary canonical point cloud concept:

```text
Source pixels + DA3 depth + Atlas Camera
-> ConceptGhost Canonical Point Cloud
```

### MoGe path

Preserve native evidence:
- point map;
- depth;
- mask;
- normals;
- estimated FOV/intrinsics;
- native MoGe geometry/mesh where produced.

Canonical geometry is then transformed/reconstructed into the same ConceptGhost camera/scene convention used by the Atlas camera.

## 5. Canonical scene-space rule

The system must explicitly define and record:
- X/Y/Z axis meaning;
- handedness;
- camera forward direction;
- origin;
- image resolution;
- principal point;
- focal/FOV;
- coordinate transforms;
- scale mode and units.

The exact canonical convention must be implemented once and consumed consistently by Maya/USD/export code.

Default scale mode is relative:

`scale_mode = relative`

Absolute metric scale must not be invented from arbitrary single-view concept art. A future/manual scale anchor may enable:

`scale_mode = anchored`

with a known real-world measurement.

## 6. Mandatory reprojection gate

Before Maya acceptance, canonical geometry must pass a reprojection consistency test.

For points derived from source pixels:

```text
Original pixel (x, y)
      + depth
        -> 3D point
        -> Atlas camera projection
        -> Reprojected pixel (x', y')
```

Expected:

`(x', y') ~= (x, y)`

Large disagreement blocks the Maya handoff until the cause is resolved.

Potential causes to diagnose include:
- wrong FOV/focal length;
- principal-point mismatch;
- image-resolution mismatch;
- axis/handedness error;
- camera transform error;
- coordinate-conversion error.

This reprojection check is a mandatory Stage 7 gate, not an optional visual check.

## 7. Compare Both semantics

When `Compare Both = ON`, DA3 and MoGe are evaluated under the same selected Atlas camera.

This ensures the comparison is primarily about geometry/depth quality rather than a confounded comparison of two different camera estimates.

Conceptually in Maya:

```text
CG_REFERENCE
|-- DA3_Ghost
`-- MoGe_Ghost
```

One may be visible by default while the alternate is hidden for inspection. No automatic fusion occurs in V1.

## 8. Final input/output contract

### User input
One concept image.

### Normal controls
- Preset: `fast_test | balanced | max_reference`
- Camera: `auto | atlas_learned | atlas_vp`
- Geometry: `da3 | moge`
- Compare Both: `off | on`
- Maya Ghost: on/off
- Diagnostics: on/off
- Point Cloud: on/off
- Optional meshes: individually on/off

### Outputs
- Output A — Camera Package
- Output B — Diagnostics Package
- Output C — Point Geometry Package
- Output D — Maya Ghost Package **(primary V1 output)**
- Output E1 — Atlas Relief Mesh (optional)
- Output E2 — MoGe Mesh (optional)
- Output E3 — DA3 Mesh (optional)

### Run bundle
Each run is self-contained:

```text
ConceptGhost_Output/<scene>/<run_id>/
|-- source/
|-- camera/
|-- diagnostics/
|-- pointcloud/
|-- maya/
|-- meshes/
`-- manifest.json
```

The manifest records source image, camera solver, geometry engine(s), model/checkpoint, resolution, filtering, coordinate convention, scale mode, generated files, warnings, and reprojection status.

## 9. Primary success criterion

ConceptGhost succeeds when the artist can open the Maya Ghost scene, view the source through the matched camera with strong projective agreement, leave the camera into a free perspective view, and use the colored ghost geometry as meaningful spatial guidance for manual blockout.

Depth maps, confidence maps, point clouds, and optional meshes remain important diagnostic/reference outputs, but the primary product is the Maya Ghost Scene.

## 10. Run bundle, output contract, and execution status

Each execution is treated as one auditable run: one source image + one configuration + one self-contained result bundle. Outputs must not be scattered across ComfyUI without a traceable run identity.

### Run identity and directory layout

Each run receives a deterministic scene name and unique run ID, for example:

```text
village_001
2026-09-16_001
```

The run bundle is written as:

```text
ConceptGhost_Output/<scene>/<run_id>/
|-- source/
|-- camera/
|-- diagnostics/
|-- geometry/
|-- maya/
|-- meshes/
|-- compare/
|-- logs/
`-- manifest.json
```

### Source package

`source/` records the original image and source metadata such as filename, width, height, aspect ratio, original path, and file hash. The source hash prevents accidental mixing of runs from different images with identical filenames.

### Output A — camera package

`camera/` stores the normalized CameraBundle plus Atlas-native evidence and review material. Expected files include, where available:

- `camera.json`
- `atlas_native.json`
- `intrinsics.json`
- `projection.json`
- `overlay.png`
- `camera_report.json`

The downstream pipeline consumes the normalized CameraBundle rather than depending directly on an Atlas-private serialization.

### Output B — diagnostics package

`diagnostics/` preserves engine evidence without fabricating unavailable data. Candidate artifacts include:

- raw depth;
- display depth;
- confidence;
- valid/sky mask;
- normals;
- engine-native camera information;
- reprojection overlay;
- `reprojection_report.json`;
- `diagnostics.json`.

For every expected diagnostic, the manifest records one of: `available`, `not_available`, `not_requested`, or `failed`.

### Output C — geometry package

Native and canonical geometry are kept separate. Example:

```text
geometry/
|-- native/
|   `-- <engine>/
|       `-- engine-native geometry
`-- canonical/
    |-- pointcloud.ply
    |-- pointcloud.usda
    `-- geometry.json
```

The primary Maya Ghost consumes canonical geometry, not the engine-native point cloud directly. Native geometry remains preserved for debugging and comparison.

### Reprojection is both a gate and a visible output

The reprojection test must generate machine-readable metrics and a visual overlay. At minimum, the report records status, tested point count, mean pixel error, median pixel error, and maximum pixel error.

A significant reprojection failure preserves diagnostics but blocks publication of a valid Maya Ghost result.

### Compare Both output layout

When `Compare Both = OFF`, only the selected geometry engine is executed.

When `Compare Both = ON`, DA3 and MoGe remain independent:

```text
geometry/
|-- da3/
|   |-- native/
|   `-- canonical/
`-- moge/
    |-- native/
    `-- canonical/

compare/
|-- comparison.json
|-- da3_preview.png
|-- moge_preview.png
`-- side_by_side.png
```

`Compare Both` is comparison, not fusion.

In Maya, the intended reference hierarchy is:

```text
CG_REFERENCE
|-- DA3_Ghost
`-- MoGe_Ghost
```

One branch may be visible by default while the other remains hidden for inspection.

### Output D — Maya Ghost package

`maya/` contains the primary V1 deliverable. USD remains the preferred point-cloud interchange unless Maya validation proves a more robust alternative. Candidate contents are:

- `ConceptGhost_<scene>.usda`;
- optional native Maya scene when justified by validation;
- an open/import helper if useful;
- `maya_manifest.json`.

Expected scene organization:

```text
ConceptGhost_<scene>
|-- CG_CAMERAS
|   |-- matchedCamera_LOCKED
|   `-- artistCamera
|-- CG_SOURCE
|   `-- sourcePlate
|-- CG_REFERENCE
|   `-- <engine>_Ghost
|-- CG_OPTIONAL_MESH
`-- CG_METADATA
```

### Outputs E1/E2/E3 — optional meshes

Optional meshes are written under `meshes/atlas_relief`, `meshes/moge`, and `meshes/da3` as requested. Their existence never implies quality. Every evaluated mesh is classified `useful`, `limited`, or `reject`.

### Central manifest

`manifest.json` is the run authority. It records at minimum:

- run ID and timestamps;
- source path and source hash;
- selected camera solver and camera confidence;
- selected geometry engine and `Compare Both` state;
- model/checkpoint and relevant parameters;
- canonical coordinate convention and scale mode;
- reprojection result;
- generated outputs;
- warnings;
- component versions;
- overall run status.

### Overall execution states

Every run resolves to exactly one high-level state:

- `PASS` — valid camera + valid canonical geometry + reprojection pass + Maya Ghost generated.
- `PARTIAL` — useful intermediate outputs exist, but a non-core or downstream component failed; successful outputs are preserved.
- `FAIL` — no valid end-to-end Maya Ghost may be presented, for example because camera solve is unusable, no usable geometry exists, or canonical reprojection fails.

Intermediate success must never silently substitute for the primary success criterion. A DA3 PLY, an Atlas camera, or a generated GLB alone is not a ConceptGhost `PASS`.

The core acceptance equation is:

```text
Atlas Camera
+ Canonical Geometry
+ Reprojection PASS
+ Maya Ghost usable
= ConceptGhost PASS
```

### User-facing result summary

The Master workflow should expose a concise run result showing status, camera engine, geometry engine, reprojection status, point-cloud status, Maya Ghost readiness, optional mesh state, and final output path. The user should not have to inspect internal nodes to determine whether a run succeeded.
