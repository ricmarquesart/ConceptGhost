#!/usr/bin/env python3
"""Stage 4S legacy storage inventory and classification.

Task 2 is deliberately read-only. It classifies the legacy C:\\ConceptGhost
workspace, hashes durable project files, maps their future G: destinations, and
blocks on unknown ownership. It never copies, moves, or deletes data.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Literal, TypeAlias

from .cg_paths import PathContract

MigrationClass: TypeAlias = Literal[
    "PROJECT",
    "RUNTIME_GRANDFATHERED",
    "TEMP",
    "BOOTSTRAP_STATE",
    "UNKNOWN",
]

PROJECT_PREFIXES = {
    "workflows",
    "manifests",
    "logs",
    "docs",
    "output",
    "maya",
}
GRANDFATHERED_RUNTIME_PREFIXES = {
    "cache/da3-comfy-env",
    "cache/pixi",
}
BOOTSTRAP_PREFIXES = {"scripts"}
TEMP_PREFIXES = {"temp", "cache/downloads"}
PROJECT_ROOT_FILES = {"config.yml"}


def _normalized_relative(rel: Path) -> str:
    text = rel.as_posix().replace("\\", "/").strip("/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.lower()


def _matches_prefix(path_text: str, prefix: str) -> bool:
    prefix = prefix.lower().strip("/")
    return path_text == prefix or path_text.startswith(prefix + "/")


def classify_legacy_path(rel: Path) -> MigrationClass:
    """Classify a path relative to the legacy root using locked Stage 4S rules."""
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
    """Map one PROJECT legacy path to its canonical durable G: destination."""
    rel = Path(rel)
    if classify_legacy_path(rel) != "PROJECT":
        raise ValueError(f"Not a PROJECT path: {rel}")

    normalized = _normalized_relative(rel)

    if normalized == "config.yml":
        return contract.project_root / "Config" / "config.yml"

    workflow_prefixes = (
        ("workflows/reference/atlas", "Atlas", 3),
        ("workflows/reference/da3", "DA3", 3),
        ("workflows/reference/moge", "MoGe", 3),
        ("workflows/project", "Project", 2),
    )
    for prefix, folder, consumed in workflow_prefixes:
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
    """Yield files and links without traversing symlink/junction targets."""
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
    """Build a read-only fail-closed inventory for the legacy ConceptGhost root."""
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
        elif kind == "other":
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
