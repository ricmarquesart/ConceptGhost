# ConceptGhost v0.18 — Semantic Assist — Tasks 1–3 Gate

This development gate starts from frozen ConceptGhost v0.17.2 (`5e8d714c343e99b5f63538e8321d689a1d83402f`). `main` remains the frozen v0.17.2 baseline; Semantic Assist development lives on branch `semantic-assist-v0.18`.

Implemented here: Task 1 optional controls/contract, Task 2 isolated A-only sidecar and official node code, and Task 3 SemanticBundle/cleanup/confidence/source-UV sampling. Semantic Assist remains OFF by default. No semantic consumer modifies geometry yet and the official Master graph does not wire the Semantic Assist node until Task 7.

The complete verified source archive is stored in Google Drive as `ConceptGhost_v0.18_SemanticAssist_Tasks1_3.zip`. Its immutable SHA-256 and Drive IDs are in `SNAPSHOT_REGISTRY.json`. Authoritative source provenance is in `SOURCE_INVENTORY_LOCK.json`.

Verification for this gate: 107 tests passed and compileall clean. Real Windows installation/model execution of the SAM sidecar still requires runtime validation before later promotion gates.

Do not proceed to geometry consumers without following Semantic Assist Design v1.1 and Implementation Plan v1.2. Tasks 4–9 remain outside this gate.
