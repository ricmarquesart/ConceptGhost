#!/usr/bin/env python3
"""ConceptGhost storage tracker with Stage 4S dual-root accounting."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .cg_paths import PathContract, load_path_contract
except ImportError:
    import sys
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from scripts.cg_paths import PathContract, load_path_contract

SCHEMA_VERSION = 2
DEFAULT_PROJECT_ROOT = Path(r"C:\ConceptGhost")
DEFAULT_DRIVE_ROOT = Path(r"G:\My Drive\ConceptGhost")
DEFAULT_RUNTIME_ROOT = Path(r"C:\ConceptGhostRuntime")
DEFAULT_LEGACY_ROOT = Path(r"C:\ConceptGhost")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
    except Exception:
        return default


def _is_link_or_junction(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
    except OSError:
        return False
    checker = getattr(path, "is_junction", None)
    if callable(checker):
        try:
            return bool(checker())
        except OSError:
            return False
    return False


def path_size(path: Path) -> int:
    """Return regular-file bytes without recursively following links/junctions."""
    path = Path(path)
    if not path.exists() or _is_link_or_junction(path):
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            p = Path(entry.path)
            if _is_link_or_junction(p):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(p)
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                pass
    return total


def first_existing_ancestor(path: Path) -> Path:
    p = Path(path)
    while not p.exists() and p.parent != p:
        p = p.parent
    return p if p.exists() else Path.cwd()


def disk_snapshot(path: Path) -> dict[str, Any]:
    anchor = first_existing_ancestor(path)
    try:
        usage = shutil.disk_usage(anchor)
        return {
            "requested_path": str(path),
            "anchor": str(anchor),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        }
    except OSError as exc:
        return {"requested_path": str(path), "anchor": str(anchor), "error": str(exc)}


def human_bytes(value: int | None) -> str:
    if value is None:
        return "n/a"
    n = float(max(0, value))
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.2f} {units[i]}" if i else f"{int(n)} B"


def component(path: Path, classification: str, note: str, *, size_bytes: int | None = None) -> dict[str, Any]:
    path = Path(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path_size(path) if size_bytes is None else int(size_bytes),
        "classification": classification,
        "note": note,
    }


def _manifest_candidates(roots: Iterable[Path], name: str) -> list[Path]:
    result: list[Path] = []
    for root in roots:
        root = Path(root)
        candidates = [root / name]
        if root.name.casefold() not in {"manifests", "manifest"}:
            candidates.extend([root / "Manifests" / name, root / "manifests" / name])
        for candidate in candidates:
            if candidate not in result:
                result.append(candidate)
    return result


def _load_manifest(roots: Iterable[Path], name: str) -> dict[str, Any]:
    for path in _manifest_candidates(roots, name):
        value = load_json(path, {})
        if isinstance(value, dict) and value:
            return value
    return {}


def selected_comfy_root(manifest_roots: Iterable[Path]) -> Path | None:
    inv = _load_manifest(manifest_roots, "preinstall_inventory.json")
    try:
        value = inv["comfyui"]["selected"]["root"]
        return Path(value) if value else None
    except Exception:
        return None


def _is_within(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
        return True
    except (ValueError, OSError):
        return False


def _dedupe_non_nested_paths(paths: Iterable[Path]) -> list[Path]:
    existing = [Path(p) for p in paths if Path(p).exists()]
    existing.sort(key=lambda p: (len(p.parts), str(p).casefold()))
    kept: list[Path] = []
    for path in existing:
        if any(_is_within(path, root) for root in kept):
            continue
        kept.append(path)
    return kept


def _infer_legacy_root(stage4_manifest: dict[str, Any]) -> Path | None:
    for key in ("project_comfy_env_workspace", "project_pixi_cache"):
        text = stage4_manifest.get(key)
        if not text:
            continue
        p = Path(text)
        parts = [part.casefold() for part in p.parts]
        if "cache" in parts:
            idx = parts.index("cache")
            if idx > 0:
                return Path(*p.parts[:idx])
    return None


def _grandfathered_da3_paths(
    stage4_manifest: dict[str, Any], contract: PathContract, legacy_root_hint: Path | None
) -> list[Path]:
    candidates: list[Path] = []
    for key in ("project_comfy_env_workspace", "project_pixi_cache"):
        text = stage4_manifest.get(key)
        if text:
            p = Path(text)
            if not _is_within(p, contract.project_root) and not _is_within(p, contract.runtime_root):
                candidates.append(p)

    legacy_root = legacy_root_hint or _infer_legacy_root(stage4_manifest)
    if legacy_root:
        for p in (
            legacy_root / "cache" / "da3-shadow-comfyui",
            legacy_root / "config" / "da3_host_paths.json",
        ):
            if p.exists() and not _is_within(p, contract.project_root) and not _is_within(p, contract.runtime_root):
                candidates.append(p)
    return _dedupe_non_nested_paths(candidates)


def build_storage_snapshot(
    *,
    reason: str,
    contract: PathContract | None = None,
    project_root: Path | None = None,
    drive_root: Path | None = None,
    comfyui_root: Path | None = None,
    legacy_root: Path | None = None,
) -> dict[str, Any]:
    legacy_api = contract is None
    if contract is None:
        local_project = Path(project_root or DEFAULT_PROJECT_ROOT)
        durable_project = Path(drive_root or DEFAULT_DRIVE_ROOT)
        contract = PathContract.from_roots(durable_project, local_project)
        manifest_roots = [local_project / "manifests", durable_project / "Manifests"]
        legacy_root_hint = local_project
    else:
        durable_project = Path(contract.project_root)
        local_project = Path(contract.runtime_root)
        manifest_roots = [contract.manifests, durable_project / "manifests"]
        legacy_root_hint = Path(legacy_root) if legacy_root else None

    comfy_root = Path(comfyui_root) if comfyui_root else selected_comfy_root(manifest_roots)
    durable_bytes = path_size(durable_project)
    runtime_bytes = path_size(local_project)

    parts: dict[str, dict[str, Any]] = {
        "durable_project_root": component(
            durable_project, "durable-project", "Authoritative Stage 4S project workspace on G:."
        ),
        "runtime_root": component(
            local_project, "runtime", "Local active runtime/cache root; counted separately from durable G: data."
        ),
        "drive_reports": component(durable_project / "Reports", "breakdown", "Included in durable_project_root."),
        "drive_logs": component(durable_project / "Logs", "breakdown", "Included in durable_project_root."),
        "drive_tests": component(durable_project / "Tests", "breakdown", "Included in durable_project_root."),
        "drive_storage": component(durable_project / "Storage", "breakdown", "Included in durable_project_root."),
        "runtime_cache": component(local_project / "cache", "breakdown", "Included in runtime_root."),
        "runtime_workers": component(local_project / "workers", "breakdown", "Included in runtime_root."),
        "runtime_temp": component(local_project / "temp", "breakdown", "Included in runtime_root."),
    }

    legacy_project_component = local_project if legacy_api else durable_project
    parts["project_root"] = component(
        legacy_project_component,
        "project-owned" if legacy_api else "durable-project",
        "Compatibility alias; Stage 4S authoritative durable root is durable_project_root.",
    )
    parts["project_output"] = component(legacy_project_component / "output", "breakdown", "Compatibility breakdown.")
    parts["project_cache"] = component(legacy_project_component / "cache", "breakdown", "Compatibility breakdown.")
    parts["project_logs"] = component(legacy_project_component / "logs", "breakdown", "Compatibility breakdown.")
    parts["project_manifests"] = component(legacy_project_component / "manifests", "breakdown", "Compatibility breakdown.")
    parts["drive_root"] = component(durable_project, "project-owned", "Compatibility alias of durable_project_root.")

    if comfy_root:
        parts["atlas_camera"] = component(
            comfy_root / "custom_nodes" / "atlas-camera",
            "related-external",
            "Atlas checkout inside ComfyUI; attribution is controlled by install manifests.",
        )
        parts["da3_models"] = component(
            comfy_root / "models" / "depthanything3",
            "shared-related",
            "Shared model directory; only manifest-recorded growth is attributed.",
        )
        parts["moge_models"] = component(
            comfy_root / "models" / "geometry_estimation",
            "shared-related",
            "Shared model directory; only manifest-recorded growth is attributed.",
        )

    external_attributable = 0

    stage3_manifest = _load_manifest(manifest_roots, "atlas_camera_deps_install.json")
    if stage3_manifest:
        package_bytes = int(stage3_manifest.get("bytes_added_packages") or 0)
        parts["atlas_camera_deps_added"] = {
            "path": str(Path(stage3_manifest.get("python_executable") or "ComfyUI Python site-packages")),
            "exists": True,
            "size_bytes": package_bytes,
            "classification": "related-external-attributable",
            "note": "Additive GeoCalib/OpenCV files attributed by the Stage 3 manifest.",
        }
        external_attributable += package_bytes
        cache_text = stage3_manifest.get("geocalib_model_cache")
        if cache_text:
            cache_path = Path(cache_text)
            before_cache = int(stage3_manifest.get("geocalib_model_cache_before_bytes") or 0)
            added_cache = max(0, path_size(cache_path) - before_cache)
            parts["geocalib_model_cache_added"] = {
                "path": str(cache_path),
                "exists": cache_path.exists(),
                "size_bytes": added_cache,
                "classification": "related-external-attributable",
                "note": "Only GeoCalib cache growth above the pre-Stage-3 baseline is attributed.",
            }
            external_attributable += added_cache

    stage4_manifest = _load_manifest(manifest_roots, "da3_baseline_install.json")
    grandfathered_paths: list[Path] = []
    if stage4_manifest:
        for key, manifest_key, note in (
            ("da3_repo_added", "bytes_added_repo", "DA3 checkout bytes created by ConceptGhost."),
            ("da3_host_packages_added", "bytes_added_host_packages", "Additive host bridge packages."),
            ("da3_comfy_env_workspace_added", "bytes_added_workspace", "External default comfy-env workspace growth."),
            ("da3_comfy_env_pixi_home_added", "bytes_added_pixi_home", "External comfy-env pixi/bootstrap growth."),
        ):
            size = int(stage4_manifest.get(manifest_key) or 0)
            if key == "da3_repo_added":
                path_text = stage4_manifest.get("target") or "DA3 custom-node checkout"
            elif key == "da3_host_packages_added":
                path_text = stage4_manifest.get("python_executable") or "ComfyUI Python site-packages"
            elif key == "da3_comfy_env_workspace_added":
                path_text = stage4_manifest.get("comfy_env_workspace") or "comfy-env workspace"
            else:
                path_text = stage4_manifest.get("comfy_env_pixi_home") or "comfy-env pixi home"
            parts[key] = {
                "path": str(path_text),
                "exists": True,
                "size_bytes": size,
                "classification": "related-external-attributable",
                "note": note,
            }
            external_attributable += size

        isolated_text = stage4_manifest.get("project_comfy_env_workspace")
        if isolated_text:
            isolated = Path(isolated_text)
            isolated_class = (
                "breakdown"
                if _is_within(isolated, contract.runtime_root) or _is_within(isolated, contract.project_root)
                else "grandfathered-runtime"
            )
            parts["da3_project_isolated_workspace"] = component(
                isolated,
                isolated_class,
                "DA3 isolated workspace; counted in its owning root and never double-counted.",
            )

        pixi_cache_text = stage4_manifest.get("project_pixi_cache")
        if pixi_cache_text:
            pixi_cache = Path(pixi_cache_text)
            pixi_class = (
                "breakdown"
                if _is_within(pixi_cache, contract.runtime_root) or _is_within(pixi_cache, contract.project_root)
                else "grandfathered-runtime"
            )
            parts["da3_project_pixi_cache"] = component(
                pixi_cache,
                pixi_class,
                "DA3 pixi cache; counted in its owning root and never double-counted.",
            )

        model_text = stage4_manifest.get("model_dir")
        if model_text:
            model_path = Path(model_text)
            before_models = int(stage4_manifest.get("model_dir_before_bytes") or 0)
            added_models = max(0, path_size(model_path) - before_models)
            parts["da3_models_added"] = {
                "path": str(model_path),
                "exists": model_path.exists(),
                "size_bytes": added_models,
                "classification": "related-external-attributable",
                "note": "Only DA3 model-folder growth above the Stage 4 baseline is attributed.",
            }
            external_attributable += added_models

        grandfathered_paths = _grandfathered_da3_paths(stage4_manifest, contract, legacy_root_hint)

    grandfathered_bytes = sum(path_size(path) for path in grandfathered_paths)
    if grandfathered_paths:
        parts["da3_grandfathered_runtime"] = {
            "path": "; ".join(str(p) for p in grandfathered_paths),
            "paths": [str(p) for p in grandfathered_paths],
            "exists": True,
            "size_bytes": grandfathered_bytes,
            "classification": "grandfathered-runtime",
            "note": "Active pre-Stage-4S DA3 runtime retained under legacy C: paths; excluded from runtime_root to prevent double counting.",
        }
        for index, path in enumerate(grandfathered_paths, start=1):
            parts[f"da3_grandfathered_runtime_{index}"] = component(
                path, "grandfathered-runtime-breakdown", "Included in da3_grandfathered_runtime."
            )
    else:
        parts["da3_grandfathered_runtime"] = {
            "path": "",
            "paths": [],
            "exists": False,
            "size_bytes": 0,
            "classification": "grandfathered-runtime",
            "note": "No active grandfathered DA3 runtime detected.",
        }

    atlas_manifest = _load_manifest(manifest_roots, "atlas_core_install.json")
    if atlas_manifest and not atlas_manifest.get("preexisting", True):
        target_text = atlas_manifest.get("target")
        if target_text:
            atlas_target = Path(target_text)
            if (
                atlas_target.exists()
                and not _is_within(atlas_target, contract.project_root)
                and not _is_within(atlas_target, contract.runtime_root)
            ):
                atlas_bytes = path_size(atlas_target)
                parts["atlas_repo_added"] = component(
                    atlas_target,
                    "related-external-attributable",
                    "Atlas checkout created by ConceptGhost outside project/runtime roots.",
                    size_bytes=atlas_bytes,
                )
                external_attributable += atlas_bytes

    combined = durable_bytes + runtime_bytes + grandfathered_bytes + external_attributable
    attributable_c = runtime_bytes + grandfathered_bytes + external_attributable

    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": utc_now(),
        "reason": reason,
        "durable_project_root": str(durable_project),
        "runtime_root": str(local_project),
        "comfyui_root": str(comfy_root) if comfy_root else None,
        "components": parts,
        "durable_g_bytes": durable_bytes,
        "runtime_c_bytes": runtime_bytes,
        "grandfathered_runtime_c_bytes": grandfathered_bytes,
        "external_attributable_bytes": external_attributable,
        "combined_tracked_bytes": combined,
        "project_root": str(legacy_project_component),
        "drive_root": str(durable_project),
        "project_attributable_c_bytes": attributable_c,
        "project_attributable_g_bytes": durable_bytes,
        "project_attributable_combined_bytes": combined,
        "drive_snapshots": {
            "G_durable_project": disk_snapshot(durable_project),
            "C_runtime": disk_snapshot(local_project),
            "C_grandfathered_runtime": disk_snapshot(grandfathered_paths[0]) if grandfathered_paths else {},
        },
        "notes": [
            "Durable G:, new runtime C:, grandfathered runtime C:, and external attributable bytes are separate top-level totals.",
            "Nested breakdown rows and junction targets are never double-counted.",
            "Shared/pre-existing ComfyUI folders are visible but only manifest-recorded additions are charged to ConceptGhost.",
        ],
    }


def format_txt(snapshot: dict[str, Any], history: list[dict[str, Any]]) -> str:
    parts = snapshot["components"]
    lines = [
        "ConceptGhost Storage Tracker",
        "=" * 78,
        f"Updated: {snapshot['timestamp']}",
        f"Reason: {snapshot['reason']}",
        f"Durable project root: {snapshot['durable_project_root']}",
        f"Runtime root: {snapshot['runtime_root']}",
        f"ComfyUI root: {snapshot.get('comfyui_root') or 'not detected'}",
        "",
        "OWNERSHIP TOTALS",
        "-" * 78,
        f"G: durable project             : {human_bytes(snapshot['durable_g_bytes'])} ({snapshot['durable_g_bytes']} bytes)",
        f"C: new runtime                 : {human_bytes(snapshot['runtime_c_bytes'])} ({snapshot['runtime_c_bytes']} bytes)",
        f"C: grandfathered runtime       : {human_bytes(snapshot['grandfathered_runtime_c_bytes'])} ({snapshot['grandfathered_runtime_c_bytes']} bytes)",
        f"External attributable          : {human_bytes(snapshot['external_attributable_bytes'])} ({snapshot['external_attributable_bytes']} bytes)",
        f"Combined tracked footprint     : {human_bytes(snapshot['combined_tracked_bytes'])} ({snapshot['combined_tracked_bytes']} bytes)",
        "",
        "COMPONENTS",
        "-" * 78,
    ]
    for key in sorted(parts):
        rec = parts[key]
        lines.append(f"{key:34} {human_bytes(rec.get('size_bytes', 0)):>12}  {rec.get('path', '')}")
        lines.append(f"  class={rec.get('classification', '')}  {rec.get('note', '')}")
    lines.extend(["", "RECENT HISTORY", "-" * 78])
    for item in history[-20:]:
        lines.append(
            f"{item.get('timestamp')} | {item.get('reason')} | "
            f"G={human_bytes(item.get('durable_g_bytes', item.get('project_attributable_g_bytes', 0)))} | "
            f"C-runtime={human_bytes(item.get('runtime_c_bytes', 0))} | "
            f"C-grandfathered={human_bytes(item.get('grandfathered_runtime_c_bytes', 0))} | "
            f"external={human_bytes(item.get('external_attributable_bytes', 0))} | "
            f"total={human_bytes(item.get('combined_tracked_bytes', item.get('project_attributable_combined_bytes', 0)))}"
        )
    lines.extend(["", "NOTES", "-" * 78])
    lines.extend(f"- {x}" for x in snapshot.get("notes", []))
    return "\n".join(lines) + "\n"


def write_storage_tracking(
    *,
    reason: str,
    contract: PathContract | None = None,
    project_root: Path | None = None,
    drive_root: Path | None = None,
    comfyui_root: Path | None = None,
    legacy_root: Path | None = None,
) -> dict[str, Any]:
    legacy_api = contract is None
    snapshot = build_storage_snapshot(
        contract=contract,
        project_root=project_root,
        drive_root=drive_root,
        reason=reason,
        comfyui_root=comfyui_root,
        legacy_root=legacy_root,
    )

    if legacy_api:
        local_project = Path(project_root or DEFAULT_PROJECT_ROOT)
        durable_project = Path(drive_root or DEFAULT_DRIVE_ROOT)
        local_manifests = local_project / "manifests"
        local_manifests.mkdir(parents=True, exist_ok=True)
        history_path = local_manifests / "storage_history.json"
        doc = load_json(history_path, {"schema_version": SCHEMA_VERSION, "snapshots": []})
        doc.setdefault("snapshots", []).append(snapshot)
        atomic_write_json(history_path, doc)
        text = format_txt(snapshot, doc["snapshots"])
        local_txt = local_manifests / "storage_usage.txt"
        atomic_write_text(local_txt, text)

        drive_txt = durable_project / "Storage" / "ConceptGhost_Disk_Usage.txt"
        drive_history = durable_project / "Storage" / "storage_history.json"
        drive_txt.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(drive_txt, text)
        atomic_write_json(drive_history, doc)
        return {
            "status": "ok",
            "snapshot": snapshot,
            "local_txt": str(local_txt),
            "local_history": str(history_path),
            "drive_written": True,
            "drive_txt": str(drive_txt),
            "drive_history": str(drive_history),
        }

    assert contract is not None
    storage_root = Path(contract.storage)
    storage_root.mkdir(parents=True, exist_ok=True)
    history_path = storage_root / "storage_history.json"
    doc = load_json(history_path, {"schema_version": SCHEMA_VERSION, "snapshots": []})
    doc.setdefault("snapshots", []).append(snapshot)
    atomic_write_json(history_path, doc)
    text = format_txt(snapshot, doc["snapshots"])
    drive_txt = storage_root / "ConceptGhost_Disk_Usage.txt"
    atomic_write_text(drive_txt, text)
    return {
        "status": "ok",
        "snapshot": snapshot,
        "local_txt": None,
        "local_history": None,
        "drive_written": True,
        "drive_txt": str(drive_txt),
        "drive_history": str(history_path),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ConceptGhost storage tracker")
    ap.add_argument("--config", default=None, help="Stage 4S path-contract config.yml")
    ap.add_argument("--project-root", default=None, help="Legacy compatibility: local project root")
    ap.add_argument("--drive-root", default=None, help="Legacy compatibility: durable Drive root")
    ap.add_argument("--runtime-root", default=None, help="Override runtime root when using the path contract")
    ap.add_argument("--legacy-root", default=None, help="Optional legacy C:\\ConceptGhost hint for grandfathered runtime")
    ap.add_argument("--comfyui-root", default=None)
    ap.add_argument("--reason", default="manual")
    args = ap.parse_args(argv)

    comfy_root = Path(args.comfyui_root) if args.comfyui_root else None
    if args.project_root or args.drive_root:
        result = write_storage_tracking(
            project_root=Path(args.project_root or DEFAULT_PROJECT_ROOT),
            drive_root=Path(args.drive_root or DEFAULT_DRIVE_ROOT),
            reason=args.reason,
            comfyui_root=comfy_root,
            legacy_root=Path(args.legacy_root) if args.legacy_root else None,
        )
    else:
        if args.config:
            config_path: Path | None = Path(args.config)
        else:
            default_cfg = Path(__file__).resolve().parents[1] / "config.yml"
            config_path = default_cfg if default_cfg.is_file() else None
        contract = load_path_contract(config_path)
        if args.runtime_root:
            contract = PathContract.from_roots(contract.project_root, Path(args.runtime_root))
        result = write_storage_tracking(
            contract=contract,
            reason=args.reason,
            comfyui_root=comfy_root,
            legacy_root=Path(args.legacy_root) if args.legacy_root else None,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
