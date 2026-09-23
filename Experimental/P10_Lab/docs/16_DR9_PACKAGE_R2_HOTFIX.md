# ConceptGhost P10 DR9 — r2 package hotfix

## Cause

The DR9 r1 source tree/manifests contained the Gate 6 r10 workflow contract, but the actual packaging/upload file list omitted:

`Payload/workflows/ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r10.json`

Therefore `install_gate6.ps1` correctly failed closed at the Gate 6 workflow-install step.

## r2 fix

- physically includes the Gate 6 r10 workflow in the expanded package and ZIP;
- reapplies the exact frozen DR8 checkpoint P10 source payload;
- updates the DR9 release/workflow revision to r2;
- strengthens `Installer/test_dr9_bundle.py` so the Gate 6 workflow is mandatory;
- validates every path/hash in `P10_DR9_BUNDLE_MANIFEST.json`;
- re-extracts the final ZIP and reruns the package test plus `SHA256SUMS.txt` verification before publishing.

ZIP SHA-256: `4128056e9b6450e25e9c194f299ae2077cae550d9716eb4dc4b52c665d6c39eb`

DR9 remains **READY_FOR_USER_RUNTIME_ACCEPTANCE / PENDING** until the real ComfyUI curved/descending PATH + SPIN_360 + collision + WAN + Gate 6 test succeeds.
