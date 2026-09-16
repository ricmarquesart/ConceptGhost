#!/usr/bin/env python3
"""ConceptGhost Stage 3 — protected Atlas learned-camera dependency installer.

Safety model:
- never upgrades/downgrades protected packages;
- installs GeoCalib from a pinned commit with --no-deps;
- installs OpenCV only when cv2 is absent, pinned and --no-deps;
- reuses existing GeoCalib/cv2 instead of overwriting them;
- snapshots pip + custom_nodes before/after and fails closed on unexpected drift;
- never writes to non-Atlas custom-node projects or workflow directories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from .cg_bootstrap import atomic_write_json, atomic_write_text, path_size, utc_now
except ImportError:  # direct script execution
    from cg_bootstrap import atomic_write_json, atomic_write_text, path_size, utc_now

DEFAULT_PROJECT_ROOT = Path(r"C:\ConceptGhost")
GEOCALIB_REPO_URL = "https://github.com/cvg/GeoCalib.git"
GEOCALIB_PINNED_COMMIT = "97b8968e7798a66bf04fcf791fb535624241bda7"
OPENCV_PYTHON_VERSION = "4.14.0.94"
OPENCV_DISTS = ["opencv-python", "opencv-contrib-python", "opencv-python-headless", "opencv-contrib-python-headless"]

PROTECTED_PACKAGES = [
    "torch",
    "torchvision",
    "numpy",
    "kornia",
    "transformers",
    "xformers",
    "triton",
    "comfyui-frontend-package",
    "comfyui-workflow-templates",
    "comfy-kitchen",
    "comfy-aimdo",
]
REQUIRED_PROTECTED = ["torch", "torchvision", "numpy", "kornia"]
ALLOWED_ADDITIONS = {"geocalib", "opencv-python"}
ATLAS_DIRNAME = "atlas-camera"


def _norm_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_freeze(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " @ " in line:
            name = line.split(" @ ", 1)[0].strip()
        elif "==" in line:
            name = line.split("==", 1)[0].strip()
        elif line.startswith("-e ") and "#egg=" in line:
            name = line.rsplit("#egg=", 1)[1].strip()
        else:
            name = line.split("[", 1)[0].split("=", 1)[0].strip()
        if name:
            result[_norm_name(name)] = line
    return result


def compare_freeze_maps(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    changed = {
        k: {"before": before[k], "after": after[k]}
        for k in sorted(set(before) & set(after))
        if before[k] != after[k]
    }
    removed = {k: before[k] for k in sorted(set(before) - set(after))}
    added = {k: after[k] for k in sorted(set(after) - set(before))}
    allowed_added = {k: v for k, v in added.items() if k in ALLOWED_ADDITIONS}
    unexpected_added = {k: v for k, v in added.items() if k not in ALLOWED_ADDITIONS}
    safe = not changed and not removed and not unexpected_added
    return {
        "safe": safe,
        "changed": changed,
        "removed": removed,
        "allowed_added": allowed_added,
        "unexpected_added": unexpected_added,
    }


def _tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "files": 0, "bytes": 0, "fingerprint": None}
    h = hashlib.sha256()
    files = 0
    total = 0
    for p in sorted((x for x in path.rglob("*") if x.is_file()), key=lambda x: x.as_posix().lower()):
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(path).as_posix()
        files += 1
        total += st.st_size
        h.update(rel.encode("utf-8", errors="surrogatepass"))
        h.update(b"\0")
        h.update(str(st.st_size).encode("ascii"))
        h.update(b"\0")
        h.update(str(st.st_mtime_ns).encode("ascii"))
        h.update(b"\n")
    return {"exists": True, "files": files, "bytes": total, "fingerprint": h.hexdigest()}


def snapshot_custom_nodes(custom_nodes_root: Path) -> dict[str, dict[str, Any]]:
    root = Path(custom_nodes_root)
    if not root.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for child in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if child.name.lower() == ATLAS_DIRNAME:
            continue
        if child.is_dir():
            result[child.name] = _tree_fingerprint(child)
        elif child.is_file():
            try:
                st = child.stat()
                h = hashlib.sha256()
                h.update(child.name.encode("utf-8"))
                h.update(str(st.st_size).encode("ascii"))
                h.update(str(st.st_mtime_ns).encode("ascii"))
                result[child.name] = {
                    "exists": True,
                    "files": 1,
                    "bytes": st.st_size,
                    "fingerprint": h.hexdigest(),
                }
            except OSError:
                pass
    return result


def compare_custom_node_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    added = {k: after[k] for k in sorted(set(after) - set(before))}
    removed = {k: before[k] for k in sorted(set(before) - set(after))}
    changed = {
        k: {"before": before[k], "after": after[k]}
        for k in sorted(set(before) & set(after))
        if before[k] != after[k]
    }
    return {"safe": not added and not removed and not changed, "added": added, "removed": removed, "changed": changed}


def build_install_plan_from_probe(probe: dict[str, Any]) -> dict[str, Any]:
    packages = {_norm_name(k): v for k, v in (probe.get("packages") or {}).items()}
    modules = probe.get("modules") or {}
    blockers: list[str] = []
    installs: list[dict[str, Any]] = []
    reuse: list[dict[str, Any]] = []

    for name in REQUIRED_PROTECTED:
        if not packages.get(_norm_name(name)):
            blockers.append(
                f"Required protected package '{name}' is missing. Stage 3 will not install or replace protected packages automatically."
            )

    if modules.get("geocalib"):
        reuse.append({"component": "geocalib", "version": packages.get("geocalib"), "action": "reuse_existing"})
    elif packages.get("geocalib"):
        blockers.append(
            "GeoCalib distribution already exists but the geocalib module is not importable. Stage 3 will not overwrite an existing GeoCalib installation."
        )
    else:
        installs.append(
            {
                "package": "geocalib",
                "action": "install_additive_only",
                "pip_args": [
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    f"git+{GEOCALIB_REPO_URL}@{GEOCALIB_PINNED_COMMIT}",
                ],
                "reason": "Atlas learned camera prior; pinned pure-Python package with dependency resolution disabled.",
            }
        )

    existing_cv_dists = [name for name in OPENCV_DISTS if packages.get(name)]
    if modules.get("cv2"):
        cv_dist = existing_cv_dists[0] if existing_cv_dists else None
        reuse.append({"component": "cv2", "distribution": cv_dist, "version": packages.get(cv_dist) if cv_dist else None, "action": "reuse_existing"})
    elif existing_cv_dists:
        blockers.append(
            "An OpenCV distribution already exists but cv2 is not importable. Stage 3 will not overwrite or replace an existing OpenCV installation."
        )
    else:
        installs.append(
            {
                "package": "opencv-python",
                "action": "install_additive_only",
                "pip_args": [
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--only-binary=:all:",
                    f"opencv-python=={OPENCV_PYTHON_VERSION}",
                ],
                "reason": "GeoCalib runtime import requires cv2; pinned wheel-only install prevents dependency resolution/source builds.",
            }
        )

    return {
        "blockers": blockers,
        "installs": installs,
        "reuse": reuse,
        "protected_packages": PROTECTED_PACKAGES,
        "protected_changes_planned": [],
        "policy": {
            "no_upgrade": True,
            "no_dependency_resolution": True,
            "no_kornia_change": True,
            "no_torch_change": True,
            "no_numpy_change": True,
            "no_transformers_change": True,
            "no_custom_nodes_writes": True,
            "no_workflow_writes": True,
        },
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_environment(project_root: Path, explicit_comfy: str | None = None) -> tuple[Path, Path]:
    inv_path = project_root / "manifests" / "preinstall_inventory.json"
    if not inv_path.is_file():
        raise RuntimeError(f"Inventory not found: {inv_path}. Run INVENTORY.bat first.")
    inv = _load_json(inv_path)
    selected = inv.get("comfyui", {}).get("selected") or {}
    comfy = Path(explicit_comfy or selected.get("root") or "")
    py = Path(selected.get("python_executable") or "")
    if not (comfy / "main.py").is_file():
        raise RuntimeError("ComfyUI root is not valid in inventory.")
    if not py.is_file():
        raise RuntimeError("ComfyUI Python executable is not valid in inventory.")
    return comfy, py


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=False)


def _pip_freeze(python_exe: Path) -> tuple[str, dict[str, str]]:
    cp = _run([str(python_exe), "-m", "pip", "freeze"], timeout=180)
    if cp.returncode != 0:
        raise RuntimeError(f"pip freeze failed: {cp.stderr[-3000:]}")
    return cp.stdout, parse_freeze(cp.stdout)


def _probe_environment(python_exe: Path) -> dict[str, Any]:
    package_names = PROTECTED_PACKAGES + ["geocalib", *OPENCV_DISTS]
    code = r'''
import importlib.metadata as md, importlib.util, json, site, sys
names = %r
packages = {}
for name in names:
    try:
        packages[name] = md.version(name)
    except md.PackageNotFoundError:
        packages[name] = None
mods = {}
for name in ["geocalib", "cv2"]:
    try:
        mods[name] = importlib.util.find_spec(name) is not None
    except Exception:
        mods[name] = False
print(json.dumps({"python": sys.version.split()[0], "executable": sys.executable, "packages": packages, "modules": mods, "site_packages": site.getsitepackages()}))
''' % package_names
    cp = _run([str(python_exe), "-c", code], timeout=120)
    if cp.returncode != 0:
        raise RuntimeError(f"environment probe failed: {cp.stderr[-3000:]}")
    return json.loads(cp.stdout.strip().splitlines()[-1])


def _runtime_import_probe(python_exe: Path, atlas_root: Path) -> dict[str, Any]:
    code = r'''
import json, sys
sys.path.insert(0, %r)
out = {}
try:
    import torch, torchvision, numpy, kornia, cv2
    from geocalib import GeoCalib
    from atlas_camera.inference.learned_prior import _require_geocalib
    _require_geocalib()
    out = {
      "ok": True,
      "torch": getattr(torch, "__version__", None),
      "torchvision": getattr(torchvision, "__version__", None),
      "numpy": getattr(numpy, "__version__", None),
      "kornia": getattr(kornia, "__version__", None),
      "cv2": getattr(cv2, "__version__", None),
      "geocalib_class": GeoCalib.__name__,
    }
except Exception as e:
    out = {"ok": False, "error": type(e).__name__ + ": " + str(e)}
print(json.dumps(out))
''' % str(atlas_root)
    cp = _run([str(python_exe), "-c", code], timeout=180)
    if cp.returncode != 0:
        return {"ok": False, "error": cp.stderr[-3000:] or f"probe exited {cp.returncode}"}
    try:
        return json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": "runtime import probe produced unreadable output", "stdout": cp.stdout[-3000:]}


def _torch_hub_dir(python_exe: Path) -> str | None:
    cp = _run([str(python_exe), "-c", "import torch; print(torch.hub.get_dir())"], timeout=60)
    return cp.stdout.strip().splitlines()[-1] if cp.returncode == 0 and cp.stdout.strip() else None


def plan_atlas_camera_deps(*, project_root: Path, comfyui_root: str | None = None) -> dict[str, Any]:
    project_root = Path(project_root)
    comfy, python_exe = _resolve_environment(project_root, comfyui_root)
    atlas_root = comfy / "custom_nodes" / ATLAS_DIRNAME
    if not (atlas_root / "atlas_camera").is_dir():
        raise RuntimeError(f"Atlas Camera core is not installed at {atlas_root}. Complete Stage 2 first.")
    probe = _probe_environment(python_exe)
    install_plan = build_install_plan_from_probe(probe)
    torch_hub = _torch_hub_dir(python_exe)
    return {
        "schema_version": 1,
        "status": "error" if install_plan["blockers"] else "dry-run",
        "stage": 3,
        "component": "Atlas Learned Camera Dependencies",
        "comfyui_root": str(comfy),
        "python_executable": str(python_exe),
        "atlas_root": str(atlas_root),
        "probe": probe,
        "install_plan": install_plan,
        "torch_hub_dir": torch_hub,
        "geocalib_model_cache": str(Path(torch_hub) / "geocalib") if torch_hub else None,
        "note": "Only missing GeoCalib and cv2 are eligible for additive installation. Existing packages/projects are reused and protected.",
    }


def _package_dir_size_from_probe(python_exe: Path, dist_names: list[str]) -> dict[str, Any]:
    code = r'''
import importlib.metadata as md, json
names=%r
out={}
for name in names:
    try:
        d=md.distribution(name)
        total=0
        for f in (d.files or []):
            p=d.locate_file(f)
            try:
                if p.is_file(): total += p.stat().st_size
            except OSError: pass
        out[name]={"version":d.version,"size_bytes":total,"location":str(d.locate_file(""))}
    except md.PackageNotFoundError:
        out[name]=None
print(json.dumps(out))
''' % dist_names
    cp = _run([str(python_exe), "-c", code], timeout=120)
    if cp.returncode != 0:
        return {name: None for name in dist_names}
    return json.loads(cp.stdout.strip().splitlines()[-1])


def apply_atlas_camera_deps(*, project_root: Path, comfyui_root: str | None = None) -> dict[str, Any]:
    project_root = Path(project_root)
    plan = plan_atlas_camera_deps(project_root=project_root, comfyui_root=comfyui_root)
    if plan["status"] == "error":
        return plan

    comfy = Path(plan["comfyui_root"])
    python_exe = Path(plan["python_executable"])
    atlas_root = Path(plan["atlas_root"])
    custom_root = comfy / "custom_nodes"
    manifests = project_root / "manifests"
    logs = project_root / "logs"
    manifests.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    freeze_before_text, freeze_before = _pip_freeze(python_exe)
    probe_before = _probe_environment(python_exe)
    nodes_before = snapshot_custom_nodes(custom_root)
    cache_path = Path(plan["geocalib_model_cache"]) if plan.get("geocalib_model_cache") else None
    cache_before = path_size(cache_path) if cache_path else 0

    atomic_write_text(manifests / "stage3_pip_freeze_before.txt", freeze_before_text)
    atomic_write_json(manifests / "stage3_environment_before.json", probe_before)
    atomic_write_json(manifests / "stage3_custom_nodes_before.json", nodes_before)

    executed: list[dict[str, Any]] = []
    for item in plan["install_plan"]["installs"]:
        cp = _run([str(python_exe), *item["pip_args"]], timeout=1800)
        rec = {
            "package": item["package"],
            "command": [str(python_exe), *item["pip_args"]],
            "returncode": cp.returncode,
            "stdout_tail": cp.stdout[-4000:],
            "stderr_tail": cp.stderr[-4000:],
        }
        executed.append(rec)
        if cp.returncode != 0:
            report = {
                "status": "error",
                "stage": 3,
                "reason": f"Installation failed for {item['package']}",
                "executed": executed,
                "policy": plan["install_plan"]["policy"],
            }
            atomic_write_json(logs / "atlas_camera_deps_report.json", report)
            return report

    freeze_after_text, freeze_after = _pip_freeze(python_exe)
    probe_after = _probe_environment(python_exe)
    nodes_after = snapshot_custom_nodes(custom_root)
    freeze_delta = compare_freeze_maps(freeze_before, freeze_after)
    nodes_delta = compare_custom_node_snapshots(nodes_before, nodes_after)
    runtime_probe = _runtime_import_probe(python_exe, atlas_root)
    dist_info = _package_dir_size_from_probe(python_exe, ["geocalib", "opencv-python"])

    atomic_write_text(manifests / "stage3_pip_freeze_after.txt", freeze_after_text)
    atomic_write_json(manifests / "stage3_environment_after.json", probe_after)
    atomic_write_json(manifests / "stage3_custom_nodes_after.json", nodes_after)
    atomic_write_json(manifests / "stage3_environment_delta.json", freeze_delta)
    atomic_write_json(manifests / "stage3_custom_nodes_delta.json", nodes_delta)

    pre_packages = probe_before.get("packages", {})
    attributable = 0
    for dist_name in ["geocalib", "opencv-python"]:
        if not pre_packages.get(dist_name) and dist_info.get(dist_name):
            attributable += int(dist_info[dist_name].get("size_bytes") or 0)

    cache_after = path_size(cache_path) if cache_path else 0
    manifest = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "stage": 3,
        "component": "Atlas Learned Camera Dependencies",
        "comfyui_root": str(comfy),
        "python_executable": str(python_exe),
        "atlas_root": str(atlas_root),
        "geocalib_repo": GEOCALIB_REPO_URL,
        "geocalib_commit": GEOCALIB_PINNED_COMMIT,
        "opencv_python_version": OPENCV_PYTHON_VERSION,
        "executed": executed,
        "probe_before": probe_before,
        "probe_after": probe_after,
        "freeze_delta": freeze_delta,
        "custom_nodes_delta": nodes_delta,
        "runtime_import_probe": runtime_probe,
        "distribution_sizes": dist_info,
        "bytes_added_packages": attributable,
        "geocalib_model_cache": str(cache_path) if cache_path else None,
        "geocalib_model_cache_before_bytes": cache_before,
        "geocalib_model_cache_after_bytes": cache_after,
        "protected_packages": PROTECTED_PACKAGES,
        "policy": plan["install_plan"]["policy"],
    }
    manifest_path = manifests / "atlas_camera_deps_install.json"
    atomic_write_json(manifest_path, manifest)

    safe = freeze_delta["safe"] and nodes_delta["safe"] and runtime_probe.get("ok") is True
    report = {
        "status": "applied" if safe else "error",
        "stage": 3,
        "component": "Atlas Learned Camera Dependencies",
        "safe": safe,
        "manifest": str(manifest_path),
        "packages_added_bytes": attributable,
        "freeze_delta_safe": freeze_delta["safe"],
        "custom_nodes_unchanged": nodes_delta["safe"],
        "runtime_import_probe": runtime_probe,
        "protected_packages_changed": list(freeze_delta["changed"].keys()),
        "unexpected_packages_added": list(freeze_delta["unexpected_added"].keys()),
        "next_gate": "Restart ComfyUI, open atlas_input_quickstart_workflow.json, load a source image, and run the learned camera solve. GeoCalib weights may download on first solve.",
    }
    if not safe:
        report["reason"] = "Compatibility gate failed. Stop; do not continue to camera execution until reviewed."
    atomic_write_json(logs / "atlas_camera_deps_report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ConceptGhost Stage 3 protected Atlas camera dependency installer")
    p.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    p.add_argument("--comfyui-root", default=None)
    p.add_argument("--apply", action="store_true", help="Install only missing additive camera dependencies. Default is dry-run.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = (
            apply_atlas_camera_deps(project_root=Path(args.project_root), comfyui_root=args.comfyui_root)
            if args.apply
            else plan_atlas_camera_deps(project_root=Path(args.project_root), comfyui_root=args.comfyui_root)
        )
    except Exception as exc:
        result = {"status": "error", "stage": 3, "reason": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())
