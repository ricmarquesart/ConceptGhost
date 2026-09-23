# ConceptGhost P9 — MoGe Depth Diagnostics — Optional Diagnostic Lane

Date: 2026-09-23

## Purpose

Provide an optional, artist-facing diagnostic lane that reveals how MoGe interpreted scene depth, planes and volume while keeping the official P9/P10 pipeline unchanged.

The diagnostic lane is **OFF by default**. When OFF, it writes no diagnostic folder and does not change the official geometry path. When ON, it becomes a side branch only: it may ask MoGe to return optional per-step evidence, then exports visual/raw diagnostics without feeding any result back into Canonical PrimaryMesh, scale, camera, fusion, Maya or P10 authority.

## Exact workflow placement

The lane is inserted in **Workflow 01 / Route Setup**, inside the Refined/P9 MoGe area.

Official path remains:

`Geometry Profile -> MoGe inference -> Projection Support -> Geometry Evidence -> Canonical P9 -> Export`

Diagnostic side path:

`Geometry Profile -> diagnostic profile tap -> MoGe inference`

and

`MoGe raw geometry + source image -> MoGe Depth Diagnostics Export -> comparison preview`

The profile tap only toggles optional return evidence. Projection Support / Geometry Evidence keep receiving the official base profile contract. Therefore the diagnostic lane does not become geometry authority.

## Node/group layout

Group title:

`P9 · MoGe Depth Diagnostics · OPTIONAL · OFF BY DEFAULT`

Nodes:

1. **P9 · MoGe Depth Diagnostics · ENABLE = OFF BY DEFAULT**
   - Enable MoGe Diagnostics
   - Save Raw Outputs
   - Generate 3D Previews
   - Generate Extra Depth Visuals

2. **P9 · MoGe Depth Diagnostics · NOTES · READ BEFORE ENABLING**
   - visible notes covering Purpose, Inputs, What it does, Outputs, Authority, Geometry impact, Default state, Failure/fallback, TEMP/retention, Next stage.

3. **P9 · MoGe Depth Diagnostics · OPTIONAL PER-STEP TAP**
   - receives official geometry profile;
   - when diagnostic mode is ON, requests optional per-step evidence only;
   - does not alter official profile fields or official geometry selection.

4. **P9 · MoGe Depth Diagnostics · EXPORT · DIAGNOSTIC ONLY**
   - consumes MoGe raw geometry/report + source image;
   - saves native and derived diagnostics;
   - fail-open: diagnostic failure does not replace or mutate official geometry.

5. **P9 · MoGe Depth Diagnostics · COMPARISON MOSAIC**
   - visual quick-inspection panel.

## Native MoGe data

When present in the MoGe geometry contract, the diagnostic exporter recognizes:

- native depth (`depth_metric_native` / `depth`);
- native point map (`points_metric_native` / `points`);
- native normals (`normal_native` / `normal`);
- native mask (`mask_native` / `mask`);
- native intrinsics (`intrinsics_native` / `intrinsics`);
- optional per-step arrays such as `depth_per_step_*`, `points_per_step_*`, `intrinsics_per_step_*`.

These are classified as **native evidence**. They are never interpreted as a new authority and never replace P9 official output.

## Derived visual diagnostics

When depth is available:

- original input image;
- depth grayscale;
- depth heatmap;
- inverse depth / disparity visualization;
- quantized depth bands;
- depth contours;
- depth discontinuity map based on log-depth gradient;
- depth percentile/window statistics.

When normals are available:
- RGB normal visualization.

When mask is available:
- binary mask preview.

When points are available and 3D preview is enabled:
- FRONT / SIDE / TOP point-cloud preview;
- source-colored sampled PLY for external inspection.

Quick inspection:
- comparison mosaic combining the main diagnostics.

The official PrimaryMesh preview is **not duplicated** in this diagnostic branch. The existing P9 Primary Master remains the authoritative downstream mesh preview.

## Raw technical outputs

With Save Raw Outputs ON, diagnostic folders can include:

- `depth_native.npy`
- `points_native.npy`
- `normal_native.npy`
- `mask_native.npy`
- `intrinsics_native.npy`
- optional `refinement_steps/*.npy`
- intrinsics JSON
- sampled diagnostic PLY
- manifest JSON with shapes, dtypes, min/max/mean, native-vs-derived classification and file paths.

Raw/per-step evidence can be large. It is intentionally generated only when the main diagnostic switch is ON.

## Storage

Path:

`<ConceptGhost output root>/_diagnostics/moge_depth/<scene_name>/<timestamp_uuid>/`

This storage is intentionally separate from official P9 and P10 attempt directories.

A diagnostic run writes its own `manifest.json`.

## Retention / cleanup

- Explicitly enabled diagnostic runs are preserved until manual cleanup.
- Normal P10 auto-clean must not delete them.
- If the diagnostic exporter itself fails after creating the folder, it attempts to preserve a partial manifest and any already-written files.
- Diagnostic retention is separate from P10 attempt retention.
- P9 authoritative run data is never deleted by this feature.

## Failure / fallback policy

Diagnostic lane = **fail-open**.

If diagnostic generation fails:
- return diagnostic WARN;
- preserve partial evidence when possible;
- do not change MoGe official geometry;
- do not replace Canonical PrimaryMesh;
- do not alter camera/scale/fusion/Maya authority.

## OFF-state authority guarantee

When `Enable MoGe Diagnostics = OFF`:

- no diagnostic directory is created;
- no raw diagnostic arrays are written;
- no derived diagnostic images are written;
- official P9/P10 output behavior is unchanged;
- existing Master extra-diagnostics behavior, if explicitly used elsewhere, is not reduced by this lane.

## Test intent

Primary use case:

Run the same street scene with diagnostics enabled and inspect whether foreground facades, street depth, tower/background planes and long perspective regions are separated by MoGe in a way that explains the downstream P9 depth structure.

This diagnostic lane is for understanding, not correcting, MoGe.

## Next stage

The official pipeline continues to normal Refined/P9 Canonical/Export, followed by Route Setup and P10 Production. Any later decision to use diagnostic evidence as authority would require a separate explicit gate and is outside this feature.


## Implementation / package status

Implementation is complete in the r8 diagnostic package.

- Default state: OFF.
- Diagnostic authority: side branch only.
- Official geometry impact: NONE.
- Package: `ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r8.zip`.
- Source commit: `e6823e4617c394aedec4796a2e277d8f9bf4429b`.
- CI run: `35900795172` — SUCCESS.
- ZIP SHA-256: `9774a887e397e18d9dcb76c65dea29ce4496ec95f0fa75570b400238dad0139c`.
- Google Drive: Evaluation_Builds, file id `1wyRBo_RqXJQXm8JCmRUpMyaPHk11X0Vr`.
- GitHub Release: `p10-dr9r-r8`.
- Runtime inspection on the target street scene is still required to judge the diagnostic usefulness, not its authority.
