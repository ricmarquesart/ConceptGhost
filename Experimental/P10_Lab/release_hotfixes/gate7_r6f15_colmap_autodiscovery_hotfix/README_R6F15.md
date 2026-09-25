# ConceptGhost R6F15 — COLMAP Auto-Discovery Hotfix

This hotfix fixes the target-PC Gate 7 failure where the Delaunay branch tried
to launch the bare command "colmap" even though Gate 6 had already used the
ConceptGhost private COLMAP runtime successfully.

## Scope

- Patches only the installed ConceptGhost P10 Lab Gate 7/preview Python source.
- Does not install or modify pip packages.
- Does not change the MoGe runtime.
- Does not modify P9 geometry/camera authority.
- Does not regenerate WAN or Gate 6 data.
- Backs up the replaced files under LOCALAPPDATA\ConceptGhost\HotfixBackups.

## Fast recovery

1. Run 01_APPLY_HOTFIX.bat.
2. Run 02_VERIFY_HOTFIX.bat.
3. Run 03_RESUME_LAST_GATE7.bat.

The resume helper finds the latest gate7_failure_manifest.json and calls Gate 7
directly against the existing P10 attempt. It does not queue Workflow 02, so it
does not create a new p10_attempt_id and does not rerun the expensive WAN/Gate 6
stages.

After the recovered Gate 7 reaches PASS, restart ComfyUI before future normal
Workflow 02 runs so the in-process custom-node modules load the patched source.
