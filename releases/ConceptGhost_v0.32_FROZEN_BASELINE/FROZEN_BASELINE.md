# ConceptGhost v0.32 — Frozen Baseline

Status: **FROZEN PRE-IMPROVEMENT BASELINE**.

The final fresh Windows/ComfyUI/Maya acceptance is intentionally deferred until the improvement program is complete.

## Exact authorities
- Complete self-contained bundle: `ConceptGhost_v0.32_COMPLETE.zip`
- Complete ZIP SHA-256: `c89c542274d924d393dd529750ba3233aa4134a61b45dc2b17f335ec31298f3b`
- Source snapshot: `ConceptGhost_v0.32_SOURCE.zip`
- Source ZIP SHA-256: `a0e076279ca81b97d16ab02235bc70b712736a98789c1f11343cace85f4fb8b4`
- Pinned MoGe vendor SHA-256: `b9a28e6a1aa86bd23399f995feb9d496a461405fe22b53b9878c21b48d46fe6d`
- Workflow: `ConceptGhost_Master_v0.32.json` — 31 nodes / 71 links
- Local regression: **64 PASS**

## Frozen storage architecture
- per-run COMPLETE.zip disabled
- one physical canonical USDA
- source texture reused
- preview transport hard-link-first, verified copy fallback
- FullScene FBX compatibility path aliases the official FBX payload
- fused-points preview restored
- Remesh Light / Medium / Strong are optional, default OFF, and never replace PrimaryMesh

## DA3
DA3 is retired from the future ConceptGhost architecture. v0.32 includes audit-first, fail-closed cleanup tooling. No DA3 deletion is part of this frozen baseline.

## Complete bundle location
Google Drive frozen folder:
https://drive.google.com/drive/folders/1x8NO2tj5PKs5RL7Q8336rCYxCJufGSEe

That folder intentionally contains only the single complete ZIP.
