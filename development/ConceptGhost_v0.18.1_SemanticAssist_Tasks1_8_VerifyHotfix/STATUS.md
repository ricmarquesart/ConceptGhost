# ConceptGhost v0.18.1 — Verify Isolation Hotfix

Date: 2026-09-17

## Root cause

The v0.18 verifier invoked `semantic_worker.py --self-test` with `python` from PATH/current runtime. That could import `semantic_runtime_core.py` outside the private sidecar and fail with `ModuleNotFoundError: cv2`.

This violated the approved Semantic Assist isolation contract: OpenCV/GroundingDINO/SAM/HQ-SAM dependencies belong only to the private sidecar runtime.

## Fix

- The main VERIFY never launches the semantic worker with system/ComfyUI Python.
- If `%LOCALAPPDATA%\ConceptGhost-SemanticAssist-v1\READY.json`, the private worker and `python311\python.exe` exist, VERIFY runs the worker self-test with that private Python.
- If the optional sidecar is not installed, VERIFY succeeds and reports Semantic Assist remains OFF.
- If a READY private sidecar exists but its private self-test fails, VERIFY fails and instructs repair via `SEMANTIC_ASSIST.bat`.
- No geometry, camera, UV, FBX, Hero Mesh, SemanticBundle, workflow, or model logic changed.

## Verification

- 125 tests passed
- compileall PASS
- semantic worker development self-test PASS
- snapshot manifest: 117 entries, 0 mismatches
- ZIP SHA256: b106f6fbc3acb352529a3a71b2691e8b4253d614b1bda141e5ddca46c5e4f275
- Drive ZIP ID: 1q5ysxTWN0O29FJljuaVHJhH2BuNA-gT3
- Drive folder ID: 19KNrNhZzx_AFigWO7FwG7eiLKo8IW6wi

Semantic Assist remains OFF by default pending Task 9.
