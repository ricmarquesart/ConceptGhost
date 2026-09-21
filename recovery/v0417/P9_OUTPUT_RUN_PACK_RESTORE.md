# ConceptGhost v0.41.7 — Official Run Pack Restore

Reference historical run audited from Drive: `20260919T091225_527169Z_e5faac4f`.

The successful historical output contract lived under:
`%USERPROFILE%\ConceptGhost_Output\concept_scene\<run_id>`

and included the official Maya scene, Ghost/FullScene/CameraOnly FBX, PrimaryMesh NPZ, camera JSON, canonical PLY/USD, manifest/output index, plus diagnostics/audit/package/validation files.

Recent Refined workflows rewrote `scene_name` to `concept_scene_refined_fusion`. This moved the authoritative run pack away from the historical root while ComfyUI preview transports remained visible.

v0.41.7 restores:
- Baseline and Refined share `concept_scene` as the scene root.
- Unique run IDs isolate executions.
- Branch identity stays in manifest metadata.
- ComfyUI PLY/GLB files are explicitly preview-only.
- On Windows after Maya worker PASS, official .ma + Ghost/CameraOnly/FullScene FBX + Maya manifest are mandatory.
- Core run pack also requires camera JSON, canonical PLY/USD, PrimaryMesh NPZ, manifest and output index.
- `LATEST_RUN.txt`, `LATEST_MAYA_SCENE.txt`, `LATEST_MANIFEST.txt` point to the newest authoritative run without duplicating the heavy .ma.

All v0.41.1–v0.41.6 runtime fixes remain incorporated. New solvers: **0**.

Bundle SHA-256: `2e7c18147178ec5a39bed1e8dba9acd7beb938a6cfd3958528127b8da92ca1d1`.
