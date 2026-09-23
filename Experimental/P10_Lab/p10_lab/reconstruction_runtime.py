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
from .p9_roundtrip_audit import run_p9_roundtrip_audit
from .reconstruction_overlay import build_metric_reconstruction_overlay
from .geometry_quality import write_gate6_geometry_quality


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


def _source_image_set_sha256_from_dataset_manifest(manifest: dict) -> str | None:
    frames=manifest.get("frames")
    if not isinstance(frames,list) or not frames:
        return None
    digest=hashlib.sha256()
    for frame in frames:
        if not isinstance(frame,dict):
            return None
        index=frame.get("global_frame_index")
        path_name=str(frame.get("path_name") or "")
        source_path=Path(str(frame.get("source_image_path") or ""))
        expected_hash=str(frame.get("source_image_sha256") or "").strip().lower()
        if type(index) is not int or not path_name or not source_path.is_file() or not expected_hash:
            return None
        actual_hash=_sha256_file(source_path)
        if actual_hash!=expected_hash:
            return "MISMATCH"
        digest.update(
            f"{index}\0{path_name}\0{actual_hash}\n".encode("utf-8")
        )
    return digest.hexdigest()


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
    expected_image_set=str(source_inputs.get("source_image_set_sha256") or "").strip().lower()
    actual_image_set=_source_image_set_sha256_from_dataset_manifest(manifest)
    if not expected_image_set:
        return False, "MISSING_SOURCE_IMAGE_HASHES"
    if actual_image_set=="MISMATCH":
        return False, "SOURCE_COMPOSITE_IMAGE_CHANGED"
    if actual_image_set is None:
        return False, "SOURCE_COMPOSITE_IMAGE_MISSING"
    if actual_image_set!=expected_image_set:
        return False, "SOURCE_IMAGE_SET_CHANGED"
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
    p9_roundtrip_audit_enabled: bool = True,
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

    p9_roundtrip=None
    if p9_roundtrip_audit_enabled:
        control_manifest_value=str(wan.get("source_control_manifest") or "").strip()
        if control_manifest_value:
            audit_root=output_root/"p9_roundtrip"
            try:
                p9_roundtrip=run_p9_roundtrip_audit(
                    control_manifest_value,
                    camera_manifest_path,
                    audit_root,
                    colmap_executable=colmap_executable,
                    resume=bool(resume),
                )
                stages["p9_roundtrip_audit"]={
                    "state":p9_roundtrip.get("execution_state","BUILT"),
                    "runtime_status":p9_roundtrip.get("runtime_status"),
                    "quality_status":p9_roundtrip.get("quality_status"),
                    "manifest_path":p9_roundtrip.get("audit_manifest_path"),
                }
            except Exception as error:
                audit_root.mkdir(parents=True,exist_ok=True)
                failure={
                    "schema":"ConceptGhost.P10P9RoundtripAudit.v0.1",
                    "runtime_status":"FAIL",
                    "quality_status":"FAIL",
                    "alerts":["P9_ONLY_ROUNDTRIP_RUNTIME_FAILURE"],
                    "error":f"{type(error).__name__}: {error}",
                    "purpose":"ISOLATE_P10_CAMERA_AND_COLMAP_FROM_WAN_GENERATION",
                    "p9_authority_changed":False,
                    "source_control_manifest":control_manifest_value,
                    "camera_manifest_path":str(camera_manifest_path),
                }
                failure_path=audit_root/"p9_roundtrip_audit.json"
                failure_path.write_text(
                    json.dumps(failure,indent=2,sort_keys=True),
                    encoding="utf-8",
                )
                failure["audit_manifest_path"]=str(failure_path)
                p9_roundtrip=failure
                stages["p9_roundtrip_audit"]={
                    "state":"FAILED_DIAGNOSTIC",
                    "runtime_status":"FAIL",
                    "quality_status":"FAIL",
                    "manifest_path":str(failure_path),
                }
        else:
            p9_roundtrip={
                "schema":"ConceptGhost.P10P9RoundtripAudit.v0.1",
                "runtime_status":"SKIPPED",
                "quality_status":"WARN",
                "alerts":["SOURCE_CONTROL_MANIFEST_MISSING"],
                "p9_authority_changed":False,
            }
            stages["p9_roundtrip_audit"]={
                "state":"SKIPPED",
                "runtime_status":"SKIPPED",
                "quality_status":"WARN",
            }

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

    metric_overlay=None
    source_p9_run_dir=str(wan.get("source_p9_run_dir") or "").strip()
    if source_p9_run_dir:
        overlay_root=output_root/"diagnostics"
        overlay_path=overlay_root/"p9_p10_metric_overlay.png"
        try:
            metric_overlay=build_metric_reconstruction_overlay(
                source_p9_run_dir,
                camera_manifest_path,
                dataset_root,
                overlay_path,
            )
            stages["metric_overlay"]={
                "state":"BUILT",
                "status":metric_overlay.get("status"),
                "manifest_path":metric_overlay.get("manifest_path"),
                "preview_png_path":metric_overlay.get("preview_png_path"),
            }
        except Exception as error:
            overlay_root.mkdir(parents=True,exist_ok=True)
            metric_overlay={
                "schema":"ConceptGhost.P10MetricReconstructionOverlay.v0.1",
                "status":"WARN",
                "alerts":["METRIC_OVERLAY_RENDER_FAILED"],
                "error":f"{type(error).__name__}: {error}",
                "p9_authority_changed":False,
                "source_p9_run_dir":source_p9_run_dir,
            }
            stages["metric_overlay"]={
                "state":"FAILED_DIAGNOSTIC",
                "status":"WARN",
                "error":metric_overlay["error"],
            }
    else:
        metric_overlay={
            "schema":"ConceptGhost.P10MetricReconstructionOverlay.v0.1",
            "status":"WARN",
            "alerts":["SOURCE_P9_RUN_DIR_MISSING"],
            "p9_authority_changed":False,
        }
        stages["metric_overlay"]={
            "state":"SKIPPED",
            "status":"WARN",
        }

    geometry_quality=write_gate6_geometry_quality(
        dataset_root,
        output_root/"diagnostics"/"gate6_geometry_quality.json",
        expected_missions=tuple(str(name) for name in (wan.get("mission_order") or [])),
        p9_roundtrip=p9_roundtrip if isinstance(p9_roundtrip,dict) else None,
        metric_overlay=metric_overlay if isinstance(metric_overlay,dict) else None,
    )
    stages["geometry_quality"]={
        "state":"EVALUATED",
        "status":geometry_quality.get("status"),
        "manifest_path":geometry_quality.get("manifest_path"),
        "alerts":geometry_quality.get("alerts",[]),
    }

    diagnostics={
        "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
        "status":geometry_quality.get("status","FAIL"),
        "runtime_status":"PASS",
        "geometry_quality_status":geometry_quality.get("status","FAIL"),
        "gate":6,
        "subgate":"6.6",
        "run_id":run_id,
        "p10_attempt_id":wan.get("p10_attempt_id"),
        "p10_attempt_root":wan.get("p10_attempt_root"),
        "wan_manifest_path":str(wan_manifest_path),
        "camera_manifest_path":str(camera_manifest_path),
        "route_authority":wan.get("route_authority"),
        "route_plan_sha256":wan.get("route_plan_sha256"),
        "mission_order":wan.get("mission_order"),
        "output_root":str(output_root),
        "dataset_root":str(dataset_root),
        "pre_fusion_mesh_path":str((dataset_root/"dense"/"pre_fusion_mesh.ply").resolve()),
        "mesh_preview_svg_path":str((dataset_root/"dense"/"pre_fusion_mesh_preview.svg").resolve()),
        "stages":stages,
        "mesh_health":final_mesh_manifest.get("mesh_health"),
        "verified_sparse_component_count":final_mesh_manifest.get("verified_sparse_component_count"),
        "mission_contribution":final_mesh_manifest.get("mission_contribution",[]),
        "sparse_quality_status":final_mesh_manifest.get("sparse_quality_status"),
        "p9_roundtrip_audit":p9_roundtrip,
        "p9_roundtrip_audit_enabled":bool(p9_roundtrip_audit_enabled),
        "metric_overlay":metric_overlay,
        "metric_overlay_preview_png_path":(
            metric_overlay.get("preview_png_path")
            if isinstance(metric_overlay,dict) else None
        ),
        "geometry_quality":geometry_quality,
        "geometry_quality_manifest_path":geometry_quality.get("manifest_path"),
        "gate7_promotion_allowed":geometry_quality.get("status")!="FAIL",
        "checkpoint_resume_enabled":bool(resume),
    }
    out=output_root/"reconstruction_runtime_manifest.json"
    out.write_text(json.dumps(diagnostics,indent=2,sort_keys=True),encoding="utf-8")
    diagnostics["runtime_manifest_path"]=str(out)

    attempt_root_value=str(wan.get("p10_attempt_root") or "").strip()
    attempt_id=str(wan.get("p10_attempt_id") or "").strip()
    if attempt_root_value and attempt_id:
        attempt_root=Path(attempt_root_value).resolve()
        attempt_manifest_path=attempt_root/"attempt_manifest.json"
        if attempt_manifest_path.is_file():
            attempt_manifest=_read_json(attempt_manifest_path,"P10 attempt manifest")
            if str(attempt_manifest.get("p10_attempt_id") or "")!=attempt_id:
                raise ContractError("P10 attempt manifest identity mismatch at Gate 6 closeout")
            from datetime import datetime, timezone
            attempt_manifest.update({
                "status":(
                    "COMPLETE_GEOMETRY_FAIL"
                    if geometry_quality.get("status")=="FAIL"
                    else "COMPLETE"
                ),
                "completed_at_utc":datetime.now(timezone.utc).isoformat(),
                "runtime_status":"PASS",
                "geometry_quality_status":geometry_quality.get("status"),
                "geometry_quality_manifest_path":geometry_quality.get("manifest_path"),
                "gate6_runtime_manifest_path":str(out),
                "pre_fusion_mesh_path":diagnostics["pre_fusion_mesh_path"],
            })
            attempt_manifest_path.write_text(
                json.dumps(attempt_manifest,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            diagnostics["attempt_manifest_path"]=str(attempt_manifest_path)

    out.write_text(json.dumps(diagnostics,indent=2,sort_keys=True),encoding="utf-8")
    return diagnostics
