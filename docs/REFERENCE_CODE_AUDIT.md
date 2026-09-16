# ConceptGhost — Reference Code & Workflow Evidence Audit

Audit date: 2026-09-15/16

## Policy

ConceptGhost does not invent camera solving, depth inference, monocular geometry, point-cloud reconstruction, or mesh triangulation when a public implementation already exists. Every algorithmic stage must first run its upstream baseline unchanged on the target machine. If the stock baseline fails, stop and diagnose it; do not hide the failure behind custom code.

Evidence levels: **A** = verified on Ricardo's machine; **B** = public runnable workflow/source with demonstrated output; **C** = public source reference, target integration still unproven; **D** = ConceptGhost integration/test/config glue where no third-party inference workflow is expected.

## Stage matrix

| Stage | Evidence | Upstream baseline |
|---|---|---|
| 0 Inventory | A/D | ConceptGhost machine inventory; observational only |
| 1 Safe foundation | A/D | ConceptGhost dry-run/manifests/storage/CI |
| 2 Atlas Core | A/B | `mikejamesvfx/atlas-camera` @ `9f9ff4511154769aa2f8c0bd40387278a69b0078`; official example workflows |
| 3 Atlas + GeoCalib | A/B | Atlas learned solve + `cvg/GeoCalib`; quickstart already completed on target machine |
| 4 DA3 | B | `PozzettiAndrea/ComfyUI-DepthAnythingV3` @ `20ef6c8ccf8d57a0ad6f6fa7031739eb8489f2a4`; `advanced_3d.json`; official ByteDance DA3; `xy-gao/DA3-blender` |
| 5 MoGe | B | Official ComfyUI `3d_moge_perspective_to_mesh.json`; `microsoft/MoGe` @ `74fbce054ebed49800de42d0ad0e83495065719a` |
| 6 config.yml | D | ConceptGhost orchestration only; no new inference math |
| 7 diagnostics/points | B/D | Native DA3 point cloud + MoGe point map; common schema only is ours |
| 8 Maya Ghost Scene | B/C | Atlas Maya exporters + Autodesk MayaUSD + Pixar OpenUSD reference code |
| 9 A/B benchmark | D | Measurement methodology; no external inference workflow required |
| 10 Atlas relief mesh | B | `AtlasDeriveProjectionGeometry` + `AtlasExportReliefMesh`; documented DCC imports |
| 11 MoGe mesh | B | Official MoGe perspective-to-mesh workflow (`MoGePointMapToMesh` → `SaveGLB`) |
| 12 DA3 mesh | B | Public `bas_relief.json` / DA3 mesh workflow |
| 13 Packaging | A/D | ConceptGhost CI/manifests/storage/uninstall tests |
| 14 PCS/fSpy future | B/C | `stuffmatic/fSpy`, `fSpy-Blender`, published Maya camera-match workflow |

## Atlas

Repository: https://github.com/mikejamesvfx/atlas-camera

Pinned revision actually installed: `9f9ff4511154769aa2f8c0bd40387278a69b0078`.

This revision contains executable ComfyUI examples and code/tests for camera solving, projection geometry, `AtlasExportReliefMesh`, Maya exporters and USD export. The project documentation records run-verified showcase workflows and real DCC validation. Ricardo has already run the pinned quickstart through an actual learned camera solve, making Stages 2/3 target-machine verified.

## Depth Anything 3

Primary ComfyUI repo: https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3

Pinned audit revision: `20ef6c8ccf8d57a0ad6f6fa7031739eb8489f2a4`.

Verbatim workflows confirmed in the repository:

- `workflows/advanced.json`
- `workflows/advanced_3d.json`
- `workflows/advanced_3d_multiview.json`
- `workflows/bas_relief.json`
- `workflows/da3_streaming.json`
- `workflows/simple.json`
- `workflows/video_multiview_depth.json`

Official research repo: https://github.com/ByteDance-Seed/Depth-Anything-3 @ `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4`.

Practical reconstruction reference: https://github.com/xy-gao/DA3-blender @ `9d3d0836ead30dd79c5f9320f5b56c4b85073478`. It implements actual point-cloud reconstruction, depth-edge filtering, confidence filtering/visualization and optional textured meshes. Stage 4 must still run `advanced_3d.json` unchanged on the target machine before any wrapper is written.

## MoGe

Research repo: https://github.com/microsoft/MoGe @ `74fbce054ebed49800de42d0ad0e83495065719a`.

Official ComfyUI template: `Comfy-Org/workflow_templates/templates/3d_moge_perspective_to_mesh.json`. The graph documents the single-photo route through MoGe inference, mesh conversion, normal previews and `SaveGLB`. Stage 5 runs this official workflow unchanged before project adaptation.

## Maya / USD

Official MayaUSD: https://github.com/Autodesk/maya-usd @ `1245b4b90e56fd7ed41feca4f08dcc11bf222cd4`.

OpenUSD audit revision: `a3d77ff5e1d405b0a5080e7c9f4c6492898fb5c5`. A concrete reference is `extras/imaging/examples/hdParticleField/py3dgsPlyToUsd.py`, which contains a public PLY reader and USD point-position authoring example. ConceptGhost will reuse Atlas's camera/Maya export logic and write only the smallest point-cloud glue necessary (prefer `UsdGeomPoints`).

## fSpy / PCS future

- https://github.com/stuffmatic/fSpy @ `702189ec5acbbd2c8ba492db0e52ecb5fc908f5c`
- https://github.com/stuffmatic/fSpy-Blender @ `eec40b085d45cc623fd379998d85b88de679d4b8`

These provide an established external vanishing-point camera-matching baseline for future PCS/manual validation.

## Non-algorithm stages

Stages 0, 1, 6, 9 and 13 intentionally do not need third-party ComfyUI JSONs. They are machine discovery, safe installation, configuration, benchmarking and packaging. Their proof is automated tests + GitHub Actions + target-machine smoke tests. Stage 7 is mixed: upstream geometry math stays untouched; only the common output contract is ConceptGhost glue.

## Acquisition

`tools/DOWNLOAD_REFERENCE_CODE.bat` collects public reference source under `G:\My Drive\ConceptGhost\References\Upstream_Code`. It installs no Python packages, no model weights, no custom nodes, does not touch ComfyUI, and does not modify PATH. It pins the audited revisions and uses sparse/selected downloads for very large MayaUSD/OpenUSD sources.

## User-provided/private references

The critical V1 path does not currently depend on inaccessible/private code. If a useful tutorial provides a ZIP/JSON only through browser-authenticated Google Drive, Gumroad, Patreon, Discord, etc., place the creator-provided file in `G:\My Drive\ConceptGhost\References\User_Provided` or upload it to ChatGPT. Videos with no auditable code remain inspiration only and are never a foundation dependency.

## Acceptance rule

1. Pin upstream revision/workflow.
2. Preserve the original verbatim.
3. Run upstream baseline unchanged on Ricardo's machine.
4. Save screenshot/log/output evidence to Drive.
5. Only after PASS add a minimal adapter.
6. Compare environment/custom nodes before/after installs.
7. Stop on upstream baseline failure.
8. Never modify Pixal3D, Single View, MultiView, Trellis, or unrelated custom nodes to make ConceptGhost work.
