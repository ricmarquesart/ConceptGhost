# ConceptGhost

Camera-aware 3D reference reconstruction from concept art using existing, demonstrated projects rather than reimplementing core solvers from scratch.

## Current status

**Stage 1/14 — Safe Project / Install Framework**

The current bootstrap is deliberately non-destructive. It inventories the machine, discovers portable/venv/Comfy Desktop installations, records pre-existing DA3/MoGe/Atlas assets, tracks disk ownership, and prepares a controlled `C:\ConceptGhost` workspace. Atlas Camera, DA3, MoGe and model weights are **not installed yet**.

## Planned backbone

- Atlas Camera: camera solve, projection geometry and DCC handoff
- Depth Anything 3: depth/camera-space point cloud path
- MoGe: independent monocular geometry/mesh path
- Maya: matched-camera ghost scene for manual blockout

## Safety rules

- Public repository contains generic code and documentation only.
- Machine inventories, local paths, logs, model weights and generated outputs are ignored.
- Existing user files/models must be detected and preserved.
- External downloads remain disabled until the inventory gate is approved.

See `docs/superpowers/plans/2026-09-15-concept-ghost-roadmap.md` for the implementation roadmap.
