# ConceptGhost P10 DR9 — r3 CURRENT_ONLY verification hotfix

## Observed failure

DR9 r2 installed the current integrated workflow and intentionally removed older P10 preview workflows under the project-wide `CURRENT_ONLY` policy. Running `04_VERIFY_INSTALL.bat` then failed in `verify_gate5.ps1` because that verifier still required the historical Gate 5 workflow path stored in `INSTALL_READY.json`.

This was a verifier-policy conflict, not a WAN, COLMAP, DR8 route-runtime or DR9 workflow failure.

## r3 correction

- `verify_gate5.ps1` detects `p10_dr9_status=PASS` and validates the Gate 5 contract against the active `p10_dr9_workflow`.
- `verify_gate6.ps1` does the same for the Gate 6 reconstruction contract.
- Gate 5 WAN model reports/assets remain mandatory.
- Gate 6 code and COLMAP reports/runtime remain mandatory.
- The project keeps `CURRENT_ONLY`; superseded Gate 5/Gate 6 preview JSON files do not need to remain installed.
- The DR9 runtime graph is unchanged from `ConceptGhost_v1.54_P10_DR9_ARTIST_ROUTE_PREVIEW_r2.json`; r3 is an installer/verifier hotfix only.
- `Installer/test_dr9_bundle.py` now regression-checks this supersession-aware verifier policy.

## Package validation

The r3 ZIP was rebuilt, extracted into a clean directory, passed the DR9 bundle regression suite, and every entry in `SHA256SUMS.txt` was revalidated. The Google Drive copy was downloaded again and its SHA-256 matched the locally validated package.

- ZIP: `ConceptGhost_v1.54_P10_DR9_ARTIST_ROUTE_RUNTIME_COMPLETE_INSTALLER_r3.zip`
- bytes: `12,189,288`
- SHA-256: `4f1adbded05fb4ff696022e38e73623f3c3d9ae52de3b8b4acc7751fe4d54d5b`
- ZIP members: `181`
- expanded Drive folder: `1vmAbzDqgkFxjRXwegSJoNoOBB4ZvtJ0d`
- Drive ZIP: `1swOq9AKx4ewEhduLuOKIIQcwwwiXqYT5`

DR9 remains **READY_FOR_USER_RUNTIME_ACCEPTANCE / PENDING** until `04_VERIFY_INSTALL.bat` passes on the target PC and the real ComfyUI curved/descending PATH + SPIN_360 + collision + WAN + Gate 6 inspection is completed.
