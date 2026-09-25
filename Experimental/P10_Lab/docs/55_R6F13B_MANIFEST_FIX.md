# ConceptGhost Gate 7 R6F13B — Exact Payload Manifest Fix

Date: 2026-09-25

Target-PC R6F13A proved the one-root v0.36-compatible MoGe runtime itself was healthy:
Torch 2.14.0+cu130, Triton Windows 3.8.0.post28, ViT-L, ViT-G, Gate 5 and Gate 6 all passed.

The install then failed at the final DR9R verification because the cumulative P10 payload no longer matched the stale hashes retained in P10_DR9_CODE_MANIFEST.json. The R6F13A packaging step also normalized text encodings/newlines while changing release metadata, which invalidated nearly every payload hash.

R6F13B rules:
- do not rewrite P10 payload files merely to rename a release;
- regenerate P10_DR9_CODE_MANIFEST.json from the exact bytes that will ship;
- keep per-file SHA-256 verification;
- validate source_commit as current metadata rather than pinning the historical DR9R SHA;
- preserve the one-root v0.36 compatibility runtime;
- provide a resume path that installs only the corrected final P10 payload/workflows when runtime and Gate 6 are already healthy;
- keep Gate 8 blocked until the PrimaryMesh visual A/B is accepted.

The helper refresh_p10_code_manifest.py is now the source-level guardrail for future cumulative bundles.
