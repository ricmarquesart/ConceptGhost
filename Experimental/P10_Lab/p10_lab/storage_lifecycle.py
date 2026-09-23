from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ContractError


_SCHEMA="ConceptGhost.P10StorageLifecycle.v0.1"
_ALLOWED_SUBROOTS=("p10_route_setup","p10_attempts","p10_route_editor")


@dataclass(frozen=True)
class P10StorageRoots:
    conceptghost_root: Path
    route_setup_root: Path
    attempts_root: Path
    route_editor_root: Path

    def to_dict(self) -> dict[str,str]:
        return {
            "conceptghost_root":str(self.conceptghost_root),
            "route_setup_root":str(self.route_setup_root),
            "attempts_root":str(self.attempts_root),
            "route_editor_root":str(self.route_editor_root),
        }


def storage_roots(comfy_output_root: str | Path) -> P10StorageRoots:
    output=Path(comfy_output_root).resolve()
    cg=(output/"conceptghost").resolve()
    return P10StorageRoots(
        conceptghost_root=cg,
        route_setup_root=(cg/"p10_route_setup").resolve(),
        attempts_root=(cg/"p10_attempts").resolve(),
        route_editor_root=(cg/"p10_route_editor").resolve(),
    )


def _safe_owned_path(path: Path, roots: P10StorageRoots) -> Path:
    resolved=path.resolve()
    allowed=(roots.route_setup_root,roots.attempts_root,roots.route_editor_root)
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ContractError(
        f"Refusing cleanup outside ConceptGhost P10-owned cache roots: {resolved}"
    )


def _tree_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total=0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total+=item.stat().st_size
            except OSError:
                pass
    return total


def build_storage_report(comfy_output_root: str | Path) -> dict:
    roots=storage_roots(comfy_output_root)
    latest_entry=roots.route_setup_root/"LATEST_PRODUCTION_ENTRY.json"
    attempt_pointers=sorted(roots.attempts_root.glob("*/LATEST_P10_RUN.json")) if roots.attempts_root.is_dir() else []
    attempts=[]
    if roots.attempts_root.is_dir():
        for run_dir in sorted(p for p in roots.attempts_root.iterdir() if p.is_dir()):
            for attempt in sorted(p for p in run_dir.iterdir() if p.is_dir()):
                manifest_path=attempt/"attempt_manifest.json"
                status="UNKNOWN"
                if manifest_path.is_file():
                    try:
                        payload=json.loads(manifest_path.read_text(encoding="utf-8"))
                        status=str(payload.get("status") or "UNKNOWN")
                    except Exception:
                        status="INVALID_MANIFEST"
                attempts.append({
                    "p9_run_id":run_dir.name,
                    "p10_attempt_id":attempt.name,
                    "path":str(attempt),
                    "status":status,
                    "bytes":_tree_bytes(attempt),
                    "manifest_path":str(manifest_path) if manifest_path.is_file() else None,
                })

    return {
        "schema":_SCHEMA,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "roots":roots.to_dict(),
        "latest_production_entry_pointer":str(latest_entry),
        "latest_production_entry_pointer_exists":latest_entry.is_file(),
        "latest_attempt_pointers":[str(path) for path in attempt_pointers],
        "attempt_count":len(attempts),
        "attempts":attempts,
        "bytes":{
            "route_setup":_tree_bytes(roots.route_setup_root),
            "attempts":_tree_bytes(roots.attempts_root),
            "route_editor":_tree_bytes(roots.route_editor_root),
        },
        "retention_policy":{
            "p9_run":"NEVER_DELETE_FROM_P10_CLEANUP",
            "route_contract":"KEEP_WHILE_P10_MAY_REUSE_IT; EXPLICIT_MANUAL_CLEANUP_NOW; FINAL_CLOSEOUT_AUTO_DELETE_ONLY_AFTER_PROVENANCE_IS_EMBEDDED_AND_VALIDATED",
            "failed_attempt":"KEEP_FOR_DIAGNOSIS_UNTIL_EXPLICIT_MANUAL_CLEANUP",
            "successful_heavy_intermediates":"KEEP_UNTIL_FINAL_P10_DOWNSTREAM_DELIVERABLES_VALIDATE",
            "future_final_success":"EMIT_CLEANUP_MANIFEST_THEN_DELETE_ONLY_DISPOSABLE_INTERMEDIATES",
        },
    }


def cleanup_p10_owned_cache(
    comfy_output_root: str | Path,
    *,
    delete_attempt_paths: list[str | Path] | tuple[str | Path,...] = (),
    delete_route_editor_cache: bool = False,
    delete_route_setup_state: bool = False,
) -> dict:
    """Explicit destructive cleanup limited to P10-owned cache/handoff roots.

    This function intentionally has no option that accepts a P9 run directory.
    """

    roots=storage_roots(comfy_output_root)
    deleted=[]
    for raw in delete_attempt_paths:
        candidate=_safe_owned_path(Path(raw),roots)
        try:
            candidate.relative_to(roots.attempts_root)
        except ValueError as error:
            raise ContractError("delete_attempt_paths may only target p10_attempts") from error
        if candidate.exists():
            bytes_before=_tree_bytes(candidate)
            shutil.rmtree(candidate)
            deleted.append({"path":str(candidate),"bytes":bytes_before,"kind":"P10_ATTEMPT"})

    if delete_route_editor_cache and roots.route_editor_root.exists():
        candidate=_safe_owned_path(roots.route_editor_root,roots)
        bytes_before=_tree_bytes(candidate)
        shutil.rmtree(candidate)
        deleted.append({"path":str(candidate),"bytes":bytes_before,"kind":"ROUTE_EDITOR_CACHE"})

    if delete_route_setup_state and roots.route_setup_root.exists():
        candidate=_safe_owned_path(roots.route_setup_root,roots)
        bytes_before=_tree_bytes(candidate)
        shutil.rmtree(candidate)
        deleted.append({"path":str(candidate),"bytes":bytes_before,"kind":"ROUTE_HANDOFF_STATE"})

    return {
        "schema":"ConceptGhost.P10StorageCleanupResult.v0.1",
        "status":"PASS",
        "deleted":deleted,
        "deleted_bytes":sum(int(item["bytes"]) for item in deleted),
        "p9_deleted":False,
        "policy":"P10_OWNED_PATHS_ONLY_FAIL_CLOSED",
        "remaining":build_storage_report(comfy_output_root),
    }
