# ConceptGhost — P10 Quality Refinement Policy

Status: **APPROVED DESIGN POLICY — implementation scheduled after the first complete end-to-end Refined result unless a requirement is needed earlier for correctness.**

This policy defines the final-quality operating profile for HiRes source authority, multiview dataset expansion, temporary working storage, automatic cleanup and retained diagnostics.

## 1. Official drone / camera-path profile

- Official default route count: **7 adaptive routes**.
- Route count may remain fixed at 7 for the first quality-refinement implementation.
- Routes remain geometry-adaptive; Gate 11 owns route-family and coverage refinement.
- Official default: **30 frames per drone**.
- Standard nominal dataset: **~210 generated frames** before later selection/subsampling.
- `frames_per_drone` must be a clear configurable node property; changing it must not require editing the workflow.
- More frames are not assumed to be better. Future intelligent frame selection/subsampling may retain only views with useful incremental coverage/parallax.

Official defaults:
```
drones = 7
frames_per_drone = 30
```

## 2. HiRes Composite — REQUIRED final-quality pass

Mode: **geometry/source-authority**.

Presets exposed as an enum/preset:
- **4K — DEFAULT**
- 6K
- 8K

Official default:
```
hires_resolution = 4K
```

Policy:
- 4K is the normal RTX 2080 Ti profile.
- 6K and 8K are optional higher-quality profiles.
- authoritative source/P9 reprojection wins wherever valid;
- WAN contributes only in genuinely unknown/disoccluded pixels;
- RAFT is **not required** for the principal geometry/source-authority mode;
- coverage/gate masks and representative evidence remain diagnosable.

Logical insertion point:
```
Gate 5 WAN generation
  -> HiRes Composite source-authority pass
  -> Gate 6 reconstruction dataset materialization
```

## 3. HiRes Views / dataset augmentation — REQUIRED final-quality pass

HiRes Views improve multiview evidence without replacing camera authority.

Requirements:
- reuse existing P9/P10 geometry and cameras;
- create additional views only when they add useful reconstruction/texture evidence;
- register added views into the reconstruction dataset with known intrinsics/poses;
- do not overwrite or move existing authoritative cameras;
- keep the same temporary-storage lifecycle as other heavy intermediates;
- retain selected views for Gate 8 texture recovery/baking.

Logical insertion point:
```
Gate 6.1 camera authority
  -> HiRes Views / useful-view selection
  -> Gate 6.3 feature extraction + matching
```

## 4. Per-run temporary workspace

All heavy run-specific intermediates must live under **one visible workspace**:

```
<ComfyUI output>/conceptghost/_temp/<run_id>/
    wan/
    hires_composite/
    hires_views/
    colmap/
    dense/
    caches/
```

Every relevant runtime node/manifest must expose:

```
temp_workspace_path
```

The real absolute path must be copyable from the UI and recorded in the master run manifest.

## 5. Automatic cleanup

Official default:
```
auto_clean = ON
```

Rules:
- heavy files are temporary;
- a stage may delete an intermediate only after the next dependent stage has completed and validated successfully;
- never remove artifacts still required downstream;
- final cleanup occurs only after final validation and final Maya/mesh/textures are confirmed.

Successful-run lifecycle:
```
FINAL VALIDATION PASS
  -> FINAL .ma / mesh / textures confirmed
  -> AUTO CLEAN LARGE INTERMEDIATES
  -> TEMP WORKSPACE removed
```

Failure/cancel/crash policy:
```
KEEP TEMP FILES
```

No automatic evidence deletion on incomplete runs.

## 6. Failed-run safety

`temp_workspace_path` must always remain visible while the workspace exists.

Workspace lifecycle state must be recorded as one of:
- `CLEAN`
- `ACTIVE`
- `FAILED_RETAINED`
- `CLEANUP_PENDING`

Record estimated and, when practical, measured workspace size.

A later UI action may provide:
```
Clean Failed Run
```
but manual cleanup must never be required during normal successful operation.

## 7. Small retained diagnostic package

Permanent delivery contains:
- final_scene.ma
- final mesh
- final textures
- compact diagnostic package

Target:
```
diagnostic_package_max <= 200 MB
```
Prefer substantially below the ceiling.

Retain useful evidence only:
- master manifest JSON;
- health summary;
- stage PASS/WARN/FAIL summary;
- camera/path summary;
- representative thumbnails;
- 1–3 panorama previews;
- representative drone views;
- hole-mask overview;
- sparse preview;
- dense point-cloud preview;
- pre-fusion mesh preview;
- final-fusion preview;
- original-camera regression preview;
- summarized logs;
- paths/categories of artifacts removed by cleanup.

Do **not** retain:
- all 4K/6K/8K frames;
- complete WAN intermediate sequences;
- mass debug PNGs;
- full depth/normal maps;
- COLMAP caches/databases after final acceptance unless explicitly retained for a failed run;
- complete HiRes Composite working frames;
- complete HiRes Views working set.

## 8. Cleanup audit

Before deleting the workspace, write:
```
cleanup_manifest.json
```

It records:
- run_id;
- temp_workspace_path;
- workspace size before cleanup;
- removed files/categories;
- cleanup timestamp;
- cleanup result;
- deliberately preserved artifacts.

After cleanup, the retained diagnostic package must be sufficient to verify that cleanup occurred.

## 9. Storage philosophy

Permanent:
- source code;
- shared model/runtime assets;
- final deliverables;
- compact diagnostic package.

Large per-run storage:
- temporary.

Temporary-space demand scales approximately with:
```
drones * frames_per_drone * resolution * enabled_stages
```

Node UI must communicate:
- **7 drones / 30 frames / 4K = official default**;
- 6K increases processing/storage;
- 8K is a high-quality profile and can require substantial temporary space.

Reference HiRes Composite working-space measurements from the upstream SplatKit documentation at 8192 panorama width and four trajectories:
- 25 selected frames/route: ~2.3 GB total;
- 41 selected frames/route: ~3.8 GB total;
- 81 frames/route: ~7.4 GB total.

Approximate linear planning envelope for 7–10 routes at comparable 8K output:
- 25 frames/route: ~4.0–5.8 GB;
- 41 frames/route: ~6.7–9.5 GB;
- 81 frames/route: ~13–18.5 GB.

For HiRes Views, reserve roughly ~1–3 GB for a moderate 4K augmentation set across 7–10 routes and ~4–8 GB for a heavier 8K set. Runtime must record actual measured usage; these are planning estimates, not hard limits.

## 10. Official default quality profile

```
drones = 7
frames_per_drone = 30
HiRes Composite = ON
HiRes Views = ON
hires_resolution = 4K
auto_clean = ON
preserve_on_failure = ON
debug_heavy = OFF
diagnostic_package = ON
diagnostic_package_max = 200 MB
```

Central principle:

> Large files should exist only for as long as they are required to produce the next validated result. Final deliverables and a small diagnostic package remain; the heavy per-run workspace is removed automatically after successful final validation.

## Roadmap mapping

- **Gate 10.3** — implement unified temp workspace lifecycle, `temp_workspace_path`, state machine and safe stage-by-stage cleanup eligibility.
- **Gate 10.6** — release-candidate lifecycle validation: final deliverables confirmed before cleanup, cleanup audit, failed-run retention.
- **Gate 11.3** — official 7 adaptive routes / 30 configurable frames per route.
- **Gate 11.6** — required HiRes Composite with 4K default and 6K/8K presets.
- **Gate 11.7** — required HiRes Views / useful-view dataset augmentation.
- **Gate 11.8** — A/B quality/runtime/storage regression of base vs HiRes-enhanced pipeline.
- **Gate 12.2–12.5** — standardized evidence folders, health states, compact diagnostic package and cleanup index/manifest.

The policy becomes release-blocking for final-quality acceptance after the first end-to-end Gates 4–10 result exists.
