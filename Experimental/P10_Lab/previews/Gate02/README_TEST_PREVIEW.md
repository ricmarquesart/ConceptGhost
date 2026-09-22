# ConceptGhost v1.54 P10 — Gate 2 Preview r1

This preview exposes the first real P10 handoff inside ComfyUI.
It does **not** run panorama, WAN, SphereSfM or COLMAP yet.

## What you should see

Two nodes under `ConceptGhost/P10 Lab`:

1. **P10 P9 Completion Bundle Builder**
2. **P10 P9 Bundle Loader / Validator**

The Builder reads one official ConceptGhost v1.53+ run directory and creates a
versioned `ConceptGhost_P9_CompletionBundle.zip` without modifying the source
run. The Loader reopens the bundle, validates hashes/identity, and exposes the
normalized source-image, camera and authoritative PrimaryMesh paths.

## Install for this preview

1. Close ComfyUI Desktop completely.
2. Copy the included `ConceptGhost_P10_Lab` folder into the ComfyUI
   `custom_nodes` directory.
3. Start ComfyUI again.
4. Load `ConceptGhost_v1.54_P10_Gate02_PREVIEW_r1.json`.

This preview uses only the Python standard library and does not install or
change shared ComfyUI packages.

## Test A — official run

In `P10 P9 Completion Bundle Builder`:

- `run_dir`: an existing official run folder under the ConceptGhost
  `concept_scene` output tree.
- `output_zip`: a new path ending in `ConceptGhost_P9_CompletionBundle.zip`.

Queue once. Expected diagnostic status: `PASS`.

Then feed `completion_bundle` to `P10 P9 Bundle Loader / Validator` and queue.
Expected diagnostics include the source stage, `source_equivalent_to=baseline`,
the exact Scene Contract identity and `primary_mesh_format=.npz` for current
v1.53 official runs.

## Fail-closed check

Do not edit a production run. To test rejection, copy a run to a temporary
folder and alter/remove one required identity artifact. The Builder or Loader
must stop with a contract error rather than silently accepting mixed/stale data.

## Limitations

- No panorama/completion envelope yet (Gate 3).
- No virtual flights/control frames/masks yet (Gate 4).
- No WAN generation yet (Gate 5).
- No SphereSfM/COLMAP reconstruction yet (Gate 6).

## Validation evidence

Synthetic RED→GREEN tests cover official-run ingestion, Baseline/P9 labeling,
identity mismatch rejection, hash tamper rejection, Baseline-vs-P9 mesh
divergence, ZIP traversal rejection and ComfyUI node discovery.

The adapter was additionally validated against real v1.53 Baseline run
`20260921T194812_539232Z_366c63df`: source image, canonical camera and
authoritative PrimaryMesh NPZ were accepted, bundled, hash-validated and loaded
again with Scene Contract `cgsc_legacy_8f72c73ab923f5801558`.
