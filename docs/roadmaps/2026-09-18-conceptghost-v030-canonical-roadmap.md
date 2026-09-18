# ConceptGhost v0.30 — Canonical Roadmap
## DA3 Retirement + True End-to-End MoGe-3 High Fidelity

**Date:** 2026-09-18  
**Status:** AUTHORITATIVE ROADMAP — IN PROGRESS  
**Target:** `ConceptGhost_v0.30_Canonical_MoGe3_HighFidelity`  
**Baseline:** v0.29.1 / main currently at the DA3Evidence scope-hotfix line.

## Goals

1. Remove DA3 completely from the active ConceptGhost workflow, code, packaging, diagnostics and clean-machine installer.
2. Make `High Fidelity` authoritative end-to-end: MASTER → profile_config → MoGe-3 RAW → canonical → PrimaryMesh → Maya → FBX/USD → final manifests.
3. Fail closed on any profile/model/mesher mismatch. No silent fallback to Standard, ViT-L, SSR3 or lower resolution.
4. Produce one current COMPLETE bundle for a clean machine, with no old release/hotfix dependency.
5. Keep Single View, Multi View/Trellis and unrelated ComfyUI runtimes untouched.

## Confirmed baseline

### High Fidelity regression
A real High Fidelity run already proved:
- RAW: `geometry_profile = High Fidelity`
- RAW model: `Ruicheng/moge-3-vitg`
- resolution: 9
- ViT-G actually ran

But the final PrimaryMesh reverted to:
- `geometry_profile = Standard`
- `mesher_policy = standard_transport_stride`
- `transport_stride = 3`
- `depth_edge_rtol = null`

This is the exact regression that v0.30 must block forever.

### DA3 status
DA3 is still present in v0.29.1 in:
- MASTER `geometry_engine`
- Atlas→DA3 conditioning
- DepthAnythingV3 model/inference
- DA3→GeometryEvidence
- DA3 preview
- DA3_ToMesh
- RECORD E3
- Stage13 DA3 report requirements
- active workflow links/groups
- node registrations

DA3 is not fusing with the selected MoGe result when MoGe-only mode is intended, but legacy diagnostics/packaging can still force DA3 work.

## Target architecture

```text
SOURCE IMAGE
    ↓
ATLAS CAMERA
    ↓
MASTER CONTROLS
    ↓
AUTHORITATIVE GeometryProfile.v1
    ↓
MoGe-3
    ├─ Standard: ViT-L / res9 / SSR3
    └─ High Fidelity: ViT-G / res9 / SSR7
    ↓
MoGe evidence
    ↓
Canonical transform (NO Standard remesh)
    ↓
Profile-specific mesher
    ├─ Standard transport
    └─ HF full-resolution depth-edge-preserving
    ↓
PrimaryMesh
    ↓
Scene / Export Bundle
    ↓
Maya
    ↓
MA / FBX / USD
    ↓
Final manifest + gates
```

DA3 does not exist in the active v0.30 graph.

## Single source of truth

Only two user-facing profiles remain:
- `Standard`
- `High Fidelity`

The profile resolver creates one explicit contract. Example HF contract:

```json
{
  "schema": "ConceptGhost.GeometryProfile.v1",
  "selected_profile": "High Fidelity",
  "effective_profile": "High Fidelity",
  "engine": "MoGe",
  "moge_version": "MoGe-3",
  "model": "Ruicheng/moge-3-vitg",
  "resolution_level": 9,
  "refine_steps": 7,
  "precision_policy": "mixed",
  "silent_fallback": false,
  "mesher_policy": "moge_full_resolution_depth_edge_preserving",
  "transport_stride": 1,
  "depth_edge_rtol": 0.04,
  "simplification_policy": "disabled",
  "decimation_policy": "disabled",
  "normal_policy": "derive_from_final_topology",
  "topology_authority": "high_fidelity_final_faces"
}
```

After initial selection, downstream missing profile data is a bug. Remove dangerous fallbacks such as:
- `.get("geometry_profile", "Standard")`
- `.get("geometry_profile") or "Standard"`
- equivalent Standard defaults in canonical/export/Maya code

## Implementation gates

### G0 — Freeze baseline / fixtures
Preserve:
- v0.29.1 source
- known Standard run
- known HF RAW → Standard PrimaryMesh failing run
- v0.28 normals regression fixture

### G1 — Profile propagation audit
Trace:
- Master
- GeometryProfile
- MoGe router
- MoGe3 inference
- MoGe evidence
- projection/support
- Geometry Router
- canonicalize_moge
- canonical point cloud
- Scene Bundle
- Export Bundle
- PrimaryMesh builder
- Maya worker input
- Maya manifest
- final manifest/output index

Document exact first point where HF can become Standard.

Known suspicious v0.29.1 areas:
- downstream `or "Standard"` fallbacks in `nodes.py`
- geometry fallback in `conceptghost_geometry.py`
- PrimaryMesh/export methods with default `geometry_profile="Standard"`

### G2 — Retire DA3 from active ConceptGhost
Remove:
- DA3 control choice
- compare_both
- Atlas→DA3
- DA3 model/inference
- DA3 Evidence
- DA3_ToMesh
- RECORD E3
- Stage13 DA3 required input
- DA3 preview dependency
- DA3 registrations/groups/labels/links

Replace DA3 preview with a ConceptGhost-native generic preview or remove it.

Hard active-workflow test: zero references to:
- `DownloadAndLoadDepthAnythingV3Model`
- `DepthAnything_V3`
- `DA3_ToMesh`
- `DA3_PreviewPointCloud`
- `ConceptGhostDA3Evidence`
- `ConceptGhostAtlasToDA3CameraParams`
- `ComfyUI-DepthAnythingV3`

### G3 — Authoritative profile_config
Implement one reusable profile contract and `assert_profile_contract(...)`.

HF must assert:
- selected/effective = High Fidelity
- model = moge-3-vitg
- res = 9
- SSR = 7
- mesher = full-resolution depth-edge-preserving
- stride = 1
- edge policy active
- silent fallback = false

### G4 — High Fidelity RAW
HF:
- ViT-G
- resolution 9
- SSR7
- mixed precision
- no downgrade
- explicit CUDA OOM failure with diagnostics

RAW preserves:
- points/depth/mask/normals/intrinsics
- source pixel/UV identity
- depth-edge evidence

Depth edges affect connectivity, not destructive RAW deletion.

### G5 — Canonical without remeshing
Canonical may transform coordinates/scale/normals.
It may not:
- re-infer Standard
- reset stride to 3
- rebuild HF using Standard sampling
- close depth gaps
- remove traceability

Preserve:
- source pixel IDs
- grid_xy
- source_uv
- canonical_point_indices

### G6 — Separate High Fidelity mesher
HF required:
- `mesher_policy = moge_full_resolution_depth_edge_preserving`
- `transport_stride = 1`
- `depth_edge_rtol = 0.04`
- no Standard vertex cap
- no aggressive decimation
- no destructive smoothing

Candidate triangles validate:
- valid vertices
- depth continuity
- forbidden edge crossing
- degeneracy
- foreground/background bridging

Track candidate/accepted/rejected faces and RAW→mesh retention.

Reference dry-run scale (not exact acceptance count):
- ~1.428M canonical points
- ~1.416M retained vertices
- ~2.806M faces
- stride 1
- ~12k depth-edge vertices excluded from topology

A HF result collapsing to ~159k vertices/~314k faces is an immediate regression alarm.

### G7 — Normals/topology
Final topology is authority.
No global Reverse.

Mandatory:
- PRE_MAYA
- MAYA_LIVE
- MAYA_REOPEN
- FBX_ROUNDTRIP

Record face totals, degenerates, camera-facing/away, aligned/opposed normals, zero normals and dot statistics.

### G8 — Provenance through Maya/FBX/USD
`maya_worker_input.json`, `maya_manifest.json`, `manifest.json`, `output_index.json` must agree on:
- selected/effective profile
- model requested/loaded
- resolution / SSR
- mesher policy
- stride
- depth-edge policy

Mismatch = FAIL.

### G9 — DA3 disk/runtime safe-removal audit
Never globally uninstall Python/Torch/CUDA/NumPy/Pillow/etc.

Inventory:
- `custom_nodes/ComfyUI-DepthAnythingV3`
- DA3 isolated env(s)
- `C:\ConceptGhost\cache\da3-comfy-env` if present
- DA3/DepthAnything model caches/checkpoints
- ConceptGhost-only DA3 caches/reports

Scan other workflows first.

Classify:
- SAFE_EXCLUSIVE → removable
- SHARED_OR_REFERENCED → preserve
- UNKNOWN → preserve

Provide audit/removal scripts with ownership/reference gates.
Report exact reclaimable disk bytes from the user machine before deletion.

### G10 — Canonical bundle
Create:
`ConceptGhost_v0.30_Canonical_MoGe3_HighFidelity_COMPLETE.zip`

Contains only current:
- workflow
- ConceptGhost nodes
- Maya worker
- profile logic
- Standard/HF mesher
- isolated MoGe bootstrap
- ViT-L/ViT-G download support
- source lock
- installer
- verifiers
- manifest/README

No DA3 installer, no DA3 plugin requirement, no Semantic/SAM active runtime.

Clean machine uses only:
`INSTALL_CONCEPTGHOST.bat`

### G11 — Tests / CI
Local:
- compileall
- unit/regression tests
- exact old HF regression
- Standard regression
- HF regression
- graph validation
- duplicate node detection
- Semantic/SAM retired token scan
- DA3 retired token/dependency scan
- PowerShell parser

GitHub Actions:
- Windows PowerShell 5.1 parsing
- workflow JSON / no dangling links
- no active DA3 dependency
- no Semantic/SAM controls
- authoritative profile contract
- HF fail-closed assertions
- old HF RAW + Standard PrimaryMesh state MUST FAIL
- Standard still valid

Remote CI is PASS only when GitHub reports PASS.

### G12 — Reference scene proof
BEFORE:
- RAW HF
- PrimaryMesh Standard
- stride 3
- Standard mesher

AFTER:
- RAW HF
- PrimaryMesh HF
- stride 1
- depth-edge-preserving mesher
- Maya HF
- FBX HF

## Mandatory HF acceptance matrix

HF-01 Master HF  
HF-02 Resolver HF  
HF-03 ViT-G  
HF-04 RAW HF  
HF-05 RAW model ID ViT-G  
HF-06 Canonical HF  
HF-07 Scene Bundle HF  
HF-08 Export Bundle HF  
HF-09 PrimaryMesh HF  
HF-10 not Standard mesher  
HF-11 HF edge-preserving mesher  
HF-12 stride 1  
HF-13 edge policy active  
HF-14 forbidden bridging blocked  
HF-15 no Standard vertex cap  
HF-16 normals from final topology  
HF-17 PRE_MAYA PASS  
HF-18 MAYA_LIVE PASS  
HF-19 MAYA_REOPEN PASS  
HF-20 FBX_ROUNDTRIP PASS  
HF-21 Maya input HF  
HF-22 Maya manifest HF  
HF-23 final manifest HF  
HF-24 selected == effective  
HF-25 no silent fallback  
HF-26 Standard works  
HF-27 no dangling links  
HF-28 regression tests PASS  
HF-29 PS5.1 parser PASS  
HF-30 final ZIP + hash

## DA3 retirement acceptance

DA3-01 no DA3 user control  
DA3-02 no DA3 nodes in active workflow  
DA3-03 no DepthAnythingV3 dependency in active workflow  
DA3-04 no DA3 packaging requirement  
DA3-05 no DA3 preview dependency  
DA3-06 installer does not install DA3  
DA3-07 clean machine works without DA3  
DA3-08 cleanup never touches shared Python/Torch/CUDA  
DA3-09 Single View/Multi View scan complete  
DA3-10 exact reclaimable disk space reported

## Current status at roadmap creation

| Item | Status |
|---|---|
| v0.29.1 DA3Evidence NameError fix | DONE |
| v0.30 release | NOT STARTED |
| ViT-G RAW path | PARTIAL / WORKING |
| HF end-to-end propagation | FAILING |
| HF PrimaryMesh | FAILING: Standard fallback |
| HF stride-1 final mesh | NOT PROVEN |
| HF edge-preserving final topology | NOT PROVEN E2E |
| DA3 removed from ConceptGhost | NOT STARTED |
| DA3 removed from installer | NOT STARTED |
| safe DA3 disk cleanup | ANALYSIS ONLY |
| Single/Multi View DA3 dependency scan | INCOMPLETE |
| v0.30 CI | NOT CREATED |
| v0.30 COMPLETE bundle | NOT CREATED |
| v0.30 freeze | BLOCKED |

## Direct-main implementation sequence

1. docs: add v0.30 canonical roadmap
2. test: freeze v0.29.1 regression fixtures
3. audit: prove exact profile fallback point
4. refactor: retire DA3 from active workflow/packaging
5. refactor: introduce authoritative GeometryProfile
6. fix: propagate HF through canonical/export/PrimaryMesh
7. feat: full-resolution depth-edge-preserving HF mesher
8. gate: fail-closed profile consistency
9. gate: Maya/FBX topology/normal provenance
10. chore: safe DA3 disk audit/removal tools
11. release: consolidate v0.30 bundle
12. ci: v0.30 acceptance matrix
13. release: freeze only after local + remote PASS

## Definition of done

v0.30 is frozen only after:
- DA3 has zero active role
- clean installer does not install/require DA3
- Standard passes
- HF ViT-G RAW passes
- HF survives canonicalization
- HF PrimaryMesh uses stride 1 + edge-aware topology
- Maya/FBX/USD preserve HF profile
- old regression is blocked
- normals/winding gates pass
- DA3 cleanup is proven safe and exact disk savings reported
- local tests pass
- GitHub Actions pass
- COMPLETE ZIP is generated, hashed and saved to Drive

Until then: **IN PROGRESS — not COMPLETE**.
