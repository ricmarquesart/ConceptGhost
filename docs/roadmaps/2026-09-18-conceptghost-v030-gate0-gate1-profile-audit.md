# ConceptGhost v0.30 — GATE 0 / GATE 1 Progress
## Baseline Freeze + Exact High Fidelity Profile Propagation Audit

Date: 2026-09-18
Status: GATE 0 PASS / GATE 1 PASS / implementation continuing
Baseline: v0.29.1
Target: ConceptGhost_v0.30_Canonical_MoGe3_HighFidelity

## Exact root cause found

The first authoritative profile loss occurs between `ConceptGhostMoGeEvidence.build()` and `canonicalize_moge()`.

In v0.29.1, `ConceptGhostMoGeEvidence.build()` calculated:
- `resolved_profile`
- `geometry_profile`

but did **not** store either as top-level evidence fields. It only copied `geometry_profile` under `evidence["native"]`.

Immediately downstream, `canonicalize_moge()` used:

```python
geometry_profile = str(evidence.get("geometry_profile") or "Standard")
profile_config = dict(evidence.get("profile_config") or {})
```

Because the top-level evidence fields were missing, the canonical stage silently assigned `Standard`.

That exact default then propagated through the SceneBundle and into `_write_primary_mesh_payload()`, which caused the PrimaryMesh to use:
- `geometry_profile = Standard`
- `mesher_policy = standard_transport_stride`
- transport sampling instead of the High Fidelity full-resolution path

Therefore the original failure was not ViT-G inference. ViT-G correctly ran in RAW. The bug was a profile metadata handoff failure followed by dangerous downstream Standard defaults.

## Secondary dangerous fallback sites confirmed

v0.29.1 also contained several downstream expressions equivalent to:
- `primary_evidence.get("geometry_profile") or primary.get("geometry_profile") or "Standard"`
- `scene_bundle.get("geometry_profile") or canonical.get("geometry_profile") or "Standard"`
- `scene_bundle.get("geometry_profile") or "Standard"`
- function arguments defaulting `geometry_profile="Standard"`

These did not create the first loss, but they allowed the first loss to remain silent and become authoritative.

## v0.30 corrective direction already implemented locally

The working v0.30 tree now:
1. creates an explicit `ConceptGhost.GeometryProfile.v1` object;
2. marks selected/effective profile separately;
3. forbids silent fallback;
4. requires High Fidelity to mean ViT-G / resolution 9 / SSR7 / stride 1 / depth-edge-preserving mesher;
5. stores profile_config + geometry_profile at the MoGe evidence top level;
6. makes canonicalization fail if profile metadata is missing;
7. makes PrimaryMesh consume profile_config explicitly rather than a default string;
8. adds profile-contract checks before PrimaryMesh, before Maya, and before final manifest;
9. removes DA3 from the active custom-node source and current workflow graph;
10. reduces current workflow graph from 34 nodes / 90 links to 27 nodes / 67 links.

## DA3 removal state

Removed from the active v0.30 working graph/source:
- Atlas → DA3 camera adapter
- DA3 model loader
- DA3 inference
- DA3 evidence node
- DA3/MoGe comparison selector
- DA3 preview node
- DA3_ToMesh
- RECORD E3
- Stage13 DA3 track requirement
- DA3 native Maya hierarchy group
- DA3 native output directory

The active current code/workflow now has zero `DA3`, `DepthAnythingV3`, or `da3` tokens.

Installer/runtime cleanup is still being consolidated and must not yet be called complete.

## Next gates

- GATE 2: finish DA3 installer/docs cleanup and safe removal audit tooling.
- GATE 3: finish authoritative profile contract propagation and regression tests.
- GATE 4–8: validate High Fidelity RAW → Canonical → PrimaryMesh → Maya → FBX/USD.
- GATE 9: inventory DA3 disk reclaim and protect Single View / Multi View shared dependencies.
- GATE 10–12: canonical bundle, CI, reference-scene proof and freeze.
