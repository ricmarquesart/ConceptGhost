from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
from typing import Any

from .contracts import ContractError
from .prefusion_mesh import _PLY_SCALAR, _read_mesh_header


_SCHEMA = "ConceptGhost.P10Gate6GeometryOutput.v0.1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _mesh_counts(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = _read_mesh_header(stream)
    return int(header.vertex_count), int(header.face_count)


def _write_obj_from_ply(source: Path, target: Path) -> tuple[int, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as stream, target.open("w", encoding="utf-8", newline="\n") as out:
        header = _read_mesh_header(stream)
        names = [name for _, name in header.vertex_properties]
        x_index = names.index("x")
        y_index = names.index("y")
        z_index = names.index("z")

        out.write("# ConceptGhost Gate 6 RAW P10 geometry\n")
        out.write("# Generated from drone/WAN multiview reconstruction BEFORE Gate 7 filtering\n")

        if header.format_name == "ascii":
            for _ in range(header.vertex_count):
                raw = stream.readline()
                if not raw:
                    raise ContractError("Unexpected EOF in ASCII PLY vertices")
                parts = raw.decode("ascii").split()
                if len(parts) < len(header.vertex_properties):
                    raise ContractError("Malformed ASCII PLY vertex row")
                values = []
                for (dtype, _name), token in zip(header.vertex_properties, parts):
                    code = _PLY_SCALAR[dtype][0]
                    values.append(float(token) if code in {"f", "d"} else int(token))
                out.write(
                    f"v {float(values[x_index]):.9g} {float(values[y_index]):.9g} "
                    f"{float(values[z_index]):.9g}\n"
                )
        else:
            fmt = "<" + "".join(_PLY_SCALAR[dtype][0] for dtype, _ in header.vertex_properties)
            size = struct.calcsize(fmt)
            for _ in range(header.vertex_count):
                raw = stream.read(size)
                if len(raw) != size:
                    raise ContractError("Unexpected EOF in binary PLY vertices")
                values = struct.unpack(fmt, raw)
                out.write(
                    f"v {float(values[x_index]):.9g} {float(values[y_index]):.9g} "
                    f"{float(values[z_index]):.9g}\n"
                )

        if header.format_name == "ascii":
            for _ in range(header.face_count):
                raw = stream.readline()
                if not raw:
                    raise ContractError("Unexpected EOF in ASCII PLY faces")
                parts = raw.decode("ascii").split()
                if not parts:
                    raise ContractError("Malformed ASCII PLY face row")
                count = int(parts[0])
                if count != 3 or len(parts) < 4:
                    raise ContractError("Gate 6 geometry output currently requires triangular faces")
                a, b, c = (int(parts[1]), int(parts[2]), int(parts[3]))
                out.write(f"f {a + 1} {b + 1} {c + 1}\n")
        else:
            count_code = _PLY_SCALAR[header.face_count_type][0]
            count_size = _PLY_SCALAR[header.face_count_type][1]
            index_code = _PLY_SCALAR[header.face_index_type][0]
            index_size = _PLY_SCALAR[header.face_index_type][1]
            for _ in range(header.face_count):
                raw = stream.read(count_size)
                if len(raw) != count_size:
                    raise ContractError("Unexpected EOF in binary PLY face count")
                count = struct.unpack("<" + count_code, raw)[0]
                if count != 3:
                    raise ContractError("Gate 6 geometry output currently requires triangular faces")
                raw = stream.read(index_size * count)
                if len(raw) != index_size * count:
                    raise ContractError("Unexpected EOF in binary PLY face indices")
                a, b, c = (int(v) for v in struct.unpack("<" + index_code * count, raw))
                out.write(f"f {a + 1} {b + 1} {c + 1}\n")

    return int(header.vertex_count), int(header.face_count)


def publish_gate6_geometry_output(
    dataset_root: str | Path,
    output_root: str | Path,
    *,
    p9_run_dir: str | Path | None = None,
    p10_attempt_id: str | None = None,
    geometry_quality: dict[str, Any] | None = None,
    metric_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a plainly inspectable Gate-6 geometry artifact.

    This is deliberately BEFORE Gate 7. The output is the raw P10 reconstruction
    from the drone/WAN image set. It is never filtered against P9 here.
    """

    dataset_root = Path(dataset_root).resolve()
    output_root = Path(output_root).resolve()
    dense_root = dataset_root / "dense"
    mesh_source = dense_root / "pre_fusion_mesh.ply"
    fused_source = dense_root / "fused.ply"
    mesh_manifest_path = dataset_root / "prefusion_mesh_manifest.json"

    if not mesh_source.is_file():
        raise ContractError(
            "Gate 6 cannot close: pre_fusion_mesh.ply was not generated from the drone views"
        )
    if not fused_source.is_file():
        raise ContractError(
            "Gate 6 cannot close: fused.ply dense reconstruction is missing"
        )
    mesh_manifest = _read_json(mesh_manifest_path, "Gate 6 pre-fusion mesh manifest")
    if mesh_manifest.get("status") != "PASS":
        raise ContractError("Gate 6 cannot close: pre-fusion mesh manifest is not PASS")

    vertex_count, face_count = _mesh_counts(mesh_source)
    if vertex_count <= 0 or face_count <= 0:
        raise ContractError(
            f"Gate 6 cannot close: generated mesh is empty ({vertex_count} vertices, {face_count} faces)"
        )

    published_root = output_root / "gate6_output"
    published_root.mkdir(parents=True, exist_ok=True)
    raw_ply = published_root / "GATE6_RAW_P10_GEOMETRY.ply"
    raw_obj = published_root / "GATE6_RAW_P10_GEOMETRY.obj"
    dense_ply = published_root / "GATE6_DENSE_POINTS.ply"
    overlay_copy = published_root / "GATE6_P9_P10_OVERLAY.png"

    shutil.copy2(mesh_source, raw_ply)
    shutil.copy2(fused_source, dense_ply)
    obj_vertices, obj_faces = _write_obj_from_ply(mesh_source, raw_obj)
    if obj_vertices != vertex_count or obj_faces != face_count:
        raise ContractError("Gate 6 OBJ export count mismatch")

    overlay_path = None
    if isinstance(metric_overlay, dict):
        value = str(metric_overlay.get("preview_png_path") or "").strip()
        if value:
            candidate = Path(value).expanduser().resolve()
            if candidate.is_file():
                shutil.copy2(candidate, overlay_copy)
                overlay_path = overlay_copy

    quality = geometry_quality if isinstance(geometry_quality, dict) else {}
    distance = {}
    if isinstance(metric_overlay, dict):
        value = metric_overlay.get("p10_dense_to_p9_distance")
        if isinstance(value, dict):
            distance = value

    attempt_id = str(p10_attempt_id or "").strip() or output_root.parent.name
    result: dict[str, Any] = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 6,
        "functional_contract": "RAW_P10_3D_GEOMETRY_MUST_EXIST_BEFORE_GATE7",
        "geometry_generated": True,
        "geometry_source": "GATE5_DRONE_WAN_MULTIVIEW_IMAGES",
        "geometry_stage": "PRE_FUSION_BEFORE_P9_COMBINATION",
        "gate7_filtering_applied": False,
        "p9_authority_changed": False,
        "p10_attempt_id": attempt_id,
        "dataset_root": str(dataset_root),
        "published_root": str(published_root),
        "raw_p10_geometry_ply": str(raw_ply),
        "raw_p10_geometry_obj": str(raw_obj),
        "dense_points_ply": str(dense_ply),
        "p9_p10_overlay_png": str(overlay_path) if overlay_path else None,
        "vertex_count": vertex_count,
        "face_count": face_count,
        "mesh_sha256": _sha256_file(raw_ply),
        "obj_sha256": _sha256_file(raw_obj),
        "dense_points_sha256": _sha256_file(dense_ply),
        "geometry_quality_status": quality.get("status"),
        "geometry_quality_alerts": quality.get("alerts") or [],
        "p10_dense_to_p9_distance": distance,
        "hole_fill_visual_validation": "REQUIRED",
        "notes": [
            "This artifact is raw P10 geometry reconstructed from the drone/WAN image set.",
            "It exists before Gate 7 and is not allowed to disappear because Gate 7 rejects it.",
            "Quality may be poor; Gate 6 acceptance requires that a non-empty new 3D reconstruction is delivered.",
            "Whether the raw geometry actually fills intended occluded holes must be validated visually and quantified separately.",
        ],
    }

    manifest_path = published_root / "GATE6_OUTPUT_MANIFEST.json"
    readme_path = published_root / "README_GATE6_OUTPUT.txt"
    result["manifest_path"] = str(manifest_path)
    result["readme_path"] = str(readme_path)
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    readme_path.write_text(
        "\n".join([
            "CONCEPTGHOST GATE 6 OUTPUT",
            "=" * 72,
            "This folder is the explicit Gate 6 deliverable.",
            "",
            "GATE6_RAW_P10_GEOMETRY.ply",
            "  Raw P10 pre-fusion mesh generated from the drone/WAN multiview images.",
            "  Gate 7 filtering has NOT been applied.",
            "",
            "GATE6_RAW_P10_GEOMETRY.obj",
            "  Same raw geometry converted to OBJ for easy DCC inspection.",
            "",
            "GATE6_DENSE_POINTS.ply",
            "  Dense fused point cloud used to generate the pre-fusion surface.",
            "",
            f"Vertices: {vertex_count}",
            f"Faces: {face_count}",
            f"Geometry quality: {quality.get('status')}",
            "",
            "Gate 6 is not allowed to claim functional completion if this geometry is empty.",
            "Visual hole-fill quality is intentionally evaluated separately.",
            "",
        ]),
        encoding="utf-8",
    )

    sidecar_root = None
    if p9_run_dir:
        source_run = Path(p9_run_dir).expanduser().resolve()
        if source_run.is_dir():
            sidecar_root = source_run / "P10_GATE6_OUTPUT" / attempt_id
            sidecar_root.mkdir(parents=True, exist_ok=True)
            for source in (raw_ply, raw_obj, manifest_path, readme_path):
                shutil.copy2(source, sidecar_root / source.name)
            if overlay_path is not None:
                shutil.copy2(overlay_path, sidecar_root / overlay_path.name)
            latest = source_run / "LATEST_P10_GATE6_OUTPUT.txt"
            latest.write_text(str(sidecar_root), encoding="utf-8")
            result["p9_run_sidecar_root"] = str(sidecar_root)
            result["p9_run_latest_pointer"] = str(latest)
            manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
            shutil.copy2(manifest_path, sidecar_root / manifest_path.name)

    return result
