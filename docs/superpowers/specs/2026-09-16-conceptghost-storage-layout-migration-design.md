# ConceptGhost — Stage 4S Storage Layout Migration Design

Date: 2026-09-16
Status: Proposed / user-approved in chat, pending written-spec review
Stage: 4S of 14

## Purpose

Separate permanent ConceptGhost project data from local runtime state.

The Google Drive project tree becomes the authoritative, durable project workspace. Local C: storage is retained only for runtime material that benefits from local disk semantics or should not be synchronized while active.

## Target roots

- Project root: `G:\My Drive\ConceptGhost`
- Runtime root: `C:\ConceptGhostRuntime`
- Existing ComfyUI installation remains untouched at its current ComfyUI Desktop paths.

## Data classes

### PROJECT — authoritative on G:

Move/copy these to the Drive project tree and treat the Drive copy as canonical:

- workflows (`.json`)
- config files (`.yml`, `.yaml`, `.json` that describe ConceptGhost)
- design/spec/docs/roadmaps
- source locks and upstream reference manifests
- reports
- logs that are useful as durable evidence
- manifests describing installs, package deltas, hashes, provenance, storage accounting
- test evidence
- ZIP packages and user-run BAT launchers
- exported cameras, point clouds, meshes, Maya handoff artifacts, and other project outputs

Recommended tree:

```text
G:\My Drive\ConceptGhost\
├── Workflows\
│   ├── Atlas\
│   ├── DA3\
│   ├── MoGe\
│   └── Project\
├── Config\
├── Docs\
│   └── Specs\
├── References\
│   └── Upstream_Code\
├── Manifests\
├── Reports\
├── Logs\
├── Tests\
│   ├── Packages\
│   ├── Compatibility\
│   ├── Local\
│   └── GitHub Actions\
├── Outputs\
│   ├── Cameras\
│   ├── Depth\
│   ├── PointClouds\
│   ├── Meshes\
│   └── Maya\
└── Storage\
```

### RUNTIME — authoritative on C:

Keep active runtime material local:

```text
C:\ConceptGhostRuntime\
├── cache\
│   ├── da3-comfy-env\
│   ├── pixi\
│   └── downloads\
├── workers\
├── temp\
└── local_state\
```

This includes:

- isolated Python/Pixi environments
- active caches
- temporary files
- lock files
- worker state
- runtime download caches
- high-churn data that should not be synchronized by Google Drive

### COMFYUI-MANAGED — remain where ComfyUI expects them

Do not migrate active installations merely for organizational symmetry:

- ComfyUI custom nodes
- active model/checkpoint directories
- host `.venv`
- Torch/CUDA packages
- ComfyUI input/output locations unless separately designed later

ConceptGhost manifests on G: record these external installation paths and ownership/delta information.

## Path contract

ConceptGhost code must stop assuming one `project_root` contains both durable files and runtime data.

Configuration must expose at least:

```yaml
paths:
  project_root: "G:\\My Drive\\ConceptGhost"
  runtime_root: "C:\\ConceptGhostRuntime"

  workflows: "G:\\My Drive\\ConceptGhost\\Workflows"
  references: "G:\\My Drive\\ConceptGhost\\References"
  reports: "G:\\My Drive\\ConceptGhost\\Reports"
  logs: "G:\\My Drive\\ConceptGhost\\Logs"
  manifests: "G:\\My Drive\\ConceptGhost\\Manifests"
  outputs: "G:\\My Drive\\ConceptGhost\\Outputs"
  packages: "G:\\My Drive\\ConceptGhost\\Tests\\Packages"

  cache: "C:\\ConceptGhostRuntime\\cache"
  workers: "C:\\ConceptGhostRuntime\\workers"
  temp: "C:\\ConceptGhostRuntime\\temp"
  local_state: "C:\\ConceptGhostRuntime\\local_state"
```

All new code must use the path contract instead of hard-coded `C:\ConceptGhost` joins.

## Migration safety model

Stage 4S is fail-closed and non-destructive by default.

### Phase A — inventory / dry-run

1. Scan `C:\ConceptGhost` and classify every tracked item as PROJECT, RUNTIME, CACHE, TEMP, or UNKNOWN.
2. Record size and SHA-256 for durable files.
3. Record external ComfyUI-managed paths without moving them.
4. Stop if an item cannot be classified safely.
5. Produce the plan under `G:\My Drive\ConceptGhost\Reports\StorageMigration\<timestamp>`.

### Phase B — copy and verify

1. Create the new G: project folders and `C:\ConceptGhostRuntime` runtime folders.
2. Copy durable files to G:; never move them on the first pass.
3. Copy/re-home runtime-owned folders to `C:\ConceptGhostRuntime` only when the owning application is closed.
4. Verify durable file SHA-256 source vs destination.
5. Verify directory inventories and expected sizes.
6. Do not delete old `C:\ConceptGhost` data.

### Phase C — path cutover

1. Update ConceptGhost config and scripts to the dual-root path contract.
2. Update storage accounting so G: project bytes and C: runtime bytes are tracked independently.
3. Workflows referenced by ConceptGhost must resolve from `G:\My Drive\ConceptGhost\Workflows`.
4. Reports/logs/manifests/packages are written directly to G:.
5. Cache/Pixi/isolated workers are written directly to `C:\ConceptGhostRuntime`.
6. Preserve compatibility with the current DA3 isolated environment during transition; no forced rebuild solely to rename a directory.

### Phase D — regression gate

Before cleanup:

- run unit tests locally
- run GitHub Actions
- confirm storage tracker paths
- open an Atlas reference workflow from G:
- open the DA3 `advanced_3d.json` from G:
- verify a protected existing Pixal3D workflow still loads
- verify no unrelated custom node/package delta

### Phase E — cleanup (separate explicit approval)

Only after all regression gates pass:

1. Generate a list of redundant files still under `C:\ConceptGhost`.
2. Verify each redundant durable file still has an identical G: copy.
3. Ask for explicit user approval before deletion.
4. Delete only verified duplicates and obsolete bootstrap state.
5. Do not delete active runtime or any path not owned by ConceptGhost.

## Workflow policy

Canonical workflows are stored on G:. The ComfyUI workflow file itself does not need to live under `C:\ConceptGhost`.

For Stage 4 DA3, canonical copies become:

```text
G:\My Drive\ConceptGhost\Workflows\DA3\advanced.json
G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json
G:\My Drive\ConceptGhost\Workflows\DA3\bas_relief.json
```

Atlas reference workflows become canonical under `Workflows\Atlas`.

Where byte-for-byte upstream copies are required, SHA-256 verification is retained and the upstream source provenance remains tied to `References\SOURCE_LOCK.json` and `References\Upstream_Code`.

## Package / BAT policy

All user-run ZIP and BAT artifacts are stored on Google Drive. The expected operational flow is:

1. package stored under `G:\My Drive\ConceptGhost\Tests\Packages`
2. user extracts on G:
3. BAT runs from the extracted package tree
4. BAT may operate on C: runtime paths when required
5. no loose BAT is presented as runnable when it depends on sibling `scripts` or package payload

Top-level BATs must use Windows CRLF line endings, and CI must contain a regression test for this.

## Error handling

Migration stops instead of guessing when:

- Google Drive is unavailable/unmounted
- source and destination hashes differ
- destination already exists with different bytes
- a path is outside the approved ownership map
- a running process would make a runtime move unsafe
- a config points to a nonexistent new root after cutover
- the storage tracker cannot distinguish project vs runtime ownership

Every stop must emit a readable report on G: and leave source data intact.

## Storage accounting

The permanent ledger must report at minimum:

- G: durable project total
- C: ConceptGhost runtime total
- ComfyUI-managed ConceptGhost-attributable additions separately
- pre-existing/shared assets separately
- per-component breakdown for Atlas / DA3 / MoGe / future stages

It must avoid double-counting nested paths and must distinguish physical bytes from directory junctions/references.

## Compatibility constraints

The migration must not:

- reinstall Torch/Torchvision/NumPy/Kornia/Transformers
- rebuild Pixal3D/Trellis environments
- modify third-party custom nodes outside ConceptGhost-owned Stage 4 work
- change the pinned upstream revisions
- alter DA3 workflow content while merely relocating it
- convert Google Drive paths into ComfyUI model/custom-node paths unless a later stage explicitly designs that change

## Acceptance criteria

Stage 4S is complete when:

1. durable project files are canonical on G:
2. active runtime/cache lives under `C:\ConceptGhostRuntime` or an explicitly grandfathered local path documented in the manifest
3. ConceptGhost scripts use dual-root configuration
4. Atlas and DA3 reference workflows open from G:
5. storage reports are generated on G:
6. GitHub Actions pass
7. existing protected ComfyUI projects show no package/custom-node regression
8. `C:\ConceptGhost` contains no required canonical workflow/config/doc after cutover
9. no old C: duplicate is deleted without a separate cleanup approval

## Non-goals

Stage 4S does not attempt to:

- move the ComfyUI installation
- move ComfyUI custom nodes to Google Drive
- move active model checkpoints to Google Drive
- fix unrelated `ComfyUI-3D-Pack` / `pyhocon` issues
- change DA3/Atlas algorithms
- optimize point-cloud quality

Those remain separate concerns.
