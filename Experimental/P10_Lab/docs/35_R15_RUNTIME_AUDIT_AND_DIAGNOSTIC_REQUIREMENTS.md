# ConceptGhost P10 — r15 Runtime Audit & Diagnostic Requirements

Date: 2026-09-24

Audited user run:
`G:\My Drive\ConceptGhost\Outputs\ConceptGhost\concept_scene\20260924T045114_907472Z_b87871d8`

r15 package:
`ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r15`

## 1. What can be proven from the persisted P9 run folder

The persisted upstream P9 run is structurally healthy and audit-complete:

- authoritative run status: PASS;
- deliverable package complete: TRUE;
- identity chain: PASS;
- geometry health: PASS;
- finite ratio: 1.0;
- catastrophic geometry: FALSE;
- extreme-outlier ratio: ~0.0757;
- integration consistency: ~0.707 px median / p95;
- stage 13 structural + quality acceptance: PASS;
- stage 14 camera validation: PASS / REFERENCE_ONLY;
- Maya scene save: PASS;
- Maya reopen normal gate: PASS;
- FBX round-trip: PASS;
- official outputs contract: PASS;
- P9 Maya/FBX/PrimaryMesh outputs exist.

The Maya stderr contains an unrelated Fab plugin userSetup failure plus batch-mode warnings, but the ConceptGhost Maya worker continued and completed MA + FBX + FBX round-trip with PASS. Treat that Fab message as environmental noise unless it begins affecting the ConceptGhost worker.

Known limitation of this run:
- manual metric known-height validation is disabled;
- metric consensus is INSUFFICIENT_EVIDENCE;
- scale remains the accepted automatic P9 baseline authority and P10 must not override it.

## 2. What the Gate 6 pre-fusion screenshot proves

The persisted screenshot reports:

- P9 vertices/points: 1,362,804;
- P10 sparse points: 3,129;
- P10 dense points: 534,155;
- P10 pre-fusion mesh vertices: 47,511;
- known cameras: 160.

The overlay is rendered in P9 canonical world meters with metric-isotropic panels.

This proves:
- Gate 6 did not collapse to empty output;
- sparse triangulation produced usable points;
- dense reconstruction produced substantial geometry;
- a non-empty pre-fusion mesh exists;
- camera evidence exists;
- P10 is in approximately the same global orientation/scale envelope as P9 rather than being obviously exploded, mirrored or many orders of magnitude off-scale.

It does **not** prove that the reconstruction is good enough for final fusion.

Visible concerns in the screenshot:
- multiple disconnected/isolated P10 clusters;
- some sparse/dense evidence extends away from the main P9 shell;
- the Top XZ view is narrow and the Front/Side views show fragmentation.

At the pre-fusion stage, some fragmentation is expected because this is reconstruction evidence before protected fusion. A quality verdict requires the Gate 6 numerical diagnostic manifests.

## 3. What should exist to judge Gate 6 decisively

The single most useful file is:

`reconstruction_runtime_manifest.json`

It aggregates:
- runtime status;
- geometry quality status;
- Gate 7 promotion flag;
- mesh health;
- verified sparse component count;
- mission contribution;
- sparse quality status;
- metric overlay;
- P9-only round-trip audit;
- paths to every stage.

Also preserve:

- `dataset_manifest.json`
- `sparse_triangulation_manifest.json`
- `dense_reconstruction_manifest.json`
- `prefusion_mesh_manifest.json`
- `metric_reconstruction_overlay.json`
- `gate6_geometry_quality.json`
- relevant COLMAP stdout/stderr logs
- WAN manifest and control manifest

Important quality fields:
- overall Gate 6 quality status: PASS / WARN / FAIL;
- alerts[];
- mission_count_contributing vs expected;
- frame drop fraction;
- verified_sparse_component_count;
- dense fused point count;
- depth-map coverage;
- invalid-face count;
- degenerate-face fraction;
- pre-fusion connected-component count;
- flattened-axis warning;
- P10 dense→P9 descriptive distance stats.

## 4. Current persistence gap

The Drive P9 run folder contains strong P9 audit evidence plus user-facing P10 preview images/GIFs, but it does **not** contain the complete P10 immutable-attempt manifests required to reconstruct the Gate 5/6 numerical audit from Drive alone.

Therefore:
- P9 can be audited from the Drive folder alone;
- P10 Gate 6 can be visually assessed from the previews;
- a definitive P10 reconstruction-quality verdict still requires the P10 attempt's Gate 5/6 manifests.

This is not the same as a runtime failure. It is an audit/persistence gap.

## 5. Gate 7 Preview candidate

New package built from frozen r15:

`ConceptGhost_v1.54_P10_GATE7_PREVIEW_r1.zip`

SHA-256:
`b921c81eeb84defe4c095947c02aa96eb87fdb28035a9548348a90058c150042`

The package adds:
- Gate 7 runtime G7.1→G7.5;
- protected fusion candidate;
- per-gate visual evidence;
- confidence BLUE=HIGH / RED=LOW;
- confidence BEFORE/AFTER/DELTA;
- same-camera drone BEFORE/AFTER GIF;
- G7.6 visual evidence index and closeout manifest;
- approval switches default FALSE;
- no Gate 8 node.

Gate 7 source is closed. Runtime acceptance remains pending until the user runs this package and reviews the real evidence.

## 6. Diagnostic policy going forward

A successful node execution is not sufficient evidence by itself.

For every test run, retain:
1. the runtime aggregate manifest;
2. gate-specific quality manifest;
3. all alerts/warnings;
4. identity/provenance IDs;
5. numerical counts/coverage;
6. visual preview;
7. BEFORE/AFTER comparison;
8. relevant stdout/stderr;
9. exact package/version/hash.

The preferred future convenience output is one small audit bundle containing manifests/logs/previews only, excluding heavy PLY/NPZ/FBX/MA geometry.
