from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

from .contracts import ContractError
from .colmap_dataset import prepare_known_camera_colmap_dataset
from .sparse_triangulation import run_sparse_triangulation
from .dense_reconstruction import run_dense_reconstruction
from .prefusion_mesh import run_prefusion_meshing


def standard_colmap_candidates(*, localappdata: str | None = None) -> tuple[Path, ...]:
    root=Path(localappdata or os.environ.get("LOCALAPPDATA") or "").expanduser()
    candidates=[]
    if str(root):
        base=root/"ConceptGhost"/"ThirdParty"/"COLMAP-4.2.0"
        candidates.extend((
            base/"COLMAP.bat",
            base/"colmap.bat",
            base/"bin"/"colmap.exe",
            base/"COLMAP-4.2.0"/"COLMAP.bat",
            base/"COLMAP-4.2.0"/"bin"/"colmap.exe",
        ))
    return tuple(candidates)


def resolve_colmap_executable(explicit: str | None = None) -> str:
    explicit=str(explicit or "").strip()
    if explicit:
        path=Path(explicit)
        if path.is_file():
            return str(path)
        resolved=shutil.which(explicit)
        if resolved:
            return resolved
        raise ContractError(f"COLMAP executable not found: {explicit}")

    env=str(os.environ.get("CONCEPTGHOST_COLMAP_EXE") or "").strip()
    if env:
        path=Path(env)
        if path.is_file():
            return str(path)

    for candidate in standard_colmap_candidates():
        if candidate.is_file():
            return str(candidate)

    resolved=shutil.which("colmap")
    if resolved:
        return resolved

    raise ContractError(
        "COLMAP runtime is not installed. Run the Gate 6 Complete Installer."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict:
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _stage_manifest(path: Path, *, require_status: bool=False) -> dict | None:
    if not path.is_file():
        return None
    payload=_read_json(path,path.name)
    if require_status and payload.get("status")!="PASS":
        return None
    return payload


def _validate_dataset_reuse(
    manifest: dict | None,
    *,
    wan_manifest_path: Path,
    camera_manifest_path: Path,
) -> tuple[bool, str]:
    if not manifest:
        return False, "MISSING_MANIFEST"
    if manifest.get("schema") != "ConceptGhost.P10KnownCameraColmapDataset.v0.2":
        return False, "STALE_DATASET_SCHEMA"
    source_inputs = manifest.get("source_inputs")
    if not isinstance(source_inputs, dict):
        return False, "MISSING_SOURCE_DIGESTS"
    expected_wan = _sha256_file(wan_manifest_path)
    expected_camera = _sha256_file(camera_manifest_path)
    if source_inputs.get("wan_manifest_sha256") != expected_wan:
        return False, "WAN_MANIFEST_CHANGED"
    if source_inputs.get("camera_manifest_sha256") != expected_camera:
        return False, "CAMERA_MANIFEST_CHANGED"
    if manifest.get("camera_image_mapping_policy") != "COMFY_COMMON_UPSCALE_CENTER_PIXEL_CENTER_AWARE":
        return False, "STALE_CAMERA_VIEWPORT_POLICY"
    if not manifest.get("frame_count"):
        return False, "EMPTY_DATASET"
    return True, "MATCHED_CONTEXT"


def _validate_mesh_reuse(dataset_root: Path, manifest: dict | None) -> bool:
    return bool(
        manifest
        and manifest.get("status")=="PASS"
        and (dataset_root/"dense"/"pre_fusion_mesh.ply").is_file()
    )


def run_reconstruction_pipeline(
    wan_manifest_path: str | Path,
    camera_manifest_path: str | Path,
    output_root: str | Path,
    *,
    colmap_executable: str | None = None,
    resume: bool = True,
) -> dict[str,object]:
    wan_manifest_path=Path(wan_manifest_path).resolve()
    camera_manifest_path=Path(camera_manifest_path).resolve()
    output_root=Path(output_root).resolve()

    wan=_read_json(wan_manifest_path,"WAN manifest")
    run_id=str(wan.get("run_id") or "").strip()
    if not run_id:
        raise ContractError("WAN manifest is missing run_id")

    if output_root.exists() and any(output_root.iterdir()) and not resume:
        raise ContractError(f"Refusing to overwrite non-empty Gate 6 output: {output_root}")
    output_root.mkdir(parents=True,exist_ok=True)

    dataset_root=output_root/"dataset"
    stages={}

    dataset_manifest_path=dataset_root/"dataset_manifest.json"
    dataset_manifest=_stage_manifest(dataset_manifest_path)
    dataset_reusable, dataset_reason = _validate_dataset_reuse(
        dataset_manifest,
        wan_manifest_path=wan_manifest_path,
        camera_manifest_path=camera_manifest_path,
    )
    if dataset_reusable:
        stages["dataset"]={
            "state":"REUSED",
            "reason":dataset_reason,
            "manifest_path":str(dataset_manifest_path),
        }
    else:
        had_existing_dataset=dataset_root.exists() and any(dataset_root.iterdir())
        prepare_known_camera_colmap_dataset(
            wan_manifest_path,
            camera_manifest_path,
            dataset_root,
            overwrite=had_existing_dataset,
        )
        stages["dataset"]={
            "state":"REBUILT_STALE_CONTEXT" if had_existing_dataset else "BUILT",
            "reason":dataset_reason,
            "manifest_path":str(dataset_manifest_path),
        }

    sparse_manifest_path=dataset_root/"sparse_triangulation_manifest.json"
    sparse_manifest=_stage_manifest(sparse_manifest_path,require_status=True)
    sparse_binary_ok=all(
        (dataset_root/"sparse"/"triangulated"/name).is_file()
        for name in ("cameras.bin","images.bin","points3D.bin")
    )
    if sparse_manifest and sparse_binary_ok:
        stages["sparse"]={"state":"REUSED","manifest_path":str(sparse_manifest_path)}
    else:
        executable=resolve_colmap_executable(colmap_executable)
        run_sparse_triangulation(
            dataset_root,
            colmap_executable=executable,
            overwrite_output=False,
        )
        stages["sparse"]={"state":"BUILT","manifest_path":str(sparse_manifest_path)}

    dense_manifest_path=dataset_root/"dense_reconstruction_manifest.json"
    dense_manifest=_stage_manifest(dense_manifest_path,require_status=True)
    if dense_manifest and (dataset_root/"dense"/"fused.ply").is_file():
        stages["dense"]={"state":"REUSED","manifest_path":str(dense_manifest_path)}
    else:
        executable=resolve_colmap_executable(colmap_executable)
        run_dense_reconstruction(
            dataset_root,
            colmap_executable=executable,
            overwrite_output=False,
        )
        stages["dense"]={"state":"BUILT","manifest_path":str(dense_manifest_path)}

    mesh_manifest_path=dataset_root/"prefusion_mesh_manifest.json"
    mesh_manifest=_stage_manifest(mesh_manifest_path,require_status=True)
    if _validate_mesh_reuse(dataset_root,mesh_manifest):
        stages["mesh"]={"state":"REUSED","manifest_path":str(mesh_manifest_path)}
    else:
        executable=resolve_colmap_executable(colmap_executable)
        run_prefusion_meshing(
            dataset_root,
            colmap_executable=executable,
            overwrite_output=False,
        )
        stages["mesh"]={"state":"BUILT","manifest_path":str(mesh_manifest_path)}

    final_mesh_manifest=_read_json(mesh_manifest_path,"pre-fusion mesh manifest")
    diagnostics={
        "schema":"ConceptGhost.P10ReconstructionRuntime.v0.1",
        "status":"PASS",
        "gate":6,
        "subgate":"6.6",
        "run_id":run_id,
        "wan_manifest_path":str(wan_manifest_path),
        "camera_manifest_path":str(camera_manifest_path),
        "output_root":str(output_root),
        "dataset_root":str(dataset_root),
        "pre_fusion_mesh_path":str((dataset_root/"dense"/"pre_fusion_mesh.ply").resolve()),
        "mesh_preview_svg_path":str((dataset_root/"dense"/"pre_fusion_mesh_preview.svg").resolve()),
        "stages":stages,
        "mesh_health":final_mesh_manifest.get("mesh_health"),
        "checkpoint_resume_enabled":bool(resume),
    }
    out=output_root/"reconstruction_runtime_manifest.json"
    out.write_text(json.dumps(diagnostics,indent=2,sort_keys=True),encoding="utf-8")
    diagnostics["runtime_manifest_path"]=str(out)
    return diagnostics
