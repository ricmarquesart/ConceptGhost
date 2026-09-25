# ConceptGhost Gate 7 R6F14 — COLMAP Graph + R6G + Audit Fix

Date: 2026-09-25

## Target evidence

P9 run: `20260925T170319_730339Z_8806dd74`
P10 attempt: `20260925T172201_471780Z_a99e3910_6be21b61`

The target run reached Gate 7.3 after Gate 6 completed. Gate 7 stopped while
reading `frame_000000.png.geometric.bin` with
`contains invalid consistency record`. P9 authority and official geometry
were unchanged.

## Root cause

ConceptGhost decoded consistency records as:

`row, col, N, sources...`

COLMAP 4.2's consistency graph implementation serializes/reads:

`col, row, N, sources...`

This is material on non-square images. A valid column in an 832-wide image may
be greater than the 480-pixel height; the reversed parser therefore rejected a
valid record as an impossible row.

R6F14 decodes the wire record as `col,row,N` but continues to expose the
Python mapping as conventional `(row,col)` image-index keys.

A non-square 832x480 regression test locks this behavior.

## Last-run Gate 6 review

The audit bundle confirms:
- runtime PASS;
- sparse quality PASS;
- Gate 7 promotion allowed;
- 100 registered images and 100/100 usable geometric-evidence views;
- 29,528 fused dense points;
- pre-fusion mesh PASS, 7,571 vertices / 13,094 faces;
- P9 roundtrip quality PASS;
- all five missions contribute to sparse reconstruction.

The overall Gate 6 quality remains WARN because:
- `SPARSE_POINT_DENSITY_LOW`;
- `HIGH_SPARSE_COMPONENT_FRAGMENTATION`.

R6F14 deliberately does not weaken the quality gates. These remain diagnostic
signals to revisit after Gate 7 can complete.

## Audit bundle

The failed run successfully proved run-local audit storage:

`<P9_RUN_DIR>/RUN_AUDIT_BUNDLE.zip`

The observed partial-failure bundle was ~258 MB and nearly consumed its 250 MiB
admission budget because it duplicated regenerable PNG frame sequences.

R6F14 excludes bulk control-sequence frames/masks, WAN raw frames, composite
frames, dataset images and dense images while preserving logs, JSON manifests,
text diagnostics, GIFs, contact sheets and selected diagnostic previews.

The audit collector now explicitly includes the P9 `logs/` folder and prioritizes
`p9_authority/` evidence ahead of optional P10 payload when the size budget is
tight. Replaying the new policy against the captured failed-run audit reduced the
ZIP from 257,810,720 bytes to 26,737,275 bytes while retaining the P9 manifest,
P9 stage log, six GIF summaries and contact-sheet/diagnostic previews.

## R6G

R6F14 carries the source/CI-complete R6G Route Editor improvements:
- selected camera view on the left;
- four-view workspace on the right;
- coherent mesh display LOD;
- image-space point sampling;
- larger local per-view controls;
- HQ selected-camera previews.

## Runtime / P9 isolation

The v0.36-compatible one-root MoGe runtime stays unchanged.
The R6F12-restored P9 PrimaryMesh policy stays unchanged.
Gate 8 remains blocked pending target-PC Gate 7 acceptance.
