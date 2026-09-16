# ConceptGhost Roadmap Addendum — Master Workflow Integration

Date: 2026-09-16
Status: Approved integration policy

This addendum clarifies how Stages 3-13 converge into one final user-facing workflow.

## Master workflow policy

- Stages 3-5 validate Atlas, DA3, and MoGe independently using upstream workflows unchanged.
- Stage 6 creates `ConceptGhost_Master.json` Alpha with one image input, camera selection, geometry selection, `Compare Both`, presets, and output switches.
- Stage 7 creates CameraBundle, GeometryBundle, CanonicalGeometry, SceneBundle, and a mandatory reprojection gate.
- Stage 8 produces the first complete V1 product: ConceptGhost Maya Ghost Scene.
- Stage 9 selects defaults through A/B evidence under a common Atlas camera authority.
- Stages 10-12 add optional Atlas/MoGe/DA3 mesh branches without changing the mandatory success path.
- Stage 13 freezes `ConceptGhost_Master.json` as the single production-facing ComfyUI workflow.

## User-facing workflow rule

Do not ship separate final workflows such as `concept_ghost_da3.json` and `concept_ghost_moge.json` as the primary UX.

The production interface is one:

`ConceptGhost_Master.json`

Development/test fixtures may remain separate for baseline debugging.

## Engine rule

Default mode runs one geometry engine:
- DA3 or
- MoGe.

`Compare Both = ON` runs both independently and preserves separate outputs. No DA3+MoGe fusion in V1.

## Camera/geometry rule

- Atlas is authoritative for camera/projection.
- DA3 or MoGe is authoritative for depth/shape evidence.
- Original image is authoritative for color.
- ConceptGhost Canonical Scene is authoritative for final Maya/USD space.

## Mandatory Stage 7 reprojection gate

Canonical geometry must reproject through the selected Atlas camera back to its source pixels within a small numerical tolerance before Maya handoff.

A significant reprojection mismatch blocks Stage 8 acceptance.

## Primary output

The primary V1 output is the ConceptGhost Maya Ghost Scene, not a raw depth map, PLY, or optional mesh.

## Run/output contract clarified

- Each Master execution creates one self-contained run bundle with source, camera, diagnostics, geometry, Maya, optional meshes, compare artifacts, logs, and a central `manifest.json`.
- Native engine geometry and ConceptGhost canonical geometry remain separate. Maya consumes canonical geometry.
- Reprojection produces both numeric metrics and a visual diagnostic, and a significant mismatch blocks a valid Stage 8 Maya Ghost.
- `Compare Both` preserves independent DA3 and MoGe branches; it never implies fusion.
- Overall run status is `PASS | PARTIAL | FAIL`.
- `PASS` requires camera + canonical geometry + reprojection pass + generated usable Maya Ghost. Intermediate PLY/GLB/camera outputs alone are never sufficient.
