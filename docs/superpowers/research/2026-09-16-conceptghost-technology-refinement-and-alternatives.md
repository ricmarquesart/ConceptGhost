# ConceptGhost — Technology Refinement and Alternative Engine Research

Date: 2026-09-16
Status: Research baseline and future-study queue
Project: ConceptGhost

## Purpose

Enrich ConceptGhost with:
1. better knowledge of how current technologies are actually used;
2. parameter candidates from upstream and community workflows;
3. fallback approaches when a current path fails;
4. a future post-V1 study of promising engines without changing the current Stage 3–14 architecture.

## A. Current technology refinements

### A1. Depth Anything V3

Useful upstream/community findings:
- 3D reconstruction should use raw depth, not display-normalized depth.
- Mono/Metric variants are useful when sky masking is needed.
- Native ComfyUI point conversion references `confidence_threshold=0.1`, `use_sky_mask=true`, `downsample=1`.
- Official DA3 API defaults include `process_res=504`, confidence percentile 40%, and max 1,000,000 export points.
- Official DA3 CLI documentation shows a higher-quality example at `process_res=1024`, 30% confidence percentile, and 2,000,000 max points.
- Official DA3 supports supplied intrinsics/extrinsics for pose-conditioned depth estimation.

ConceptGhost action:
- keep current unchanged baseline;
- benchmark raw model variants;
- test Atlas-conditioned DA3 through the official API as an experimental adapter;
- do not silently replace the selected DA3 workflow.

### A2. MoGe

Useful upstream findings:
- native ComfyUI defaults `resolution_level=9`;
- `fov_x_degrees=0` means auto recovery;
- `force_projection=true`;
- `apply_mask=true`;
- mesh default discontinuity threshold is 0.04 with decimation 1;
- official MoGe explicitly supports known FOV and states that ground-truth FOV can improve accuracy;
- MoGe-2 provides metric point maps; normal-capable variants are available;
- official MoGe-3 research targets fine details/thin structures with sparse 3D refinement, but the main repo still says new code/checkpoints are coming.

ConceptGhost action:
- high-priority A/B: MoGe auto FOV vs Atlas FOV;
- benchmark resolution 9 as Max Reference candidate;
- keep MoGe-3 on future watch list.

### A3. Atlas Camera

Useful upstream findings:
- learned solve uses GeoCalib;
- VP/classical solve remains an important independent fallback;
- EXIF focal can override learned focal for real photographs, but concept art usually lacks trustworthy EXIF;
- Atlas itself reports that its depth backend default was reverted from DA3 to Depth Anything V2 Metric Outdoor after a four-scene exterior A/B where V2 was best or tied.

ConceptGhost action:
- preserve Atlas as camera authority;
- keep DA2 Metric Outdoor as a low-cost future fallback/reference candidate, not a current geometry-engine change;
- continue learned + VP validation on concept-art-specific scenes.

### A4. DA3-Blender and other practical point workflows

ConceptGhost should borrow concepts rather than make Blender mandatory:
- confidence filtering;
- depth discontinuity filtering;
- streamer cleanup;
- point-radius/display decisions;
- preserve raw/native data separately from cleaned output.

## B. Additional approaches discovered

### B1. VGGT — highest-priority future alternative

Why it is relevant:
- predicts intrinsics, extrinsics, depth, confidence, point maps, and tracks;
- officially supports a single image, even though single-view was not its dedicated training target;
- official implementation notes that unprojecting depth with predicted cameras usually gives more accurate 3D points than using the direct point-map branch.

Why this matters to ConceptGhost:
- its own preferred pattern mirrors the ConceptGhost Normalizer philosophy;
- could become an independent GeometryAdapter or comparison engine;
- can export COLMAP and integrates with broader 3D ecosystems.

Future test:
- single concept image;
- VGGT depth+camera branch;
- VGGT point-map branch;
- Atlas-constrained canonical reconstruction;
- compare against DA3/MoGe.

### B2. UniDepth V2

Why relevant:
- metric monocular depth;
- predicts intrinsics, points, rays, and confidence;
- directly exposes the types of data ConceptGhost GeometryBundle wants.

Potential role:
- future third geometry engine;
- independent metric-depth cross-check.

Caution:
- license and dependency compatibility must be reviewed before integration.

### B3. Apple Depth Pro

Why relevant:
- sharp metric monocular depth;
- strong boundary focus;
- predicts focal length in pixels from one image.

Potential role:
- specialist fallback for sharp depth boundaries;
- independent depth/focal diagnostic against Atlas + DA3/MoGe;
- possible source for edge-quality benchmark ideas.

### B4. Metric3D V2

Why relevant:
- metric depth + surface normals;
- official project warns that incorrect focal length distorts point clouds.

Why this is especially useful:
- independently reinforces ConceptGhost’s decision to separate camera authority from depth prediction;
- Atlas focal/intrinsics could potentially address the exact failure mode called out by Metric3D.

Potential role:
- future GeometryAdapter and normal-map reference.

### B5. GeoWizard

Why relevant:
- diffusion-based single-image depth + normals;
- aims at detailed geometry and broad generalization;
- has a public Kijai ComfyUI wrapper.

Potential role:
- slower alternative for difficult/stylized concepts where discriminative depth models fail;
- geometry-detail comparison source, not current V1 dependency.

### B6. MoGe-3

Why relevant:
- explicitly targets fine structures and local geometric distortion;
- introduces sparse 3D refinement rather than only 2D decoder refinement.

Potential role:
- likely first upgrade candidate to the current MoGe branch when public code/weights are stable and environment-safe.

### B7. Depth Anything V2 Metric Outdoor

Why relevant:
- Atlas maintainers reverted their depth default to V2 Metric Outdoor after their own four-scene exterior A/B.

Potential role:
- lightweight/reference fallback for environment concepts;
- future comparison baseline, not current engine replacement.

## C. Approaches not prioritized for V1

DUSt3R / MASt3R and related multi-view pipelines are powerful, but ConceptGhost V1 is intentionally single-image-first.

They become more attractive only if a future version accepts:
- multiple concept views;
- image sequences;
- generated alternate views.

Do not complicate the current single-image V1 with them.

## D. YouTube/community references

Indexed YouTube references found during this pass include:

1. “ComfyUI新节点Depth Anything V3，一键实现3D重建 + ControlNet深度控制 ，支持输出glb/ply格式模型！”
   - creator: 电磁波Studio
   - demonstrates DA3 in ComfyUI, including PLY/GLB reconstruction
   - explicitly recommends V2-style normalization for ControlNet and Raw mode for 3D reconstruction

2. “Depth Anything V3 is here for ComfyUI!”
   - creator: LIMBICNATION ART
   - demonstrates DA3 integration in ComfyUI and discusses model/detail changes

Important research policy:
- creator demos are useful for discovering practical workflows and parameter ideas;
- upstream code/docs remain the source of truth for exact parameter semantics;
- no community setting becomes a ConceptGhost default without controlled benchmark evidence.

## E. Future Stage 15 — Alternative Engine Evaluation / Technology Watch

This stage begins only after Stages 3–14 are complete.

It does NOT change the current V1 roadmap.

Objectives:
1. re-check current releases and public demos;
2. test new candidate engines in isolation;
3. compare against the frozen V1 on the same benchmark scenes;
4. integrate only through a new GeometryAdapter or CameraAdapter;
5. never destabilize the proven V1 environment.

Initial candidate queue:

```text
1. MoGe-3
2. VGGT
3. UniDepth V2
4. Depth Pro
5. Metric3D V2
6. GeoWizard
7. Depth Anything V2 Metric Outdoor baseline
8. other newly released monocular geometry systems found at that future date
```

Evaluation criteria:
- single-image suitability;
- stylized concept-art behavior;
- camera/intrinsics compatibility;
- fine structure;
- depth discontinuities;
- off-camera usefulness;
- point-cloud cleanliness;
- VRAM/RAM/runtime;
- license;
- Windows/ComfyUI compatibility;
- non-interference with protected workflows;
- value over existing DA3/MoGe V1.

## F. Source list

Official / primary sources:
- Depth Anything 3: https://github.com/ByteDance-Seed/Depth-Anything-3
- ComfyUI DA3 native nodes: https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_depth_anything_3.py
- ComfyUI-DepthAnythingV3: https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3
- Atlas Camera: https://github.com/mikejamesvfx/atlas-camera
- MoGe: https://github.com/microsoft/MoGe
- ComfyUI MoGe native nodes: https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_moge.py
- VGGT: https://github.com/facebookresearch/vggt
- UniDepth: https://github.com/lpiccinelli-eth/UniDepth
- Depth Pro: https://github.com/apple-aiml-research/ml-depth-pro
- Metric3D: https://github.com/YvanYin/Metric3D
- GeoWizard: https://github.com/fuxiao0719/GeoWizard
- Kijai ComfyUI GeoWizard: https://github.com/kijai/ComfyUI-Geowizard
