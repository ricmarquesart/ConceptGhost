# Stage 4S — Storage Layout Migration

Stage 4S separates durable ConceptGhost project data from local runtime state without rebuilding the working DA3 environment and without removing the legacy `C:\ConceptGhost` tree.

## Canonical roots

Durable project state is canonical under `G:\My Drive\ConceptGhost`. New runtime/cache state is canonical under `C:\ConceptGhostRuntime`. The active Stage 4 DA3 Pixi/comfy-env runtime under `C:\ConceptGhost\cache` is explicitly grandfathered until a later runtime transition proves it can move safely.

## Operator modes

`STORAGE_MIGRATION.bat` is **DRY RUN by default**. It inventories `C:\ConceptGhost`, classifies every leaf path, hashes durable PROJECT files, and blocks if any path has unknown ownership.

`STORAGE_MIGRATION.bat --copy` copies only PROJECT files to their canonical G: destinations. Each file is copied through a sibling temporary file, SHA-256 verified, and atomically placed. Existing G: files are reused only when their SHA-256 is identical. Conflicts block the operation. Source files remain on C:.

`STORAGE_MIGRATION.bat --cutover-check` is read-only. It verifies that every PROJECT source still matches its inventory hash and that the canonical G: destination exists with the same SHA-256. The release cutover gate additionally requires all seven canonical upstream workflows below and verifies their source/destination SHA-256 values explicitly:

- `G:\My Drive\ConceptGhost\Workflows\Atlas\atlas_photo_to_atlas_scene_workflow.json`
- `G:\My Drive\ConceptGhost\Workflows\Atlas\atlas_input_quickstart_workflow.json`
- `G:\My Drive\ConceptGhost\Workflows\Atlas\atlas_hero_02_photo_to_editable_scene_workflow.json`
- `G:\My Drive\ConceptGhost\Workflows\Atlas\atlas_export_fanout_workflow.json`
- `G:\My Drive\ConceptGhost\Workflows\DA3\advanced.json`
- `G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json`
- `G:\My Drive\ConceptGhost\Workflows\DA3\bas_relief.json`

The same gate verifies that `G:\My Drive\ConceptGhost\References\SOURCE_LOCK.json` exists and that `G:\My Drive\ConceptGhost\References\Upstream_Code` exists. These provenance references are read-only during Stage 4S; the cutover gate never modifies them.

Stage 4S intentionally exposes no cleanup/remove mode. Cleanup is a later, separately approved stage after cutover and regression gates pass.

## Storage accounting

`STORAGE.bat` follows the Stage 4S path contract and reports four independent ownership totals without nested double-counting:

- durable project bytes under `G:\My Drive\ConceptGhost`;
- new runtime bytes under `C:\ConceptGhostRuntime`;
- grandfathered DA3 runtime bytes that remain under the legacy `C:\ConceptGhost` tree;
- external attributable bytes recorded by install manifests for approved ComfyUI/custom-node/model additions.

The permanent ledger remains `G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt`. Junction/symlink targets are not recursively charged to a second ownership bucket.

## Persistent evidence

Every operator run writes evidence to:

- `G:\My Drive\ConceptGhost\Reports\StorageMigration\<timestamp>\`
- `G:\My Drive\ConceptGhost\Tests\Compatibility\Stage4S_<timestamp>\`
- `G:\My Drive\ConceptGhost\Logs\STORAGE_MIGRATION_<timestamp>.log`

The JSON report records mode, blockers, file mappings/hashes, canonical workflow verification, reference provenance, and explicitly records that legacy sources were preserved.

## Rollback property

Until a future cleanup stage receives explicit approval, rollback is simply to keep using the existing C: source/runtime paths. Stage 4S does not remove them.
