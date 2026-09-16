from __future__ import annotations

from dataclasses import dataclass, replace
import json
import ntpath
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path(r"G:\My Drive\ConceptGhost")
DEFAULT_RUNTIME_ROOT = Path(r"C:\ConceptGhostRuntime")
LEGACY_PROJECT_ROOT = Path(r"C:\ConceptGhost")
DA3_ENV_NAME = "depthanythingv3-nodes"


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
        project_root = Path(project_root)
        runtime_root = Path(runtime_root)
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


def _load_config(config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    from .cg_bootstrap import load_config
    return load_config(config_path)


def _path_from_value(value: object) -> Path:
    text = str(value)
    if len(text) >= 4 and text[1:2] == ":" and text[2:4] == "\\\\":
        text = text[:2] + text[2:].replace("\\\\", "\\")
    return Path(text)


def load_path_contract(config_path: Path | None) -> PathContract:
    config = _load_config(config_path)
    paths = config.get("paths", {}) if isinstance(config, dict) else {}
    if not isinstance(paths, dict):
        paths = {}

    project_root = _path_from_value(
        os.environ.get("CONCEPTGHOST_PROJECT_ROOT")
        or paths.get("project_root")
        or DEFAULT_PROJECT_ROOT
    )
    runtime_root = _path_from_value(
        os.environ.get("CONCEPTGHOST_RUNTIME_ROOT")
        or paths.get("runtime_root")
        or DEFAULT_RUNTIME_ROOT
    )
    contract = PathContract.from_roots(project_root, runtime_root)

    overrides = {}
    for field_name in (
        "workflows",
        "references",
        "reports",
        "logs",
        "manifests",
        "outputs",
        "packages",
        "storage",
        "cache",
        "workers",
        "temp",
        "local_state",
    ):
        value = paths.get(field_name)
        if value:
            overrides[field_name] = _path_from_value(value)
    return replace(contract, **overrides) if overrides else contract


def _windows_norm(path: Path) -> str:
    return ntpath.normcase(ntpath.normpath(str(path)))


def _is_nested(parent: Path, child: Path) -> bool:
    parent_s = _windows_norm(parent)
    child_s = _windows_norm(child)
    if parent_s == child_s:
        return False
    try:
        return ntpath.commonpath([parent_s, child_s]) == parent_s
    except ValueError:
        return False


def validate_path_contract(contract: PathContract, require_drive: bool) -> list[str]:
    errors: list[str] = []
    if _windows_norm(contract.project_root) == _windows_norm(contract.runtime_root):
        errors.append("Project root and runtime root are identical.")
    elif _is_nested(contract.project_root, contract.runtime_root) or _is_nested(
        contract.runtime_root, contract.project_root
    ):
        errors.append("Project root and runtime root must not be nested.")

    if require_drive and not contract.project_root.exists():
        errors.append(f"Project root is missing or unavailable: {contract.project_root}")
    return errors


def resolve_stage4s_contract(
    project_root: Path | None = None,
    *,
    config_path: Path | None = None,
) -> PathContract:
    """Resolve the approved dual-root contract for legacy stage launchers.

    Older BAT/scripts still pass ``C:\\ConceptGhost`` as ``--project-root``.
    Stage 4S treats that legacy value as a compatibility alias for the approved
    durable/runtime roots. Explicit non-legacy roots remain self-contained so
    unit tests and deliberate custom workspaces are still possible.
    """
    requested = Path(project_root) if project_root is not None else LEGACY_PROJECT_ROOT
    if _windows_norm(requested) == _windows_norm(LEGACY_PROJECT_ROOT):
        if config_path is not None and Path(config_path).is_file():
            return load_path_contract(Path(config_path))
        return PathContract.from_roots(DEFAULT_PROJECT_ROOT, DEFAULT_RUNTIME_ROOT)
    return PathContract.from_roots(requested, requested / "_runtime")


def resolve_inventory_path(
    contract: PathContract,
    legacy_project_root: Path | None = None,
) -> Path:
    """Prefer migrated G: inventory, then read the legacy C: inventory fallback."""
    canonical = contract.manifests / "preinstall_inventory.json"
    if canonical.is_file():
        return canonical
    legacy = Path(legacy_project_root or LEGACY_PROJECT_ROOT) / "manifests" / "preinstall_inventory.json"
    return legacy


def _load_json_if_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_da3_runtime_layout(contract: PathContract) -> dict[str, Any]:
    """Reuse a materialized legacy DA3 worker; otherwise use C: runtime root.

    The migrated Stage 4 install manifest is the authority. A legacy worker is
    grandfathered only when both its workspace and isolated environment still
    exist. No rebuild is triggered merely to make paths look cleaner.
    """
    manifest_path = contract.manifests / "da3_baseline_install.json"
    manifest = _load_json_if_file(manifest_path)
    workspace_text = manifest.get("project_comfy_env_workspace")
    env_text = manifest.get("project_isolated_env")
    pixi_text = manifest.get("project_pixi_cache")
    shadow_text = manifest.get("shadow_comfyui")
    if workspace_text and env_text:
        workspace = Path(str(workspace_text))
        isolated_env = Path(str(env_text))
        if workspace.is_dir() and isolated_env.is_dir():
            pixi_cache = Path(str(pixi_text)) if pixi_text else workspace.parent / "pixi"
            shadow = Path(str(shadow_text)) if shadow_text else workspace.parent / "da3-shadow-comfyui"
            return {
                "workspace": str(workspace),
                "isolated_env": str(isolated_env),
                "pixi_cache": str(pixi_cache),
                "shadow_comfyui": str(shadow),
                "grandfathered_runtime": True,
                "source_manifest": str(manifest_path),
            }

    workspace = contract.cache / "da3-comfy-env"
    return {
        "workspace": str(workspace),
        "isolated_env": str(workspace / ".pixi" / "envs" / DA3_ENV_NAME),
        "pixi_cache": str(contract.cache / "pixi"),
        "shadow_comfyui": str(contract.cache / "da3-shadow-comfyui"),
        "grandfathered_runtime": False,
        "source_manifest": None,
    }
