from __future__ import annotations

from dataclasses import dataclass, replace
import ntpath
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path(r"G:\My Drive\ConceptGhost")
DEFAULT_RUNTIME_ROOT = Path(r"C:\ConceptGhostRuntime")


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


def load_path_contract(config_path: Path | None) -> PathContract:
    config = _load_config(config_path)
    paths = config.get("paths", {}) if isinstance(config, dict) else {}
    if not isinstance(paths, dict):
        paths = {}

    project_root = Path(
        os.environ.get("CONCEPTGHOST_PROJECT_ROOT")
        or paths.get("project_root")
        or DEFAULT_PROJECT_ROOT
    )
    runtime_root = Path(
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
            overrides[field_name] = Path(value)
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
