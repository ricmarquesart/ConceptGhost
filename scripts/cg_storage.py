#!/usr/bin/env python3
"""ConceptGhost storage tracker.

Measures project-related storage on C: and the Google Drive mirror on G:.
Writes a human-readable TXT plus a JSON history. Uses only the Python standard
library so it can run before Atlas/DA3/MoGe dependencies are installed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_PROJECT_ROOT = Path(r"C:\ConceptGhost")
DEFAULT_DRIVE_ROOT = Path(r"G:\My Drive\ConceptGhost")


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


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def first_existing_ancestor(path: Path) -> Path:
    p = path
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


def component(path: Path, classification: str, note: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path_size(path),
        "classification": classification,
        "note": note,
    }


def selected_comfy_root(project_root: Path) -> Path | None:
    inv = load_json(project_root / "manifests" / "preinstall_inventory.json", {})
    try:
        value = inv["comfyui"]["selected"]["root"]
        return Path(value) if value else None
    except Exception:
        return None


def build_storage_snapshot(
    *, project_root: Path, drive_root: Path, reason: str, comfyui_root: Path | None = None
) -> dict[str, Any]:
    project_root = Path(project_root)
    drive_root = Path(drive_root)
    comfy_root = Path(comfyui_root) if comfyui_root else selected_comfy_root(project_root)

    parts: dict[str, dict[str, Any]] = {
        "project_root": component(project_root, "project-owned", "Main C: workspace; breakdown rows below are included here."),
        "project_output": component(project_root / "output", "breakdown", "Included in project_root."),
        "project_cache": component(project_root / "cache", "breakdown", "Included in project_root."),
        "project_logs": component(project_root / "logs", "breakdown", "Included in project_root."),
        "project_manifests": component(project_root / "manifests", "breakdown", "Included in project_root."),
        "drive_root": component(drive_root, "project-owned", "Google Drive mirror total; breakdown rows below are included here."),
        "drive_reports": component(drive_root / "Reports", "breakdown", "Included in drive_root."),
        "drive_logs": component(drive_root / "Logs", "breakdown", "Included in drive_root."),
        "drive_tests": component(drive_root / "Tests", "breakdown", "Included in drive_root."),
        "drive_storage": component(drive_root / "Storage", "breakdown", "Included in drive_root."),
    }
    if comfy_root:
        parts["atlas_camera"] = component(
            comfy_root / "custom_nodes" / "atlas-camera",
            "related-external",
            "Atlas checkout inside ComfyUI; attribution is controlled by atlas_core_install.json.",
        )
        parts["da3_models"] = component(
            comfy_root / "models" / "depthanything3",
            "shared-related",
            "May contain pre-existing/shared files; whole folder is not automatically attributed to ConceptGhost.",
        )
        parts["moge_models"] = component(
            comfy_root / "models" / "geometry_estimation",
            "shared-related",
            "May contain pre-existing/shared files; whole folder is not automatically attributed to ConceptGhost.",
        )

    attributable_c = parts["project_root"]["size_bytes"]

    stage3_manifest = load_json(project_root / "manifests" / "atlas_camera_deps_install.json", {})
    if stage3_manifest:
        package_bytes = int(stage3_manifest.get("bytes_added_packages") or 0)
        parts["atlas_camera_deps_added"] = {
            "path": str(Path(stage3_manifest.get("python_executable") or "ComfyUI Python site-packages")),
            "exists": True,
            "size_bytes": package_bytes,
            "classification": "related-external-attributable",
            "note": "Additive GeoCalib/OpenCV files attributed by Stage 3 manifest; protected package replacements are forbidden.",
        }
        attributable_c += package_bytes
        cache_text = stage3_manifest.get("geocalib_model_cache")
        if cache_text:
            cache_path = Path(cache_text)
            before_cache = int(stage3_manifest.get("geocalib_model_cache_before_bytes") or 0)
            current_cache = path_size(cache_path)
            added_cache = max(0, current_cache - before_cache)
            parts["geocalib_model_cache_added"] = {
                "path": str(cache_path),
                "exists": cache_path.exists(),
                "size_bytes": added_cache,
                "classification": "related-external-attributable",
                "note": "Only growth above the pre-Stage-3 GeoCalib cache baseline is attributed to ConceptGhost.",
            }
            attributable_c += added_cache

    stage4_manifest = load_json(project_root / "manifests" / "da3_baseline_install.json", {})
    if stage4_manifest:
        repo_bytes = int(stage4_manifest.get("bytes_added_repo") or 0)
        host_bytes = int(stage4_manifest.get("bytes_added_host_packages") or 0)
        workspace_bytes = int(stage4_manifest.get("bytes_added_workspace") or 0)
        pixi_home_bytes = int(stage4_manifest.get("bytes_added_pixi_home") or 0)

        parts["da3_repo_added"] = {
            "path": str(stage4_manifest.get("target") or "DA3 custom-node checkout"),
            "exists": True,
            "size_bytes": repo_bytes,
            "classification": "related-external-attributable",
            "note": "DA3 checkout bytes created by ConceptGhost; pre-existing upstream checkouts are preserved and not charged.",
        }
        parts["da3_host_packages_added"] = {
            "path": str(stage4_manifest.get("python_executable") or "ComfyUI Python site-packages"),
            "exists": True,
            "size_bytes": host_bytes,
            "classification": "related-external-attributable",
            "note": "Additive host bridge packages approved by the Stage 4 resolver gate; existing package versions are preserved.",
        }
        parts["da3_comfy_env_workspace_added"] = {
            "path": str(stage4_manifest.get("comfy_env_workspace") or "comfy-env workspace"),
            "exists": True,
            "size_bytes": workspace_bytes,
            "classification": "related-external-attributable",
            "note": "External default comfy-env workspace growth. Stage 4 normally keeps this at 0 bytes and adds only a runtime junction.",
        }
        parts["da3_comfy_env_pixi_home_added"] = {
            "path": str(stage4_manifest.get("comfy_env_pixi_home") or "comfy-env pixi home"),
            "exists": True,
            "size_bytes": pixi_home_bytes,
            "classification": "related-external-attributable",
            "note": "Growth in comfy-env's pixi/bootstrap home attributable to Stage 4.",
        }
        isolated_workspace_text = stage4_manifest.get("project_comfy_env_workspace")
        if isolated_workspace_text:
            isolated_workspace = Path(isolated_workspace_text)
            parts["da3_project_isolated_workspace"] = {
                "path": str(isolated_workspace),
                "exists": isolated_workspace.exists(),
                "size_bytes": path_size(isolated_workspace),
                "classification": "breakdown",
                "note": "Project-owned DA3-only comfy-env workspace; already included in project_root and never double-counted.",
            }
        attributable_c += repo_bytes + host_bytes + workspace_bytes + pixi_home_bytes

        model_text = stage4_manifest.get("model_dir")
        if model_text:
            model_path = Path(model_text)
            before_models = int(stage4_manifest.get("model_dir_before_bytes") or 0)
            current_models = path_size(model_path)
            added_models = max(0, current_models - before_models)
            parts["da3_models_added"] = {
                "path": str(model_path),
                "exists": model_path.exists(),
                "size_bytes": added_models,
                "classification": "related-external-attributable",
                "note": "Only DA3 model-folder growth above the Stage 4 pre-run baseline is attributed to ConceptGhost.",
            }
            attributable_c += added_models

        pixi_cache_text = stage4_manifest.get("project_pixi_cache")
        if pixi_cache_text:
            pixi_cache_path = Path(pixi_cache_text)
            parts["da3_project_pixi_cache"] = {
                "path": str(pixi_cache_path),
                "exists": pixi_cache_path.exists(),
                "size_bytes": path_size(pixi_cache_path),
                "classification": "breakdown",
                "note": "Project-owned pixi cache; already included in project_root and therefore not double-counted.",
            }

    atlas_manifest = load_json(project_root / "manifests" / "atlas_core_install.json", {})
    if atlas_manifest and not atlas_manifest.get("preexisting", True):
        target_text = atlas_manifest.get("target")
        if target_text:
            atlas_target = Path(target_text)
            if atlas_target.exists():
                try:
                    atlas_target.relative_to(project_root)
                    outside_project = False
                except ValueError:
                    outside_project = True
                if outside_project:
                    attributable_c += path_size(atlas_target)

    attributable_g = parts["drive_root"]["size_bytes"]
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": utc_now(),
        "reason": reason,
        "project_root": str(project_root),
        "drive_root": str(drive_root),
        "comfyui_root": str(comfy_root) if comfy_root else None,
        "components": parts,
        "project_attributable_c_bytes": attributable_c,
        "project_attributable_g_bytes": attributable_g,
        "project_attributable_combined_bytes": attributable_c + attributable_g,
        "drive_snapshots": {
            "C_project_drive": disk_snapshot(project_root),
            "G_google_drive": disk_snapshot(drive_root),
        },
        "notes": [
            "Nested breakdown rows are not added twice to totals.",
            "Shared/pre-existing ComfyUI folders are visible but not automatically charged to ConceptGhost.",
            "Install-specific manifests are the authority for bytes added by Atlas/DA3/MoGe/dependency operations.",
        ],
    }


def format_txt(snapshot: dict[str, Any], history: list[dict[str, Any]]) -> str:
    p = snapshot["components"]
    lines = [
        "ConceptGhost Storage Tracker",
        "=" * 78,
        f"Updated: {snapshot['timestamp']}",
        f"Reason: {snapshot['reason']}",
        f"Project root: {snapshot['project_root']}",
        f"Google Drive root: {snapshot['drive_root']}",
        f"ComfyUI root: {snapshot.get('comfyui_root') or 'not detected'}",
        "",
        "PROJECT-ATTRIBUTABLE TOTALS",
        "-" * 78,
        f"C: attributable to ConceptGhost : {human_bytes(snapshot['project_attributable_c_bytes'])} ({snapshot['project_attributable_c_bytes']} bytes)",
        f"G: ConceptGhost mirror          : {human_bytes(snapshot['project_attributable_g_bytes'])} ({snapshot['project_attributable_g_bytes']} bytes)",
        f"Combined tracked footprint      : {human_bytes(snapshot['project_attributable_combined_bytes'])} ({snapshot['project_attributable_combined_bytes']} bytes)",
        "",
        "C: COMPONENTS",
        "-" * 78,
    ]
    for key in [
        "project_root", "project_output", "project_cache", "project_logs", "project_manifests",
        "atlas_camera", "atlas_camera_deps_added", "geocalib_model_cache_added",
        "da3_repo_added", "da3_host_packages_added", "da3_comfy_env_workspace_added",
        "da3_comfy_env_pixi_home_added", "da3_project_isolated_workspace", "da3_project_pixi_cache", "da3_models_added",
        "da3_models", "moge_models"
    ]:
        rec = p.get(key)
        if rec:
            lines.append(f"{key:24} {human_bytes(rec['size_bytes']):>12}  {rec['path']}")
            lines.append(f"  class={rec['classification']}  {rec['note']}")
    lines.extend(["", "G: COMPONENTS", "-" * 78])
    for key in ["drive_root", "drive_reports", "drive_logs", "drive_tests", "drive_storage"]:
        rec = p[key]
        lines.append(f"{key:24} {human_bytes(rec['size_bytes']):>12}  {rec['path']}")
        lines.append(f"  class={rec['classification']}  {rec['note']}")
    lines.extend(["", "DRIVE CAPACITY SNAPSHOT", "-" * 78])
    for label, snap in snapshot["drive_snapshots"].items():
        if "error" in snap:
            lines.append(f"{label}: unavailable ({snap['error']})")
        else:
            lines.append(
                f"{label}: total={human_bytes(snap['total_bytes'])}, used={human_bytes(snap['used_bytes'])}, free={human_bytes(snap['free_bytes'])}, anchor={snap['anchor']}"
            )
    lines.extend(["", "RECENT HISTORY", "-" * 78])
    for h in history[-20:]:
        lines.append(
            f"{h.get('timestamp')} | {h.get('reason')} | C={human_bytes(h.get('project_attributable_c_bytes', 0))} | G={human_bytes(h.get('project_attributable_g_bytes', 0))} | total={human_bytes(h.get('project_attributable_combined_bytes', 0))}"
        )
    lines.extend(["", "NOTES", "-" * 78])
    lines.extend(f"- {x}" for x in snapshot.get("notes", []))
    return "\n".join(lines) + "\n"


def write_storage_tracking(
    *, project_root: Path, drive_root: Path, reason: str, comfyui_root: Path | None = None
) -> dict[str, Any]:
    snapshot = build_storage_snapshot(
        project_root=project_root, drive_root=drive_root, reason=reason, comfyui_root=comfyui_root
    )
    manifests = project_root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    history_path = manifests / "storage_history.json"
    doc = load_json(history_path, {"schema_version": SCHEMA_VERSION, "snapshots": []})
    doc.setdefault("snapshots", []).append(snapshot)
    atomic_write_json(history_path, doc)
    text = format_txt(snapshot, doc["snapshots"])
    local_txt = manifests / "storage_usage.txt"
    atomic_write_text(local_txt, text)

    drive_written = False
    drive_txt = drive_root / "Storage" / "ConceptGhost_Disk_Usage.txt"
    drive_history = drive_root / "Storage" / "storage_history.json"
    try:
        if drive_root.exists() or (os.name == "nt" and Path(drive_root.anchor).exists()):
            drive_txt.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(drive_txt, text)
            atomic_write_json(drive_history, doc)
            drive_written = True
    except OSError:
        drive_written = False

    return {
        "status": "ok",
        "snapshot": snapshot,
        "local_txt": str(local_txt),
        "local_history": str(history_path),
        "drive_written": drive_written,
        "drive_txt": str(drive_txt),
        "drive_history": str(drive_history),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ConceptGhost storage tracker")
    ap.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    ap.add_argument("--drive-root", default=str(DEFAULT_DRIVE_ROOT))
    ap.add_argument("--comfyui-root", default=None)
    ap.add_argument("--reason", default="manual")
    args = ap.parse_args(argv)
    result = write_storage_tracking(
        project_root=Path(args.project_root),
        drive_root=Path(args.drive_root),
        reason=args.reason,
        comfyui_root=Path(args.comfyui_root) if args.comfyui_root else None,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
