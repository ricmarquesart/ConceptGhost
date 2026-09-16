# Stage 4S — Storage Layout Migration

Stage 4S separates durable ConceptGhost project data from local runtime state without rebuilding the working DA3 environment and without removing the legacy `C:\ConceptGhost` tree.

## Canonical roots

Durable project state is canonical under `G:\My Drive\ConceptGhost`. New runtime/cache state is canonical under `C:\ConceptGhostRuntime`. The active Stage 4 DA3 Pixi/comfy-env runtime under `C:\ConceptGhost\cache` is explicitly grandfathered until a later runtime transition proves it can move safely.

## Operator modes

`STORAGE_MIGRATION.bat` is **DRY RUN by default**. It inventories `C:\ConceptGhost`, classifies every leaf path, hashes durable PROJECT files, and blocks if any path has unknown ownership.

`STORAGE_MIGRATION.bat --copy` copies only PROJECT files to their canonical G: destinations. Each file is copied through a sibling temporary file, SHA-256 verified, and atomically placed. Existing G: files are reused only when their SHA-256 is identical. Conflicts block the operation. Source files remain on C:.

`STORAGE_MIGRATION.bat --cutover-check` is read-only. It verifies that every PROJECT source still matches its inventory hash and that the canonical G: destination exists with the same SHA-256.

Stage 4S intentionally exposes no cleanup/remove mode. Cleanup is a later, separately approved stage after cutover and regression gates pass.

## Persistent evidence

Every operator run writes evidence to:

- `G:\My Drive\ConceptGhost\Reports\StorageMigration\<timestamp>\`
- `G:\My Drive\ConceptGhost\Tests\Compatibility\Stage4S_<timestamp>\`
- `G:\My Drive\ConceptGhost\Logs\STORAGE_MIGRATION_<timestamp>.log`

The JSON report records mode, blockers, file mappings/hashes, and explicitly records that legacy sources were preserved.

## Rollback property

Until a future cleanup stage receives explicit approval, rollback is simply to keep using the existing C: source/runtime paths. Stage 4S does not remove them.
