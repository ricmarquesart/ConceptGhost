# P10 Result Output Evidence Contract

**Status:** MANDATORY  
**Effective:** 2026-09-25

## Canonical active-run location

Every new P10 attempt owns a physical result tree inside the ComfyUI executable output hierarchy:

```text
<COMFYUI_OUTPUT>/
  conceptghost/
    p10_attempts/
      <P9_RUN_ID>/
        <P10_ATTEMPT_ID>/
          RESULTS/
```

This tree is created at attempt creation time, before panorama/WAN/reconstruction starts.

## Stage folders

The result tree contains one folder for every result milestone:

- `CG_00_P9_AUTHORITY`
- `CG_01_PRIVATE_AUTHOR_BASELINE`
- `CG_02_PANORAMA_360`
- `CG_03_PANORAMA_VALIDATION`
- `CG_04_CAMERA_RAILS`
- `CG_05_CAMERA_COVERAGE`
- `CG_06_WAN_COMPLETION`
- `CG_07_HIRES_COMPOSITE`
- `CG_08_MULTIVIEW_DATASET`
- `CG_09_WORLD_3DGS`
- `CG_10_COVERAGE_EXTENSION`
- `CG_11_P9_WORLD_REGISTRATION`
- `CG_12_POLYGON_WORLD`
- `CG_13_HOLE_FILL_ACCEPTANCE`
- `CG_14_P9_P10_FUSION`
- `CG_15_GEOMETRY_CLEANUP`
- `CG_16_TEXTURE_PROVENANCE`
- `CG_17_MAYA_360`
- `CG_18_COMPLETE_RELEASE`

Every stage contains:

```text
OUTPUTS/
PREVIEWS/
LOGS/
MANIFESTS/
STATUS.json
```

The root contains `RESULT_INDEX.json`.

## Result-first closure rule

A node, executable, CI job, model load, log file or non-empty artifact is not by itself proof that a result milestone succeeded.

Code must reject `functional_status=PASS` unless that stage already contains physical evidence in:

- `OUTPUTS`;
- `PREVIEWS`;
- `MANIFESTS`.

`artist_quality_status=ACCEPTED/PASS` is invalid unless functional status is already PASS.

This is specifically intended to prevent the historical failure mode where the pipeline advanced despite lacking useful artist-visible reconstruction.

## CG-00 seed evidence

At attempt creation the runtime immediately materializes:

```text
CG_00_P9_AUTHORITY/
  OUTPUTS/source_concept.png
  OUTPUTS/camera.json
  PREVIEWS/source_concept.png
  MANIFESTS/p9_authority_evidence.json
  STATUS.json
```

The authority manifest records source/camera SHA-256 and the immutable PrimaryMesh authority path.

## Later stages

Each author-aligned pipeline stage must write directly into its matching `CG_XX` result directory while that stage executes.

Examples:

- panorama generation → `CG_02_PANORAMA_360`;
- panorama reprojection/seam proof → `CG_03_PANORAMA_VALIDATION`;
- persistent rail files → `CG_04_CAMERA_RAILS`;
- coverage/closed-loop proof → `CG_05_CAMERA_COVERAGE`;
- WAN frames → `CG_06_WAN_COMPLETION`;
- source-preserving composites → `CG_07_HIRES_COMPOSITE`;
- SphereSfM/COLMAP data → `CG_08_MULTIVIEW_DATASET`;
- trained explorable world → `CG_09_WORLD_3DGS`;
- registered world → `CG_11_P9_WORLD_REGISTRATION`;
- polygonal reconstruction → `CG_12_POLYGON_WORLD`;
- accepted/rejected fill → `CG_13_HOLE_FILL_ACCEPTANCE`;
- Maya fusion diagnostic → `CG_14_P9_P10_FUSION`;
- final Maya world → `CG_17_MAYA_360`;
- final private bundle → `CG_18_COMPLETE_RELEASE`.

## Compatibility mirror

Historical/compatibility output trees under:

```text
<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/
```

may remain, but they are not the canonical active-run evidence tree and may not require a later backfill BAT for normal new runs.

## Implementation

The contract is implemented in:

`Experimental/P10_Lab/p10_lab/result_output_contract.py`

and initialized from P10 attempt creation in:

`Experimental/P10_Lab/p10_lab/route_handoff.py`

The detailed private per-stage artifact inventory remains in the private Google Drive roadmap and is intentionally not reproduced from licensed source materials here.
