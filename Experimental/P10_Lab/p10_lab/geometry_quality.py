from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError


_SCHEMA="ConceptGhost.P10Gate6GeometryQuality.v0.1"
_RANK={"PASS":0,"WARN":1,"FAIL":2}


def _status_max(current: str, candidate: str) -> str:
    return candidate if _RANK[candidate] > _RANK[current] else current


def _read_json(path: str | Path, label: str) -> dict:
    path=Path(path)
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError,ValueError):
        return int(default)


def evaluate_gate6_geometry_quality(
    dataset_root: str | Path,
    *,
    expected_missions: list[str] | tuple[str,...] = (),
    p9_roundtrip: dict | None = None,
    metric_overlay: dict | None = None,
) -> dict[str,object]:
    """Classify Gate-6 geometry independently from runtime/file-existence PASS.

    The policy is intentionally conservative:
    - P9 is immutable authority and is never classified as a defect here.
    - zero/invalid reconstruction evidence is FAIL;
    - partial mission/frame contribution and fragmentation are WARN unless the
      reconstruction has no usable geometry at all;
    - P10->P9 distance is descriptive because unseen surfaces may legitimately
      lie away from the observed P9 shell.
    """

    dataset_root=Path(dataset_root).resolve()
    sparse=_read_json(dataset_root/"sparse_triangulation_manifest.json","sparse manifest")
    dense=_read_json(dataset_root/"dense_reconstruction_manifest.json","dense manifest")
    mesh=_read_json(dataset_root/"prefusion_mesh_manifest.json","pre-fusion manifest")

    expected=[str(name) for name in expected_missions if str(name).strip()]
    contribution=sparse.get("mission_contribution")
    if not isinstance(contribution,list):
        contribution=[]

    by_name={
        str(item.get("mission_name") or item.get("name") or ""):item
        for item in contribution
        if isinstance(item,dict) and str(item.get("mission_name") or item.get("name") or "").strip()
    }
    mission_rows=[]
    total_dataset=0
    total_selected=0
    total_dropped=0
    contributing=0
    for name in expected or list(by_name):
        item=by_name.get(name,{})
        dataset_frames=_int(item.get("dataset_frame_count",item.get("frame_count",0)))
        selected=_int(item.get("selected_frame_count",item.get("selected_image_count",0)))
        dropped=_int(item.get("dropped_frame_count",max(0,dataset_frames-selected)))
        contributes=bool(item.get("contributes_to_sparse"))
        total_dataset+=dataset_frames
        total_selected+=selected
        total_dropped+=dropped
        contributing+=1 if contributes else 0
        mission_rows.append({
            "mission_name":name,
            "dataset_frame_count":dataset_frames,
            "selected_frame_count":selected,
            "dropped_frame_count":dropped,
            "contributes_to_sparse":contributes,
            "component_indices":item.get("component_indices",[]),
        })

    sparse_points=_int(sparse.get("sparse_point_count"))
    component_count=_int(sparse.get("verified_component_count"))
    dense_cloud=dense.get("fused_cloud") if isinstance(dense.get("fused_cloud"),dict) else {}
    dense_points=_int(dense_cloud.get("vertex_count"))
    depth_maps=_int(dense.get("depth_map_file_count"))
    normal_maps=_int(dense.get("normal_map_file_count"))
    mesh_health=mesh.get("mesh_health") if isinstance(mesh.get("mesh_health"),dict) else {}
    mesh_vertices=_int(mesh_health.get("vertex_count"))
    mesh_faces=_int(mesh_health.get("face_count"))
    invalid_faces=_int(mesh_health.get("invalid_face_index_count"))
    degenerate_fraction=float(mesh_health.get("degenerate_face_sample_fraction") or 0.0)
    mesh_components=_int(mesh_health.get("sampled_connected_component_count"))
    mesh_components_approx=bool(mesh_health.get("sampled_connected_component_count_is_approximate"))
    flattened=list(mesh_health.get("flattened_axes_warning") or [])

    status="PASS"
    alerts=[]

    def add(level: str, code: str):
        nonlocal status
        if code not in alerts:
            alerts.append(code)
        status=_status_max(status,level)

    if sparse_points <= 0:
        add("FAIL","SPARSE_POINT_CLOUD_EMPTY")
    elif total_selected > 0 and sparse_points < max(32,total_selected*2):
        add("WARN","SPARSE_POINT_DENSITY_LOW")

    if expected:
        if contributing == 0:
            add("FAIL","NO_AUTHORED_MISSION_CONTRIBUTES_TO_SPARSE")
        elif contributing < len(expected):
            add("WARN","AUTHORED_MISSION_MISSING_FROM_SPARSE")
    if total_dataset > 0:
        drop_fraction=total_dropped/float(total_dataset)
        if drop_fraction >= 0.80:
            add("WARN","VERY_HIGH_FRAME_DROP_FRACTION")
        elif drop_fraction >= 0.35:
            add("WARN","HIGH_FRAME_DROP_FRACTION")
    else:
        drop_fraction=None

    if component_count <= 0:
        add("FAIL","NO_VERIFIED_SPARSE_COMPONENT")
    elif component_count > max(1,contributing*2):
        add("WARN","HIGH_SPARSE_COMPONENT_FRAGMENTATION")

    if dense_points <= 0:
        add("FAIL","DENSE_FUSED_CLOUD_EMPTY")
    elif sparse_points > 0 and dense_points < sparse_points:
        add("WARN","DENSE_CLOUD_SMALLER_THAN_SPARSE_CLOUD")

    if total_selected > 1:
        if depth_maps <= 0:
            add("FAIL","NO_DENSE_DEPTH_MAPS")
        elif depth_maps < max(1,total_selected//2):
            add("WARN","LOW_DENSE_DEPTH_MAP_COVERAGE")
        if normal_maps <= 0:
            add("WARN","NO_DENSE_NORMAL_MAPS")

    if mesh_vertices <= 0 or mesh_faces <= 0:
        add("FAIL","PREFUSION_MESH_EMPTY")
    if invalid_faces > 0:
        add("FAIL","PREFUSION_INVALID_FACE_INDICES")
    if degenerate_fraction > 0.25:
        add("FAIL","PREFUSION_DEGENERATE_FACE_FRACTION_CRITICAL")
    elif degenerate_fraction > 0.05:
        add("WARN","PREFUSION_DEGENERATE_FACE_FRACTION_HIGH")
    if flattened:
        add("WARN","PREFUSION_FLATTENED_AXIS")
    if mesh_components > max(8,contributing*4 if contributing else 8):
        add("WARN","PREFUSION_HIGH_FRAGMENTATION")

    roundtrip_status=None
    if isinstance(p9_roundtrip,dict):
        roundtrip_status=str(
            p9_roundtrip.get("quality_status")
            or p9_roundtrip.get("runtime_status")
            or ""
        ).upper() or None
        if roundtrip_status=="FAIL":
            add("WARN","P9_ONLY_ROUNDTRIP_AUDIT_FAILED")
        elif roundtrip_status=="WARN":
            add("WARN","P9_ONLY_ROUNDTRIP_AUDIT_WARN")

    overlay_status=None
    overlay_distance=None
    overlay_bounds={}
    if isinstance(metric_overlay,dict):
        overlay_status=str(metric_overlay.get("status") or "").upper() or None
        overlay_distance=metric_overlay.get("p10_dense_to_p9_distance")
        overlay_bounds={
            "p9":(metric_overlay.get("p9") or {}).get("bounds"),
            "p10_sparse":(metric_overlay.get("p10_sparse") or {}).get("bounds"),
            "p10_dense":(metric_overlay.get("p10_dense") or {}).get("bounds"),
            "p10_prefusion_mesh":(metric_overlay.get("p10_prefusion_mesh") or {}).get("bounds"),
            "cameras":(metric_overlay.get("cameras") or {}).get("bounds"),
        }
        if overlay_status=="WARN":
            add("WARN","METRIC_OVERLAY_WARN")
        elif overlay_status=="FAIL":
            add("WARN","METRIC_OVERLAY_FAILED")

    result={
        "schema":_SCHEMA,
        "status":status,
        "runtime_files_exist":True,
        "p9_authority_changed":False,
        "authority_statement":"P9_ACCEPTED_IMMUTABLE_UPSTREAM; QUALITY_CLASSIFIES_P10_RECONSTRUCTION_ONLY",
        "alerts":alerts,
        "expected_missions":expected,
        "mission_count_expected":len(expected),
        "mission_count_contributing":contributing,
        "mission_contribution":mission_rows,
        "frames":{
            "dataset":total_dataset,
            "selected":total_selected,
            "dropped":total_dropped,
            "drop_fraction":drop_fraction,
        },
        "sparse":{
            "point_count":sparse_points,
            "verified_component_count":component_count,
            "quality_status":sparse.get("quality_status"),
        },
        "dense":{
            "fused_point_count":dense_points,
            "depth_map_file_count":depth_maps,
            "normal_map_file_count":normal_maps,
        },
        "prefusion_mesh":{
            "vertex_count":mesh_vertices,
            "face_count":mesh_faces,
            "invalid_face_index_count":invalid_faces,
            "degenerate_face_sample_fraction":degenerate_fraction,
            "sampled_connected_component_count":mesh_components,
            "sampled_connected_component_count_is_approximate":mesh_components_approx,
            "flattened_axes_warning":flattened,
            "mesh_health_status":mesh_health.get("health_status"),
        },
        "p9_roundtrip_quality_status":roundtrip_status,
        "metric_overlay_status":overlay_status,
        "metric_bounds":overlay_bounds,
        "p10_dense_to_p9_distance":overlay_distance,
        "distance_policy":"DESCRIPTIVE_ONLY_FOR_GENERATED_UNSEEN_SURFACES",
        "promotion_policy":{
            "PASS":"runtime complete and no material reconstruction-quality alert",
            "WARN":"usable geometry exists but evidence is partial/fragmented or a diagnostic audit warns",
            "FAIL":"zero/invalid core reconstruction evidence; do not promote to Gate 7",
        },
    }
    return result


def write_gate6_geometry_quality(
    dataset_root: str | Path,
    output_path: str | Path,
    *,
    expected_missions: list[str] | tuple[str,...] = (),
    p9_roundtrip: dict | None = None,
    metric_overlay: dict | None = None,
) -> dict[str,object]:
    result=evaluate_gate6_geometry_quality(
        dataset_root,
        expected_missions=expected_missions,
        p9_roundtrip=p9_roundtrip,
        metric_overlay=metric_overlay,
    )
    output_path=Path(output_path).resolve()
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    result["manifest_path"]=str(output_path)
    return result
