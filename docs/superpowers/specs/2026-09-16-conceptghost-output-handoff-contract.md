# ConceptGhost — Output / Handoff Contract

Date: 2026-09-16
Status: Approved output target; mandatory read before Stage 8
Project: ConceptGhost

> DEVELOPMENT GATE
>
> Stage 8 Maya/export work must read this document before implementation. The user explicitly requires all standard formats to be generated together; do not turn them into mutually exclusive export choices.

## 1. User-facing promise

One valid ConceptGhost execution produces one self-contained run folder and automatically attempts all standard deliverables.

The user should normally open:

```text
ConceptGhost_<scene>_Ghost.ma
```

No manual camera reconstruction or DA3/MoGe import is required.

## 2. Required standard deliverables

```text
maya/ConceptGhost_<scene>_Ghost.ma
maya/ConceptGhost_<scene>_Ghost.usda
maya/ConceptGhost_<scene>_Ghost.fbx
geometry/canonical/pointcloud.ply
```

These are complementary outputs, not alternatives.

### `.ma` — artist entry point

Purpose:
- normal file the artist opens in Maya;
- preassembled camera, source reference, Ghost reference, optional validated meshes, and metadata;
- should use relative companion-file paths where possible.

Target hierarchy:

```text
ConceptGhost_<scene>
├── CG_CAMERAS
│   ├── matchedCamera_LOCKED
│   └── artistCamera
├── CG_SOURCE
│   └── sourcePlate
├── CG_REFERENCE
│   └── <engine>_Ghost
├── CG_OPTIONAL_MESH
└── CG_METADATA
```

### `.usda` — authoritative technical Ghost scene

Purpose:
- efficient point-scene interchange;
- expected carrier for the Canonical Point Cloud via OpenUSD/UsdGeomPoints;
- can also preserve camera/transforms/metadata where useful;
- intended to be consumed by MayaUSD/Hydra after Stage 8 validation.

This is the primary technical representation of the dense Ghost.

### `.fbx` — compatibility companion

Purpose:
- portable matched-camera handoff;
- portable mesh handoff when optional meshes exist and are valid for export;
- useful for Maya/Blender/other FBX-capable software.

Minimum FBX contract:

```text
matchedCamera
supported camera projection/FOV data
scene transform/axis/scale context
validated optional meshes when available
```

FBX must be generated automatically; it is not a user choice instead of MA/USD.

Important limitation:
- do not promise the Canonical Point Cloud inside FBX;
- standard FBX interoperability is not a reliable point-cloud carrier;
- if Stage 8 proves a stable point representation, it may be added as an enhancement only;
- USD/PLY remain authoritative for points.

### `.ply` — portable Canonical Point Cloud

Purpose:
- simple XYZ/RGB canonical point representation;
- diagnostics;
- recovery;
- inspection in other 3D tools;
- independent verification of the Ghost data.

PLY is not the normal Maya entry point.

## 3. Relationship between the files

```text
Canonical Point Cloud
     ├── pointcloud.ply
     └── Ghost.usda
             │
             └── referenced/loaded by Ghost.ma

Atlas Camera
     ├── Ghost.ma
     ├── Ghost.usda where useful
     └── Ghost.fbx

Optional validated meshes
     ├── Maya scene / USD as appropriate
     └── FBX
```

No output should require a Blender conversion step before Maya.

## 4. Normal artist workflow

```text
Run ConceptGhost
-> open run folder
-> open ConceptGhost_<scene>_Ghost.ma
-> matched camera is ready
-> source plate is ready
-> Ghost is ready
-> orbit with artist/perspective camera
-> create normal Maya geometry and model
```

Alternative files are present for portability and troubleshooting, not because the artist must assemble the scene manually.

## 5. Stage 8 validation matrix

Stage 8 must test at minimum:

```text
MA
- opens without manual relinking
- correct matched camera
- source plate relationship correct
- Ghost visible
- usable viewport performance

USD
- point count preserved
- XYZ convention preserved
- RGB preserved
- camera relationship preserved
- MayaUSD load stable

FBX
- matched camera imports correctly
- FOV/projection remains acceptably consistent
- axis/scale conversion documented
- optional validated meshes import correctly
- point-cloud absence does not count as FBX failure

PLY
- point count preserved
- XYZ preserved
- RGB preserved
- can be independently inspected
```

Maya 2018, 2024, and 2026 compatibility should be characterized, not assumed identical. The final supported Maya target(s) must be based on fresh Stage 8 evidence.

## 6. Package-completeness semantics

The product distinguishes artist usability from export completeness:

```text
maya_ghost_ready
deliverable_package_complete
run.status
```

Target production behavior:

```text
valid .ma + .usda Ghost
-> maya_ghost_ready = true

.ma + .usda + .fbx + .ply all produced
-> deliverable_package_complete = true
```

If Maya Ghost is usable but a required companion exporter fails, preserve the usable Ghost and mark the run/package PARTIAL rather than deleting successful outputs.

## 7. Optional meshes

Atlas relief, MoGe mesh, and DA3 mesh remain optional branches.

Only meshes that exist and are suitable for export are added to the normal FBX companion.

A mesh classified `reject` must not be silently presented as a good primary FBX mesh.

Mesh success/failure does not redefine the Canonical Point Cloud.

## 8. Essential evidence

Every run that reaches these stages preserves:

```text
manifest.json
diagnostics/reprojection_report.json
diagnostics/reprojection_overlay.png
geometry/canonical/geometry.json
```

The manifest records each deliverable separately:

```text
outputs.ma.status
outputs.usd.status
outputs.fbx.status
outputs.ply.status
```

It also records file paths, hashes where practical, exporter versions, coordinate/scale conventions, and warnings.

## 9. Storage safety

Every run has a unique `run_id`.

Never:
- overwrite a previous run;
- silently reuse an existing deliverable filename in the same run folder;
- automatically delete prior results.

Before Max Reference, perform a disk-space preflight and warn when available storage is below the documented safe threshold.

## 10. Local processing

Generating MA/USD/FBX/PLY is part of the local ConceptGhost workflow.

Google Drive is for project-development documentation/tools and is not required to process a user's concept image.
