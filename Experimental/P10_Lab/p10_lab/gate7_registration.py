from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .p9_boundary import validate_official_run


_SCHEMA = "ConceptGhost.P10Gate7Registration.v0.1"
_IDENTITY_4X4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object: {path}")
    return payload


def _require_nonempty(value: Any, label: str) -> str:
    rendered = str(value or "").strip()
    if not rendered:
        raise ContractError(f"{label} is required")
    return rendered


def _same_path(a: str | Path, b: str | Path) -> bool:
    return Path(a).resolve() == Path(b).resolve()


def build_gate7_registration(
    p9_run_dir: str | Path,
    reconstruction_runtime_manifest_path: str | Path,
) -> dict[str, Any]:
    """Validate Gate 6 output and bind it to the authoritative P9 world.

    Current Gate 6 uses fixed P9-derived known cameras. Therefore P10 geometry is
    already reconstructed in the P9 canonical world; Gate 7.1 must validate that
    invariant rather than estimate a new Sim(3) transform that could move P9.
    """

    boundary = validate_official_run(p9_run_dir)
    runtime_path = Path(reconstruction_runtime_manifest_path).resolve()
    runtime = _read_json(runtime_path, "Gate 6 reconstruction runtime manifest")

    if str(runtime.get("runtime_status") or "").upper() != "PASS":
        raise ContractError("Gate 7.1 requires Gate 6 runtime_status PASS")
    quality = str(runtime.get("geometry_quality_status") or "").upper()
    if quality == "FAIL":
        raise ContractError("Gate 7.1 refuses Gate 6 geometry_quality_status FAIL")
    if runtime.get("gate7_promotion_allowed") is not True:
        raise ContractError("Gate 7.1 requires gate7_promotion_allowed=true")

    wan_path = Path(_require_nonempty(runtime.get("wan_manifest_path"), "wan_manifest_path")).resolve()
    wan = _read_json(wan_path, "Gate 5 WAN manifest")

    source_p9_run_dir = Path(
        _require_nonempty(wan.get("source_p9_run_dir"), "WAN source_p9_run_dir")
    ).resolve()
    if not _same_path(source_p9_run_dir, boundary.root):
        raise ContractError("Gate 7.1 WAN source_p9_run_dir does not match authoritative P9 run")
    if str(wan.get("source_run_id") or "") != boundary.run_id:
        raise ContractError("Gate 7.1 WAN source_run_id does not match authoritative P9 run")
    if str(wan.get("scene_contract_id") or "") != boundary.scene_contract_id:
        raise ContractError("Gate 7.1 WAN scene_contract_id does not match authoritative P9 run")

    dataset_root = Path(_require_nonempty(runtime.get("dataset_root"), "dataset_root")).resolve()
    dataset_manifest_path = dataset_root / "dataset_manifest.json"
    dataset = _read_json(dataset_manifest_path, "Gate 6 known-camera dataset manifest")

    if dataset.get("reconstruction_strategy") != "KNOWN_CAMERA_COLMAP_PRIMARY":
        raise ContractError("Gate 7.1 requires known-camera COLMAP primary reconstruction")
    if dataset.get("camera_authority") != "P9_BASELINE_WORLD_DERIVED":
        raise ContractError("Gate 7.1 requires P9-derived camera authority")
    if str(dataset.get("scene_contract_id") or "") != boundary.scene_contract_id:
        raise ContractError("Gate 7.1 dataset scene_contract_id mismatch")

    conversion = dataset.get("coordinate_conversion")
    if not isinstance(conversion, dict):
        raise ContractError("Gate 7.1 dataset coordinate_conversion is missing")
    if conversion.get("source") != "CONCEPTGHOST_MAYA_CAMERA_C2W_XRIGHT_YUP_MINUSZ_FORWARD":
        raise ContractError("Gate 7.1 dataset source coordinate convention mismatch")
    if conversion.get("target") != "COLMAP_W2C_XRIGHT_YDOWN_ZFORWARD":
        raise ContractError("Gate 7.1 dataset target coordinate convention mismatch")
    if conversion.get("axis_transform") != "diag(1,-1,-1)":
        raise ContractError("Gate 7.1 dataset axis transform mismatch")

    mesh_path = Path(
        _require_nonempty(runtime.get("pre_fusion_mesh_path"), "pre_fusion_mesh_path")
    ).resolve()
    if not mesh_path.is_file():
        raise ContractError(f"Gate 7.1 pre-fusion mesh is missing: {mesh_path}")

    attempt_id = _require_nonempty(
        runtime.get("p10_attempt_id") or wan.get("p10_attempt_id"),
        "p10_attempt_id",
    )
    attempt_root = Path(
        _require_nonempty(
            runtime.get("p10_attempt_root") or wan.get("p10_attempt_root"),
            "p10_attempt_root",
        )
    ).resolve()
    route_hash = _require_nonempty(
        runtime.get("route_plan_sha256") or wan.get("route_plan_sha256"),
        "route_plan_sha256",
    ).lower()
    if len(route_hash) != 64 or any(ch not in "0123456789abcdef" for ch in route_hash):
        raise ContractError("Gate 7.1 route_plan_sha256 is invalid")

    return {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.1",
        "registration_policy": "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
        "registration_solver": "NOT_RUN_BY_DESIGN",
        "registration_reason": (
            "Gate 6 reconstructs with fixed P9-derived camera poses; P10 geometry "
            "is already expressed in the authoritative P9 world. Gate 7.1 validates "
            "that provenance instead of estimating a transform that could move P9."
        ),
        "coordinate_space": "P9_CANONICAL_WORLD_METERS",
        "p9_authority": "P9_ACCEPTED_IMMUTABLE_UPSTREAM",
        "p9_authority_changed": False,
        "p9_run_dir": str(boundary.root),
        "p9_run_id": boundary.run_id,
        "scene_contract_id": boundary.scene_contract_id,
        "p10_attempt_id": attempt_id,
        "p10_attempt_root": str(attempt_root),
        "route_plan_sha256": route_hash,
        "gate6_runtime_manifest_path": str(runtime_path),
        "wan_manifest_path": str(wan_path),
        "dataset_manifest_path": str(dataset_manifest_path),
        "pre_fusion_mesh_path": str(mesh_path),
        "gate6_geometry_quality_status": quality,
        "transform_p10_to_p9": [list(row) for row in _IDENTITY_4X4],
        "scale": 1.0,
        "translation_m": [0.0, 0.0, 0.0],
        "rotation_policy": "IDENTITY_NO_REORIENTATION",
        "sim3_refit_allowed": False,
        "ready_for_gate7_2": True,
    }


def write_gate7_registration(
    p9_run_dir: str | Path,
    reconstruction_runtime_manifest_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    result = build_gate7_registration(
        p9_run_dir,
        reconstruction_runtime_manifest_path,
    )
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result["manifest_path"] = str(output_path)
    return result
