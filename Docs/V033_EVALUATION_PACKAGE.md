# ConceptGhost v0.33 EVALUATION Package

Rollback authority remains `frozen/v0.32-complete-20260918`.

## Complete evaluation bundle
Google Drive folder:
https://drive.google.com/drive/folders/1TlE4pHmJYeY-rtnWdZAN9-tAOcujeO1R

File:
`ConceptGhost_v0.33_EVALUATION.zip`

SHA-256:
`db32301e68a11b9af0b4749dd3c72f26c7938c0a3827f80c1800ef8bea3cec39`

## Package validation
- v0.32 × v0.33 benchmark comparator included and synthetic self-test PASS
- comparator checks source-image hash, Atlas camera/FOV, PrimaryMesh arrays, vertex/face counts, storage dedup invariants, and P8 safety constraints
- 43 total files; bundle manifest inventories 41 payload files
- workflow: 40 nodes / 87 links
- pinned MoGe vendor included: 11,590,402 bytes
- packaged Python/import validation: PASS
- bundle hash inventory: PASS
- local source regression suite: 125 PASS

## Safety defaults
- Remesh variants OFF
- Depth Pro OFF
- Metric consensus OFF
- P7 geometric regions OFF
- P8 local cleanup OFF
- P8 artist approval OFF
- official PrimaryMesh is never automatically replaced

## Real frozen-reference evidence
P7:
- 2,823,599 faces processed in ~10.5 s
- ~940 MB peak RSS
- 96 retained regions
- 96.65% face coverage
- PrimaryMesh unchanged

P8 derived candidate:
- 1 severe removable face
- 1 planar region selected
- 14,705 vertices moved in derived candidate only
- mean displacement ~1.24 cm
- hard max displacement 2.00 cm
- planar RMS 7.50 cm -> 6.25 cm (~16.7% reduction)
- zero movement outside approved region
- PrimaryMesh replacement false

## P9
No new frozen external model is promoted. Point-SAM, EZ-SP, UniDepth, Metric3D, Mask3D, Mosaic3D and similar heavier systems remain frozen until a benchmark proves a specific unresolved gap.


## P8 final safety decision
- Small-hole real proof on frozen 2,823,599-face PrimaryMesh: 30,965 boundary edges, 218 closed loops, 202 loops with <=64 edges, only 3 artist-review candidates after region/depth-boundary protection.
- Automatic hole filling remains disabled.
- Adaptive local remesh status: `DEFERRED_BY_BENCHMARK`; do not ship an unproven local triangulator before boundary-constrained crack-free stitching is demonstrated.
- P7 + P8 real evaluation: ~14 s total, ~993 MB peak RSS on frozen reference.
- Local regression suite: **125 PASS**.


## Source checkpoint
- Drive source snapshot: `ConceptGhost_v0.33_SOURCE_SNAPSHOT.zip`
- SHA-256: `a3131ea45f5929b00009337e9140be90ac47ad046a72528b0a5b2db18aa7e3dd`
- 77 source/test/doc files; the 11.59 MB pinned MoGe vendor archive is intentionally excluded from this source-only snapshot and remains in the complete EVALUATION bundle.
