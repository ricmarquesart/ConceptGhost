# DR9R r10 — Nested Installer Compatibility Hotfix

Date: 2026-09-23

## Trigger

Target-machine execution of DR9R r9 passed the protected shared-environment fingerprint, MoGe runtime verification, Maya capability verification, and the base v1.53 runtime checks, then failed inside the inherited Gate5 installer because the modern two-stage package intentionally contains only the current numbered workflows while the legacy Gate5 installer still unconditionally required `ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1.json`.

The inherited Gate6 installer had the same latent dependency on the removed Gate6 preview workflow and would have failed next.

## r10 correction

When `CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY=1` is set by DR9R:

- Gate5 reuses `Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json` as a private verifier fixture under `%LOCALAPPDATA%\\ConceptGhost\\internal\\workflows`.
- Gate6 reuses the same current Production workflow as a private verifier fixture.
- Neither inherited installer requires nor installs a historical Gate5/Gate6 preview JSON.
- The user-facing workflow folder remains reserved for exactly `01_ConceptGhost_P10_ROUTE_SETUP.json` and `02_ConceptGhost_P10_PRODUCTION.json` after DR9R installation completes.
- Standalone historical Gate5/Gate6 behavior is not silently redefined; the compatibility behavior is scoped to the explicit internal flag.

The current Production workflow already contains the exact Gate5 and Gate6 node/link contracts used by the inherited verifiers, so no historical workflow is needed for validation.

## Regression coverage

`test_r10_nested_installer_contract.py` verifies that the current Production workflow contains the required Gate5/Gate6 nodes and links, that both inherited installers honor the internal mode, and that the bundle's public workflow payload contains exactly the current numbered 01/02 files.

This hotfix changes installer compatibility only. P9 authority, P10 geometry code, MoGe diagnostics, route authoring, WAN, COLMAP reconstruction, storage, and Maya contracts are unchanged.
