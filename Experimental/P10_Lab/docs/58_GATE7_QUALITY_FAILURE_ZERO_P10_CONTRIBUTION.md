# Gate 7 target-PC quality finding — zero P10 geometric contribution

Date: 2026-09-25
Run: `20260925T170319_730339Z_8806dd74`
P10 attempt: `20260925T182415_329568Z_a99e3910_7d5df9fe`

## Result

R6F15 fixed the runtime blocker and Gate 7 now executes to completion on the
target PC. Runtime status PASS is confirmed.

The artist review and the run audit show, however, that this is **not yet a
quality success**.

Protected fusion counts:
- P9 vertices: 1,362,804
- P9 faces: 2,665,370
- P10 pre-fusion vertices: 12,184
- P10 pre-fusion faces: 21,089
- P10 accepted faces: **0**
- P10 rejected faces: **21,089**
- P10 candidate vertices added: **0**
- final candidate vertices: 1,362,804
- final candidate faces: 2,665,370

The uploaded protected-fusion PLY therefore contains only layer 1 / P9 geometry.
The candidate topology counts are identical to P9 because Gate 7 accepted no
P10 geometry.

## Rejection distribution

- P9_SOURCE_PROTECTED_OVERLAP: 16,090
- FREE_SPACE_CONFLICT: 4,379
- CONFIRMED_FREE_VETO: 620
- DELAUNAY_DISAGREEMENT: 0
- INSUFFICIENT_PROVENANCE: 0
- LOW_CONFIDENCE: 0
- SUPPORT_DISTANCE: 0

## Provenance finding

Gate 7.2 sampled 6,092 P10 vertices and classified:
- P9_RETAINED: 6,092 / 100%
- P10_MULTIVIEW_SUPPORTED: 0
- P10_GENERATED_ONLY: 0
- CONFLICT: 0
- UNKNOWN: 0

Gate 7.2C therefore assigned all sampled P10 evidence to NEUTRAL confidence
(mean ~0.55); no P10 sample reached HIGH.

Gate 6 was already WARN:
- sparse points: 64
- verified sparse components: 12
- SPARSE_POINT_DENSITY_LOW
- HIGH_SPARSE_COMPONENT_FRAGMENTATION

The pre-fusion mesh itself is technically healthy, but it is mostly close to
the existing P9 surface: dense-to-P9 median ~0.145 m, p90 ~0.403 m,
p95 ~0.534 m.

## Interpretation

The current pipeline proves that Route -> WAN -> COLMAP -> Gate 7 can execute,
but it does not yet prove the actual ConceptGhost objective of reconstructing
useful novel/occluded geometry.

Gate 8 structural regularization cannot solve this specific failure because
there is no accepted P10 geometry to regularize.

Mainline priority is therefore changed:
1. preserve the recovered P9 quality and R6F15 runtime;
2. keep R6H observability work safe/parallel;
3. add explicit completion-effectiveness authority;
4. diagnose why Gate 6/7 produces zero multiview-supported novel surface;
5. prove non-zero, spatially meaningful P10 contribution on the target scene;
6. only then promote Gate 8 runtime work.

## Audit-sidecar improvement

Future audit builds will write beside `RUN_AUDIT_BUNDLE.zip`:
- `RUN_TECHNICAL_SUMMARY.json`
- `RUN_TECHNICAL_SUMMARY.txt`
- `RUN_GATE7_VISUAL_REVIEW.png` when available

The summary explicitly separates runtime PASS from completion quality and
contains P9/P10 counts, acceptance ratio, rejection reasons, Gate 6 quality,
provenance/confidence and key artifact paths.

For the current target run these three sidecars were also written manually to
the run directory in Google Drive.

## Gate state

- Gate 7 runtime: PASS
- Gate 7 completion effectiveness: FAIL
- Gate 7 artist quality acceptance: NOT ACCEPTED
- Gate 8 runtime promotion: BLOCKED
