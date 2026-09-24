# ConceptGhost P10 — Gate 7 r3 Runtime Fix + Drone Route UX

Date: 2026-09-24

## Runtime failure reproduced from user evidence

Observed failure:

`ConceptGhostP10Gate7Runtime` node 2400 entered Gate 7.3 free-space evidence and failed because:

`dense/sparse/cameras.txt` did not exist.

The Gate 6 attempt itself had already completed WAN / known-camera reconstruction and produced the dense COLMAP workspace.

## Root cause

Gate 6 invokes COLMAP `image_undistorter` using `--output_type COLMAP`.

A valid COLMAP dense workspace commonly stores its undistorted sparse calibration/poses as native binary files:

- `dense/sparse/cameras.bin`
- `dense/sparse/images.bin`

Gate 7.3 incorrectly assumed those same models would always be serialized as text:

- `cameras.txt`
- `images.txt`

Therefore the failure was a Gate 7 reader-contract defect, not evidence that WAN, Gate 6, the GPU, or P9 camera authority had failed.

## r3 correction

`colmap_dense_io.py` now supports both representations:

1. text model when `.txt` exists;
2. native binary model when `.bin` exists.

Native binary readers added:

- `parse_colmap_cameras_bin`
- `parse_colmap_images_bin`
- `load_colmap_sparse_cameras`
- `load_colmap_sparse_images`

Gate 7.3 now consumes those generic loaders.

The authority remains fail-closed:

- undistorted camera must still be PINHOLE;
- invalid/truncated binary payloads fail;
- non-finite poses/intrinsics fail;
- no camera refit or P9 scale/camera mutation occurs.

Focused Gate 7.3 regression: GitHub Actions run `35970218207` — SUCCESS.

## Drone route editor refinements

r3 also incorporates the requested route-authoring refinements:

- orthographic zoom ceiling: 160x;
- perspective zoom ceiling: 48x;
- point placement no longer invokes automatic route fitting;
- point dragging no longer invokes automatic route fitting;
- same-scene Queue Prompt refresh preserves artist zoom/pan;
- explicit Enquadrar tudo remains the viewport reset;
- route reset preserves the current viewport;
- Exportar trajeto writes a portable JSON route preset;
- Importar trajeto validates and loads saved missions, then removes the old route hash so the backend rebinds/re-hashes it against the current accepted scene/run;
- cross-scene import is allowed as an artist preset but visibly warns that coordinates must be reviewed;
- four-view internal panel resolution increased to 720x660;
- dynamic interactive P9 point budget increased to 50,000;
- backend static preview budget increased to 70,000.

These are editor/evidence changes only and do not alter P9 solver authority.

## Package

`ConceptGhost_v1.54_P10_GATE7_PREVIEW_r3_ROUTE_UX_COLMAP_FIX.zip`

Inner package SHA-256:

`de9c377e4da3d5cbf103bd1c1cbd626469fb0f9ef1049b6d84d9ad16a3b10f05`

Inner package bytes:

`12,348,390`

Frozen base:

`ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r15`

Base SHA-256:

`cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd`

Source/package build commit:

`09183c3d40e181dd7da6d0777d48681b56fd3e14`

GitHub Actions:
- r3 package build: `35971021535` — SUCCESS;
- ConceptGhost Tests: `35971021815` — SUCCESS;
- P10 source snapshot: `35971021529` — SUCCESS.

Google Drive:
`ConceptGhost/Storage/Evaluation_Builds/ConceptGhost_v1.54_P10_GATE7_PREVIEW_r3_ROUTE_UX_COLMAP_FIX.zip`

## Gate status

Gate 7 source/runtime defect correction: implemented and CI-green.

Gate 7 real-user runtime acceptance: pending this r3 test.

RUN_AUDIT_BUNDLE: retained.

Gate 8: blocked.
