# ConceptGhost P10 — R6H Gate 6 Live Progress & Streaming Logs

Date: 2026-09-25  
Status: PLANNED NEXT AFTER R6G SOURCE/CI CLOSEOUT — do not alter the currently running target-PC test

## Why this exists

Gate 6 can legitimately spend many minutes inside COLMAP, especially
`patch_match_stereo`. The current implementation launches each native command
with captured stdout/stderr and writes its log file only after the command exits.
That makes a healthy 15–30 minute operation look frozen in ComfyUI.

R6H changes observability only. It must not change cameras, image resolution,
COLMAP reconstruction settings, P9/P10 geometry, WAN outputs, Poisson settings or
Gate 7 authority.

## R6H-A — Stage-visible reconstruction status

Workflow 02 / STEP 4 must expose the current bounded stage:

1. dataset preparation;
2. sparse triangulation;
3. image undistortion;
4. PatchMatchStereo;
5. stereo fusion;
6. Poisson meshing;
7. geometry-quality analysis;
8. reconstruction preview/final manifest.

Each stage reports at minimum:
- PENDING / RUNNING / PASS / REUSED / FAIL;
- start time;
- elapsed time;
- current command;
- absolute log path;
- last output/heartbeat time.

No invented percentage is allowed. A percentage is displayed only if the native
tool provides trustworthy progress information.

## R6H-B — Streaming native logs

Replace end-only `subprocess.run(..., capture_output=True)` behavior for the
long-running COLMAP reconstruction commands with a streaming process runner.

Requirements:
- stdout/stderr are appended to disk while COLMAP is running;
- the UI/status manifest receives periodic heartbeat updates;
- partial logs survive crash, cancellation or native-process failure;
- final logs preserve command line, exit code, start/end time and duration;
- UTF-8 decoding errors cannot kill the reconstruction monitor;
- no unbounded in-memory capture of long COLMAP output.

## R6H-C — Artist-visible heartbeat

The STEP 4 node must visibly distinguish:
- active work;
- reuse of an already-valid checkpoint;
- a process with no recent output but still alive;
- a failed/stopped native process.

Example target presentation:

```
STEP 4 — Known-Camera Reconstruction
✓ Dataset               REUSED
✓ Sparse triangulation  PASS
✓ Image undistortion    PASS
▶ PatchMatchStereo      RUNNING · 00:16:24
  GPU 0 · geometric consistency ON
  last log update: 8 s ago
○ Stereo fusion
○ Poisson mesh
○ Geometry quality
```

## R6H-D — Resume/audit integration

When `resume_existing = ON`, the same status report must show exactly which
stages were REUSED versus rebuilt.

Streaming logs and the final progress/status manifest must be discoverable by the
run audit collector so a later `RUN_AUDIT_BUNDLE.zip` contains the reconstruction
history without the artist manually finding individual folders.

## R6H-E — Safety / acceptance

R6H passes only if:
- reconstruction result hashes/authority are unchanged for the same inputs;
- native COLMAP return codes still fail closed;
- cancellation leaves readable partial evidence;
- resume still reuses valid dataset/sparse/dense/mesh checkpoints;
- logs update while a long PatchMatchStereo process is still running;
- no extra runtime/model installation is introduced;
- target RTX 2080 Ti can complete the same reconstruction path.

## Roadmap placement

Current official runtime-validation boundary remains Gate 7 / R6F.

Latest independent source work:
- Gate 8.1 defect analysis: SOURCE/CI COMPLETE, promotion blocked by Gate 7;
- R6G Route Editor visual quality/layout: SOURCE/CI COMPLETE;
  target-PC visual acceptance still pending.

R6H is inserted immediately after R6G as the next bounded observability
refinement before further user-facing Gate 8 promotion. It does not retroactively
change the current test package.
