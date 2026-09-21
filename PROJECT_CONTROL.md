# ConceptGhost — PROJECT CONTROL
## Environment & Installation Contract
**Status:** MANDATORY / READ BEFORE ANY CODE CHANGE, INSTALLATION, CLEANUP OR DEPENDENCY CHANGE
**Effective date:** 2026-09-21

## 0. Purpose and authority

This is the primary safety contract for ConceptGhost.

Before changing code, creating a bundle, changing an installer, installing a dependency, updating a model/runtime, cleaning folders, or modifying the shared ComfyUI Desktop environment, this document MUST be read first.

If another README, installer, script, chat instruction, package requirement, or upstream project conflicts with this contract, STOP. Do not change the protected shared environment automatically. Update this contract only with explicit user approval after compatibility evidence.

ConceptGhost shares the user's ComfyUI Desktop machine with protected projects including:
- Pixal3D Single View — PixelArtistry_Pixal3D_RTX2080Ti_HQ_SAFE_ANNOTATED.json
- Pixal3D Single View — PixelArtistry_Pixal3D_ORIGINAL_SAFE_300K.json
- Pixal3D Multi View — 2VIEW / 3VIEW / 4VIEW SAFE workflows
- Geekatplay_Pixal3D_Turnaround_Meshwright_Integrated_v1.json
- Trellis2 / visualbruno ComfyUI-Trellis2 and its compiled stack
- ConceptGhost

Breaking another project to make ConceptGhost work is NOT an acceptable installation strategy.

## 1. Hard rules

1. NEVER upgrade, downgrade, uninstall, replace, or repair a compatible package in the shared ComfyUI Desktop Python environment as part of a ConceptGhost update.
2. NEVER change shared Python, PyTorch, torchvision, CUDA runtime/toolkit, NumPy, or compiled Trellis/Pixal3D extensions automatically.
3. NEVER use unconstrained `pip install --upgrade` against the shared ComfyUI Desktop environment.
4. NEVER use a ConceptGhost installer to “normalize” the user's shared environment to ConceptGhost preferences.
5. If a required dependency is missing/incompatible in shared Desktop, STOP or use a private ConceptGhost runtime. Do not mutate the shared stack.
6. Private runtimes may be installed/updated only inside their owned stable folders.
7. Before and after an allowed shared-host operation, fingerprint the protected environment and compare it. Unexpected differences = FAIL / rollback.
8. UNCERTAIN means KEEP. Do not delete a folder/package/runtime unless ownership is proven.
9. A ConceptGhost release must not create a new AppData state directory merely because the version changed.
10. Baseline and Refined/P9 Clone remain structurally equivalent until P10 is explicitly introduced.

## 2. Protected shared ComfyUI Desktop

Canonical root:
`%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI`

Shared models:
`%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models`

Shared input:
`%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\input`

Protected baseline used by Single View / Multi View / Trellis2:
- Python: **3.13.12**
- PyTorch: **2.12.1+cu130**
- torchvision: **0.27.1+cu130**
- NumPy: **2.5.2**
- transformers: **5.16.1**
- huggingface-hub: **1.30.0**
- tokenizers: **0.23.2**

Kornia requires special handling:
- protected historical baseline recorded on 2026-09-16: **0.8.3**
- version observed on the machine before the v1.49.1 dependency change on 2026-09-21: **0.8.2**
- Rule: ConceptGhost MUST NOT change Kornia automatically. Keep the version already installed if it is 0.8.2 or 0.8.3 until the Single/Multi View compatibility snapshot is explicitly revalidated.

Protected compiled/runtime components include, at minimum:
- cumesh
- nvdiffrast
- nvdiffrec_render
- o-voxel
- natten
- custom-rasterizer

Exact versions of those compiled components are not reconstructed in this contract. Therefore the policy is stricter: fingerprint and preserve them; automatic update/uninstall is forbidden.

## 3. Stable ConceptGhost-owned paths

Installer state, logs, manifests and current install marker:
`%LOCALAPPDATA%\ConceptGhost`

This path is stable across ConceptGhost releases. DO NOT create:
`ConceptGhost-v1.49`, `ConceptGhost-v1.49.1`, `ConceptGhost-v1.50`, etc.

Private MoGe runtime:
`%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`

This path is also stable and must be reused across releases.

Current verified private MoGe runtime:
- Python: **3.11.9**
- PyTorch: **2.14.0+cu130**
- torchvision: **0.29.0+cu130**
- CUDA runtime reported by PyTorch: **13.0**
- MoGe: **3.0.0**
- Low Resolution model: **Ruicheng/moge-3-vitl**
- High Fidelity model: **Ruicheng/moge-3-vitg**

MoGe is private. Its Python/Torch packages MUST NOT be installed into the shared ComfyUI Desktop Python.

If an isolated ConceptGhost portable ComfyUI fallback is required, keep it under:
`%LOCALAPPDATA%\ConceptGhost\ComfyUI_windows_portable`

Do not create another versioned portable root.

## 4. Shared-environment installation policy

When ComfyUI Desktop already exists:
- ConceptGhost code may refresh only its owned `custom_nodes\ConceptGhost_Stage68` folder.
- The current ConceptGhost workflow may be copied into `user\default\workflows\ConceptGhost`.
- A compatible existing Atlas Camera must be REUSED, not replaced.
- Existing compatible Python packages must be REUSED.
- Missing/incompatible dependencies must NOT trigger shared upgrades/downgrades. Use an isolated runtime/fallback or stop with a clear diagnostic.
- The ConceptGhost installer must not modify global PATH, global Python, system CUDA Toolkit, NVIDIA driver, or unrelated custom nodes.

## 5. Model/cache policy

Large model/runtime caches must be reused whenever healthy.
Do not redownload ViT-L, ViT-G, Atlas/Depth weights, or rebuild private Python environments merely because ConceptGhost version changed.

A cache/runtime may be repaired only when verification proves it is missing/corrupt/incompatible.

## 6. Folder cleanup policy

Allowed automatic cleanup after a successful installation:
- ConceptGhost-owned temporary downloads
- ConceptGhost-owned temporary backup created by the current install
- obsolete installer-state folders matching `%LOCALAPPDATA%\ConceptGhost-v*` after ownership is confirmed

Never automatically delete:
- shared ComfyUI Desktop
- ComfyUI-Shared models/input
- ConceptGhost-MoGeRuntime-v1
- Single View / Multi View / Trellis runtimes
- `C:\tmp\Geometry`
- any folder whose ownership is uncertain

## 7. Required bundle contents

Every COMPLETE ConceptGhost bundle MUST contain, at minimum:
- `PROJECT_CONTROL.md` — this contract
- `ENVIRONMENT_LOCK.json` — machine-readable version/path policy
- `README.md`
- `INSTALL_ALL.bat`
- `VERIFY_INSTALL.bat`
- `RUN_CONCEPTGHOST.bat`
- current root workflow JSON: `ConceptGhost_Master_v<current>.json`
- same current workflow under `Payload\workflows`
- current ConceptGhost custom-node payload
- required private runtime installer/worker payload
- `LOCKS.json`
- `RELEASE.json`
- `BUNDLE_MANIFEST.json`
- `SHA256SUMS.txt`

A bundle missing the workflow JSON or PROJECT_CONTROL is INVALID.

## 8. Installer gates

Before installation:
1. Load PROJECT_CONTROL and ENVIRONMENT_LOCK.
2. Detect shared ComfyUI Desktop.
3. Snapshot protected package versions and compiled/runtime fingerprints.
4. Verify that the installer will not mutate protected versions.
5. If a shared dependency would need downgrade/upgrade/replacement: BLOCK or switch to isolated mode.

During installation:
1. Update only ConceptGhost-owned files in the shared host.
2. Reuse compatible Atlas and dependencies.
3. Reuse/verify private MoGe runtime and model caches.
4. Never create per-version AppData state folders.

After installation:
1. Verify current workflow exists.
2. Verify ConceptGhost imports.
3. Verify Atlas/GeoCalib required nodes.
4. Verify MoGe ViT-L and ViT-G private runtime.
5. Verify MayaUSD and FBX.
6. Verify Baseline/Refined Scene Authority parity.
7. Verify point cloud / hero mesh metric alignment.
8. Compare protected shared-environment fingerprint to the preflight snapshot.
9. Only then write `%LOCALAPPDATA%\ConceptGhost\INSTALL_READY.json`.

Unexpected shared-environment mutation = installation FAIL.

## 9. Workflow / geometry invariants

Until P10 is implemented:
- Baseline/P9 and Refined/P9 Clone must have the same authority structure and equivalent export path.
- Manual Metric, Camera Anchor, Origin, Ground and World Up authority changes must occur before final geometry publication.
- Point cloud and PrimaryMesh must share the same post-authority canonical geometry.
- Canonical geometry is in meters.
- Maya scene is in centimeters.
- Maya geometry conversion: **1 meter = 100 Maya centimeters**.
- Maya point-cloud transport and hero mesh must use the same effective conversion factor.
- `CG_FUSED_POINTS` and `CG_HERO_MESH` must remain position/scale/orientation coherent in both Baseline and Refined.

## 10. Change-control rule

Any proposal to change a protected shared version, shared path, installer ownership boundary, or bundle required-file list requires:
1. explicit justification;
2. compatibility impact analysis for Single View, Multi View/Trellis and ConceptGhost;
3. rollback plan;
4. user approval;
5. update to this document, ENVIRONMENT_LOCK.json, Google Drive copy, GitHub copy, and the bundle copy in the same release.

No silent drift is allowed.
