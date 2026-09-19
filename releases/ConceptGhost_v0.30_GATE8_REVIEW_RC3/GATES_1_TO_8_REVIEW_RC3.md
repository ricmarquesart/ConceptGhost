# ConceptGhost v0.30 — Gates 1–8 Full Re-Audit RC3

**Date:** 2026-09-18  
**Trigger:** user-requested full re-review plus RC2 Windows `NameError` in `ConceptGhostMoGe3Inference`.  
**Build:** `ConceptGhost_v0.30_Gate8_Review_RC3`

## Executive result

The Gates 1–8 implementation was re-audited from code and regression evidence rather than inheriting previous PASS labels. The RC2 package had a real packaging regression: the inference node called `_conceptghost_moge3_runtime_root()` but the helper was missing from packaged `nodes.py`. RC3 restores that helper and `_as_worker_tensor()`, adds direct execution regression coverage, and hardens the MoGe worker/profile/Maya topology contracts.

**Current acceptance:** Gates 1–6 PASS; Gate 7 PRE_MAYA PASS with Maya runtime gates fail-closed and awaiting a fresh Windows/Maya run; Gate 8 implementation PASS, runtime acceptance pending that same fresh run.

## Gate 1 — baseline / exact root-cause audit — PASS
- Original High Fidelity loss remains documented: RAW was High Fidelity/ViT-G, but `geometry_profile` was not persisted at the evidence level expected by canonicalization and downstream `Standard` defaults silently took authority.
- v0.30 keeps one authoritative `ConceptGhost.GeometryProfile.v1` contract.
- RC3 additionally rejects mutated Standard or High Fidelity quality fields in unit tests.

## Gate 2 — DA3 retirement — PASS for active ConceptGhost product
- Active workflow contains no DA3, DepthAnythingV3, `compare_both`, retired Geometry Router or Semantic Assist controls.
- Current workflow: 26 nodes / 66 links, no dangling links.
- Installer does not install DA3.
- Existing unrelated DA3 plugin/runtime on the user's machine is not auto-deleted; cleanup remains a separate safety-audited operation.

## Gate 3 — authoritative profile contract — PASS
- `selected_profile` and `effective_profile` must match.
- High Fidelity contract requires MoGe-3 / ViT-G / resolution 9 / SSR7 / mixed precision / force projection / mask / stride 1 / depth-edge-preserving mesher / no silent fallback.
- Standard contract is also now validated fail-closed, preventing accidental ViT-G or other quality-field mutation from masquerading as Standard.

## Gate 4 — MoGe-3 inference — PASS in code/regression; fresh Windows execution required after RC3 install
- RC2 Windows failure was **before inference**: missing `_conceptghost_moge3_runtime_root` helper.
- RC3 restores runtime locator and worker tensor bridge.
- Regression test instantiates `ConceptGhostMoGe3Inference` and verifies it reaches the explicit private-runtime readiness error rather than `NameError`.
- Worker request is now fail-closed: no hidden model/refine/resolution/projection/mask defaults.
- Worker result identity is checked against requested model/profile/resolution/SSR/precision before geometry is accepted.

## Gate 5 — canonical profile preservation — PASS
- Canonicalization consumes explicit profile metadata; missing/contradictory authoritative profile is an error.
- No Standard remesh/default may silently replace High Fidelity state.
- Source pixel/canonical identity remains traceable.

## Gate 6 — High Fidelity PrimaryMesh — PASS on real ViT-G RAW reconstruction
Reference evidence from the real historical failing scene:
- canonical points: 1,433,610
- retained mesh vertices: 1,426,735
- accepted faces: 2,823,599
- rejected depth-edge faces: 36,019
- forbidden depth-edge bridges after independent final-triangle recheck: 0
- mesher: `moge_full_resolution_depth_edge_preserving`
- stride: 1
- `depth_edge_rtol`: 0.04
- normal gate: PASS

RC3 adds an independent post-filter recheck on accepted High Fidelity triangles; a surviving forbidden bridge now aborts the run.

## Gate 7 — topology / normals — PRE_MAYA PASS; Maya runtime observation pending
Real reconstructed High Fidelity mesh PRE_MAYA result:
- faces: 2,823,599
- degenerate faces: 0
- camera-away faces: 0
- opposed normals: 0
- zero face-vertex normals: 0

RC3 strengthens Maya gates:
- each gate records vertex count;
- MAYA_LIVE and MAYA_REOPEN must preserve PrimaryMesh vertex/face counts;
- FBX roundtrip signature compares vertex, face and edge counts plus spatial signature;
- any degenerate face is a gate failure.

MAYA_LIVE / MAYA_REOPEN / FBX_ROUNDTRIP require the user's Autodesk Maya runtime and are not falsely marked observed in this build environment.

## Gate 8 — Maya/FBX provenance and final manifest — IMPLEMENTATION PASS / RUNTIME ACCEPTANCE PENDING
- Windows High Fidelity export requires a real Maya worker manifest; absence is now an error, not a warning-only path.
- Maya worker input, Maya manifest, PrimaryMesh and final manifest must agree on profile/model/mesher/stride/depth-edge policy.
- Versioned v0.30 workflow and schema guards reject pre-v0.30 output folders.
- Final acceptance still requires one fresh RC3 Windows/Maya High Fidelity run and `VERIFY_HIGH_FIDELITY_OUTPUT.bat` PASS.

## RC3 regression suite
- Python compileall: PASS
- pytest: 26 PASS
- exact missing-runtime-helper regression: PASS
- profile mutation rejection: PASS
- worker hidden-default rejection: PASS
- topology count drift rejection: PASS
- degenerate Maya gate rejection: PASS
- workflow graph/retired-token checks: PASS

## Required fresh Windows procedure
1. Install RC3 with `INSTALL_CONCEPTGHOST.bat`.
2. Run `VERIFY_CONCEPTGHOST.bat`.
3. Run `VERIFY_HIGH_FIDELITY_VITG.bat`.
4. Run `PREPARE_GATE8_VALIDATION.bat`.
5. Fully restart ComfyUI Desktop.
6. Explicitly open `ConceptGhost_Master_v0.30_CANONICAL.json` (do not run a restored old tab).
7. Select High Fidelity and execute once to completion.
8. Run `VERIFY_HIGH_FIDELITY_OUTPUT.bat`.

Only that fresh Maya/FBX result can close the remaining Gate-7 runtime observations and Gate-8 runtime acceptance.
