# ConceptGhost v0.30 — Gate 8 Validation RC2

Date: 2026-09-18
Requested stop point: Gate 8
Status: implementation complete through Gate 8; final runtime acceptance requires one fresh v0.30 Windows/Maya High Fidelity run.

## Corrected verifier behavior
The previous verifier selected the newest historical ConceptGhost run without checking schema/version. That run was pre-v0.30 and correctly reproduced the old regression:
- PrimaryMesh schema v0.29
- Maya worker input schema v0.29
- Maya manifest schema v0.28
- Standard profile
- standard transport
- stride 3

RC2 now installs the uniquely named workflow:
`ConceptGhost_Master_v0.30_CANONICAL.json`

The installer records the canonical workflow SHA256. The verifier refuses pre-v0.30 runs and only accepts v0.30 schemas with High Fidelity selected/effective profile.

## High Fidelity contract
- MoGe-3
- `Ruicheng/moge-3-vitg`
- resolution 9
- SSR7
- mixed precision
- no silent fallback
- full-resolution depth-edge-preserving mesher
- stride 1
- `depth_edge_rtol=0.04`
- no Standard vertex cap
- simplification/decimation disabled
- final topology is normal authority

## Real RAW -> PrimaryMesh proof
Before v0.30:
- RAW High Fidelity / ViT-G
- PrimaryMesh Standard
- stride 3
- 159,368 vertices
- 316,244 faces

After v0.30 offline reconstruction from the same real RAW:
- Canonical High Fidelity
- PrimaryMesh High Fidelity
- stride 1
- 1,426,735 retained vertices
- 2,823,599 faces
- 36,019 faces rejected at depth discontinuities
- 0 forbidden bridges

## Local validation
- compileall PASS
- pytest 20 PASS
- workflow 26 nodes / 66 links
- no dangling links
- no active DA3 / DepthAnythingV3 / compare_both / Semantic controls

## Delivery
Bundle SHA256:
`eb87aa2c2c1a68e4fa7f00d823eeda96ee3b7c3d544d883c03fca675345dce10`

Source SHA256:
`67640999f72345b661a205e5703a07644266036bae796039c64d46c408cb9e8a`

Per project control, work stops at Gate 8 for this delivery.
