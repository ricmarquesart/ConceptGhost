#!/usr/bin/env python3
"""ConceptGhost Stage 2 — Atlas Camera core installer.

Installs only the public Atlas Camera repository into ComfyUI custom_nodes.
It deliberately performs no pip/package/model changes. The repository revision
is pinned for reproducibility and reference workflows are copied verbatim into
the ConceptGhost project tree.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:
    from .cg_bootstrap import atomic_write_json, path_size, sha256_file, utc_now
except ImportError:  # direct script execution
    from cg_bootstrap import atomic_write_json, path_size, sha256_file, utc_now

ATLAS_REPO_URL = "https://github.com/mikejamesvfx/atlas-camera.git"
ATLAS_PINNED_COMMIT = "9f9ff4511154769aa2f8c0bd40387278a69b0078"
REFERENCE_WORKFLOWS = [
    "atlas_input_quickstart_workflow.json",
    "atlas_export_fanout_workflow.json",
    "atlas_hero_02_photo_to_editable_scene_workflow.json",
    "atlas_photo_to_atlas_scene_workflow.json",
]
DEFAULT_PROJECT_ROOT = Path(r"C:\ConceptGhost")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_remote(value: str) -> str:
    value = value.strip().replace("\\", "/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.rstrip("/").lower()


def _run_git(args: list[str], cwd: Path | None = None, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def _git_head(repo: Path) -> str | None:
    try:
        return _run_git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    except Exception:
        return None


def _git_remote(repo: Path) -> str | None:
    try:
        return _run_git(["config", "--get", "remote.origin.url"], cwd=repo).stdout.strip()
    except Exception:
        return None


def _resolve_comfy_root(project_root: Path, explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser()
        if not (root / "main.py").is_file():
            raise RuntimeError(f"ComfyUI root does not contain main.py: {root}")
        return root
    inv_path = project_root / "manifests" / "preinstall_inventory.json"
    if not inv_path.is_file():
        raise RuntimeError(f"Inventory not found: {inv_path}. Run INVENTORY.bat first.")
    inventory = _load_json(inv_path)
    selected = inventory.get("comfyui", {}).get("selected")
    if not isinstance(selected, dict) or not selected.get("root"):
        raise RuntimeError("Inventory has no unambiguous selected ComfyUI root. Run INVENTORY.bat again.")
    root = Path(str(selected["root"]))
    if not (root / "main.py").is_file():
        raise RuntimeError(f"Selected ComfyUI root is no longer valid: {root}")
    return root


def _target_state(target: Path, repo_url: str) -> tuple[str, dict[str, Any]]:
    if not target.exists():
        return "clone", {}
    if not (target / ".git").is_dir():
        return "blocked_conflict", {"reason": "target exists but is not a Git repository"}
    remote = _git_remote(target)
    head = _git_head(target)
    if not remote or _canonical_remote(remote) != _canonical_remote(repo_url):
        return "blocked_conflict", {
            "reason": "target Git repository has a different or unreadable origin",
            "existing_remote": remote,
            "existing_head": head,
        }
    return "reuse_existing", {"existing_remote": remote, "existing_head": head}


def plan_atlas_core(
    *,
    project_root: Path,
    comfyui_root: str | None = None,
    repo_url: str = ATLAS_REPO_URL,
    pinned_commit: str = ATLAS_PINNED_COMMIT,
) -> dict[str, Any]:
    project_root = Path(project_root)
    comfy = _resolve_comfy_root(project_root, comfyui_root)
    target = comfy / "custom_nodes" / "atlas-camera"
    action, detail = _target_state(target, repo_url)
    return {
        "schema_version": 1,
        "status": "dry-run",
        "stage": 2,
        "component": "Atlas Camera Core",
        "core_only": True,
        "pip_changes": False,
        "model_downloads": False,
        "repo_url": repo_url,
        "pinned_commit": pinned_commit,
        "comfyui_root": str(comfy),
        "target": str(target),
        "action": action,
        "detail": detail,
        "reference_workflows": REFERENCE_WORKFLOWS,
        "note": "This stage only clones/reuses Atlas Camera. GeoCalib/OpenCV/Kornia are Stage 3.",
    }


def _copy_reference_workflow(src: Path, dst: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    src_hash = sha256_file(src)
    if dst.exists():
        dst_hash = sha256_file(dst)
        if dst_hash == src_hash:
            return {"source": str(src), "path": str(dst), "action": "reuse_identical", "sha256": dst_hash}
        alt = dst.with_name(dst.name + ".new")
        shutil.copy2(src, alt)
        return {
            "source": str(src),
            "path": str(alt),
            "action": "write_conflict_copy",
            "sha256": sha256_file(alt),
            "preserved": str(dst),
        }
    shutil.copy2(src, dst)
    return {"source": str(src), "path": str(dst), "action": "copy", "sha256": src_hash}


def apply_atlas_core(
    *,
    project_root: Path,
    comfyui_root: str | None = None,
    repo_url: str = ATLAS_REPO_URL,
    pinned_commit: str = ATLAS_PINNED_COMMIT,
) -> dict[str, Any]:
    project_root = Path(project_root)
    plan = plan_atlas_core(
        project_root=project_root,
        comfyui_root=comfyui_root,
        repo_url=repo_url,
        pinned_commit=pinned_commit,
    )
    if plan["action"] == "blocked_conflict":
        return {**plan, "status": "error"}
    if not shutil.which("git"):
        return {**plan, "status": "error", "reason": "git executable not found on PATH"}

    target = Path(plan["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    before = path_size(target)
    preexisting = target.exists()
    action = plan["action"]

    if action == "clone":
        temp_target = target.parent / f".conceptghost-atlas-{uuid.uuid4().hex}.tmp"
        try:
            clone = _run_git(["clone", "--no-checkout", repo_url, str(temp_target)], check=False)
            if clone.returncode != 0:
                return {
                    **plan,
                    "status": "error",
                    "reason": "git clone failed",
                    "stderr": clone.stderr[-4000:],
                }
            checkout = _run_git(["checkout", "--detach", pinned_commit], cwd=temp_target, check=False)
            if checkout.returncode != 0:
                return {
                    **plan,
                    "status": "error",
                    "reason": "pinned Atlas commit could not be checked out",
                    "stderr": checkout.stderr[-4000:],
                }
            os.replace(temp_target, target)
        finally:
            if temp_target.exists():
                shutil.rmtree(temp_target, ignore_errors=True)

    head = _git_head(target)
    remote = _git_remote(target)
    if not head:
        return {**plan, "status": "error", "reason": "Atlas repository HEAD could not be read after install"}

    workflow_records: list[dict[str, Any]] = []
    ref_root = project_root / "workflows" / "reference" / "atlas"
    for name in REFERENCE_WORKFLOWS:
        src = target / "examples" / name
        if not src.is_file():
            workflow_records.append({"path": str(src), "action": "missing_upstream"})
            continue
        workflow_records.append(_copy_reference_workflow(src, ref_root / name))

    after = path_size(target)
    manifest = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "stage": 2,
        "component": "Atlas Camera Core",
        "repo_url": repo_url,
        "requested_commit": pinned_commit,
        "atlas_commit": head,
        "remote": remote,
        "target": str(target),
        "preexisting": preexisting,
        "action": action,
        "size_before": before,
        "size_after": after,
        "bytes_added": max(0, after - before),
        "pip_changes": False,
        "model_downloads": False,
        "reference_workflows": workflow_records,
    }
    manifest_path = project_root / "manifests" / "atlas_core_install.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(manifest_path, manifest)

    report = {
        "status": "applied",
        "stage": 2,
        "action": action,
        "target": str(target),
        "atlas_commit": head,
        "requested_commit": pinned_commit,
        "preexisting": preexisting,
        "bytes_added": manifest["bytes_added"],
        "pip_changes": False,
        "model_downloads": False,
        "manifest": str(manifest_path),
        "reference_workflows": workflow_records,
        "next_gate": "Restart ComfyUI and confirm AtlasInput appears before installing Stage 3 dependencies.",
    }
    report_path = project_root / "logs" / "atlas_core_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ConceptGhost Stage 2 Atlas Camera core installer")
    p.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    p.add_argument("--comfyui-root", default=None)
    p.add_argument("--apply", action="store_true", help="Clone/reuse Atlas core. Default is dry-run.")
    p.add_argument("--repo-url", default=ATLAS_REPO_URL, help=argparse.SUPPRESS)
    p.add_argument("--pinned-commit", default=ATLAS_PINNED_COMMIT, help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.apply:
            result = apply_atlas_core(
                project_root=Path(args.project_root),
                comfyui_root=args.comfyui_root,
                repo_url=args.repo_url,
                pinned_commit=args.pinned_commit,
            )
        else:
            result = plan_atlas_core(
                project_root=Path(args.project_root),
                comfyui_root=args.comfyui_root,
                repo_url=args.repo_url,
                pinned_commit=args.pinned_commit,
            )
    except Exception as exc:
        result = {"status": "error", "stage": 2, "reason": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())
