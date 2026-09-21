# ConceptGhost v0.42.0 — Frozen Baseline Reset

Architecture:
- Baseline v0.42 Frozen is the numerical reference.
- Refined Solver is intentionally an exact Baseline clone in v0.42 and reserved for future P10.
- Previous P9 Solver Fusion graph is retired from the active workflow.
- Retired P9 Solver Fusion nodes are not registered by v0.42.

Deliberate Baseline changes:
1. Only Primary Master remains as artist-facing mesh output; Light/Medium/Strong remesh outputs are removed.
2. FOV Authority exists in both branches:
   - AUTO = Atlas baseline camera/FOV numerical pass-through.
   - MANUAL = artist horizontal FOV authority; Atlas extrinsics/orientation preserved.
   - default manual FOV = 50.0 degrees.
3. RUN_PARAMETERS.txt / LATEST_RUN_PARAMETERS.txt and Official Run Pack are retained.
4. Legacy pre-P9 export identity compatibility is retained.
5. Baseline/Refined workflow layout: 76 nodes, 145 links, 17 groups, zero node overlap with 60px safety envelope, zero group overlap.

Retained runtime:
- ComfyUI Desktop / ConceptGhost_Stage68
- Atlas Camera + Depth Anything V2 metric model/cache
- %LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1
- Maya/mayapy

Retired P9-only private runtimes:
- %LOCALAPPDATA%\ConceptGhost-DepthProRuntime-v1
- %LOCALAPPDATA%\ConceptGhost-DepthAnythingRuntime-v1
- %LOCALAPPDATA%\ConceptGhost-SemanticAssist-v1

Bundle SHA-256:
c76d6b667b0402acc99b0a5f2af446c4573af73be9f6b9c005daafb6aaf0f68a

Workflow SHA-256:
76bfb11a86ac37f0403bf216f16084422be60e2f3a6a10fc31749d62227f834e

Validation:
- local/static/synthetic gates PASS
- 83/83 payload manifest hashes valid
- ZIP CRC PASS
- Windows + ComfyUI + Maya v0.42 runtime acceptance still pending.
