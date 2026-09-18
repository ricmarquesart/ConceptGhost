# ConceptGhost v0.26 — Clean workflow + MoGe-3 Phase A

This build removes the retired Semantic Assist feature from the active ConceptGhost workflow and custom-node runtime while preserving MoGe-2, MoGe-3, Single View, Multi View and shared dependencies.

## What changed

- Removed Semantic Assist nodes, ports, configuration, geometry hooks, Maya/USD metadata and Semantic-only tests/assets from the active workflow package.
- Active workflow integrity: 31 nodes / 79 links, with no dangling links after the removal.
- Preserved the v0.25 camera-facing winding and face-vertex-normal repair.
- Added an ownership-guarded cleanup for the retired private runtime.
- Fixed the Stage A1 MoGe-3 PowerShell parser failure by changing `$LASTEXITCODE:` to `${LASTEXITCODE}:` inside the interpolated error string.
- Retained the pinned MoGe 3.0.0 source bundle and isolated worker needed by the Stage A1 installer.

## Recommended install / cleanup

Run:

```text
INSTALL_V026_CLEAN.bat
```

This fresh-replaces only the active `ConceptGhost_Stage68` custom node and ConceptGhost workflow folder, then removes `%LOCALAPPDATA%\ConceptGhost-SemanticAssist-v1` only when the ConceptGhost ownership marker is present. It does not globally uninstall Torch, Transformers, OpenCV, NumPy, Hugging Face packages, or any other shared dependency.

Verify the installed active files with:

```text
VERIFY_V026_INSTALLED.bat
```

## MoGe-3 Stage A1

Install or repair the isolated MoGe-3 runtime with:

```text
INSTALL_MOGE3_RUNTIME.bat
```

Verify it later with:

```text
VERIFY_MOGE3_RUNTIME.bat
```

Target runtime:

```text
%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1
```

The MoGe-3 installer does not modify ComfyUI or the existing MoGe-2 runtime.

## Standalone retired-runtime cleanup

If only the retired private runtime needs removal, run:

```text
REMOVE_SEMANTIC_RUNTIME.bat
```

The cleanup refuses deletion when `OWNED_BY_CONCEPTGHOST_SEMANTIC_ASSIST_V1.txt` is missing.


## Distribution note

The GitHub SOURCE archive intentionally excludes the pinned 11.6 MB MoGe vendor ZIP. The tested COMPLETE package, including that vendor archive, is retained in Google Drive Evaluation_Builds. GitHub CI validates the source/runtime logic and PowerShell syntax; the COMPLETE package was validated locally with the vendor SHA-256 lock.
