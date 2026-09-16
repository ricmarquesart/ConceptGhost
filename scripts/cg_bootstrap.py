#!/usr/bin/env python3
"""ConceptGhost Stage 0/1 bootstrap.

Standard-library-only safety layer for inventory, staged project creation,
disk accounting, and conservative uninstall. No third-party model/node install
is performed by this version.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
PACKAGE_VERSION = "0.1.2-stage01"
FUTURE_DOWNLOAD_ESTIMATES = [
    {"component": "DA3 Base checkpoint", "estimated_bytes": 542 * 1024 * 1024, "approximate": True, "scheduled_now": False},
    {"component": "MoGe-2 ViT-L normal FP16 checkpoint", "estimated_bytes": 662 * 1024 * 1024, "approximate": True, "scheduled_now": False},
]
DEFAULT_WINDOWS_ROOT = r"C:\ConceptGhost"
PROJECT_DIRS = [
    "scripts",
    "logs",
    "manifests",
    "workflows/reference/atlas",
    "workflows/reference/da3",
    "workflows/reference/moge",
    "workflows/project",
    "output",
    "cache/downloads",
    "maya",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
]
PAYLOAD_FILES = [
    "SETUP.bat",
    "INVENTORY.bat",
    "UNINSTALL.bat",
    "config.yml",
    "scripts/__init__.py",
    "scripts/cg_bootstrap.py",
    "docs/README_STAGE_0_1.md",
    "docs/superpowers/specs/2026-09-15-concept-ghost-blockout-design.md",
    "docs/superpowers/plans/2026-09-15-concept-ghost-roadmap.md",
]


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


def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def download_to_temp_and_move(url: str, target: Path, *, expected_sha256: str | None = None, allow: bool = False) -> dict[str, Any]:
    """Download to a temp sibling, verify, then atomically place it.

    External downloads are locked at Stage 0/1 and must be explicitly enabled
    by a later stage after inventory review.
    """
    if not allow:
        raise PermissionError("External downloads are disabled by Stage 0/1 safety policy")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".download", dir=str(target.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        actual_hash = sha256_file(tmp)
        if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
            raise ValueError(f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {actual_hash}")
        size = tmp.stat().st_size
        os.replace(tmp, target)
        return {"path": str(target), "size_bytes": size, "sha256": actual_hash, "source": url}
    finally:
        if tmp.exists():
            tmp.unlink()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


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


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    low = value.lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"null", "none", "~"}:
        return None
    if re.fullmatch(r"[-+]?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", value):
        try:
            return float(value)
        except ValueError:
            pass
    return value.replace("\\\\", "\\")


def parse_minimal_yaml(path: Path) -> dict[str, Any]:
    """Parse the small map/scalar YAML subset used by bootstrap.

    PyYAML is intentionally not required at Stage 0/1. Lists and advanced YAML
    features are ignored because bootstrap only needs simple nested settings.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split(" #", 1)[0].rstrip()
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _scalar(value)
    return root


def load_config(config_path: Path | None) -> dict[str, Any]:
    if not config_path or not config_path.exists():
        return {}
    try:
        import yaml  # type: ignore
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return parse_minimal_yaml(config_path)


def _first_existing_ancestor(path: Path) -> Path:
    p = path
    while not p.exists() and p.parent != p:
        p = p.parent
    return p if p.exists() else Path.cwd()


def disk_snapshot(path: Path) -> dict[str, Any]:
    anchor = _first_existing_ancestor(path)
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


def _normalise_comfy_root(candidate: Path) -> Path | None:
    candidate = candidate.expanduser()
    if (candidate / "main.py").is_file():
        return candidate.resolve()
    nested = candidate / "ComfyUI"
    if (nested / "main.py").is_file():
        return nested.resolve()
    return None


def classify_comfyui_root(root: Path) -> dict[str, Any]:
    root = root.resolve()
    parent = root.parent
    portable_py = parent / "python_embeded" / "python.exe"
    desktop_py = root / ".venv" / "Scripts" / "python.exe"
    desktop_legacy_py = parent / "envs" / "default" / "Scripts" / "python.exe"
    venv_candidates = [root / "venv" / "Scripts" / "python.exe", desktop_py]
    desktop_marker = parent / ".comfyui-desktop-2"
    desktop_standalone = parent / "standalone-env"
    if portable_py.exists():
        mode = "portable"
        py = portable_py
        distribution_root = parent
    elif desktop_marker.exists() or desktop_standalone.exists() or desktop_legacy_py.exists():
        py = desktop_py if desktop_py.exists() else (desktop_legacy_py if desktop_legacy_py.exists() else None)
        mode = "desktop" if py else "desktop-unknown"
        distribution_root = parent
    else:
        py = next((p for p in venv_candidates if p.exists()), None)
        mode = "venv" if py else "unknown"
        distribution_root = root
    return {
        "root": str(root),
        "distribution_root": str(distribution_root),
        "mode": mode,
        "python_executable": str(py) if py else None,
        "preexisting": True,
    }


def _desktop_install_candidates() -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return results
    installations_file = Path(appdata) / "Comfy Desktop" / "installations.json"
    if not installations_file.is_file():
        return results
    try:
        data = json.loads(installations_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return results
    if not isinstance(data, list):
        return results
    for record in data:
        if not isinstance(record, dict):
            continue
        install_path = record.get("installPath")
        if not isinstance(install_path, str) or not install_path.strip():
            continue
        results.append((Path(install_path), f"{installations_file}::{record.get('id', 'unknown')}"))
    return results


def discover_comfyui(explicit: str | None = None) -> list[dict[str, Any]]:
    candidates: list[tuple[Path, str]] = []
    if explicit and explicit.lower() != "auto":
        candidates.append((Path(explicit), f"explicit::{explicit}"))
    env_root = os.environ.get("COMFYUI_ROOT")
    if env_root:
        candidates.append((Path(env_root), "env::COMFYUI_ROOT"))
    candidates.extend(_desktop_install_candidates())
    cwd = Path.cwd()
    for c in [cwd, cwd.parent, cwd / "ComfyUI"]:
        candidates.append((c, str(c)))
    home = Path.home()
    for base in [home, home / "Desktop", home / "Documents", home / "Downloads"]:
        for c in [base / "ComfyUI", base / "ComfyUI_windows_portable"]:
            candidates.append((c, str(c)))
    if os.name == "nt":
        for drive in ["C:\\", "D:\\", "E:\\"]:
            d = Path(drive)
            for c in [
                d / "ComfyUI",
                d / "ComfyUI_windows_portable",
                d / "AI" / "ComfyUI",
                d / "AI" / "ComfyUI_windows_portable",
            ]:
                candidates.append((c, str(c)))
    seen: set[str] = set()
    found: list[dict[str, Any]] = []
    for c, source in candidates:
        try:
            root = _normalise_comfy_root(c)
        except OSError:
            root = None
        if not root:
            continue
        key = os.path.normcase(str(root))
        if key in seen:
            continue
        seen.add(key)
        info = classify_comfyui_root(root)
        info["discovery_source"] = source
        found.append(info)
    return found


def _run_json_probe(executable: Path, code: str, timeout: int = 30) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            [str(executable), "-c", code],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if cp.returncode != 0:
            return {"ok": False, "returncode": cp.returncode, "stderr": cp.stderr.strip()[-4000:]}
        lines = [x for x in cp.stdout.splitlines() if x.strip()]
        if not lines:
            return {"ok": False, "stderr": "probe produced no output"}
        return {"ok": True, "data": json.loads(lines[-1])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def probe_python_environment(executable: Path | None) -> dict[str, Any]:
    if not executable or not executable.exists():
        return {"ok": False, "reason": "ComfyUI Python executable not found"}
    code = r'''
import importlib.util, json, platform
mods = ["torch", "torchvision", "numpy", "transformers", "kornia", "cv2"]
out = {"python": platform.python_version(), "executable": __import__("sys").executable, "packages": {}, "modules": {}}
for name in mods:
    try:
        m = __import__(name)
        out["packages"][name] = getattr(m, "__version__", "present")
    except Exception as e:
        out["packages"][name] = None
        out["modules"][name + "_error"] = str(e)
for name in ["moge", "depth_anything_3", "geocalib"]:
    try:
        spec = importlib.util.find_spec(name)
        out["modules"][name] = spec.origin if spec else None
    except Exception as e:
        out["modules"][name] = None
        out["modules"][name + "_error"] = str(e)
print(json.dumps(out))
'''
    return _run_json_probe(executable, code)


def pip_freeze(executable: Path | None) -> str:
    if not executable or not executable.exists():
        return "# ComfyUI Python executable not found; pip freeze unavailable.\n"
    try:
        cp = subprocess.run([str(executable), "-m", "pip", "freeze"], text=True, capture_output=True, timeout=60)
        return cp.stdout if cp.returncode == 0 else f"# pip freeze failed\n{cp.stderr}\n"
    except Exception as exc:
        return f"# pip freeze failed: {exc}\n"


def _file_record(path: Path, category: str, do_hash: bool = True) -> dict[str, Any]:
    rec = {
        "path": str(path.resolve()),
        "name": path.name,
        "category": category,
        "size_bytes": path.stat().st_size,
        "preexisting": True,
    }
    if do_hash:
        try:
            rec["sha256"] = sha256_file(path)
        except OSError as exc:
            rec["sha256_error"] = str(exc)
    return rec


def scan_comfy_components(info: dict[str, Any], hash_models: bool = True) -> dict[str, Any]:
    root = Path(info["root"])
    custom = root / "custom_nodes"
    models = root / "models"
    result: dict[str, Any] = {
        "custom_nodes": [],
        "models": [],
        "native_moge": False,
        "native_moge_path": None,
    }
    if custom.is_dir():
        for child in custom.iterdir():
            low = child.name.lower()
            if child.is_dir() and ("atlas" in low or "depthanythingv3" in low or "depth-anything" in low):
                result["custom_nodes"].append({"path": str(child.resolve()), "name": child.name, "preexisting": True, "size_bytes": path_size(child)})
    native = root / "comfy_extras" / "nodes_moge.py"
    result["native_moge"] = native.is_file()
    if native.is_file():
        result["native_moge_path"] = str(native.resolve())
    scan_dirs = [models / "depthanything3", models / "geometry_estimation"]
    patterns = ("*.safetensors", "*.pt", "*.pth", "*.ckpt")
    for d in scan_dirs:
        if not d.is_dir():
            continue
        for pattern in patterns:
            for p in d.glob(pattern):
                low = p.name.lower()
                if "da3" in low or "depth_anything_3" in low or "depth-anything" in low or "moge" in low:
                    result["models"].append(_file_record(p, "model", hash_models))
    return result


def discover_maya(hash_plugins: bool = False) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    candidates: list[Path] = []
    maya_location = os.environ.get("MAYA_LOCATION")
    if maya_location:
        candidates.append(Path(maya_location))
    autodesk_base = Path(r"C:\Program Files\Autodesk") if os.name == "nt" else None
    if autodesk_base and autodesk_base.is_dir():
        candidates.extend(sorted(autodesk_base.glob("Maya20*")))
    seen: set[str] = set()
    for root in candidates:
        if not root.is_dir():
            continue
        key = os.path.normcase(str(root.resolve()))
        if key in seen:
            continue
        seen.add(key)
        version_match = re.search(r"Maya(\d{4})", root.name, re.I)
        rec: dict[str, Any] = {
            "root": str(root.resolve()),
            "version_hint": version_match.group(1) if version_match else None,
            "preexisting": True,
        }
        mayapy = root / "bin" / "mayapy.exe"
        rec["mayapy"] = str(mayapy) if mayapy.exists() else None
        plugin_hits: list[dict[str, Any]] = []
        direct_candidates = [
            root / "bin" / "plug-ins" / "mayaUsdPlugin.mll",
            root / "plug-ins" / "mayaUsdPlugin.mll",
            root / "modules" / "mayaUsdPlugin.mll",
        ]
        for candidate in direct_candidates:
            if candidate.is_file():
                plugin_hits.append(_file_record(candidate, "maya_plugin", hash_plugins))
        if autodesk_base and autodesk_base.is_dir():
            maya_usd_root = autodesk_base / "MayaUSD"
            if maya_usd_root.is_dir():
                try:
                    for candidate in list(maya_usd_root.glob("**/mayaUsdPlugin.mll"))[:20]:
                        resolved = str(candidate.resolve())
                        if candidate.is_file() and all(x["path"] != resolved for x in plugin_hits):
                            plugin_hits.append(_file_record(candidate, "maya_plugin", hash_plugins))
                except OSError:
                    pass
        rec["maya_usd_plugin_files"] = plugin_hits
        if mayapy.exists():
            probe_code = (
                "import json\n"
                "out={'maya_initialized':False,'maya_usd_loadable':False,'maya_usd_loaded':False}\n"
                "try:\n"
                " import maya.standalone; maya.standalone.initialize(name='python'); out['maya_initialized']=True\n"
                " import maya.cmds as cmds\n"
                " try:\n"
                "  cmds.loadPlugin('mayaUsdPlugin', quiet=True)\n"
                "  out['maya_usd_loadable']=True\n"
                "  out['maya_usd_loaded']=bool(cmds.pluginInfo('mayaUsdPlugin', q=True, loaded=True))\n"
                " except Exception as e: out['maya_usd_error']=str(e)\n"
                "except Exception as e: out['maya_error']=str(e)\n"
                "print(json.dumps(out))\n"
            )
            rec["maya_usd_probe"] = _run_json_probe(mayapy, probe_code, timeout=45)
        else:
            rec["maya_usd_probe"] = {"ok": False, "reason": "mayapy.exe not found"}
        found.append(rec)
    return found


def build_inventory(
    project_root: Path,
    comfyui_root: str | None = None,
    hash_models: bool = True,
) -> tuple[dict[str, Any], str]:
    comfy_candidates = discover_comfyui(comfyui_root)
    selected = comfy_candidates[0] if len(comfy_candidates) == 1 else None
    if comfyui_root and comfyui_root.lower() != "auto":
        explicit_norm = _normalise_comfy_root(Path(comfyui_root))
        if explicit_norm:
            selected = classify_comfyui_root(explicit_norm)
    py_probe = probe_python_environment(Path(selected["python_executable"]) if selected and selected.get("python_executable") else None)
    components = scan_comfy_components(selected, hash_models) if selected else None
    mayas = discover_maya(False)
    disk_targets = [project_root]
    disk_targets.extend(Path(x["root"]) for x in comfy_candidates)
    disk_targets.extend(Path(x["root"]) for x in mayas)
    unique_targets: list[Path] = []
    seen_targets: set[str] = set()
    for p in disk_targets:
        key = os.path.normcase(str(p))
        if key not in seen_targets:
            seen_targets.add(key)
            unique_targets.append(p)
    disk_targets = unique_targets
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "conceptghost_version": PACKAGE_VERSION,
        "system": {
            "platform": platform.platform(),
            "os_name": os.name,
            "machine": platform.machine(),
            "python_running_inventory": sys.version,
        },
        "project": {"root": str(project_root), "preexisting": project_root.exists()},
        "comfyui": {
            "selected": selected,
            "candidates": comfy_candidates,
            "ambiguous": len(comfy_candidates) > 1 and selected is None,
            "python_probe": py_probe,
            "components": components,
        },
        "maya": mayas,
        "disk": [disk_snapshot(p) for p in disk_targets],
        "notes": [
            "All discovered components are observational records and are marked preexisting=true.",
            "No Atlas/DA3/MoGe installation is performed by Stage 0/1 bootstrap.",
        ],
    }
    freeze = pip_freeze(Path(selected["python_executable"]) if selected and selected.get("python_executable") else None)
    return inventory, freeze


def _record_event(events: list[dict[str, Any]], *, path: Path, action: str, category: str, before: int, after: int, preexisting: bool, source: str | None = None, sha_after: str | None = None, owner: str = "ConceptGhost") -> None:
    events.append({
        "timestamp": utc_now(),
        "path": str(path),
        "action": action,
        "category": category,
        "source": source,
        "owner": owner,
        "preexisting": preexisting,
        "size_before": before,
        "size_after": after,
        "bytes_added": max(0, after - before),
        "sha256_after": sha_after,
    })


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_ledger(project_root: Path, run_id: str, events: list[dict[str, Any]]) -> None:
    manifest_dir = project_root / "manifests"
    ledger_path = manifest_dir / "disk_ledger.json"
    existing = _load_json(ledger_path, {"schema_version": SCHEMA_VERSION, "runs": []})
    existing.setdefault("runs", []).append({"run_id": run_id, "timestamp": utc_now(), "events": events})
    atomic_write_json(ledger_path, existing)
    csv_path = manifest_dir / "disk_ledger.csv"
    rows = []
    for run in existing.get("runs", []):
        for e in run.get("events", []):
            rows.append({"run_id": run.get("run_id"), **e})
    fields = ["run_id", "timestamp", "path", "action", "category", "source", "owner", "preexisting", "size_before", "size_after", "bytes_added", "sha256_after"]
    fd, tmp_name = tempfile.mkstemp(prefix=csv_path.name + ".", suffix=".tmp", dir=str(manifest_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, csv_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _manifest_file_entry(target: Path, project_root: Path, preexisting: bool, source: str) -> dict[str, Any]:
    return {
        "path": str(target),
        "relative_path": target.relative_to(project_root).as_posix(),
        "preexisting": preexisting,
        "size_bytes": target.stat().st_size if target.exists() else 0,
        "installed_sha256": sha256_file(target) if target.exists() and target.is_file() else None,
        "source": source,
        "owner": "ConceptGhost" if not preexisting else "preexisting",
    }


def run_setup(*, package_root: Path, project_root: Path, dry_run: bool = True) -> dict[str, Any]:
    package_root = package_root.resolve()
    project_root = project_root.expanduser()
    operations: list[dict[str, Any]] = []
    for rel in PROJECT_DIRS:
        operations.append({"action": "ensure_dir", "path": str(project_root / rel)})
    for rel in PAYLOAD_FILES:
        src = package_root / rel
        if src.exists():
            operations.append({"action": "deploy_file", "source": str(src), "path": str(project_root / rel)})
    if dry_run:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "dry-run",
            "project_root": str(project_root),
            "planned_operations": operations,
            "estimated_known_payload_bytes": sum((package_root / rel).stat().st_size for rel in PAYLOAD_FILES if (package_root / rel).is_file()),
            "external_downloads": [],
            "future_download_estimates": FUTURE_DOWNLOAD_ESTIMATES,
            "note": "Stage 0/1 performs no Atlas/DA3/MoGe download.",
        }

    run_id = str(uuid.uuid4())
    events: list[dict[str, Any]] = []
    disk_before = disk_snapshot(project_root)
    project_size_before = path_size(project_root)
    project_preexisting = project_root.exists()
    project_root.mkdir(parents=True, exist_ok=True)
    for rel in PROJECT_DIRS:
        target = project_root / rel
        existed = target.exists()
        before = path_size(target)
        target.mkdir(parents=True, exist_ok=True)
        after = path_size(target)
        _record_event(events, path=target, action="reuse_dir" if existed else "create_dir", category="directory", before=before, after=after, preexisting=existed)

    previous_manifest = _load_json(project_root / "manifests" / "install_manifest.json", {})
    prev_by_rel = {x.get("relative_path"): x for x in previous_manifest.get("managed_files", []) if isinstance(x, dict)}
    managed_files: list[dict[str, Any]] = []

    for rel in PAYLOAD_FILES:
        src = package_root / rel
        if not src.is_file():
            continue
        target = project_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        before = target.stat().st_size if existed and target.is_file() else 0
        preexisting = existed and rel not in prev_by_rel
        src_hash = sha256_file(src)
        if rel == "config.yml" and existed:
            default_target = project_root / "config.default.yml"
            dt_existed = default_target.exists()
            dt_before = default_target.stat().st_size if dt_existed else 0
            if not dt_existed or sha256_file(default_target) != src_hash:
                shutil.copy2(src, default_target)
            dt_after = default_target.stat().st_size
            dt_hash = sha256_file(default_target)
            _record_event(events, path=default_target, action="update_default_config" if dt_existed else "create_default_config", category="config", before=dt_before, after=dt_after, preexisting=dt_existed and "config.default.yml" not in prev_by_rel, source=str(src), sha_after=dt_hash)
            managed_files.append(_manifest_file_entry(default_target, project_root, False, str(src)))
            managed_files.append(_manifest_file_entry(target, project_root, True, "user-preserved"))
            continue

        should_write = True
        action = "create_file"
        if existed and target.is_file():
            current_hash = sha256_file(target)
            if current_hash == src_hash:
                should_write = False
                action = "reuse_identical"
            else:
                prev = prev_by_rel.get(rel)
                if prev and prev.get("installed_sha256") == current_hash and not prev.get("preexisting", False):
                    action = "update_managed_file"
                else:
                    alt = target.with_name(target.name + ".new")
                    shutil.copy2(src, alt)
                    alt_after = alt.stat().st_size
                    alt_hash = sha256_file(alt)
                    _record_event(events, path=alt, action="write_conflict_copy", category="payload", before=0, after=alt_after, preexisting=False, source=str(src), sha_after=alt_hash)
                    managed_files.append(_manifest_file_entry(alt, project_root, False, str(src)))
                    managed_files.append(_manifest_file_entry(target, project_root, True, "preserved-conflict"))
                    continue
        if should_write:
            shutil.copy2(src, target)
        after = target.stat().st_size
        final_hash = sha256_file(target)
        _record_event(events, path=target, action=action, category="payload", before=before, after=after, preexisting=preexisting, source=str(src), sha_after=final_hash)
        managed_files.append(_manifest_file_entry(target, project_root, preexisting if not should_write else False, str(src)))

    config_path = project_root / "config.yml"
    cfg = load_config(config_path) if config_path.exists() else {}
    comfy_cfg = str(cfg.get("comfyui", {}).get("root", "auto")) if isinstance(cfg.get("comfyui", {}), dict) else "auto"
    inventory, freeze = build_inventory(project_root=project_root, comfyui_root=comfy_cfg, hash_models=True)
    inv_path = project_root / "manifests" / "preinstall_inventory.json"
    freeze_path = project_root / "manifests" / "preinstall_python_packages.txt"
    disk_path = project_root / "manifests" / "preinstall_disk.json"
    for p, content, category in [
        (inv_path, json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", "inventory"),
        (freeze_path, freeze, "inventory"),
        (disk_path, json.dumps(inventory["disk"], indent=2, ensure_ascii=False) + "\n", "inventory"),
    ]:
        existed = p.exists()
        before = p.stat().st_size if existed else 0
        atomic_write_text(p, content)
        after = p.stat().st_size
        _record_event(events, path=p, action="update_inventory" if existed else "create_inventory", category=category, before=before, after=after, preexisting=False, sha_after=sha256_file(p))
        managed_files.append(_manifest_file_entry(p, project_root, False, "generated"))

    downloads_hashes = project_root / "manifests" / "download_hashes.json"
    if not downloads_hashes.exists():
        atomic_write_json(downloads_hashes, {"schema_version": SCHEMA_VERSION, "downloads": [], "note": "No external downloads performed in Stage 0/1."})
        _record_event(events, path=downloads_hashes, action="create_manifest", category="manifest", before=0, after=downloads_hashes.stat().st_size, preexisting=False, sha_after=sha256_file(downloads_hashes))
    managed_files.append(_manifest_file_entry(downloads_hashes, project_root, False, "generated"))

    install_manifest = {
        "schema_version": SCHEMA_VERSION,
        "conceptghost_version": PACKAGE_VERSION,
        "run_id": run_id,
        "generated_at": utc_now(),
        "project_root": str(project_root),
        "project_root_preexisting": project_preexisting,
        "stage": "0-1",
        "managed_files": managed_files,
        "external_writes": [],
        "preexisting_assets": [
            x for x in managed_files if x.get("preexisting")
        ] + ([inventory["comfyui"]["selected"]] if inventory["comfyui"].get("selected") else []),
        "policy": {
            "no_external_downloads": True,
            "preserve_preexisting": True,
            "preserve_modified_on_uninstall": True,
        },
    }
    manifest_path = project_root / "manifests" / "install_manifest.json"
    existed = manifest_path.exists()
    before = manifest_path.stat().st_size if existed else 0
    atomic_write_json(manifest_path, install_manifest)
    after = manifest_path.stat().st_size
    _record_event(events, path=manifest_path, action="update_manifest" if existed else "create_manifest", category="manifest", before=before, after=after, preexisting=False, sha_after=sha256_file(manifest_path))

    _write_ledger(project_root, run_id, events)
    disk_after = disk_snapshot(project_root)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "applied",
        "stage": "0-1",
        "run_id": run_id,
        "project_root": str(project_root),
        "disk_before": disk_before,
        "disk_after": disk_after,
        "bytes_added_recorded": sum(e["bytes_added"] for e in events),
        "operations": events,
        "external_downloads": [],
        "next_stage": "Stage 2 — Atlas Camera core (not installed yet)",
    }
    report_path = project_root / "logs" / "setup_report.json"
    atomic_write_json(report_path, report)
    log_path = project_root / "logs" / "install.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{utc_now()}] Stage 0/1 applied; run_id={run_id}; recorded_bytes_added={report['bytes_added_recorded']}\n")
    project_size_after = path_size(project_root)
    report["project_root_size_before"] = project_size_before
    report["project_root_size_after"] = project_size_after
    report["actual_project_bytes_added"] = max(0, project_size_after - project_size_before)
    atomic_write_json(report_path, report)
    return report


def run_uninstall(*, project_root: Path, dry_run: bool = True, preserve_output: bool = True, force: bool = False) -> dict[str, Any]:
    project_root = project_root.expanduser()
    manifest_path = project_root / "manifests" / "install_manifest.json"
    manifest = _load_json(manifest_path, None)
    if not manifest:
        return {"status": "error", "reason": "install_manifest.json not found", "project_root": str(project_root), "deleted": [], "skipped": []}
    deleted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for item in manifest.get("managed_files", []):
        if item.get("preexisting"):
            skipped.append({"path": item.get("path"), "reason": "preexisting asset preserved"})
            continue
        path = Path(item["path"])
        try:
            rel = path.relative_to(project_root).as_posix()
        except ValueError:
            skipped.append({"path": str(path), "reason": "external path not owned by Stage 0/1"})
            continue
        if preserve_output and (rel == "output" or rel.startswith("output/")):
            skipped.append({"path": str(path), "reason": "output preserved"})
            continue
        if not path.exists():
            continue
        if path.is_file():
            installed_hash = item.get("installed_sha256")
            current_hash = sha256_file(path)
            if installed_hash and current_hash != installed_hash and not force:
                skipped.append({"path": str(path), "reason": "modified after installation; preserved"})
                continue
            candidates.append({"path": path, "bytes": path.stat().st_size})
    expected = sum(x["bytes"] for x in candidates)
    if dry_run:
        return {
            "status": "dry-run",
            "project_root": str(project_root),
            "expected_reclaim_bytes": expected,
            "would_delete": [str(x["path"]) for x in candidates],
            "skipped": skipped,
        }
    for c in candidates:
        p = c["path"]
        try:
            p.unlink()
            deleted.append({"path": str(p), "bytes": c["bytes"]})
        except OSError as exc:
            skipped.append({"path": str(p), "reason": f"delete failed: {exc}"})
    for rel in sorted(PROJECT_DIRS, key=lambda s: len(Path(s).parts), reverse=True):
        if preserve_output and (rel == "output" or rel.startswith("output/")):
            continue
        d = project_root / rel
        try:
            d.rmdir()
        except OSError:
            pass
    result = {
        "status": "applied",
        "project_root": str(project_root),
        "reclaimed_bytes": sum(x["bytes"] for x in deleted),
        "deleted": deleted,
        "skipped": skipped,
    }
    logs = project_root / "logs"
    if logs.exists():
        try:
            atomic_write_json(logs / "uninstall_report.json", result)
        except OSError:
            pass
    return result


def run_inventory(*, project_root: Path, comfyui_root: str | None, output: bool = True, hash_models: bool = True) -> dict[str, Any]:
    inventory, freeze = build_inventory(project_root, comfyui_root, hash_models)
    if output:
        manifests = project_root / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        atomic_write_json(manifests / "preinstall_inventory.json", inventory)
        atomic_write_text(manifests / "preinstall_python_packages.txt", freeze)
        atomic_write_json(manifests / "preinstall_disk.json", inventory["disk"])
    return inventory


def _resolve_roots(args: argparse.Namespace) -> tuple[Path, Path]:
    package_root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config).expanduser() if getattr(args, "config", None) else package_root / "config.yml"
    cfg = load_config(config_path)
    cfg_project = cfg.get("project", {}).get("root") if isinstance(cfg.get("project", {}), dict) else None
    project_str = getattr(args, "project_root", None) or os.environ.get("CONCEPTGHOST_ROOT") or cfg_project
    if not project_str:
        project_str = DEFAULT_WINDOWS_ROOT if os.name == "nt" else str(package_root / "_local_ConceptGhost")
    return package_root, Path(str(project_str))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ConceptGhost Stage 0/1 bootstrap")
    p.add_argument("--config", help="Path to config.yml")
    p.add_argument("--project-root", help="Override ConceptGhost project root")
    sub = p.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="Inventory existing machine state")
    inv.add_argument("--config", help=argparse.SUPPRESS)
    inv.add_argument("--project-root", help=argparse.SUPPRESS)
    inv.add_argument("--comfyui-root", default=None)
    inv.add_argument("--no-model-hashes", action="store_true")
    setup = sub.add_parser("setup", help="Create safe project framework")
    setup.add_argument("--config", help=argparse.SUPPRESS)
    setup.add_argument("--project-root", help=argparse.SUPPRESS)
    mode = setup.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply Stage 0/1 filesystem changes")
    mode.add_argument("--dry-run", action="store_true", help="Show actions only (default)")
    un = sub.add_parser("uninstall", help="Remove only owned Stage 0/1 files")
    un.add_argument("--config", help=argparse.SUPPRESS)
    un.add_argument("--project-root", help=argparse.SUPPRESS)
    umode = un.add_mutually_exclusive_group()
    umode.add_argument("--apply", action="store_true")
    umode.add_argument("--dry-run", action="store_true")
    un.add_argument("--delete-output", action="store_true", help="Allow deletion of tracked output files (not recommended)")
    un.add_argument("--force", action="store_true", help="Delete tracked files even when modified")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package_root, project_root = _resolve_roots(args)
    if args.command == "setup":
        result = run_setup(package_root=package_root, project_root=project_root, dry_run=not args.apply)
    elif args.command == "inventory":
        result = run_inventory(project_root=project_root, comfyui_root=args.comfyui_root, output=True, hash_models=not args.no_model_hashes)
    elif args.command == "uninstall":
        result = run_uninstall(project_root=project_root, dry_run=not args.apply, preserve_output=not args.delete_output, force=args.force)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())
