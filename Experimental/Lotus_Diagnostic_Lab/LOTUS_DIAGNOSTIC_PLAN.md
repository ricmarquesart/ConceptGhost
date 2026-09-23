# Lotus Diagnostic — Isolation and Workflow Contract

## Purpose
Run Lotus manually on the same single source image used for ConceptGhost testing, inspect how Lotus separates foreground, facades, towers, street depth and distant background, and compare the resulting diagnostics visually with the existing MoGe diagnostic lane.

## Authority
DIAGNOSTIC ONLY. No Lotus output is connected to Canonical P9, PrimaryMesh, scale, camera solve, fusion, Maya export or P10.

## Runtime isolation
All Lotus runtime state is owned by `%LOCALAPPDATA%\ConceptGhost-LotusDiagnostic`. The host ComfyUI Python environment is read-only. The bridge custom node uses only packages already present in ComfyUI to serialize the input image, launch the external Lotus worker and load generated preview PNGs.

## Models
Depth: `jingheya/lotus-depth-d-v2-0-disparity`, regression/discriminative, relative disparity.
Normal: `jingheya/lotus-normal-d-v1-1`, regression/discriminative, native aligned normals.

The models execute sequentially so they are never intentionally resident on the GPU at the same time.

## Workflow groups
1. Lotus Input
2. Lotus Depth Inference
3. Lotus Depth Diagnostics
4. Lotus 3D Preview
5. Lotus Output Bundle

Each group contains a visible Note with Purpose, Inputs, What it does, Outputs, Authority, Geometry impact, Default state, Failure/fallback, TEMP/retention and Next stage.

## Output conventions
Naming mirrors the MoGe diagnostic lane where semantics allow it. Lotus disparity is never labeled as metric depth. Inverse disparity is explicitly labeled a relative-depth proxy.

## Failure policy
A Lotus failure stops only this diagnostic node, preserves the run folder/log/partial manifest when possible, and cannot mutate or replace official ConceptGhost outputs.

## Retention
Outputs remain below the Lotus diagnostic runtime until manual cleanup or uninstall. The official P10 cleanup lifecycle does not own this directory.

## Future integration gate
There is none in this package. Any future use of Lotus as geometry evidence requires a separate explicit comparison/validation gate after visual testing.
