# ConceptGhost v1.54 P10 — Gate 2 Preview r2

This is the first executable P10 handoff preview. It validates the real P9/Baseline boundary and shows the validation report directly in the ComfyUI node UI.

## What this preview contains

Two nodes under `ConceptGhost/P10 Lab`:

1. **P10 P9 Completion Bundle Builder**
2. **P10 P9 Bundle Loader / Validator**

The Builder reads one official ConceptGhost v1.53+ run directory and creates a versioned `ConceptGhost_P9_CompletionBundle.zip` without modifying the source run.

The Loader reopens that bundle, re-validates identity and SHA-256, and exposes the normalized source image, camera and authoritative PrimaryMesh paths.

Both nodes are output nodes in this preview so the JSON diagnostic report is published visibly in ComfyUI after execution. The report includes `status`, source stage, Scene Contract identity and other boundary information.

## Install

1. Close ComfyUI Desktop completely.
2. Extract this ZIP.
3. Copy the included `ConceptGhost_P10_Lab` folder into your ComfyUI `custom_nodes` folder.
4. Start ComfyUI.
5. Load `ConceptGhost_v1.54_P10_Gate02_PREVIEW_r2.json`.

This preview uses only the Python standard library. It installs no models and does not modify the shared ComfyUI environment.

## Test A — existing official Baseline/P9 run

In **P10 P9 Completion Bundle Builder**:

- `run_dir`: point to one completed official ConceptGhost run folder under your `concept_scene` output tree.
- `output_zip`: choose a new writable path ending in `.zip`.

Queue the workflow.

Expected Builder result:

- visible diagnostic status `PASS`;
- `source_stage = baseline` for a `Baseline / P9` run;
- exact `scene_contract_id` from the source run;
- a 64-character `bundle_sha256`.

Expected Loader result:

- visible diagnostic status `PASS`;
- `source_equivalent_to = baseline`;
- `identity_status = PASS`;
- current v1.53 official runs show `primary_mesh_format = .npz`;
- source image, camera JSON and PrimaryMesh output paths are populated.

## Fail-closed check

Do not edit a production run. If you want to test rejection, copy a run to a temporary folder and remove or alter one required identity artifact. The Builder/Loader must stop with a contract error rather than silently accepting a mixed or stale boundary.

## Scope intentionally not present yet

- Gate 3: temporary panorama + completion envelope.
- Gate 4: virtual flights + collision + raw controls + masks.
- Gate 5: WAN generation + source-preserving composite.
- Gate 6: SphereSfM/COLMAP reconstruction.

## r2 change from r1

r1 had correct machine-readable STRING outputs, but its diagnostics were mainly available through output sockets. r2 additionally publishes the same JSON through ComfyUI's node UI response so PASS/identity information is visible after execution. r1 is superseded for user testing.

## Validation evidence

Synthetic RED→GREEN tests cover official-run ingestion, Baseline/P9 labeling,
identity mismatch rejection, hash tamper rejection, Baseline-vs-P9 mesh
divergence, ZIP traversal rejection, ComfyUI node discovery and visible UI
diagnostics.

The adapter was additionally validated against real v1.53 Baseline run
`20260921T194812_539232Z_366c63df`: source image, canonical camera and
authoritative PrimaryMesh NPZ were accepted, bundled, hash-validated and loaded
again with Scene Contract `cgsc_legacy_8f72c73ab923f5801558`.
