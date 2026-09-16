#!/usr/bin/env python3
"""ConceptGhost Stage 4S storage migration safety layer.

Stages 4S.2-4 inventory the legacy C:\\ConceptGhost tree, classify ownership,
map durable project files to canonical G: destinations, optionally copy them
with SHA-256 verification, and perform a read-only cutover readiness check.
Legacy source files are never moved or removed by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Literal, TypeAlias

try:
    from .cg_paths import PathContract, load_path_contract, validate_path_contract
except ImportError:  # direct execution: python scripts\cg_storage_migration.py
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from scripts.cg_paths import PathContract, load_path_contract, validate_path_contract

MigrationClass: TypeAlias = Literal[
    "PROJECT",
    "RUNTIME_GRANDFATHERED",
    "TEMP",
    "BOOTSTRAP_STATE",
    "UNKNOWN",
]

PROJECT_PREFIXES = {"workflows", "manifests", "logs", "docs", "output", "maya"}
GRANDFATHERED_RUNTIME_PREFIXES = {"cache/da3-comfy-env", "cache/pixi"}
BOOTSTRAP_PREFIXES = {"scripts"}
TEMP_PREFIXES = {"temp", "cache/downloads"}
PROJECT_ROOT_FILES = {"config.yml"}
DEFAULT_LEGACY_ROOT = Path(r"C:\ConceptGhost")


class MigrationBlocked(RuntimeError):
    """Raised when Stage 4S must stop instead of overwriting or guessing."""


def _normalized_relative(rel: Path) -> str:
    text = rel.as_posix().replace("\\", "/").strip("/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.lower()


def _matches_prefix(path_text: str, prefix: str) -> bool:
    prefix = prefix.lower().strip("/")
    return path_text == prefix or path_text.startswith(prefix + "/")


def classify_legacy_path(rel: Path) -> MigrationClass:
    rel = Path(rel)
    normalized = _normalized_relative(rel)
    if not normalized or ".." in rel.parts:
        return "UNKNOWN"
    if normalized in PROJECT_ROOT_FILES:
        return "PROJECT"
    if any(_matches_prefix(normalized, p) for p in GRANDFATHERED_RUNTIME_PREFIXES):
        return "RUNTIME_GRANDFATHERED"
    if any(_matches_prefix(normalized, p) for p in TEMP_PREFIXES):
        return "TEMP"
    if any(_matches_prefix(normalized, p) for p in BOOTSTRAP_PREFIXES):
        return "BOOTSTRAP_STATE"
    if any(_matches_prefix(normalized, p) for p in PROJECT_PREFIXES):
        return "PROJECT"
    return "UNKNOWN"


def _tail_after(rel: Path, count: int) -> Path:
    parts = rel.parts[count:]
    return Path(*parts) if parts else Path()


def destination_for_project_path(rel: Path, contract: PathContract) -> Path:
    rel = Path(rel)
    if classify_legacy_path(rel) != "PROJECT":
        raise ValueError(f"Not a PROJECT path: {rel}")
    normalized = _normalized_relative(rel)
    if normalized == "config.yml":
        return contract.project_root / "Config" / "config.yml"

    for prefix, folder, consumed in (
        ("workflows/reference/atlas", "Atlas", 3),
        ("workflows/reference/da3", "DA3", 3),
        ("workflows/reference/moge", "MoGe", 3),
        ("workflows/project", "Project", 2),
    ):
        if _matches_prefix(normalized, prefix):
            return contract.workflows / folder / _tail_after(rel, consumed)
    if _matches_prefix(normalized, "manifests"):
        return contract.manifests / _tail_after(rel, 1)
    if _matches_prefix(normalized, "logs"):
        return contract.logs / "Legacy_C_ConceptGhost" / _tail_after(rel, 1)
    if _matches_prefix(normalized, "docs"):
        return contract.project_root / "Documentation" / "Legacy_C_ConceptGhost" / _tail_after(rel, 1)
    if _matches_prefix(normalized, "output"):
        return contract.outputs / "Legacy_C_ConceptGhost" / _tail_after(rel, 1)
    if _matches_prefix(normalized, "maya"):
        return contract.outputs / "Maya" / "Legacy_C_ConceptGhost" / _tail_after(rel, 1)
    raise ValueError(f"PROJECT path has no Stage 4S destination mapping: {rel}")


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            return bool(is_junction())
        except OSError:
            return False
    return False


def _link_target(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except OSError:
        return None


def _iter_leaf_entries_no_follow(root: Path):
    stack = [Path(root)]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name.casefold(), reverse=True)
        except OSError as exc:
            yield current, "scan_error", exc
            continue
        for entry in entries:
            path = Path(entry.path)
            if _is_link(path):
                yield path, "link", None
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    yield path, "file", None
                else:
                    yield path, "other", None
            except OSError as exc:
                yield path, "scan_error", exc


def build_migration_inventory(legacy_root: Path, contract: PathContract) -> dict:
    legacy_root = Path(legacy_root)
    items: list[dict] = []
    blockers: list[str] = []
    counts = {
        "PROJECT": 0,
        "RUNTIME_GRANDFATHERED": 0,
        "TEMP": 0,
        "BOOTSTRAP_STATE": 0,
        "UNKNOWN": 0,
        "links": 0,
    }
    if not legacy_root.is_dir():
        blockers.append(f"Legacy root is missing or unavailable: {legacy_root}")
        return {
            "schema_version": 1,
            "status": "blocked",
            "legacy_root": str(legacy_root),
            "project_root": str(contract.project_root),
            "runtime_root": str(contract.runtime_root),
            "items": items,
            "counts": counts,
            "blockers": blockers,
            "read_only": True,
        }

    for path, kind, scan_error in _iter_leaf_entries_no_follow(legacy_root):
        try:
            rel = path.relative_to(legacy_root)
        except ValueError:
            blockers.append(f"Path escaped legacy root: {path}")
            continue
        rel_text = rel.as_posix()
        classification = classify_legacy_path(rel)
        counts[classification] += 1
        if kind == "link":
            counts["links"] += 1
        record = {
            "relative_path": rel_text,
            "source": str(path),
            "classification": classification,
            "kind": kind,
        }
        if scan_error is not None:
            record["error"] = str(scan_error)
            blockers.append(f"Could not inspect {rel_text}: {scan_error}")
        elif kind == "file":
            try:
                record["size_bytes"] = path.stat().st_size
            except OSError as exc:
                record["size_error"] = str(exc)
                blockers.append(f"Could not stat {rel_text}: {exc}")
            if classification == "PROJECT" and "size_error" not in record:
                try:
                    record["destination"] = str(destination_for_project_path(rel, contract))
                    record["sha256"] = sha256_file(path)
                except (OSError, ValueError) as exc:
                    record["project_inventory_error"] = str(exc)
                    blockers.append(f"PROJECT inventory failed for {rel_text}: {exc}")
        elif kind == "link":
            record["link_target"] = _link_target(path)
            if classification == "PROJECT":
                try:
                    record["destination"] = str(destination_for_project_path(rel, contract))
                except ValueError as exc:
                    record["project_inventory_error"] = str(exc)
                    blockers.append(f"PROJECT inventory failed for link {rel_text}: {exc}")
        else:
            blockers.append(f"Unsupported filesystem object at {rel_text}")
        if classification == "UNKNOWN":
            blockers.append(f"Unknown ownership/classification: {rel_text}")
        items.append(record)

    return {
        "schema_version": 1,
        "status": "blocked" if blockers else "ready",
        "legacy_root": str(legacy_root),
        "project_root": str(contract.project_root),
        "runtime_root": str(contract.runtime_root),
        "items": items,
        "counts": counts,
        "blockers": blockers,
        "read_only": True,
    }


def copy_one_verified(src: Path, dst: Path) -> dict:
    src, dst = Path(src), Path(dst)
    if not src.is_file() or src.is_symlink():
        raise MigrationBlocked(f"source is not a regular file: {src}")
    source_hash = sha256_file(src)
    if dst.exists():
        if not dst.is_file() or dst.is_symlink():
            raise MigrationBlocked(f"destination is not a regular file: {dst}")
        if sha256_file(dst) != source_hash:
            raise MigrationBlocked(f"destination conflict: {dst}")
        return {"action": "reuse-identical", "source": str(src), "destination": str(dst), "sha256": source_hash}

    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dst.name + ".", suffix=".conceptghost-copying", dir=str(dst.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(src, tmp)
        if sha256_file(tmp) != source_hash:
            raise MigrationBlocked(f"copy hash mismatch: {src} -> {dst}")
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    if not src.exists():
        raise MigrationBlocked(f"source disappeared during copy: {src}")
    return {"action": "copied", "source": str(src), "destination": str(dst), "sha256": source_hash}


def verify_project_copies(result: dict) -> dict:
    verified_items: list[dict] = []
    remaining: list[str] = []
    blockers = list(result.get("blocked", []))
    for item in result.get("items", []):
        src, dst = Path(item["source"]), Path(item["destination"])
        record = dict(item)
        if src.is_file():
            remaining.append(str(src))
        else:
            record["verified"] = False
            blockers.append(f"source missing after copy: {src}")
            verified_items.append(record)
            continue
        if not dst.is_file():
            record["verified"] = False
            blockers.append(f"destination missing after copy: {dst}")
            verified_items.append(record)
            continue
        source_hash, destination_hash = sha256_file(src), sha256_file(dst)
        record["source_sha256"] = source_hash
        record["destination_sha256"] = destination_hash
        record["verified"] = source_hash == destination_hash == item.get("sha256")
        if not record["verified"]:
            blockers.append(f"verification hash mismatch: {src} -> {dst}")
        verified_items.append(record)
    expected_count = int(result.get("project_file_count", len(verified_items)))
    all_verified = (
        not blockers
        and len(verified_items) == expected_count
        and len(remaining) == expected_count
        and all(x.get("verified") for x in verified_items)
    )
    verified = dict(result)
    verified.update(
        items=verified_items,
        blocked=blockers,
        source_files_remaining=remaining,
        all_verified=all_verified,
        status="verified" if all_verified else "blocked",
    )
    return verified


def copy_project_items(inventory: dict) -> dict:
    project_items = [x for x in inventory.get("items", []) if x.get("classification") == "PROJECT"]
    project_files = [x for x in project_items if x.get("kind") == "file"]
    blockers = list(inventory.get("blockers", []))
    if inventory.get("status") != "ready":
        return {
            "schema_version": 1,
            "status": "blocked",
            "copied": 0,
            "reused_identical": 0,
            "blocked": blockers or ["inventory is not ready"],
            "items": [],
            "project_file_count": len(project_files),
            "source_files_remaining": [x["source"] for x in project_files if Path(x["source"]).exists()],
            "all_verified": False,
        }
    if len(project_files) != len(project_items):
        blockers.append("PROJECT links or non-file objects require explicit handling and are not copied in Stage 4S.")

    for item in project_files:
        src, dst = Path(item["source"]), Path(item["destination"])
        expected_hash = item.get("sha256")
        if not src.is_file() or src.is_symlink():
            blockers.append(f"source is not a regular file: {src}")
            continue
        source_hash = sha256_file(src)
        if source_hash != expected_hash:
            blockers.append(f"source changed since inventory: {src}")
            continue
        if dst.exists():
            if not dst.is_file() or dst.is_symlink():
                blockers.append(f"destination is not a regular file: {dst}")
            elif sha256_file(dst) != source_hash:
                blockers.append(f"destination conflict: {dst}")
    if blockers:
        return {
            "schema_version": 1,
            "status": "blocked",
            "copied": 0,
            "reused_identical": 0,
            "blocked": blockers,
            "items": [],
            "project_file_count": len(project_files),
            "source_files_remaining": [x["source"] for x in project_files if Path(x["source"]).exists()],
            "all_verified": False,
        }

    copied = reused = 0
    results: list[dict] = []
    for item in project_files:
        try:
            result = copy_one_verified(Path(item["source"]), Path(item["destination"]))
        except MigrationBlocked as exc:
            blockers.append(str(exc))
            break
        result["relative_path"] = item["relative_path"]
        results.append(result)
        copied += result["action"] == "copied"
        reused += result["action"] == "reuse-identical"
    report = {
        "schema_version": 1,
        "status": "copied" if not blockers else "blocked",
        "copied": copied,
        "reused_identical": reused,
        "blocked": blockers,
        "items": results,
        "project_file_count": len(project_files),
        "source_files_remaining": [x["source"] for x in project_files if Path(x["source"]).exists()],
        "all_verified": False,
    }
    return verify_project_copies(report) if not blockers else report


def cutover_check(inventory: dict) -> dict:
    blockers = list(inventory.get("blockers", []))
    verified: list[dict] = []
    project_items = [x for x in inventory.get("items", []) if x.get("classification") == "PROJECT"]
    if inventory.get("status") != "ready" and not blockers:
        blockers.append("inventory is not ready")
    for item in project_items:
        rel = item.get("relative_path", "<unknown>")
        if item.get("kind") != "file":
            blockers.append(f"PROJECT item is not a regular file: {rel}")
            continue
        src, dst = Path(item["source"]), Path(item["destination"])
        expected = item.get("sha256")
        record = {
            "relative_path": rel,
            "source": str(src),
            "destination": str(dst),
            "expected_sha256": expected,
            "source_exists": src.is_file() and not src.is_symlink(),
            "destination_exists": dst.is_file() and not dst.is_symlink(),
        }
        if not record["source_exists"]:
            blockers.append(f"source missing or not regular: {src}")
            record["verified"] = False
            verified.append(record)
            continue
        source_hash = sha256_file(src)
        record["source_sha256"] = source_hash
        if source_hash != expected:
            blockers.append(f"source changed since inventory: {src}")
        if not record["destination_exists"]:
            blockers.append(f"destination missing or not regular: {dst}")
            record["verified"] = False
            verified.append(record)
            continue
        destination_hash = sha256_file(dst)
        record["destination_sha256"] = destination_hash
        record["verified"] = source_hash == destination_hash == expected
        if not record["verified"]:
            blockers.append(f"cutover hash mismatch: {src} -> {dst}")
        verified.append(record)
    safe = not blockers and len(verified) == len(project_items) and all(x.get("verified") for x in verified)
    return {
        "schema_version": 1,
        "mode": "cutover-check",
        "safe": safe,
        "status": "ready" if safe else "blocked",
        "blockers": blockers,
        "verified": verified,
        "project_file_count": len(project_items),
        "legacy_sources_deleted": False,
        "read_only": True,
    }


def _atomic_write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            json.dump(value, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ConceptGhost Stage 4S non-destructive storage migration gate")
    parser.add_argument("--config", help="Path to ConceptGhost config.yml; package config is used when present.")
    parser.add_argument("--legacy-root", default=str(DEFAULT_LEGACY_ROOT), help=r"Legacy workspace (default: C:\ConceptGhost).")
    parser.add_argument("--report-json", help="Optional persistent JSON evidence path.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--copy", action="store_true", help="Copy PROJECT files to G: with SHA-256 verification while preserving sources.")
    mode.add_argument("--cutover-check", action="store_true", help="Read-only verification that PROJECT source/destination hashes match.")
    return parser


def _resolve_contract(config_arg: str | None) -> PathContract:
    if config_arg:
        config_path: Path | None = Path(config_arg).expanduser()
    else:
        default_config = Path(__file__).resolve().parents[1] / "config.yml"
        config_path = default_config if default_config.is_file() else None
    return load_path_contract(config_path)


def run_cli(args: argparse.Namespace) -> dict:
    contract = _resolve_contract(args.config)
    path_errors = validate_path_contract(contract, require_drive=True)
    mode = "copy" if args.copy else ("cutover-check" if args.cutover_check else "dry-run")
    if path_errors:
        return {
            "schema_version": 1,
            "mode": mode,
            "status": "blocked",
            "blockers": path_errors,
            "project_root": str(contract.project_root),
            "runtime_root": str(contract.runtime_root),
            "legacy_root": str(Path(args.legacy_root)),
            "legacy_sources_deleted": False,
        }
    inventory = build_migration_inventory(Path(args.legacy_root), contract)
    if args.copy:
        operation = copy_project_items(inventory)
        operation["mode"] = "copy"
    elif args.cutover_check:
        operation = cutover_check(inventory)
    else:
        operation = {
            "schema_version": 1,
            "mode": "dry-run",
            "status": inventory.get("status", "blocked"),
            "inventory": inventory,
            "blockers": list(inventory.get("blockers", [])),
            "legacy_sources_deleted": False,
            "read_only": True,
        }
    operation.setdefault("project_root", str(contract.project_root))
    operation.setdefault("runtime_root", str(contract.runtime_root))
    operation.setdefault("legacy_root", str(Path(args.legacy_root)))
    operation.setdefault("legacy_sources_deleted", False)
    return operation


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = run_cli(args)
    if args.report_json:
        _atomic_write_json(Path(args.report_json), result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if result.get("status") == "blocked" or result.get("safe") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
