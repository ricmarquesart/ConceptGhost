# ConceptGhost

Camera-aware 3D reference reconstruction from concept art using existing, demonstrated projects rather than reimplementing core solvers from scratch.

## Current status

**Stage 4/14 — Depth Anything V3 baseline / colored point-cloud gate, with Stage 4S storage cutover in final regression.**

Stages 0–3 are technically proven on the target ComfyUI: inventory and safe framework, Atlas Camera core, protected GeoCalib/OpenCV additions, and a completed learned-camera solve. Stage 4 adds the public `PozzettiAndrea/ComfyUI-DepthAnythingV3` path. The isolated DA3 worker repair is complete; the remaining Stage 4 functional gate is the real colored point-cloud run.

Stage 4S separates durable project files from heavy local runtime state without rebuilding the working DA3 environment.

## Stage 4S storage contract

Authoritative durable project data lives under:

`G:\My Drive\ConceptGhost`

New runtime/cache/worker state lives under:

`C:\ConceptGhostRuntime`

The already-working DA3 isolated environment and Pixi cache under `C:\ConceptGhost\cache` are **grandfathered runtime** during Stage 4S. They are not moved or rebuilt merely for storage cleanup.

Durable G: data includes workflows, references, manifests, reports, logs, tests/packages, outputs and the permanent storage ledger. The canonical workflow roots are:

- `G:\My Drive\ConceptGhost\Workflows\Atlas`
- `G:\My Drive\ConceptGhost\Workflows\DA3`
- `G:\My Drive\ConceptGhost\Workflows\MoGe`
- `G:\My Drive\ConceptGhost\Workflows\Project`

Stage 4S is deliberately non-destructive. Its migration gate supports inventory, verified copy and read-only cutover verification. It exposes no delete/remove action. Any future cleanup of verified legacy duplicates requires a separate explicit approval.

## Hard non-interference rule

ConceptGhost must not overwrite or re-resolve software used by existing projects. Stage 4 therefore:

- blocks instead of changing an already-installed host package version;
- uses pip resolver **dry-run** first and permits only new additions;
- installs accepted host additions with `--no-deps`;
- reuses an existing correct DA3 checkout untouched, and blocks a conflicting target;
- fingerprints every other `custom_nodes` project before/after;
- avoids comfy-env 0.3.89's workspace-wide installer entirely;
- builds a DA3-only shadow workspace, with the active pre-4S worker grandfathered under `C:\ConceptGhost\cache`;
- strips only optional flash/sage CUDA accelerators from the **shadow build config**, leaving the upstream DA3 checkout untouched;
- downloads no DA3 checkpoint during installation;
- copies public upstream workflows byte-for-byte rather than recreating point-cloud math.

## Permanent upstream references

ConceptGhost follows a **baseline-first** development rule. The exact public revisions used as implementation evidence are pinned in:

- `references/SOURCE_LOCK.json`
- `references/README.md`
- `docs/REFERENCE_CODE_AUDIT.md`

Frozen physical copies are kept in Google Drive under `G:\My Drive\ConceptGhost\References\Upstream_Code`. The full third-party repositories are intentionally not vendored into this repository; GitHub stores the immutable source lock, audit, project-owned adapters, collector, verifier, and tests.

Before a camera/depth/geometry/mesh/DCC stage begins, verify the locked references with:

`tools\VERIFY_REFERENCE_CODE.bat`

If a required mirror is missing or is not at the locked commit, stop that stage until the reference is restored or deliberately re-audited.

## Stage 4S operator gates

`STORAGE_MIGRATION.bat` is dry-run by default. `--copy` copies only PROJECT files with SHA-256 verification while preserving C: sources. `--cutover-check` independently re-verifies every source/destination pair, the seven required Atlas/DA3 workflows, `References\SOURCE_LOCK.json`, and `References\Upstream_Code`.

`STAGE4S_FINALIZE.bat` is a final read-only evidence gate. It writes `stage4s_cutover_report.json` and an informational `stage4s_cleanup_plan.json`. The cleanup plan has no execution path and records that separate explicit approval is required before any future deletion stage.

`STORAGE.bat` records four separate ownership totals:

- G: durable project bytes;
- C: new runtime bytes;
- C: grandfathered runtime bytes;
- external attributable ComfyUI/custom-node/model additions.

Nested paths and junction targets are not double-counted.

## Stage 4 functional usage

After Stage 4S regression is closed, open the unmodified DA3 upstream workflow from:

`G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json`

Load the same test image and run the workflow. Gate 4 closes only when it produces a colored PLY point cloud that can be inspected as useful scene reference.

## Compatibility evidence

Stage 4S writes persistent evidence to:

- `G:\My Drive\ConceptGhost\Reports\StorageMigration\<timestamp>`
- `G:\My Drive\ConceptGhost\Tests\Compatibility\Stage4S_<timestamp>`
- `G:\My Drive\ConceptGhost\Logs\...`

The permanent storage ledger is:

`G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt`

## Planned backbone

- Atlas Camera: camera solve, projection geometry and DCC handoff
- Depth Anything 3: depth/camera-space colored point cloud
- MoGe: independent monocular geometry/mesh comparison
- Maya: matched-camera ghost scene for manual blockout

See `docs/STAGE4_DA3_BASELINE.md`, `docs/STAGE4S_STORAGE_MIGRATION.md`, `docs/superpowers/plans/2026-09-16-conceptghost-storage-layout-migration.md`, and `docs/REFERENCE_CODE_AUDIT.md`.
