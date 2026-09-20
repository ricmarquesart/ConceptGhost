# ConceptGhost v0.38.1 — P9 Recovery Checkpoint

Status: **WIP / STATIC RECOVERY PASS / WINDOWS-COMFYUI-MAYA RUNTIME PENDING**

Baseline authority:
- branch: `frozen/v0.36-stable-p9-20260919`
- commit: `f76a62cce9ed639cbf99099f596b7f15aafd1115`
- frozen source SHA-256: `02ff409d700f37693c7b1e802b5e10123227856a3eabc4346d24b1b3a6f0dfd8`
- complete baseline bundle SHA-256: `3cf763e76f9bdbca436643e3edad6f8e95d782252328b589a668d7f105d79d6b`

Recovery checkpoint:
- Drive folder: `ConceptGhost_v0.38.1_P9_RECOVERY_CHECKPOINT`
- Drive folder id: `1MDc8EkENRIakHHRHw8e0WCqoUriZYz29`
- ZIP: `ConceptGhost_v0.38.1_P9_RECOVERY_CHECKPOINT.zip`
- Drive file id: `1MOoULgfWBRClAUDOvDWwhmLZuKvO1LqD`
- ZIP SHA-256: `24971e79972e9b82eee7918ef1596f6362dfdd06b0da67ea07c383685e66a3fa`
- source-only ZIP SHA-256: `999c5c003c0ea8d8d3df2714033dce887014e93d491dc38fdffbb1b077717dbd`
- bundle manifest: 59 payload files, hash/size validation PASS
- promotion_allowed: false

GitHub recovery guard:
- workflow: `.github/workflows/p9-recovery-guard.yml`
- protects the frozen v0.36 source hash and baseline path
- validates the checkpoint contract and blocks a false `promotion_allowed: true`
- connector-created commits did not auto-trigger an Actions run at checkpoint creation; no CI PASS is claimed until GitHub records an actual run

## Recovery fixes completed

1. Dense Depth Fusion boundary voting ignores zero/near-zero gradients before quantile selection.
2. Dense Depth confidence is based on coherent inliers instead of merely valid solver inputs.
3. Canonical geometry authority explicitly accepts `p9_solver_fusion` in the PrimaryMesh builder.
4. Maya export receives the actual canonical `geometry_engine` instead of a hard-coded `moge`.
5. v0.38.1 packaging/verifier/version metadata was rebuilt around one canonical recovery workflow.

## Static recovery evidence

- Reference focal consensus: 36.83 / 38.10 / 37.40 -> 37.43639826191275 deg
- Atlas-outlier case: MoGe independent + DepthPro remain the coherent pair
- No safe two-source cluster: fail-closed
- Dense-depth boundary ratio: 0.020833333333333332
- Clean median confidence: 1.0
- Deliberate outlier-region median confidence: 0.6666666865348816
- Canonical point count: 6144
- PrimaryMesh vertices: 6144
- PrimaryMesh faces: 11970
- Reprojection RMSE: 1.434430298025357e-06 px
- Canonical source engine: `p9_solver_fusion`
- Workflow: 92 nodes / 189 links / 17 groups
- Static recovery suite: PASS

## Gate interpretation

This checkpoint closes the identified P9 Recovery defects at static/synthetic level only. It does **not** claim Windows GPU execution, ComfyUI execution, Maya opening/export acceptance, or final P9 promotion.

Next implementation gate:
**repersist/complete P9.3-P9.8 contracts before P9.10 geometry authority work.**
