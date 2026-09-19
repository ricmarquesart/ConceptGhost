# ConceptGhost v0.31.2 RC3 WIP — Runtime Ready Report

Baseline authority remains frozen at GitHub commit `20d2109de78754c6bd3306e6ad2f2f96cab4cc4a` / branch `frozen/v0.31.1-runtime-validated-20260918`.

## Local result
- compile/import: PASS
- pytest: 57 PASS
- v0.31.2 workflow graph: PASS — 31 nodes / 71 links / no dangling links
- active workflow: `ConceptGhost_Master_v0.31.2_DEDUP_REMESH.json`
- duplicate complete-run ZIP: disabled
- fused-points preview: restored without another PLY payload
- PrimaryMesh Master: exact Maya authority
- remesh switch: OFF by default
- Light / Medium / Strong: optional derived outputs only

## Real frozen-run remesh proof
Reference run: `20260919T032045_435115Z_63417285`

| Output | Vertices | Faces | GLB bytes |
|---|---:|---:|---:|
| PrimaryMesh Master | 1,426,735 | 2,823,599 | 82,206,728 |
| Remesh Light | 354,777 | 684,730 | 22,238,152 |
| Remesh Medium | 157,415 | 300,267 | 11,309,012 |
| Remesh Strong | 88,294 | 166,803 | 7,495,568 |

All derived remeshes use `depth_edge_rtol=0.04`, have `vertex_motion=0`, embed the source texture, and contain `CG_ARTIST_CAMERA`.

## Runtime acceptance still required
Run RC3 on the target Windows/ComfyUI/Maya 2026 machine, then require:
- High Fidelity PrimaryMesh parity PASS
- MAYA_LIVE PASS
- MAYA_REOPEN PASS
- FBX_ROUNDTRIP PASS
- `CG_FUSED_POINTS` present in `.ma`
- camera/FOV/transforms/UV/normals/material linkage unchanged
- normal run contains no `*_COMPLETE.zip`
- only one physical canonical USDA
- source texture is reused rather than duplicated
- Remesh OFF produces no Light/Medium/Strong files
- Remesh ON produces all three separate outputs

RC3 WIP source SHA-256: `e64a1d08557869cb9ae433891f6620a9b32e129978aa1876ef8d16205fe96776`.
