from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
from typing import Any, Iterable

from .contracts import ContractError
from .prefusion_mesh import _PLY_SCALAR, _read_mesh_header


_SCHEMA = "ConceptGhost.GateOutputContract.v0.1"


_GATE_NAMES = {
    1: "FOUNDATION_RUN",
    2: "P9_TO_P10_HANDOFF",
    3: "KNOWN_UNKNOWN",
    4: "DRONES_CAMERAS",
    5: "NEW_VIEWS",
    6: "RECONSTRUCTION_3D",
    7: "P9_P10_FUSION",
    8: "REPAIR_CLEANUP",
    9: "VALIDATION_MAYA",
    10: "RELEASE",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gate_outputs_root(
    p9_run_dir: str | Path,
    p10_attempt_id: str,
) -> Path:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt = str(p10_attempt_id or "").strip()
    if not attempt:
        raise ContractError("Gate output contract requires p10_attempt_id")
    return p9 / "GATE_OUTPUTS" / attempt


def gate_output_dir(
    p9_run_dir: str | Path,
    p10_attempt_id: str,
    gate: int,
) -> Path:
    if gate not in _GATE_NAMES:
        raise ContractError(f"Unsupported Gate output number: {gate}")
    return gate_outputs_root(p9_run_dir, p10_attempt_id) / (
        f"GATE_{gate:02d}_{_GATE_NAMES[gate]}"
    )


def _reset_gate_dir(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    for name in ("INPUTS", "OUTPUTS", "PREVIEWS", "LOGS"):
        (root / name).mkdir(parents=True, exist_ok=True)


def _copy_file(source: Path, target: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise ContractError(f"Gate output source file is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _copy_tree_files(
    source_root: Path,
    target_root: Path,
    *,
    suffixes: set[str] | None = None,
) -> list[Path]:
    source_root = source_root.expanduser().resolve()
    copied: list[Path] = []
    if not source_root.is_dir():
        return copied
    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        if suffixes is not None and source.suffix.lower() not in suffixes:
            continue
        relative = source.relative_to(source_root)
        copied.append(_copy_file(source, target_root / relative))
    return copied


def _manifest_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"SHA256SUMS.txt", "OUTPUT_MANIFEST.json"}:
            continue
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    return rows


def _write_contract_files(
    root: Path,
    *,
    gate: int,
    p9_run_dir: Path,
    p10_attempt_id: str,
    required: dict[str, bool],
    runtime_status: str,
    functional_status: str,
    quality_status: str | None,
    input_sources: list[str],
    notes: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = sorted(name for name, present in required.items() if not present)
    complete = not missing
    status = (
        "INCOMPLETE"
        if not complete
        else (
            "PASS"
            if functional_status == "PASS"
            else "PARTIAL"
        )
    )
    rows = _manifest_rows(root)
    output_manifest = {
        "schema": "ConceptGhost.GateOutputManifest.v0.1",
        "gate": gate,
        "gate_name": _GATE_NAMES[gate],
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_id": p10_attempt_id,
        "created_at_utc": _utc_now(),
        "files": rows,
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
    }
    (root / "OUTPUT_MANIFEST.json").write_text(
        json.dumps(output_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    input_manifest = {
        "schema": "ConceptGhost.GateInputManifest.v0.1",
        "gate": gate,
        "gate_name": _GATE_NAMES[gate],
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_id": p10_attempt_id,
        "sources": input_sources,
    }
    (root / "INPUT_MANIFEST.json").write_text(
        json.dumps(input_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    gate_status = {
        "schema": _SCHEMA,
        "gate": gate,
        "gate_name": _GATE_NAMES[gate],
        "status": status,
        "runtime_status": runtime_status,
        "functional_status": functional_status,
        "quality_status": quality_status,
        "required_outputs_complete": complete,
        "missing_required_outputs": missing,
        "next_gate_authorized": bool(complete and functional_status == "PASS"),
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_id": p10_attempt_id,
        "gate_output_dir": str(root),
        "created_at_utc": _utc_now(),
        "metrics": metrics or {},
        "notes": notes or [],
        "policy": {
            "runtime_pass_is_not_quality_pass": True,
            "low_quality_alone_does_not_mean_missing_output": True,
            "missing_required_output_blocks_next_gate": True,
            "gate_outputs_never_overwrite_other_gate_products": True,
        },
    }
    (root / "GATE_STATUS.json").write_text(
        json.dumps(gate_status, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    checksum_lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        checksum_lines.append(
            f"{_sha256(path)}  {path.relative_to(root).as_posix()}"
        )
    (root / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return gate_status


def _write_gate_index(
    p9_run_dir: Path,
    p10_attempt_id: str,
) -> dict[str, Any]:
    root = gate_outputs_root(p9_run_dir, p10_attempt_id)
    gates = []
    for gate, name in sorted(_GATE_NAMES.items()):
        gate_dir = root / f"GATE_{gate:02d}_{name}"
        status_path = gate_dir / "GATE_STATUS.json"
        status = _read_json(status_path) if status_path.is_file() else {}
        gates.append({
            "gate": gate,
            "name": name,
            "status": status.get("status", "NOT_PUBLISHED"),
            "runtime_status": status.get("runtime_status"),
            "functional_status": status.get("functional_status"),
            "quality_status": status.get("quality_status"),
            "required_outputs_complete": status.get("required_outputs_complete"),
            "next_gate_authorized": status.get("next_gate_authorized"),
            "gate_output_dir": str(gate_dir) if gate_dir.exists() else None,
            "status_path": str(status_path) if status_path.is_file() else None,
        })
    payload = {
        "schema": "ConceptGhost.GateOutputIndex.v0.1",
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_id": p10_attempt_id,
        "gate_outputs_root": str(root),
        "updated_at_utc": _utc_now(),
        "gates": gates,
    }
    index_path = p9_run_dir / "GATE_OUTPUT_INDEX.json"
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (p9_run_dir / "LATEST_GATE_OUTPUTS.txt").write_text(
        str(root) + "\n",
        encoding="utf-8",
    )
    return payload


def _find_p9_maya(p9_run_dir: Path) -> Path | None:
    candidates = []
    for relative in ("maya", "package", "."):
        root = (p9_run_dir / relative).resolve()
        if root.is_dir():
            candidates.extend(sorted(root.glob("*.ma")))
    if not candidates:
        candidates.extend(sorted(p9_run_dir.rglob("*.ma")))
    return candidates[0].resolve() if candidates else None


def _maya_escape(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace('"', '\\"')


def _write_diagnostic_maya(
    path: Path,
    *,
    gate: int,
    obj_imports: list[tuple[str, Path, tuple[float, float, float]]],
    p9_maya_reference: Path | None = None,
    camera_manifest_path: Path | None = None,
) -> Path:
    """Write a diagnostic Maya ASCII shell with explicit provenance layers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "//Maya ASCII 2024 scene",
        f"// ConceptGhost Gate {gate} diagnostic scene",
        'requires maya "2020";',
        'currentUnit -l centimeter -a degree -t film;',
        'fileInfo "ConceptGhostGate" "' + str(gate) + '";',
        'createNode transform -n "GROUP_GATE%02d";' % gate,
    ]
    if p9_maya_reference is not None and p9_maya_reference.is_file():
        lines.append(
            'file -r -ignoreVersion -gl -mergeNamespacesOnClash false '
            '-namespace "P9_ORIGINAL" -options "v=0;" '
            f'-type "mayaAscii" "{_maya_escape(p9_maya_reference)}";'
        )

    for namespace, obj_path, color in obj_imports:
        if not obj_path.is_file():
            continue
        mat = f"{namespace}_MAT"
        sg = f"{namespace}_MATSG"
        lines += [
            'file -import -ignoreVersion -ra true -mergeNamespacesOnClash false '
            f'-namespace "{namespace}" -options "mo=1" -type "OBJ" '
            f'"{_maya_escape(obj_path)}";',
            f'createNode lambert -n "{mat}";',
            f'setAttr "{mat}.color" -type "double3" {color[0]} {color[1]} {color[2]};',
            f'createNode shadingEngine -n "{sg}";',
            f'connectAttr -f "{mat}.outColor" "{sg}.surfaceShader";',
            f'select -r "{namespace}:*";',
            f'sets -e -forceElement "{sg}";',
            'select -cl;',
        ]

    if camera_manifest_path is not None and camera_manifest_path.is_file():
        camera_manifest = _read_json(camera_manifest_path)
        frames = camera_manifest.get("frames")
        if isinstance(frames, list):
            lines.append(
                'createNode transform -n "CAMERAS_GATE%02d" -p "GROUP_GATE%02d";'
                % (gate, gate)
            )
            indexes = list(range(0, len(frames), 5))
            if frames and (len(frames) - 1) not in indexes:
                indexes.append(len(frames) - 1)
            for index in indexes:
                frame = frames[index]
                if not isinstance(frame, dict):
                    continue
                camera = frame.get("camera")
                if not isinstance(camera, dict):
                    continue
                matrix = camera.get("world_matrix")
                if (
                    not isinstance(matrix, list)
                    or len(matrix) != 4
                    or any(not isinstance(row, list) or len(row) != 4 for row in matrix)
                ):
                    continue
                try:
                    flat = [float(value) for row in matrix for value in row]
                    fx = float(camera.get("fx") or 0.0)
                    width = float(camera.get("width") or 0.0)
                except (TypeError, ValueError):
                    continue
                name = f"GATE{gate:02d}_CAM_{index:04d}"
                lines += [
                    f'createNode transform -n "{name}" -p "CAMERAS_GATE{gate:02d}";',
                    f'setAttr "{name}.m" -type "matrix" '
                    + " ".join(f"{value:.17g}" for value in flat)
                    + ";",
                    f'createNode camera -n "{name}Shape" -p "{name}";',
                ]
                if fx > 0 and width > 0:
                    focal_mm = fx * 36.0 / width
                    lines.append(f'setAttr "{name}Shape.fl" {focal_mm:.9g};')

    lines += [
        'select -cl;',
        "// Geometry authority note: diagnostic only; never overwrites P9.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_sparse_ply(points_txt: Path, output_ply: Path) -> int:
    rows: list[tuple[float, float, float, int, int, int]] = []
    if points_txt.is_file():
        for raw in points_txt.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                rows.append((
                    float(parts[1]), float(parts[2]), float(parts[3]),
                    int(parts[4]), int(parts[5]), int(parts[6]),
                ))
            except (TypeError, ValueError):
                continue
    output_ply.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "ply",
        "format ascii 1.0",
        "comment ConceptGhost Gate 6 sparse triangulation points",
        f"element vertex {len(rows)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
    ]
    with output_ply.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("\n".join(header) + "\n")
        for row in rows:
            stream.write(
                f"{row[0]:.9g} {row[1]:.9g} {row[2]:.9g} "
                f"{row[3]} {row[4]} {row[5]}\n"
            )
    return len(rows)


def _read_ply_mesh(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    with path.open("rb") as stream:
        header = _read_mesh_header(stream)
        names = [name for _, name in header.vertex_properties]
        x_index, y_index, z_index = (names.index("x"), names.index("y"), names.index("z"))
        if header.format_name == "ascii":
            for _ in range(header.vertex_count):
                parts = stream.readline().decode("ascii").split()
                values = []
                for (dtype, _name), token in zip(header.vertex_properties, parts):
                    code = _PLY_SCALAR[dtype][0]
                    values.append(float(token) if code in {"f", "d"} else int(token))
                vertices.append((
                    float(values[x_index]), float(values[y_index]), float(values[z_index])
                ))
            for _ in range(header.face_count):
                parts = stream.readline().decode("ascii").split()
                count = int(parts[0])
                if count != 3:
                    raise ContractError("Gate output split supports triangular PLY faces only")
                faces.append((int(parts[1]), int(parts[2]), int(parts[3])))
        else:
            fmt = "<" + "".join(_PLY_SCALAR[dtype][0] for dtype, _ in header.vertex_properties)
            size = struct.calcsize(fmt)
            for _ in range(header.vertex_count):
                values = struct.unpack(fmt, stream.read(size))
                vertices.append((
                    float(values[x_index]), float(values[y_index]), float(values[z_index])
                ))
            count_code = _PLY_SCALAR[header.face_count_type][0]
            count_size = _PLY_SCALAR[header.face_count_type][1]
            index_code = _PLY_SCALAR[header.face_index_type][0]
            index_size = _PLY_SCALAR[header.face_index_type][1]
            for _ in range(header.face_count):
                count = int(struct.unpack("<" + count_code, stream.read(count_size))[0])
                if count != 3:
                    raise ContractError("Gate output split supports triangular PLY faces only")
                face = struct.unpack("<" + index_code * count, stream.read(index_size * count))
                faces.append(tuple(int(v) for v in face))
    return vertices, faces


def _write_selected_obj(
    source_ply: Path,
    face_indices: Iterable[int],
    target_obj: Path,
) -> tuple[int, int]:
    vertices, faces = _read_ply_mesh(source_ply)
    selected = [
        faces[int(index)]
        for index in face_indices
        if 0 <= int(index) < len(faces)
    ]
    used = sorted({vertex for face in selected for vertex in face})
    remap = {old: new + 1 for new, old in enumerate(used)}
    target_obj.parent.mkdir(parents=True, exist_ok=True)
    with target_obj.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# ConceptGhost Gate 7 P10 face subset\n")
        for old in used:
            x, y, z = vertices[old]
            stream.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for face in selected:
            stream.write("f " + " ".join(str(remap[index]) for index in face) + "\n")
    return len(used), len(selected)


def publish_gate4_output(
    p9_run_dir: str | Path,
    p10_attempt_root: str | Path,
    *,
    p10_attempt_id: str | None = None,
) -> dict[str, Any]:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt_root = Path(p10_attempt_root).expanduser().resolve()
    attempt_id = str(p10_attempt_id or attempt_root.name)
    source = attempt_root / "gate4"
    root = gate_output_dir(p9, attempt_id, 4)
    _reset_gate_dir(root)

    control = source / "control_sequence"
    route = control / "route_plan.json"
    manifest = control / "manifest.json"
    cameras = control / "camera_manifest.json"
    gif = source / "P10_drone_flights_P9_holes.gif"

    if route.is_file():
        _copy_file(route, root / "INPUTS" / "route.json")
    if manifest.is_file():
        _copy_file(manifest, root / "OUTPUTS" / "control_sequence_manifest.json")
    if cameras.is_file():
        _copy_file(cameras, root / "OUTPUTS" / "cameras.json")
    _copy_tree_files(control / "frames", root / "OUTPUTS" / "CONTROL_FRAMES")
    _copy_tree_files(control / "masks", root / "OUTPUTS" / "HIDDEN_AREA_MASKS")
    if gif.is_file():
        _copy_file(gif, root / "PREVIEWS" / gif.name)
    for name in (
        "drone_flight_views_contact_sheet.png",
        "raw_holes_contact_sheet.png",
        "camera_paths_topdown.png",
        "p9_3d_partial_erp.png",
        "source_authority_partial_erp.png",
        "source_lock_known_unknown.png",
    ):
        preview = source / name
        if preview.is_file():
            _copy_file(preview, root / "PREVIEWS" / name)

    control_payload = _read_json(manifest)
    camera_payload = _read_json(cameras)
    frame_count = int(control_payload.get("frame_count") or 0)
    camera_count = int(camera_payload.get("frame_count") or 0)
    copied_frames = len(list((root / "OUTPUTS" / "CONTROL_FRAMES").glob("*.png")))
    copied_masks = len(list((root / "OUTPUTS" / "HIDDEN_AREA_MASKS").glob("*.png")))
    required = {
        "route.json": (root / "INPUTS" / "route.json").is_file(),
        "control_sequence_manifest.json": (root / "OUTPUTS" / "control_sequence_manifest.json").is_file(),
        "cameras.json": (root / "OUTPUTS" / "cameras.json").is_file(),
        "all_control_frames": frame_count > 0 and copied_frames == frame_count,
        "all_hidden_area_masks": frame_count > 0 and copied_masks == frame_count,
        "flight_gif": (root / "PREVIEWS" / gif.name).is_file(),
        "camera_path_preview": (root / "PREVIEWS" / "camera_paths_topdown.png").is_file(),
    }
    status = _write_contract_files(
        root,
        gate=4,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required=required,
        runtime_status="PASS" if source.is_dir() else "FAIL",
        functional_status="PASS" if all(required.values()) else "FAIL",
        quality_status=None,
        input_sources=[str(source)],
        metrics={
            "authored_frame_count": frame_count,
            "published_control_frame_count": copied_frames,
            "published_mask_count": copied_masks,
            "camera_frame_count": camera_count,
        },
        notes=[
            "Every authored Gate 4 control PNG and hidden-area mask is copied here for direct inspection.",
            "These are camera/drone evidence outputs, not generated WAN views.",
        ],
    )
    _write_gate_index(p9, attempt_id)
    return status


def publish_gate5_output(
    p9_run_dir: str | Path,
    p10_attempt_root: str | Path,
    *,
    p10_attempt_id: str | None = None,
) -> dict[str, Any]:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt_root = Path(p10_attempt_root).expanduser().resolve()
    attempt_id = str(p10_attempt_id or attempt_root.name)
    source = attempt_root / "gate5"
    root = gate_output_dir(p9, attempt_id, 5)
    _reset_gate_dir(root)

    manifest = source / "wan_manifest.json"
    if manifest.is_file():
        _copy_file(manifest, root / "OUTPUTS" / "view_manifest.json")
    raw_files = _copy_tree_files(
        source / "wan_raw",
        root / "OUTPUTS" / "WAN_RAW_GENERATED",
        suffixes={".png"},
    )
    composite_files = _copy_tree_files(
        source / "composite",
        root / "OUTPUTS" / "FINAL_SOURCE_PRESERVED_VIEWS",
        suffixes={".png"},
    )
    preview_files = _copy_tree_files(
        source / "drone_previews",
        root / "PREVIEWS" / "DRONE_PREVIEWS",
    )

    payload = _read_json(manifest)
    expected = sum(
        int(item.get("frame_count") or 0)
        for item in payload.get("missions", [])
        if isinstance(item, dict)
    )
    gif_count = len([path for path in preview_files if path.suffix.lower() == ".gif"])
    required = {
        "view_manifest.json": (root / "OUTPUTS" / "view_manifest.json").is_file(),
        "raw_generated_views": expected > 0 and len(raw_files) >= expected,
        "final_source_preserved_views": expected > 0 and len(composite_files) >= expected,
        "drone_preview_gif": gif_count > 0,
        "known_pixel_preservation_contract": payload.get("known_pixel_policy")
            == "CONTROL_VIDEO_PRESERVED_WHERE_HOLE_MASK_IS_BLACK",
    }
    status = _write_contract_files(
        root,
        gate=5,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required=required,
        runtime_status="PASS" if manifest.is_file() else "FAIL",
        functional_status="PASS" if all(required.values()) else "FAIL",
        quality_status=None,
        input_sources=[str(source)],
        metrics={
            "expected_generated_frame_count": expected,
            "raw_generated_png_count": len(raw_files),
            "final_composite_png_count": len(composite_files),
            "preview_gif_count": gif_count,
        },
        notes=[
            "FINAL_SOURCE_PRESERVED_VIEWS is the Gate 5 product consumed by Gate 6.",
            "WAN_RAW_GENERATED is retained so generated pixels can be compared against the source-preserving composite.",
        ],
    )
    _write_gate_index(p9, attempt_id)
    return status


def publish_gate6_output_tree(
    p9_run_dir: str | Path,
    p10_attempt_root: str | Path,
    *,
    p10_attempt_id: str | None = None,
) -> dict[str, Any]:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt_root = Path(p10_attempt_root).expanduser().resolve()
    attempt_id = str(p10_attempt_id or attempt_root.name)
    source = attempt_root / "gate6"
    root = gate_output_dir(p9, attempt_id, 6)
    _reset_gate_dir(root)

    explicit = source / "gate6_output"
    dataset = source / "dataset"
    diagnostics = source / "diagnostics"

    raw_ply = explicit / "GATE6_RAW_P10_GEOMETRY.ply"
    raw_obj = explicit / "GATE6_RAW_P10_GEOMETRY.obj"
    dense_ply = explicit / "GATE6_DENSE_POINTS.ply"
    runtime_manifest = source / "reconstruction_runtime_manifest.json"
    quality = diagnostics / "gate6_geometry_quality.json"
    camera_manifest = attempt_root / "gate4" / "control_sequence" / "camera_manifest.json"

    for src, name in (
        (raw_ply, "reconstructed_mesh.ply"),
        (raw_obj, "reconstructed_mesh.obj"),
        (dense_ply, "dense_points.ply"),
        (runtime_manifest, "reconstruction_manifest.json"),
        (quality, "geometry_quality.json"),
        (camera_manifest, "reconstruction_camera_set.json"),
    ):
        if src.is_file():
            _copy_file(src, root / "OUTPUTS" / name)

    sparse_ply = root / "OUTPUTS" / "sparse_points.ply"
    sparse_count = _write_sparse_ply(
        dataset / "sparse" / "triangulated_txt" / "points3D.txt",
        sparse_ply,
    )

    for src in (
        explicit / "GATE6_P9_P10_OVERLAY.png",
        diagnostics / "p9_p10_metric_overlay.png",
        dataset / "dense" / "pre_fusion_mesh_preview.svg",
    ):
        if src.is_file():
            _copy_file(src, root / "PREVIEWS" / src.name)

    _copy_tree_files(dataset / "logs", root / "LOGS")

    ma_path = root / "OUTPUTS" / "Gate06_Reconstruction_Diagnostic.ma"
    _write_diagnostic_maya(
        ma_path,
        gate=6,
        obj_imports=[
            ("P10_RECONSTRUCTED_RAW", root / "OUTPUTS" / "reconstructed_mesh.obj", (0.20, 0.75, 0.30)),
        ],
        camera_manifest_path=root / "OUTPUTS" / "reconstruction_camera_set.json",
    )

    runtime = _read_json(runtime_manifest)
    quality_payload = _read_json(quality)
    explicit_manifest = _read_json(explicit / "GATE6_OUTPUT_MANIFEST.json")
    vertex_count = int(explicit_manifest.get("vertex_count") or 0)
    face_count = int(explicit_manifest.get("face_count") or 0)
    required = {
        "sparse_points.ply": sparse_ply.is_file() and sparse_count > 0,
        "dense_points.ply": (root / "OUTPUTS" / "dense_points.ply").is_file(),
        "reconstructed_mesh.ply": (root / "OUTPUTS" / "reconstructed_mesh.ply").is_file() and vertex_count > 0 and face_count > 0,
        "reconstructed_mesh.obj": (root / "OUTPUTS" / "reconstructed_mesh.obj").is_file(),
        "reconstruction_camera_set.json": (root / "OUTPUTS" / "reconstruction_camera_set.json").is_file(),
        "reconstruction_manifest.json": (root / "OUTPUTS" / "reconstruction_manifest.json").is_file(),
        "geometry_quality.json": (root / "OUTPUTS" / "geometry_quality.json").is_file(),
        "Gate06_Reconstruction_Diagnostic.ma": ma_path.is_file(),
        "logs": any(path.is_file() for path in (root / "LOGS").rglob("*")),
        "preview": any(path.is_file() for path in (root / "PREVIEWS").rglob("*")),
    }
    status = _write_contract_files(
        root,
        gate=6,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required=required,
        runtime_status=str(runtime.get("runtime_status") or runtime.get("status") or "UNKNOWN"),
        functional_status="PASS" if all(required.values()) else "FAIL",
        quality_status=str(runtime.get("geometry_quality_status") or quality_payload.get("status") or "UNKNOWN"),
        input_sources=[str(source), str(attempt_root / "gate5")],
        metrics={
            "sparse_point_count": sparse_count,
            "reconstructed_vertex_count": vertex_count,
            "reconstructed_face_count": face_count,
        },
        notes=[
            "Gate 6 PASS is based on the existence of a non-empty new P10 reconstruction, not on visual quality.",
            "Quality may be WARN and Gate 6 can still be functionally complete.",
            "The diagnostic Maya scene imports the raw P10 mesh and materializes sampled reconstruction cameras.",
        ],
    )
    _write_gate_index(p9, attempt_id)
    return status


def publish_gate7_output_tree(
    p9_run_dir: str | Path,
    p10_attempt_root: str | Path,
    *,
    p10_attempt_id: str | None = None,
) -> dict[str, Any]:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt_root = Path(p10_attempt_root).expanduser().resolve()
    attempt_id = str(p10_attempt_id or attempt_root.name)
    source = attempt_root / "gate7"
    root = gate_output_dir(p9, attempt_id, 7)
    _reset_gate_dir(root)

    gate6_root = gate_output_dir(p9, attempt_id, 6)
    raw_p10 = gate6_root / "OUTPUTS" / "reconstructed_mesh.ply"
    raw_p10_obj = gate6_root / "OUTPUTS" / "reconstructed_mesh.obj"
    camera_manifest = gate6_root / "OUTPUTS" / "reconstruction_camera_set.json"
    fusion_manifest = source / "g7_4" / "protected_fusion_candidate_manifest.json"
    candidate = source / "g7_4" / "protected_fusion_candidate.ply"
    face_evidence = source / "g7_4" / "protected_fusion_face_provenance.npz"
    confidence = source / "g7_2c" / "geometry_confidence_manifest.json"
    constraints = source / "g7_3" / "constraints" / "free_space_constraints.npz"
    constraints_manifest = source / "g7_3" / "constraints" / "free_space_constraints_manifest.json"
    review = source / "g7_5" / "gate7_registration_provenance_review.png"
    runtime = source / "gate7_runtime_manifest.json"

    for src, name in (
        (raw_p10, "P10_reconstructed_mesh.ply"),
        (raw_p10_obj, "P10_reconstructed_mesh.obj"),
        (candidate, "fused_candidate_mesh.ply"),
        (face_evidence, "face_provenance_and_reason_codes.npz"),
        (confidence, "confidence_manifest.json"),
        (constraints, "free_space_constraints.npz"),
        (constraints_manifest, "free_space_constraints_manifest.json"),
        (fusion_manifest, "fusion_manifest.json"),
        (runtime, "gate7_runtime_manifest.json"),
    ):
        if src.is_file():
            _copy_file(src, root / "OUTPUTS" / name)

    if review.is_file():
        _copy_file(review, root / "PREVIEWS" / "GATE_07_SUMMARY.png")

    p9_maya = _find_p9_maya(p9)
    p9_pointer = {
        "p9_run_dir": str(p9),
        "p9_maya": str(p9_maya) if p9_maya else None,
        "policy": "P9_IMMUTABLE_REFERENCE_DO_NOT_DUPLICATE_HEAVY_AUTHORITY",
    }
    (root / "INPUTS" / "P9_ORIGINAL_POINTER.json").write_text(
        json.dumps(p9_pointer, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    fusion = _read_json(fusion_manifest)
    counts = fusion.get("counts") if isinstance(fusion.get("counts"), dict) else {}
    accepted_count = int(counts.get("p10_accepted_faces") or 0)
    rejected_count = int(counts.get("p10_rejected_faces") or 0)
    input_faces = int(counts.get("p10_input_faces") or 0)

    accepted_obj = root / "OUTPUTS" / "P10_ACCEPTED.obj"
    rejected_obj = root / "OUTPUTS" / "P10_REJECTED.obj"
    if raw_p10.is_file() and face_evidence.is_file():
        try:
            import numpy as np
            with np.load(face_evidence, allow_pickle=False) as payload:
                accepted_idx = payload["p10_accepted_face_indices"].astype("int64").tolist()
                rejected_idx = payload["p10_rejected_face_indices"].astype("int64").tolist()
            _write_selected_obj(raw_p10, accepted_idx, accepted_obj)
            _write_selected_obj(raw_p10, rejected_idx, rejected_obj)
        except Exception as error:
            (root / "LOGS" / "gate7_split_mesh_error.txt").write_text(
                f"{type(error).__name__}: {error}\n",
                encoding="utf-8",
            )

    ma_path = root / "OUTPUTS" / "Gate07_Fusion_Diagnostic.ma"
    gate7_obj_imports = [
        ("P10_RECONSTRUCTION", root / "OUTPUTS" / "P10_reconstructed_mesh.obj", (0.20, 0.45, 1.00)),
    ]
    if accepted_count > 0 and accepted_obj.is_file():
        gate7_obj_imports.append(("P10_ACCEPTED", accepted_obj, (0.20, 0.90, 0.30)))
    if rejected_count > 0 and rejected_obj.is_file():
        gate7_obj_imports.append(("P10_REJECTED", rejected_obj, (0.95, 0.25, 0.20)))
    _write_diagnostic_maya(
        ma_path,
        gate=7,
        p9_maya_reference=p9_maya,
        obj_imports=gate7_obj_imports,
        camera_manifest_path=camera_manifest if camera_manifest.is_file() else None,
    )

    _copy_tree_files(source, root / "LOGS" / "GATE7_MANIFESTS", suffixes={".json", ".txt", ".log"})

    required = {
        "P9_original_reference": (root / "INPUTS" / "P9_ORIGINAL_POINTER.json").is_file() and bool(p9_pointer.get("p9_maya")),
        "P10_reconstructed_mesh": (root / "OUTPUTS" / "P10_reconstructed_mesh.ply").is_file(),
        "fused_candidate_mesh": (root / "OUTPUTS" / "fused_candidate_mesh.ply").is_file(),
        "face_provenance_reason_codes": (root / "OUTPUTS" / "face_provenance_and_reason_codes.npz").is_file(),
        "confidence": (root / "OUTPUTS" / "confidence_manifest.json").is_file(),
        "free_space_constraints": (root / "OUTPUTS" / "free_space_constraints.npz").is_file(),
        "fusion_manifest": (root / "OUTPUTS" / "fusion_manifest.json").is_file(),
        "Gate07_Fusion_Diagnostic.ma": ma_path.is_file(),
        "summary_preview": (root / "PREVIEWS" / "GATE_07_SUMMARY.png").is_file(),
    }
    functional = "PASS" if all(required.values()) and accepted_count > 0 else "FAIL"
    runtime_payload = _read_json(runtime)
    status = _write_contract_files(
        root,
        gate=7,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required=required,
        runtime_status=str(runtime_payload.get("status") or "UNKNOWN"),
        functional_status=functional,
        quality_status="PASS" if accepted_count > 0 else "FAIL",
        input_sources=[str(source), str(gate6_root)],
        metrics={
            "p10_input_faces": input_faces,
            "p10_accepted_faces": accepted_count,
            "p10_rejected_faces": rejected_count,
            "accepted_face_fraction": accepted_count / float(input_faces) if input_faces > 0 else None,
            "reason_counts": fusion.get("reason_counts") or {},
        },
        notes=[
            "Gate 7 runtime PASS does not imply functional PASS.",
            "Functional PASS requires a measurable P10 contribution after provenance/confidence/free-space filtering.",
            "The diagnostic Maya references P9 and layers raw/accepted/rejected P10 geometry separately.",
        ],
    )
    _write_gate_index(p9, attempt_id)
    return status


def publish_gate1_to_gate3_snapshots(
    p9_run_dir: str | Path,
    p10_attempt_root: str | Path,
    *,
    p10_attempt_id: str | None = None,
) -> list[dict[str, Any]]:
    p9 = Path(p9_run_dir).expanduser().resolve()
    attempt_root = Path(p10_attempt_root).expanduser().resolve()
    attempt_id = str(p10_attempt_id or attempt_root.name)
    statuses = []

    root = gate_output_dir(p9, attempt_id, 1)
    _reset_gate_dir(root)
    copied = []
    for name in ("manifest.json", "output_index.json", "RUN_PARAMETERS.txt"):
        src = p9 / name
        if src.is_file():
            copied.append(_copy_file(src, root / "OUTPUTS" / name))
    status = _write_contract_files(
        root,
        gate=1,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required={
            "run_manifest": (root / "OUTPUTS" / "manifest.json").is_file(),
            "output_index": (root / "OUTPUTS" / "output_index.json").is_file(),
            "run_parameters": (root / "OUTPUTS" / "RUN_PARAMETERS.txt").is_file(),
        },
        runtime_status="REUSED",
        functional_status="PASS" if len(copied) >= 2 else "FAIL",
        quality_status=None,
        input_sources=[str(p9)],
        notes=["Gate 1 snapshot is reconstructed from the already accepted P9 run."],
    )
    statuses.append(status)

    root = gate_output_dir(p9, attempt_id, 2)
    _reset_gate_dir(root)
    pointers = {
        "p9_run_dir": str(p9),
        "attempt_manifest": str(attempt_root / "attempt_manifest.json"),
        "policy": "P9_IMMUTABLE_P10_SEPARATE",
    }
    (root / "OUTPUTS" / "P9_HANDOFF_POINTERS.json").write_text(
        json.dumps(pointers, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if (attempt_root / "attempt_manifest.json").is_file():
        _copy_file(attempt_root / "attempt_manifest.json", root / "OUTPUTS" / "attempt_manifest.json")
    status = _write_contract_files(
        root,
        gate=2,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required={
            "P9_HANDOFF_POINTERS.json": (root / "OUTPUTS" / "P9_HANDOFF_POINTERS.json").is_file(),
            "attempt_manifest.json": (root / "OUTPUTS" / "attempt_manifest.json").is_file(),
        },
        runtime_status="REUSED",
        functional_status="PASS" if (root / "OUTPUTS" / "attempt_manifest.json").is_file() else "FAIL",
        quality_status=None,
        input_sources=[str(p9), str(attempt_root)],
        notes=["Gate 2 records immutable handoff pointers instead of duplicating heavy P9 authority."],
    )
    statuses.append(status)

    root = gate_output_dir(p9, attempt_id, 3)
    _reset_gate_dir(root)
    gate4 = attempt_root / "gate4"
    for name in ("source_lock_known_unknown.png", "raw_holes_contact_sheet.png"):
        src = gate4 / name
        if src.is_file():
            _copy_file(src, root / "PREVIEWS" / name)
    explicit_free = gate4 / "free_space_mask.png"
    explicit_conflict = gate4 / "conflict_mask.png"
    if explicit_free.is_file():
        _copy_file(explicit_free, root / "OUTPUTS" / "free_space_mask.png")
    if explicit_conflict.is_file():
        _copy_file(explicit_conflict, root / "OUTPUTS" / "conflict_mask.png")
    known_unknown = (root / "PREVIEWS" / "source_lock_known_unknown.png").is_file()
    full_contract = explicit_free.is_file() and explicit_conflict.is_file()
    status = _write_contract_files(
        root,
        gate=3,
        p9_run_dir=p9,
        p10_attempt_id=attempt_id,
        required={
            "known_unknown_visualization": known_unknown,
            "explicit_free_space_mask": full_contract and (root / "OUTPUTS" / "free_space_mask.png").is_file(),
            "explicit_conflict_mask": full_contract and (root / "OUTPUTS" / "conflict_mask.png").is_file(),
        },
        runtime_status="REUSED",
        functional_status="PASS" if known_unknown and full_contract else "FAIL",
        quality_status=None,
        input_sources=[str(gate4)],
        notes=[
            "Gate 3 is intentionally surfaced as incomplete until explicit free-space and conflict masks exist at this gate.",
            "Later Gate 7 free-space evidence does not retroactively prove the Gate 3 contract.",
        ],
    )
    statuses.append(status)

    _write_gate_index(p9, attempt_id)
    return statuses
