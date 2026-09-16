# ConceptGhost Stage 4S Storage Layout Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `G:\My Drive\ConceptGhost` the authoritative durable project workspace while keeping only active runtime/cache state on local `C:` storage, without deleting legacy data during Stage 4S.

**Architecture:** Introduce a single dual-root path contract, then build a fail-closed migration engine that inventories `C:\ConceptGhost`, copies durable files to Google Drive with SHA-256 verification, preserves the current DA3 runtime as an explicitly grandfathered local path, and cuts all ConceptGhost writers/readers over to the new roots. Cleanup is deliberately excluded from this implementation; Stage 4S ends with a verified cleanup *plan* and requires separate user approval before any deletion.

**Tech Stack:** Python 3.12+ standard library, Windows BAT launchers, Google Drive desktop mount (`G:`), ComfyUI Desktop, `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-conceptghost-storage-layout-migration-design.md`

## Global Constraints

- Durable project root is exactly `G:\My Drive\ConceptGhost`.
- New local runtime root is exactly `C:\ConceptGhostRuntime`.
- Current ComfyUI installation paths remain unchanged.
- Canonical workflows live under `G:\My Drive\ConceptGhost\Workflows`.
- Reports, logs, manifests, test evidence, packages, and project outputs are written directly to G: after cutover.
- New caches/workers/temp state are written under `C:\ConceptGhostRuntime` after cutover.
- The existing active DA3 isolated environment under `C:\ConceptGhost\cache` is grandfathered during Stage 4S; it is not rebuilt or moved merely to rename its directory.
- Stage 4S is fail-closed: missing G:, hash mismatch, destination byte conflict, unknown ownership, or unsafe runtime movement stops the operation without deleting source data.
- Stage 4S never deletes `C:\ConceptGhost` content. Deletion is a later, separately approved operation.
- Do not reinstall or alter Torch, Torchvision, NumPy, Kornia, Transformers, CUDA, Pixal3D, Trellis, Atlas dependencies, or unrelated custom nodes.
- Do not alter pinned upstream revisions or upstream workflow bytes during relocation.
- All user-run ZIP/BAT artifacts are stored on G: and extracted/run there.
- Top-level BAT files use Windows CRLF line endings and CI enforces this.
- The existing permanent storage ledger remains on G: and must separately report G: durable bytes, C: runtime bytes, and external ComfyUI-attributable bytes without double-counting.

---

## File Structure Locked for Stage 4S

**Create**
- `scripts/cg_paths.py` — single source of truth for project/runtime path resolution and validation.
- `scripts/cg_storage_migration.py` — inventory, classification, copy verification, cutover validation, and cleanup-plan generation. No delete API.
- `STORAGE_MIGRATION.bat` — user-facing dry-run/copy/cutover launcher; always mirrors evidence to G:.
- `tests/test_paths.py` — dual-root contract tests.
- `tests/test_storage_migration.py` — classification/copy/hash/fail-closed/grandfathering tests.
- `docs/STAGE4S_STORAGE_MIGRATION.md` — operator procedure and rollback rules.

**Modify**
- `config.yml` — replace the single-root layout with explicit `paths.project_root` and `paths.runtime_root` plus durable/runtime subpaths.
- `scripts/cg_bootstrap.py` — use `cg_paths`; stop creating canonical workflows/logs/manifests under `C:\ConceptGhost`.
- `scripts/cg_storage.py` — account for G: durable root and C: runtime root independently; keep external attribution separate.
- `scripts/cg_atlas_core.py` — write/copy reference workflows and manifests via the path contract.
- `scripts/cg_atlas_camera_deps.py` — write reports/manifests via the path contract.
- `scripts/cg_da3_baseline.py` plus its `.pyinc` implementation parts — use G: for manifests/workflows/reports and `C:\ConceptGhostRuntime` for future cache creation, while honoring the grandfathered DA3 runtime recorded by the install manifest.
- `scripts/cg_verify_references.py` — resolve reference lock/mirror from G: through the path contract.
- `SETUP.bat`, `INVENTORY.bat`, `STORAGE.bat`, `ATLAS_CORE.bat`, `ATLAS_CAMERA_DEPS.bat`, `DA3_BASELINE.bat`, `TEST.bat`, `UNINSTALL.bat` — remove operational assumptions that the project root is `C:\ConceptGhost`; preserve CRLF.
- `tests/test_bootstrap.py`, `tests/test_storage.py`, `tests/test_atlas_core.py`, `tests/test_atlas_camera_deps.py`, `tests/test_da3_baseline.py`, `tests/test_reference_sources.py`, `tests/test_bat_reporting.py` — assert new path behavior and non-regression.
- `README.md` — document G:/C: ownership model and Stage 4S procedure.

**Do not modify**
- `references/SOURCE_LOCK.json` pinned revisions.
- Upstream files inside `G:\My Drive\ConceptGhost\References\Upstream_Code`.
- Active ComfyUI custom nodes or model paths as part of Stage 4S.

---

### Task 1: Add the Dual-Root Path Contract

**Files:**
- Create: `scripts/cg_paths.py`
- Create: `tests/test_paths.py`
- Modify: `config.yml`

**Interfaces:**
- Consumes: `config.yml` and optional environment overrides only for tests.
- Produces: `PathContract`, `load_path_contract(config_path: Path | None) -> PathContract`, `validate_path_contract(contract: PathContract, require_drive: bool) -> list[str]`.

- [ ] **Step 1: Write failing tests for exact defaults, configured paths, and G: availability**

```python
# tests/test_paths.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.cg_paths import PathContract, load_path_contract, validate_path_contract


class PathContractTests(unittest.TestCase):
    def test_defaults_match_approved_stage4s_roots(self):
        c = load_path_contract(None)
        self.assertEqual(c.project_root, Path(r"G:\My Drive\ConceptGhost"))
        self.assertEqual(c.runtime_root, Path(r"C:\ConceptGhostRuntime"))
        self.assertEqual(c.workflows, c.project_root / "Workflows")
        self.assertEqual(c.manifests, c.project_root / "Manifests")
        self.assertEqual(c.cache, c.runtime_root / "cache")

    def test_config_override_keeps_project_and_runtime_separate(self):
        with TemporaryDirectory() as td:
            cfg = Path(td) / "config.yml"
            cfg.write_text(
                'paths:\n  project_root: "G:\\\\My Drive\\\\ConceptGhost"\n'
                '  runtime_root: "C:\\\\ConceptGhostRuntime"\n',
                encoding="utf-8",
            )
            c = load_path_contract(cfg)
            self.assertNotEqual(c.project_root, c.runtime_root)

    def test_validation_blocks_missing_drive_when_required(self):
        c = PathContract.from_roots(Path(r"Z:\missing\ConceptGhost"), Path(r"C:\Runtime"))
        errors = validate_path_contract(c, require_drive=True)
        self.assertTrue(any("project root" in e.lower() for e in errors))
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest tests.test_paths -v`

Expected: FAIL because `scripts.cg_paths` does not exist.

- [ ] **Step 3: Implement the minimal path contract**

```python
# scripts/cg_paths.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROJECT_ROOT = Path(r"G:\My Drive\ConceptGhost")
DEFAULT_RUNTIME_ROOT = Path(r"C:\ConceptGhostRuntime")


@dataclass(frozen=True)
class PathContract:
    project_root: Path
    runtime_root: Path
    workflows: Path
    references: Path
    reports: Path
    logs: Path
    manifests: Path
    outputs: Path
    packages: Path
    storage: Path
    cache: Path
    workers: Path
    temp: Path
    local_state: Path

    @classmethod
    def from_roots(cls, project_root: Path, runtime_root: Path) -> "PathContract":
        return cls(
            project_root=project_root,
            runtime_root=runtime_root,
            workflows=project_root / "Workflows",
            references=project_root / "References",
            reports=project_root / "Reports",
            logs=project_root / "Logs",
            manifests=project_root / "Manifests",
            outputs=project_root / "Outputs",
            packages=project_root / "Tests" / "Packages",
            storage=project_root / "Storage",
            cache=runtime_root / "cache",
            workers=runtime_root / "workers",
            temp=runtime_root / "temp",
            local_state=runtime_root / "local_state",
        )
```

`load_path_contract()` must reuse the repository's existing YAML loader logic rather than add PyYAML as a new dependency. `validate_path_contract()` must reject identical/nested project/runtime roots and must report a missing/unmounted project root when `require_drive=True`.

- [ ] **Step 4: Update `config.yml` to the approved contract and run tests**

Use this exact path section:

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
  storage: "G:\\My Drive\\ConceptGhost\\Storage"
  cache: "C:\\ConceptGhostRuntime\\cache"
  workers: "C:\\ConceptGhostRuntime\\workers"
  temp: "C:\\ConceptGhostRuntime\\temp"
  local_state: "C:\\ConceptGhostRuntime\\local_state"
```

Run: `python -m unittest tests.test_paths tests.test_bootstrap -v`

Expected: PASS after updating bootstrap tests that asserted `C:\ConceptGhost` as canonical.

- [ ] **Step 5: Commit**

```bash
git add config.yml scripts/cg_paths.py tests/test_paths.py tests/test_bootstrap.py
git commit -m "feat: add ConceptGhost dual-root path contract"
```

---

### Task 2: Build the Fail-Closed Legacy Inventory and Classification Engine

**Files:**
- Create: `scripts/cg_storage_migration.py`
- Create: `tests/test_storage_migration.py`

**Interfaces:**
- Consumes: `PathContract`, legacy root `C:\ConceptGhost`.
- Produces: `classify_legacy_path(rel: Path) -> MigrationClass`, `build_migration_inventory(legacy_root: Path, contract: PathContract) -> dict`.

Migration classes are exact strings: `PROJECT`, `RUNTIME_GRANDFATHERED`, `TEMP`, `BOOTSTRAP_STATE`, `UNKNOWN`.

- [ ] **Step 1: Write failing classification tests**

```python
class MigrationClassificationTests(unittest.TestCase):
    def test_known_durable_paths_are_project(self):
        self.assertEqual(classify_legacy_path(Path("workflows/reference/da3/advanced_3d.json")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("manifests/da3_baseline_install.json")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("docs/STAGE4_DA3_BASELINE.md")), "PROJECT")
        self.assertEqual(classify_legacy_path(Path("config.yml")), "PROJECT")

    def test_active_da3_cache_is_grandfathered(self):
        self.assertEqual(classify_legacy_path(Path("cache/da3-comfy-env/.pixi/pixi.lock")), "RUNTIME_GRANDFATHERED")
        self.assertEqual(classify_legacy_path(Path("cache/pixi/archive.bin")), "RUNTIME_GRANDFATHERED")

    def test_unrecognized_path_blocks_inventory(self):
        self.assertEqual(classify_legacy_path(Path("mystery/data.bin")), "UNKNOWN")
```

- [ ] **Step 2: Run and confirm failure**

Run: `python -m unittest tests.test_storage_migration.MigrationClassificationTests -v`

Expected: FAIL because migration functions do not exist.

- [ ] **Step 3: Implement deterministic classification and SHA inventory**

Durable mapping rules:

```python
PROJECT_PREFIXES = {"workflows", "manifests", "logs", "docs", "output", "maya"}
GRANDFATHERED_RUNTIME_PREFIXES = {"cache/da3-comfy-env", "cache/pixi"}
BOOTSTRAP_PREFIXES = {"scripts"}
TEMP_PREFIXES = {"temp", "cache/downloads"}
PROJECT_ROOT_FILES = {"config.yml"}
```

For every `PROJECT` file record `relative_path`, `source`, `destination`, `size_bytes`, and SHA-256. `UNKNOWN` must be accumulated in `blockers`; the function may complete its scan but the returned status is `blocked` whenever blockers are non-empty. Junctions/symlinks must be recorded as links and never recursively followed.

- [ ] **Step 4: Add destination mapping tests and run the migration test module**

Required mappings:

```text
workflows/reference/atlas/* -> G:\My Drive\ConceptGhost\Workflows\Atlas\*
workflows/reference/da3/*   -> G:\My Drive\ConceptGhost\Workflows\DA3\*
workflows/reference/moge/*  -> G:\My Drive\ConceptGhost\Workflows\MoGe\*
workflows/project/*         -> G:\My Drive\ConceptGhost\Workflows\Project\*
config.yml                  -> G:\My Drive\ConceptGhost\Config\config.yml
manifests/*                 -> G:\My Drive\ConceptGhost\Manifests\*
logs/*                      -> G:\My Drive\ConceptGhost\Logs\Legacy_C_ConceptGhost\*
docs/*                      -> G:\My Drive\ConceptGhost\Documentation\Legacy_C_ConceptGhost\*
output/*                    -> G:\My Drive\ConceptGhost\Outputs\Legacy_C_ConceptGhost\*
maya/*                      -> G:\My Drive\ConceptGhost\Outputs\Maya\Legacy_C_ConceptGhost\*
```

Run: `python -m unittest tests.test_storage_migration -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/cg_storage_migration.py tests/test_storage_migration.py
git commit -m "feat: inventory legacy ConceptGhost storage safely"
```

---

### Task 3: Implement Copy-and-Verify Without Deletion

**Files:**
- Modify: `scripts/cg_storage_migration.py`
- Modify: `tests/test_storage_migration.py`

**Interfaces:**
- Consumes: inventory from Task 2.
- Produces: `copy_project_items(inventory: dict) -> dict`, `verify_project_copies(result: dict) -> dict`.

- [ ] **Step 1: Write failing tests for identical destination, conflicts, and hash verification**

```python
class CopyVerificationTests(unittest.TestCase):
    def test_existing_identical_destination_is_reused(self):
        result = copy_one_verified(src, dst)
        self.assertEqual(result["action"], "reuse-identical")
        self.assertTrue(src.exists())

    def test_existing_different_destination_blocks(self):
        dst.write_bytes(b"different")
        with self.assertRaises(MigrationBlocked):
            copy_one_verified(src, dst)
        self.assertTrue(src.exists())

    def test_copy_never_deletes_source(self):
        copy_one_verified(src, dst)
        self.assertTrue(src.exists())
        self.assertEqual(sha256_file(src), sha256_file(dst))
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python -m unittest tests.test_storage_migration.CopyVerificationTests -v`

Expected: FAIL because copy helpers do not exist.

- [ ] **Step 3: Implement atomic copy semantics**

Use a sibling temporary file on the destination volume, verify source hash against temp hash, then `os.replace(temp, destination)`. If destination exists: reuse only if SHA-256 matches; otherwise block. Never call `unlink`, `rmtree`, `move`, or `replace` on the source path in Stage 4S.

```python
def copy_one_verified(src: Path, dst: Path) -> dict:
    source_hash = sha256_file(src)
    if dst.exists():
        dest_hash = sha256_file(dst)
        if dest_hash != source_hash:
            raise MigrationBlocked(f"destination conflict: {dst}")
        return {"action": "reuse-identical", "sha256": source_hash}
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".conceptghost-copying")
    shutil.copy2(src, tmp)
    if sha256_file(tmp) != source_hash:
        tmp.unlink(missing_ok=True)
        raise MigrationBlocked(f"copy hash mismatch: {src} -> {dst}")
    os.replace(tmp, dst)
    return {"action": "copied", "sha256": source_hash}
```

- [ ] **Step 4: Add whole-inventory verification and source-preservation assertions**

The final copy report must include `copied`, `reused_identical`, `blocked`, `source_files_remaining`, and `all_verified`. Run:

`python -m unittest tests.test_storage_migration -v`

Expected: PASS with explicit tests that every source file remains after a successful copy.

- [ ] **Step 5: Commit**

```bash
git add scripts/cg_storage_migration.py tests/test_storage_migration.py
git commit -m "feat: add hash-verified non-destructive storage copy"
```

---

### Task 4: Add Stage 4S Operator BAT and Persistent Evidence

**Files:**
- Create: `STORAGE_MIGRATION.bat`
- Create: `docs/STAGE4S_STORAGE_MIGRATION.md`
- Modify: `tests/test_bat_reporting.py`
- Modify: `scripts/cg_bootstrap.py`

**Interfaces:**
- Consumes: `cg_storage_migration.py` CLI.
- Produces: dry-run by default; `--copy` performs Task 3 only; `--cutover-check` validates readiness but does not delete.

- [ ] **Step 1: Add failing BAT-policy tests**

```python
def test_storage_migration_bat_is_dry_run_by_default(self):
    data = (self.root / "STORAGE_MIGRATION.bat").read_bytes()
    text = data.decode("utf-8").lower()
    self.assertIn("cg_storage_migration.py", text)
    self.assertIn("reports\\storagemigration", text)
    self.assertIn("--copy", text)
    self.assertIn("--cutover-check", text)
    self.assertNotIn("--delete", text)
    self.assertIn(b"\r\n", data)
    self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
```

- [ ] **Step 2: Run and confirm failure**

Run: `python -m unittest tests.test_bat_reporting -v`

Expected: FAIL because `STORAGE_MIGRATION.bat` does not exist.

- [ ] **Step 3: Implement BAT behavior and Drive report layout**

The BAT must write/copy evidence to:

```text
G:\My Drive\ConceptGhost\Reports\StorageMigration\<timestamp>\
G:\My Drive\ConceptGhost\Tests\Compatibility\Stage4S_<timestamp>\
G:\My Drive\ConceptGhost\Logs\STORAGE_MIGRATION_<timestamp>.log
```

It must print `DRY RUN` unless `--copy` or `--cutover-check` is present, keep the window open with `pause >nul`, and never contain a delete command.

- [ ] **Step 4: Add the Stage 4S BAT/doc to bootstrap payload metadata and run BAT tests**

Update `PAYLOAD_FILES` to include:

```python
"STORAGE_MIGRATION.bat",
"scripts/cg_paths.py",
"scripts/cg_storage_migration.py",
"docs/STAGE4S_STORAGE_MIGRATION.md",
```

Run: `python -m unittest tests.test_bat_reporting tests.test_bootstrap -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add STORAGE_MIGRATION.bat docs/STAGE4S_STORAGE_MIGRATION.md scripts/cg_bootstrap.py tests/test_bat_reporting.py tests/test_bootstrap.py
git commit -m "feat: add Stage 4S storage migration launcher"
```

---

### Task 5: Cut Project Writers/Readers Over to the Path Contract

**Files:**
- Modify: `scripts/cg_bootstrap.py`
- Modify: `scripts/cg_atlas_core.py`
- Modify: `scripts/cg_atlas_camera_deps.py`
- Modify: `scripts/cg_da3_baseline.py`
- Modify: `scripts/cg_da3_baseline_part1.pyinc`
- Modify: `scripts/cg_da3_baseline_part2.pyinc`
- Modify: `scripts/cg_da3_baseline_part3.pyinc`
- Modify: `scripts/cg_da3_baseline_part4.pyinc`
- Modify: `scripts/cg_verify_references.py`
- Modify: corresponding existing tests.

**Interfaces:**
- Consumes: `load_path_contract()`.
- Produces: all durable writes on G:, all *new* runtime/cache writes under `C:\ConceptGhostRuntime`, plus manifest-driven grandfathering for the active DA3 worker.

- [ ] **Step 1: Add failing tests that reject new canonical writes under `C:\ConceptGhost`**

Add assertions such as:

```python
self.assertEqual(plan["reference_workflow_root"], r"G:\My Drive\ConceptGhost\Workflows\DA3")
self.assertEqual(plan["manifest_root"], r"G:\My Drive\ConceptGhost\Manifests")
self.assertTrue(plan["runtime_cache_root"].startswith(r"C:\ConceptGhostRuntime"))
self.assertNotIn(r"C:\ConceptGhost\workflows", json.dumps(plan))
```

For an existing `da3_baseline_install.json` whose `project_isolated_env` points to `C:\ConceptGhost\cache\da3-comfy-env\...`, assert the resolver returns that exact existing path as `grandfathered_runtime` rather than rebuilding it.

- [ ] **Step 2: Run the affected tests and confirm expected failures**

Run:

```bash
python -m unittest \
  tests.test_bootstrap \
  tests.test_atlas_core \
  tests.test_atlas_camera_deps \
  tests.test_da3_baseline \
  tests.test_reference_sources -v
```

Expected: FAIL on old C: path assumptions.

- [ ] **Step 3: Replace hard-coded durable roots with `PathContract`**

Rules to implement exactly:

```python
contract.manifests   # all new durable manifests
contract.logs        # all new durable logs
contract.workflows   # Atlas/DA3/MoGe reference workflow destinations
contract.references  # SOURCE_LOCK and Upstream_Code
contract.outputs     # cameras/depth/pointcloud/mesh/Maya handoff
contract.cache       # future new caches only
contract.workers     # future workers only
contract.temp        # future temp state only
```

When Stage 4 code needs the already-created DA3 worker, load `project_isolated_env` / `project_comfy_env_workspace` from the migrated install manifest first. If that path exists, mark it `grandfathered_runtime=true` and reuse it. Only a *new* DA3 environment uses `contract.cache`.

- [ ] **Step 4: Run all affected tests plus compile**

Run:

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Expected: all tests pass; no test expects canonical workflow/report/manifest paths under `C:\ConceptGhost`.

- [ ] **Step 5: Commit**

```bash
git add scripts tests
git commit -m "refactor: cut ConceptGhost durable IO over to Google Drive"
```

---

### Task 6: Convert Storage Accounting to Durable-vs-Runtime Ownership

**Files:**
- Modify: `scripts/cg_storage.py`
- Modify: `tests/test_storage.py`
- Modify: `STORAGE.bat`

**Interfaces:**
- Consumes: `PathContract`, migrated G: manifests, external ComfyUI install manifests.
- Produces: durable G: total, local runtime C: total, external attributable total, combined total, component breakdown with no nested double-counting.

- [ ] **Step 1: Write failing storage-contract tests**

```python
def test_dual_root_totals_are_separate(self):
    snap = build_storage_snapshot(contract=contract, reason="test", comfyui_root=None)
    self.assertEqual(snap["durable_project_root"], str(contract.project_root))
    self.assertEqual(snap["runtime_root"], str(contract.runtime_root))
    self.assertIn("durable_g_bytes", snap)
    self.assertIn("runtime_c_bytes", snap)
    self.assertIn("external_attributable_bytes", snap)


def test_grandfathered_da3_runtime_is_reported_not_double_counted(self):
    self.assertEqual(snap["components"]["da3_grandfathered_runtime"]["classification"], "grandfathered-runtime")
```

- [ ] **Step 2: Run and confirm failure**

Run: `python -m unittest tests.test_storage -v`

Expected: FAIL because current tracker still treats `C:\ConceptGhost` as the main project-owned root.

- [ ] **Step 3: Implement the new accounting model**

Top-level totals must be:

```python
{
    "durable_g_bytes": path_size(contract.project_root),
    "runtime_c_bytes": path_size(contract.runtime_root),
    "grandfathered_runtime_c_bytes": grandfathered_owned_bytes,
    "external_attributable_bytes": external_added_bytes,
    "combined_tracked_bytes": durable + runtime + grandfathered + external,
}
```

Never add a nested component twice. A junction contributes reference metadata only, not target bytes. Existing shared ComfyUI model folders remain visible but are not charged wholesale.

- [ ] **Step 4: Update `STORAGE.bat` to use config/path contract and run tests**

Run:

```bash
python -m unittest tests.test_storage tests.test_bat_reporting -v
```

Expected: PASS and `ConceptGhost_Disk_Usage.txt` target remains `G:\My Drive\ConceptGhost\Storage`.

- [ ] **Step 5: Commit**

```bash
git add scripts/cg_storage.py STORAGE.bat tests/test_storage.py tests/test_bat_reporting.py
git commit -m "refactor: separate durable and runtime storage accounting"
```

---

### Task 7: Canonicalize Atlas/DA3 Workflows on G: and Verify Bytes

**Files:**
- Modify: `scripts/cg_storage_migration.py`
- Modify: `tests/test_storage_migration.py`
- Modify: `docs/STAGE4S_STORAGE_MIGRATION.md`

**Interfaces:**
- Consumes: legacy workflow files plus `references/SOURCE_LOCK.json` provenance.
- Produces: verified canonical copies in `Workflows\Atlas`, `Workflows\DA3`, `Workflows\MoGe`, and `Workflows\Project`.

- [ ] **Step 1: Write failing workflow-canonicalization tests**

```python
def test_da3_upstream_workflow_destination_is_canonical(self):
    dst = destination_for(Path("workflows/reference/da3/advanced_3d.json"), contract)
    self.assertEqual(dst, contract.workflows / "DA3" / "advanced_3d.json")


def test_relocation_preserves_workflow_bytes(self):
    copy_one_verified(src, dst)
    self.assertEqual(src.read_bytes(), dst.read_bytes())
```

- [ ] **Step 2: Run and verify failure before implementation changes**

Run: `python -m unittest tests.test_storage_migration -v`

Expected: FAIL until all four workflow destination families are implemented.

- [ ] **Step 3: Implement canonical workflow verification**

The Stage 4S report must explicitly list SHA-256 for each canonical Atlas and DA3 workflow. At minimum DA3 must include:

```text
G:\My Drive\ConceptGhost\Workflows\DA3\advanced.json
G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json
G:\My Drive\ConceptGhost\Workflows\DA3\bas_relief.json
```

No JSON normalization or rewrite is allowed; copy bytes only.

- [ ] **Step 4: Add cutover-readiness checks**

`--cutover-check` passes only if every required canonical workflow exists and its SHA matches the migrated source. It must also verify `References\SOURCE_LOCK.json` and `References\Upstream_Code` exist on G: without modifying either.

Run: `python -m unittest tests.test_storage_migration tests.test_reference_sources -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/cg_storage_migration.py tests/test_storage_migration.py docs/STAGE4S_STORAGE_MIGRATION.md
git commit -m "feat: canonicalize verified workflows on Google Drive"
```

---

### Task 8: Add Regression Gate, Cleanup Plan, Packaging, and CI

**Files:**
- Modify: `scripts/cg_storage_migration.py`
- Modify: `tests/test_storage_migration.py`
- Modify: `.github/workflows/tests.yml` only if needed for new explicit Stage 4S guards.
- Modify: `README.md`
- Create package: `ConceptGhost_Stage04S_v0.4.5.zip`

**Interfaces:**
- Consumes: successful Tasks 1–7.
- Produces: `stage4s_cutover_report.json`, `stage4s_cleanup_plan.json`, validated ZIP/BAT package, GitHub Actions evidence.

- [ ] **Step 1: Write failing cleanup-plan tests proving there is no deletion path**

```python
def test_cleanup_plan_lists_only_verified_redundant_files(self):
    plan = build_cleanup_plan(copy_report, cutover_report)
    self.assertTrue(plan["requires_explicit_user_approval"])
    self.assertFalse(plan["deletion_performed"])
    self.assertTrue(all(x["source_sha256"] == x["destination_sha256"] for x in plan["verified_duplicates"]))


def test_stage4s_cli_has_no_delete_action(self):
    parser = build_arg_parser()
    option_strings = {opt for action in parser._actions for opt in action.option_strings}
    self.assertNotIn("--delete", option_strings)
```

- [ ] **Step 2: Run the full local suite and verify it fails until cleanup-plan support is added**

Run:

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Expected: FAIL only on the new cleanup-plan tests before implementation.

- [ ] **Step 3: Implement final gate/report generation**

`stage4s_cutover_report.json` must contain:

```json
{
  "safe": true,
  "g_project_root": "G:\\My Drive\\ConceptGhost",
  "c_runtime_root": "C:\\ConceptGhostRuntime",
  "canonical_workflows_verified": true,
  "legacy_sources_deleted": false,
  "grandfathered_runtime": [],
  "unknown_paths": [],
  "hash_mismatches": [],
  "destination_conflicts": []
}
```

The real `grandfathered_runtime` array may contain the current DA3 paths under `C:\ConceptGhost\cache`; that is accepted if documented and existing. `stage4s_cleanup_plan.json` is informational only and has `requires_explicit_user_approval: true`.

- [ ] **Step 4: Run local + ZIP smoke + GitHub Actions and manual runtime gates**

Automated commands:

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Package validation:

```text
- ZIP contains STORAGE_MIGRATION.bat and sibling scripts/
- every top-level BAT is CRLF-only
- extracted ZIP test suite passes from a fresh directory
- SHA-256 file matches the final ZIP
```

GitHub Actions must pass the existing Windows 3.12, Windows 3.14, and Ubuntu 3.12 matrix before user release.

Manual regression gate after copy/cutover-check:

```text
1. Open an Atlas reference workflow from G:\My Drive\ConceptGhost\Workflows\Atlas.
2. Open G:\My Drive\ConceptGhost\Workflows\DA3\advanced_3d.json.
3. Confirm a protected Pixal3D SingleView workflow still loads.
4. Confirm a protected Pixal3D MultiView workflow still loads.
5. Compare host pip freeze/custom-node fingerprints against pre-4S evidence; unrelated deltas must be empty.
6. Run STORAGE.bat and confirm the ledger separates G durable, C runtime, grandfathered runtime, and external attributable bytes.
```

- [ ] **Step 5: Commit and release the non-destructive Stage 4S package**

```bash
git add .github README.md scripts tests docs STORAGE_MIGRATION.bat config.yml
git commit -m "feat: complete non-destructive Stage 4S storage cutover"
```

Upload final artifacts to:

```text
G:\My Drive\ConceptGhost\Tests\Packages\ConceptGhost_Stage04S_v0.4.5_READY\
```

Required artifacts:

```text
ConceptGhost_Stage04S_v0.4.5.zip
ConceptGhost_Stage04S_v0.4.5_SHA256.txt
ConceptGhost_Stage04S_v0.4.5_validation.txt
stage04s_v0.4.5_tests.log
stage04s_v0.4.5_smoke.log
```

Do **not** create or run any delete-capable package. End Stage 4S by presenting the generated cleanup plan and asking separately for explicit approval before any future deletion stage.

---

## Self-Review Results

- **Spec coverage:** every approved requirement is mapped: dual roots (Task 1), inventory/fail-closed classification (Task 2), copy/hash/source preservation (Task 3), Drive BAT/report policy (Task 4), code cutover and DA3 grandfathering (Task 5), storage accounting (Task 6), canonical G: workflows and upstream provenance (Task 7), regression/CI/no-deletion cleanup plan (Task 8).
- **Placeholder scan:** no placeholders remain.
- **Type/interface consistency:** `PathContract`, `load_path_contract`, migration inventory, copy verification, and cleanup-plan interfaces are defined before downstream use.
- **Destructive-scope check:** no task exposes a delete CLI or instructs deletion of legacy `C:\ConceptGhost`; Stage 4S remains reversible.
