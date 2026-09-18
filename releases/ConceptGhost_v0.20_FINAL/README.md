# ConceptGhost v0.20 FINAL

Portable release based on the verified v0.19.1 FINAL parent and the Semantic Assist Design/Implementation v2.0 authorities.

Key changes:
- complete per-execution ZIP download from the final workflow node;
- saved run folder shown directly in the workflow;
- direct Maya-ready GLB/FBX download output removed, MoGe preview retained;
- default geometry engine changed to MoGe;
- Semantic Assist Flow A supports Legacy, V1, V2 Local Refine and V3 Parent-Locked;
- V1 + SAM ViT-B + Balanced remains the trusted default when Semantic Assist is manually enabled;
- all advanced semantic controls reach the sidecar IPC;
- V3 L0/L1/L2 hierarchy diagnostics retained without extra geometry authority;
- sidecar remains isolated and Semantic Assist remains OFF by default.

Full binary archive lives in Google Drive and is pinned by SHA-256 in SNAPSHOT_REGISTRY.json.

Fresh extraction verification:
- 135 snapshot files / 0 divergences
- 161 tests passed
- compileall PASS
- Semantic worker self-test PASS
- Master: 34 nodes / 97 links
