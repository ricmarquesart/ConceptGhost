from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .p9_boundary import sha256_file, validate_official_run


_SCHEMA="ConceptGhost.P9PersistedDependencyInventory.v0.1"
_SCAN_ROOTS=("source","camera","geometry","maya","diagnostics","package")


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_p9_dependency_inventory(run_dir: str | Path) -> dict[str,Any]:
    """Describe the persisted P9 evidence available to split-stage P10.

    P10 does not copy/reduce the authoritative run. It keeps a reference to the
    complete run_dir and freezes hashes for the critical boundary files so the
    Production workflow can prove that its upstream authority did not change.
    """

    boundary=validate_official_run(run_dir)
    root=boundary.root
    critical={
        "manifest":root/"manifest.json",
        "source_image":boundary.source_image,
        "camera":boundary.camera,
        "primary_mesh":boundary.primary_mesh,
        "primary_mesh_payload":boundary.primary_mesh_payload,
        "official_outputs_contract":boundary.official_outputs_contract,
        "output_index":boundary.output_index,
    }
    for key,path in boundary.optional.items():
        critical.setdefault(key,path)

    critical_rows={}
    for name,path in critical.items():
        path=Path(path).resolve()
        critical_rows[name]={
            "relative_path":_relative(root,path),
            "absolute_path":str(path),
            "bytes":path.stat().st_size,
            "sha256":sha256_file(path),
        }

    persisted=[]
    for dirname in _SCAN_ROOTS:
        folder=root/dirname
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            persisted.append({
                "relative_path":_relative(root,path),
                "bytes":path.stat().st_size,
            })

    root_level=[]
    for path in sorted(root.iterdir()):
        if path.is_file():
            root_level.append({
                "relative_path":path.name,
                "bytes":path.stat().st_size,
            })

    return {
        "schema":_SCHEMA,
        "status":"PASS",
        "source_p9_run_dir":str(root),
        "source_run_id":boundary.run_id,
        "scene_contract_id":boundary.scene_contract_id,
        "branch_mode":boundary.branch_mode,
        "p9_authority_policy":"REFERENCE_FULL_PERSISTED_RUN; DO_NOT_COPY_OR_REDUCE",
        "critical":critical_rows,
        "persisted_file_count":len(persisted)+len(root_level),
        "persisted_files":root_level+persisted,
        "scan_roots":list(_SCAN_ROOTS),
        "future_gate_policy":{
            "gate7_registration_fusion":"READ_REQUIRED_P9_EVIDENCE_FROM_SOURCE_RUN_DIR",
            "gate8_texture_recovery":"READ_SOURCE_OBSERVATION_UV_SEMANTIC_CONFIDENCE_WHERE_PERSISTED",
            "gate9_regression_maya":"PRESERVE_P9_MAYA_AND_EXPORT_SEPARATE_P10_REFINED_MAYA",
            "missing_dependency":"FAIL_CLOSED_BEFORE_PROMOTION",
        },
    }


def write_p9_dependency_inventory(run_dir: str | Path, output_path: str | Path) -> dict[str,Any]:
    payload=build_p9_dependency_inventory(run_dir)
    output=Path(output_path).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    payload["inventory_path"]=str(output)
    payload["inventory_sha256"]=sha256_file(output)
    return payload


def validate_p9_dependency_inventory(inventory_path: str | Path) -> dict[str,Any]:
    path=Path(inventory_path).resolve()
    if not path.is_file():
        raise ContractError(f"P9 dependency inventory is missing: {path}")
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read P9 dependency inventory {path}: {error}") from error
    if not isinstance(payload,dict) or payload.get("schema")!=_SCHEMA:
        raise ContractError("Unsupported P9 dependency inventory schema")

    boundary=validate_official_run(payload.get("source_p9_run_dir") or "")
    if str(payload.get("source_run_id") or "")!=boundary.run_id:
        raise ContractError("P9 dependency inventory run id no longer matches official run")
    if str(payload.get("scene_contract_id") or "")!=boundary.scene_contract_id:
        raise ContractError("P9 dependency inventory scene identity no longer matches official run")

    critical=payload.get("critical")
    if not isinstance(critical,dict) or not critical:
        raise ContractError("P9 dependency inventory has no critical file set")
    mismatches=[]
    for name,row in critical.items():
        if not isinstance(row,dict):
            mismatches.append(f"{name}:invalid_record")
            continue
        rel=str(row.get("relative_path") or "")
        candidate=(boundary.root/rel).resolve()
        try:
            candidate.relative_to(boundary.root.resolve())
        except ValueError:
            mismatches.append(f"{name}:unsafe_path")
            continue
        if not candidate.is_file():
            mismatches.append(f"{name}:missing")
            continue
        expected=str(row.get("sha256") or "").lower()
        actual=sha256_file(candidate)
        if expected!=actual:
            mismatches.append(f"{name}:sha256")

    if mismatches:
        raise ContractError(
            "Persisted P9 dependency evidence changed after Route Setup: "
            +", ".join(mismatches)
        )

    return {
        **payload,
        "status":"PASS",
        "inventory_path":str(path),
        "inventory_sha256":sha256_file(path),
        "critical_validation":"PASS",
    }
