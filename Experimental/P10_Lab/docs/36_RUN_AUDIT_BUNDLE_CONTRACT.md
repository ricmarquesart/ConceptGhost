# ConceptGhost P10 — RUN_AUDIT_BUNDLE Contract

Date: 2026-09-24

## Objective

Every real P10 test must leave one compact audit artifact that is sufficient for later remote diagnosis without requiring the full heavy reconstruction payload.

The terminal diagnostic artifact is:

RUN_AUDIT_BUNDLE.zip

The adjacent machine-readable summary is:

RUN_AUDIT_BUNDLE_manifest.json

## Hard requirement

reconstruction_runtime_manifest.json is mandatory. The audit bundle must fail closed if this file cannot be resolved or collected.

This manifest is the primary aggregate reconstruction audit because it links runtime status, geometry-quality status, Gate 7 promotion state, mesh health, sparse component count, mission contribution, P9 round-trip evidence, metric overlay and downstream reconstruction paths.

## Auto-growth invariant

The audit node remains the last diagnostic node in Workflow 02.

As later Gate 8 / Gate 9 / Gate 10 stages are inserted before it, the collector automatically adds safe evidence persisted under the same immutable p10_attempt_root. This means the audit ZIP becomes richer as ConceptGhost evolves without requiring a new manual audit workflow.

Safe auto-collected evidence includes:

- JSON manifests and reports;
- TXT / LOG diagnostics;
- MD / CSV / TSV summaries;
- PNG / JPG / GIF / SVG visual evidence.

Heavy geometry and DCC payloads are deliberately excluded:

- PLY;
- NPZ;
- FBX;
- MA;
- USDA;
- other unsupported/heavy binary formats.

The audit bundle records excluded files and the reason for exclusion.

## Accepted P9 authority evidence

The collector also copies selected small P9 authority diagnostics while leaving the authoritative P9 run untouched. This includes root manifests/run parameters and small evidence from acceptance, benchmark, camera, diagnostics, package, validation, Maya logs/manifests and geometry/native diagnostics.

P9 geometry/camera/scale authority is not changed by this feature.

## Integrity

The internal RUN_AUDIT_BUNDLE_index.json records:

- scene_contract_id;
- P9 run id;
- P10 attempt id;
- P9 run path;
- P10 attempt root;
- explicit reconstruction_runtime_manifest path;
- reconstruction_runtime_manifest_included=true;
- growth policy;
- size limits;
- every included archive path;
- original source path;
- byte count;
- SHA-256 for every included file;
- omitted files/reasons.

The external RUN_AUDIT_BUNDLE_manifest.json additionally records the final ZIP SHA-256 and bundle byte size.

## Current limits

Default per-file limit: 50 MiB.
Default total collected evidence limit: 250 MiB.

These limits apply only to the compact audit ZIP and do not delete or modify any original output.

## Workflow placement

Gate 7 Preview r2 Audit adds node:

ConceptGhostP10RunAuditBundle

Inputs:
- gate7_runtime_manifest_path;
- visual_pack_manifest_path;
- optional output_root.

Outputs:
- run_audit_bundle_zip;
- run_audit_bundle_manifest_path;
- diagnostics_json.

The node is OUTPUT_NODE=true and terminal: nothing from the audit branch feeds geometry, camera, scale or later authority.

## Promotion policy

This feature does not promote Gate 8. Gate 8 remains blocked until Gate 7 real runtime/visual acceptance is completed.
