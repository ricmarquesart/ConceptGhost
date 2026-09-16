#!/usr/bin/env python3
"""Write Stage 4S final cutover and cleanup-plan evidence without deleting files."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

try:
    from .cg_paths import PathContract, load_path_contract, validate_path_contract
    from .cg_storage_migration import (
        REQUIRED_CANONICAL_WORKFLOWS,
        build_cleanup_plan,
        build_migration_inventory,
        build_stage4s_cutover_report,
        cutover_check,
    )
except ImportError:
    import sys
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from scripts.cg_paths import PathContract, load_path_contract, validate_path_contract
    from scripts.cg_storage_migration import (
        REQUIRED_CANONICAL_WORKFLOWS,
        build_cleanup_plan,
        build_migration_inventory,
        build_stage4s_cutover_report,
        cutover_check,
    )

DEFAULT_LEGACY_ROOT = Path(r"C:\ConceptGhost")


def _atomic_write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            json.dump(value, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _copy_report_from_cutover(cutover_report: dict) -> dict:
    items = []
    for item in cutover_report.get("verified", []):
        items.append(
            {
                "relative_path": item.get("relative_path"),
                "source": item.get("source"),
                "destination": item.get("destination"),
                "source_sha256": item.get("source_sha256"),
                "destination_sha256": item.get("destination_sha256"),
                "verified": bool(item.get("verified")),
            }
        )
    all_verified = bool(
        cutover_report.get("safe")
        and items
        and all(item.get("verified") for item in items)
    )
    return {
        "schema_version": 1,
        "status": "verified" if all_verified else "blocked",
        "all_verified": all_verified,
        "items": items,
    }


def write_stage4s_final_evidence(
    *,
    legacy_root: Path,
    contract: PathContract,
    evidence_dir: Path,
) -> dict:
    """Re-scan and verify current state, then write read-only final evidence."""
    legacy_root = Path(legacy_root)
    evidence_dir = Path(evidence_dir)
    inventory = build_migration_inventory(legacy_root, contract)
    cutover = cutover_check(
        inventory,
        required_workflows=REQUIRED_CANONICAL_WORKFLOWS,
        require_reference_provenance=True,
    )
    final_cutover = build_stage4s_cutover_report(inventory, cutover)
    cleanup_plan = build_cleanup_plan(_copy_report_from_cutover(cutover), cutover)

    cutover_path = evidence_dir / "stage4s_cutover_report.json"
    cleanup_path = evidence_dir / "stage4s_cleanup_plan.json"
    _atomic_write_json(cutover_path, final_cutover)
    _atomic_write_json(cleanup_path, cleanup_plan)

    ready = bool(final_cutover.get("safe") and cleanup_plan.get("status") == "ready")
    return {
        "schema_version": 1,
        "status": "ready" if ready else "blocked",
        "safe": ready,
        "cutover_report": str(cutover_path),
        "cleanup_plan": str(cleanup_path),
        "legacy_sources_deleted": False,
        "deletion_performed": False,
        "requires_explicit_user_approval": True,
        "blockers": list(final_cutover.get("blockers", [])) + list(cleanup_plan.get("blockers", [])),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ConceptGhost Stage 4S final read-only evidence writer")
    parser.add_argument("--config", help="Path to Stage 4S config.yml")
    parser.add_argument("--legacy-root", default=str(DEFAULT_LEGACY_ROOT))
    parser.add_argument("--evidence-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.config:
        config_path: Path | None = Path(args.config).expanduser()
    else:
        default_config = Path(__file__).resolve().parents[1] / "config.yml"
        config_path = default_config if default_config.is_file() else None
    contract = load_path_contract(config_path)
    path_errors = validate_path_contract(contract, require_drive=True)
    if path_errors:
        result = {
            "schema_version": 1,
            "status": "blocked",
            "safe": False,
            "blockers": path_errors,
            "legacy_sources_deleted": False,
            "deletion_performed": False,
        }
    else:
        result = write_stage4s_final_evidence(
            legacy_root=Path(args.legacy_root),
            contract=contract,
            evidence_dir=Path(args.evidence_dir),
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("safe") else 2


if __name__ == "__main__":
    raise SystemExit(main())
