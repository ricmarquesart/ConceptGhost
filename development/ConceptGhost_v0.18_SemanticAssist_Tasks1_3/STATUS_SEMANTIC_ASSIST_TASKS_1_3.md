# ConceptGhost v0.18 — Semantic Assist Integration — Tasks 1–3

Date: 2026-09-17

## Frozen baseline
- v0.17.2 HeroMesh / Camera / FBX / UV
- GitHub commit `5e8d714c343e99b5f63538e8321d689a1d83402f`
- ZIP SHA256 `85afee8525bd23bb42acbb424ffbbbd626a11e8f4edc1a226671040fc9fc7f0f`
- Baseline: 94 tests passed

## Implemented in this development snapshot

### Task 1 — optional contract and controls
- `semantic_assist_enabled` default `False`
- `semantic_backend`: SAM ViT-B / HQ-SAM ViT-B
- `semantic_refine_mode`: V1 / V2 Local / Legacy
- `semantic_profile`: Balanced / Detailed / Conservative
- invalid vocabulary rejected
- MasterConfig exposes the values after existing outputs to minimize link churn

### Task 2 — isolated A-only worker
- official `ConceptGhostSemanticAssist` node exists in code but is NOT wired into Master yet (Task 7 owns workflow wiring)
- plain-Python sidecar target `%LOCALAPPDATA%\ConceptGhost-SemanticAssist-v1`
- private Python 3.11.9 bootstrap
- private pinned dependencies, models, caches
- explicit worker executable path
- JSON/NPZ file IPC
- ownership marker and fail-closed uninstall
- protected runtime fingerprints before/after install
- no second ComfyUI server
- missing/crashed/invalid worker => `DEGRADED_BYPASS`
- OFF mode does not spawn worker
- production runtime core is byte-identical to `probe_core.py` from A-only v2.2.2 (SHA in SOURCE_INVENTORY_LOCK)

### Task 3 — SemanticBundle / cleanup / confidence
- `ConceptGhost.SemanticBundle.v0.1`
- macro classes 0–7 exactly per Design v1.1
- class-aware tiny component removal
- small-hole filling
- separate instance and macro maps
- confidence penalty for fragmentation
- uncertainty and boundary-strength maps
- nearest sampling for IDs and bilinear sampling for float fields at `source_uv`
- disabled/degraded sampling returns UNKNOWN/no-op evidence

## Intentionally NOT implemented yet
Tasks 4–9. In particular, semantic information is not connected to:
- canonical XYZ modification
- metric ground registration
- sky support policy
- Hero Mesh boundary decisions
- Maya/USD/FBX semantic grouping
- official workflow branch
- packaging diagnostics
- promotion benchmark

This is deliberate. Geometry remains baseline until the first three gates are validated.

## Verification
- full suite: 107 tests passed
- compileall: clean
- Stage 11–14 + Master rebuilt with new MasterConfig controls only
- Master Semantic Assist node count: 0 by design until Task 7
