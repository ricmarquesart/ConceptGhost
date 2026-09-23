from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from .contracts import ContractError
from .colmap_dataset import (
    _camera_key,
    _fmt,
    _sha256_file,
    world_matrix_to_colmap_pose,
)
from .dense_reconstruction import run_dense_reconstruction
from .p9_boundary import validate_official_run
from .prefusion_mesh import run_prefusion_meshing
from .sparse_triangulation import run_sparse_triangulation
from .wan_sequence import read_control_manifest
from .reconstruction_overlay import build_metric_reconstruction_overlay


_SCHEMA = "ConceptGhost.P10P9RoundtripDataset.v0.1"
_AUDIT_SCHEMA = "ConceptGhost.P10P9RoundtripAudit.v0.1"


def _read_json(path: str | Path, label: str) -> tuple[Path, dict]:
    path=Path(path).resolve()
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must contain a JSON object")
    return path,payload


def _ordered_frame_set_sha256(records: list[dict]) -> str:
    digest=hashlib.sha256()
    for record in records:
        digest.update(
            (
                f'{record["global_frame_index"]}\0'
                f'{record["path_name"]}\0'
                f'{record["source_image_sha256"]}\n'
            ).encode("utf-8")
        )
    return digest.hexdigest()


def prepare_p9_roundtrip_colmap_dataset(
    control_manifest_path: str | Path,
    camera_manifest_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool=False,
) -> dict[str,object]:
    """Build a known-camera COLMAP dataset from Gate-4 P9-only control renders.

    No WAN/generated pixels enter this dataset. Its only purpose is to audit the
    exact camera/intrinsic/viewport/COLMAP path independently from generation.
    P9 itself remains immutable authority and is never modified by this stage.
    """

    control_path,control,missions=read_control_manifest(control_manifest_path)
    camera_path,cameras=_read_json(camera_manifest_path,"camera manifest")
    output_dir=Path(output_dir).resolve()

    if output_dir.exists() and any(output_dir.iterdir()):
        if not overwrite:
            raise ContractError(
                f"Refusing to overwrite non-empty P9 round-trip dataset: {output_dir}"
            )
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)

    scene_contract_id=str(control.get("scene_contract_id") or "").strip()
    source_run_id=str(control.get("source_run_id") or "").strip()
    if not scene_contract_id or not source_run_id:
        raise ContractError("P9 round-trip control manifest requires scene/run identity")
    if str(cameras.get("scene_contract_id") or "").strip()!=scene_contract_id:
        raise ContractError("P9 round-trip camera/control scene contract mismatch")
    if str(cameras.get("source_run_id") or "").strip()!=source_run_id:
        raise ContractError("P9 round-trip camera/control source run mismatch")

    control_route_hash=control.get("route_plan_sha256")
    camera_route_hash=cameras.get("route_plan_sha256")
    if control_route_hash!=camera_route_hash:
        raise ContractError("P9 round-trip camera/control route hash mismatch")
    if control.get("route_authority")!=cameras.get("route_authority"):
        raise ContractError("P9 round-trip camera/control route authority mismatch")

    control_frames=control.get("frames")
    camera_frames=cameras.get("frames")
    if not isinstance(control_frames,list) or not control_frames:
        raise ContractError("P9 round-trip requires non-empty control frames")
    if not isinstance(camera_frames,list) or len(camera_frames)!=len(control_frames):
        raise ContractError("P9 round-trip camera/control frame counts differ")

    source_p9_run_dir=str(
        control.get("source_p9_run_dir")
        or cameras.get("source_p9_run_dir")
        or ""
    ).strip()
    if (
        control.get("source_p9_run_dir")
        and cameras.get("source_p9_run_dir")
        and Path(str(control["source_p9_run_dir"])).resolve()
            !=Path(str(cameras["source_p9_run_dir"])).resolve()
    ):
        raise ContractError("P9 round-trip camera/control P9 run directories differ")

    p9_boundary=None
    if source_p9_run_dir:
        p9_boundary=validate_official_run(source_p9_run_dir)
        if p9_boundary.run_id!=source_run_id:
            raise ContractError("P9 round-trip source P9 run_id mismatch")
        if p9_boundary.scene_contract_id!=scene_contract_id:
            raise ContractError("P9 round-trip source P9 scene contract mismatch")

    camera_by_index={}
    for record in camera_frames:
        if not isinstance(record,dict):
            raise ContractError("P9 round-trip camera frame must be an object")
        index=record.get("global_frame_index")
        if type(index) is not int or index<0 or index in camera_by_index:
            raise ContractError("P9 round-trip camera global indexes must be unique integers")
        camera_by_index[index]=record

    images_dir=output_dir/"images"
    known_dir=output_dir/"sparse"/"known"
    images_dir.mkdir(parents=True,exist_ok=True)
    known_dir.mkdir(parents=True,exist_ok=True)

    camera_id_by_key={}
    camera_rows=[]
    image_rows=[]
    records=[]

    for image_id,frame in enumerate(control_frames,start=1):
        if not isinstance(frame,dict):
            raise ContractError("P9 round-trip control frame must be an object")
        global_index=frame.get("global_frame_index")
        if type(global_index) is not int or global_index!=image_id-1:
            raise ContractError("P9 round-trip control indexes must be contiguous from zero")
        path_name=str(frame.get("path_name") or "").strip()
        if not path_name:
            raise ContractError("P9 round-trip frame path_name cannot be empty")

        camera_record=camera_by_index.get(global_index)
        if camera_record is None:
            raise ContractError(f"Missing P9 round-trip camera frame {global_index}")
        if str(camera_record.get("path_name") or "")!=path_name:
            raise ContractError(f"P9 round-trip path mismatch at frame {global_index}")
        camera=camera_record.get("camera")
        if not isinstance(camera,dict) or camera.get("model")!="PINHOLE":
            raise ContractError(f"P9 round-trip frame {global_index} requires PINHOLE camera")

        frame_file=str(frame.get("frame_file") or "").strip()
        if not frame_file:
            raise ContractError(f"P9 round-trip control frame {global_index} is missing frame_file")
        source_image=(control_path.parent/frame_file).resolve()
        if not source_image.is_file():
            raise ContractError(f"Missing P9-only control frame: {source_image}")

        suffix=source_image.suffix.lower() or ".png"
        image_name=f"frame_{global_index:06d}{suffix}"
        destination=images_dir/image_name
        shutil.copy2(source_image,destination)

        key=_camera_key(camera)
        camera_id=camera_id_by_key.get(key)
        if camera_id is None:
            camera_id=len(camera_id_by_key)+1
            camera_id_by_key[key]=camera_id
            width,height,fx,fy,cx,cy=key
            camera_rows.append(
                f"{camera_id} PINHOLE {width} {height} "
                f"{_fmt(fx)} {_fmt(fy)} {_fmt(cx)} {_fmt(cy)}"
            )

        qvec,tvec=world_matrix_to_colmap_pose(camera["world_matrix"])
        pose_numbers=" ".join(_fmt(value) for value in (*qvec,*tvec))
        image_rows.append(
            f"{image_id} {pose_numbers} {camera_id} {image_name}\n"
        )

        records.append({
            "image_id":image_id,
            "camera_id":camera_id,
            "global_frame_index":global_index,
            "path_name":path_name,
            "path_frame_index":frame.get("path_frame_index"),
            "image_name":image_name,
            "source_image_path":str(source_image),
            "source_image_sha256":_sha256_file(source_image),
            "materialized_image_path":str(destination),
            "image_provenance":"P9_ONLY_GATE4_CONTROL_FRAME_NO_WAN",
            "camera_authority":"P9_BASELINE_WORLD_DERIVED",
            "qvec":list(qvec),
            "tvec":list(tvec),
        })

    declared_order=control.get("mission_order")
    derived_order=[mission.mission_name for mission in missions]
    if declared_order is not None and declared_order!=derived_order:
        raise ContractError("P9 round-trip mission order mismatch")

    (known_dir/"cameras.txt").write_text(
        "# Camera list with one line of data per camera:\n"
        "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
        f"# Number of cameras: {len(camera_rows)}\n"
        +"\n".join(camera_rows)+"\n",
        encoding="utf-8",
    )
    (known_dir/"images.txt").write_text(
        "# Image list with two lines of data per image:\n"
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n"
        "#   POINTS2D[] as (X, Y, POINT3D_ID)\n"
        f"# Number of images: {len(image_rows)}\n"
        +"".join(row+"\n" for row in image_rows),
        encoding="utf-8",
    )
    (known_dir/"points3D.txt").write_text(
        "# 3D point list with one line of data per point:\n"
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n"
        "# Number of points: 0\n",
        encoding="utf-8",
    )

    manifest={
        "schema":_SCHEMA,
        "audit_role":"P9_ONLY_CAMERA_RECONSTRUCTION_ROUNDTRIP",
        "run_id":source_run_id,
        "source_run_id":source_run_id,
        "source_p9_run_dir":source_p9_run_dir or None,
        "scene_contract_id":scene_contract_id,
        "frame_count":len(records),
        "camera_count":len(camera_rows),
        # Sparse/dense helpers intentionally reuse the proven known-camera path.
        "reconstruction_strategy":"KNOWN_CAMERA_COLMAP_PRIMARY",
        "camera_authority":"P9_BASELINE_WORLD_DERIVED",
        "image_authority":"P9_ONLY_GATE4_CONTROL_FRAME_NO_WAN",
        "generation_authority":"NONE",
        "wan_pixels_present":False,
        "route_authority":control.get("route_authority"),
        "route_plan_sha256":control_route_hash,
        "mission_order":derived_order,
        "mission_modes":{
            str(item.get("name")):item.get("mode")
            for item in control.get("missions",[])
            if isinstance(item,dict)
        },
        "coordinate_conversion":{
            "source":"CONCEPTGHOST_MAYA_CAMERA_C2W_XRIGHT_YUP_MINUSZ_FORWARD",
            "target":"COLMAP_W2C_XRIGHT_YDOWN_ZFORWARD",
            "axis_transform":"diag(1,-1,-1)",
        },
        "source_inputs":{
            "control_manifest_path":str(control_path),
            "control_manifest_sha256":_sha256_file(control_path),
            "camera_manifest_path":str(camera_path),
            "camera_manifest_sha256":_sha256_file(camera_path),
            "source_image_set_sha256":_ordered_frame_set_sha256(records),
        },
        "images_dir":str(images_dir),
        "known_sparse_model_dir":str(known_dir),
        "p9_primary_mesh_path":(
            str(p9_boundary.primary_mesh) if p9_boundary is not None else None
        ),
        "frames":records,
    }
    manifest_path=output_dir/"dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    return manifest


def _audit_reusable(
    manifest: dict | None,
    *,
    control_manifest_path: Path,
    camera_manifest_path: Path,
    output_root: Path,
) -> bool:
    if not isinstance(manifest,dict) or manifest.get("schema")!=_AUDIT_SCHEMA:
        return False
    inputs=manifest.get("source_inputs")
    if not isinstance(inputs,dict):
        return False
    if inputs.get("control_manifest_sha256")!=_sha256_file(control_manifest_path):
        return False
    if inputs.get("camera_manifest_sha256")!=_sha256_file(camera_manifest_path):
        return False
    return (
        manifest.get("runtime_status")=="PASS"
        and (output_root/"dataset"/"dense"/"fused.ply").is_file()
        and (output_root/"dataset"/"dense"/"pre_fusion_mesh.ply").is_file()
    )


def run_p9_roundtrip_audit(
    control_manifest_path: str | Path,
    camera_manifest_path: str | Path,
    output_root: str | Path,
    *,
    colmap_executable: str | None=None,
    resume: bool=True,
) -> dict[str,object]:
    """Execute the P9-only known-camera reconstruction audit.

    This stage never changes P9 authority. A failure is diagnostic evidence for
    camera/intrinsic/reconstruction plumbing and can be surfaced by Gate 6/B6.
    """

    control_manifest_path=Path(control_manifest_path).resolve()
    camera_manifest_path=Path(camera_manifest_path).resolve()
    output_root=Path(output_root).resolve()
    output_root.mkdir(parents=True,exist_ok=True)
    audit_path=output_root/"p9_roundtrip_audit.json"

    previous=None
    if audit_path.is_file():
        try:
            candidate=json.loads(audit_path.read_text(encoding="utf-8"))
            if isinstance(candidate,dict):
                previous=candidate
        except (OSError,json.JSONDecodeError):
            previous=None
    if resume and _audit_reusable(
        previous,
        control_manifest_path=control_manifest_path,
        camera_manifest_path=camera_manifest_path,
        output_root=output_root,
    ):
        result=dict(previous)
        result["execution_state"]="REUSED"
        return result

    dataset_root=output_root/"dataset"
    prepare_p9_roundtrip_colmap_dataset(
        control_manifest_path,
        camera_manifest_path,
        dataset_root,
        overwrite=dataset_root.exists() and any(dataset_root.iterdir()),
    )

    # Local import avoids making reconstruction_runtime <-> audit imports cyclic.
    from .reconstruction_runtime import resolve_colmap_executable
    executable=resolve_colmap_executable(colmap_executable)

    sparse=run_sparse_triangulation(
        dataset_root,
        colmap_executable=executable,
        overwrite_output=False,
    )
    dense=run_dense_reconstruction(
        dataset_root,
        colmap_executable=executable,
        overwrite_output=False,
    )
    mesh=run_prefusion_meshing(
        dataset_root,
        colmap_executable=executable,
        overwrite_output=False,
    )
    dataset=json.loads((dataset_root/"dataset_manifest.json").read_text(encoding="utf-8"))

    metric_overlay=None
    source_p9_run_dir=str(dataset.get("source_p9_run_dir") or "").strip()
    if source_p9_run_dir:
        overlay_path=output_root/"p9_roundtrip_metric_overlay.png"
        try:
            metric_overlay=build_metric_reconstruction_overlay(
                source_p9_run_dir,
                camera_manifest_path,
                dataset_root,
                overlay_path,
            )
        except Exception as error:
            metric_overlay={
                "schema":"ConceptGhost.P10MetricReconstructionOverlay.v0.1",
                "status":"WARN",
                "alerts":["P9_ROUNDTRIP_METRIC_OVERLAY_RENDER_FAILED"],
                "error":f"{type(error).__name__}: {error}",
                "p9_authority_changed":False,
            }
    else:
        metric_overlay={
            "schema":"ConceptGhost.P10MetricReconstructionOverlay.v0.1",
            "status":"WARN",
            "alerts":["SOURCE_P9_RUN_DIR_MISSING"],
            "p9_authority_changed":False,
        }

    sparse_points=int(sparse.get("sparse_point_count") or 0)
    dense_points=int((dense.get("fused_cloud") or {}).get("vertex_count") or 0)
    mesh_health=mesh.get("mesh_health") or {}
    quality_status="PASS"
    alerts=[]
    if sparse_points<=0:
        quality_status="FAIL"
        alerts.append("NO_SPARSE_POINTS")
    if dense_points<=0:
        quality_status="FAIL"
        alerts.append("NO_DENSE_POINTS")
    if mesh_health.get("health_status")=="WARN" and quality_status=="PASS":
        quality_status="WARN"
        alerts.extend(str(value) for value in mesh_health.get("warnings") or ())

    result={
        "schema":_AUDIT_SCHEMA,
        "runtime_status":"PASS",
        "quality_status":quality_status,
        "alerts":alerts,
        "execution_state":"BUILT",
        "purpose":"ISOLATE_P10_CAMERA_AND_COLMAP_FROM_WAN_GENERATION",
        "p9_authority_changed":False,
        "scene_contract_id":dataset.get("scene_contract_id"),
        "source_run_id":dataset.get("source_run_id"),
        "source_p9_run_dir":dataset.get("source_p9_run_dir"),
        "route_plan_sha256":dataset.get("route_plan_sha256"),
        "mission_order":dataset.get("mission_order"),
        "frame_count":dataset.get("frame_count"),
        "source_inputs":dataset.get("source_inputs"),
        "dataset_manifest_path":str((dataset_root/"dataset_manifest.json").resolve()),
        "sparse_manifest_path":str((dataset_root/"sparse_triangulation_manifest.json").resolve()),
        "dense_manifest_path":str((dataset_root/"dense_reconstruction_manifest.json").resolve()),
        "prefusion_manifest_path":str((dataset_root/"prefusion_mesh_manifest.json").resolve()),
        "sparse_point_count":sparse_points,
        "dense_point_count":dense_points,
        "mesh_health":mesh_health,
        "dense_preview_path":(dense.get("fused_cloud") or {}).get("preview_path"),
        "prefusion_preview_path":mesh_health.get("preview_path"),
        "metric_overlay":metric_overlay,
        "metric_overlay_preview_png_path":(
            metric_overlay.get("preview_png_path")
            if isinstance(metric_overlay,dict) else None
        ),
    }
    audit_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    result["audit_manifest_path"]=str(audit_path)
    return result
