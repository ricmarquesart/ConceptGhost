from __future__ import annotations

from array import array
from dataclasses import dataclass
import html
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess

from .contracts import ContractError


@dataclass(frozen=True)
class ColmapMeshStep:
    command: str
    args: tuple[str, ...]

    def argv(self, executable: str) -> tuple[str, ...]:
        return (executable, self.command, *self.args)


@dataclass(frozen=True)
class PreFusionMeshPlan:
    dataset_root: Path
    fused_ply_path: Path
    mesh_path: Path
    preview_path: Path
    poisson_depth: int
    poisson_trim: float
    point_weight: float
    color: bool
    steps: tuple[ColmapMeshStep, ...]

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10PreFusionMeshPlan.v0.1",
            "dataset_root": str(self.dataset_root),
            "fused_ply_path": str(self.fused_ply_path),
            "mesh_path": str(self.mesh_path),
            "preview_path": str(self.preview_path),
            "poisson_depth": self.poisson_depth,
            "poisson_trim": self.poisson_trim,
            "point_weight": self.point_weight,
            "color": self.color,
            "purpose": "P10_PRE_FUSION_SURFACE_FOR_GATE7",
            "steps": [
                {"command": step.command, "args": list(step.args)}
                for step in self.steps
            ],
        }


def _resolve_executable(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ContractError("COLMAP executable cannot be empty")
    path = Path(value)
    if path.parent != Path("."):
        if not path.is_file():
            raise ContractError(f"COLMAP executable does not exist: {path}")
        return str(path)
    return shutil.which(value) or value


def build_prefusion_mesh_plan(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    poisson_depth: int = 10,
    poisson_trim: float = 10.0,
    point_weight: float = 1.0,
    color: bool = True,
) -> PreFusionMeshPlan:
    dataset_root = Path(dataset_root).resolve()
    fused_ply = dataset_root / "dense" / "fused.ply"
    if not fused_ply.is_file():
        raise ContractError(f"Missing Gate 6.4 fused cloud: {fused_ply}")
    if type(poisson_depth) is not int or not (6 <= poisson_depth <= 14):
        raise ContractError("poisson_depth must be an integer in [6, 14]")
    if not math.isfinite(float(poisson_trim)) or float(poisson_trim) < 0.0:
        raise ContractError("poisson_trim must be finite and nonnegative")
    if not math.isfinite(float(point_weight)) or float(point_weight) < 0.0:
        raise ContractError("point_weight must be finite and nonnegative")

    mesh_path = dataset_root / "dense" / "pre_fusion_mesh.ply"
    preview_path = dataset_root / "dense" / "pre_fusion_mesh_preview.svg"
    step = ColmapMeshStep(
        "poisson_mesher",
        (
            "--input_path", str(fused_ply),
            "--output_path", str(mesh_path),
            "--PoissonMeshing.depth", str(poisson_depth),
            "--PoissonMeshing.trim", f"{float(poisson_trim):g}",
            "--PoissonMeshing.point_weight", f"{float(point_weight):g}",
            "--PoissonMeshing.color", "1" if color else "0",
        ),
    )
    return PreFusionMeshPlan(
        dataset_root=dataset_root,
        fused_ply_path=fused_ply,
        mesh_path=mesh_path,
        preview_path=preview_path,
        poisson_depth=poisson_depth,
        poisson_trim=float(poisson_trim),
        point_weight=float(point_weight),
        color=bool(color),
        steps=(step,),
    )


_PLY_SCALAR = {
    "char": ("b", 1),
    "int8": ("b", 1),
    "uchar": ("B", 1),
    "uint8": ("B", 1),
    "short": ("h", 2),
    "int16": ("h", 2),
    "ushort": ("H", 2),
    "uint16": ("H", 2),
    "int": ("i", 4),
    "int32": ("i", 4),
    "uint": ("I", 4),
    "uint32": ("I", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
    "double": ("d", 8),
    "float64": ("d", 8),
}


@dataclass(frozen=True)
class _PlyHeader:
    format_name: str
    vertex_count: int
    face_count: int
    vertex_properties: tuple[tuple[str, str], ...]
    face_count_type: str
    face_index_type: str
    data_offset: int


def _read_mesh_header(stream) -> _PlyHeader:
    first = stream.readline()
    if first.strip() != b"ply":
        raise ContractError("Invalid PLY header")

    format_name = None
    vertex_count = None
    face_count = None
    vertex_properties: list[tuple[str, str]] = []
    face_count_type = None
    face_index_type = None
    active_element = None

    while True:
        raw = stream.readline()
        if not raw:
            raise ContractError("Unexpected EOF inside PLY header")
        try:
            line = raw.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise ContractError("PLY header is not ASCII") from error
        if line == "end_header":
            break
        if not line or line.startswith("comment"):
            continue
        parts = line.split()
        if parts[0] == "format":
            if len(parts) < 2:
                raise ContractError("Malformed PLY format line")
            format_name = parts[1]
        elif parts[0] == "element":
            if len(parts) != 3:
                raise ContractError("Malformed PLY element line")
            active_element = parts[1]
            if active_element == "vertex":
                vertex_count = int(parts[2])
            elif active_element == "face":
                face_count = int(parts[2])
        elif parts[0] == "property":
            if active_element == "vertex":
                if len(parts) != 3 or parts[1] == "list":
                    raise ContractError("Unsupported vertex PLY property")
                if parts[1] not in _PLY_SCALAR:
                    raise ContractError(f"Unsupported PLY vertex type: {parts[1]}")
                vertex_properties.append((parts[1], parts[2]))
            elif active_element == "face":
                if len(parts) == 5 and parts[1] == "list":
                    name = parts[4]
                    if name in {"vertex_index", "vertex_indices"}:
                        if parts[2] not in _PLY_SCALAR or parts[3] not in _PLY_SCALAR:
                            raise ContractError("Unsupported PLY face list type")
                        face_count_type = parts[2]
                        face_index_type = parts[3]

    if format_name not in {"ascii", "binary_little_endian"}:
        raise ContractError(f"Unsupported PLY format: {format_name}")
    if vertex_count is None or vertex_count <= 0:
        raise ContractError("PLY mesh requires at least one vertex")
    if face_count is None or face_count <= 0:
        raise ContractError("PLY mesh requires at least one face")
    names = [name for _, name in vertex_properties]
    for required in ("x", "y", "z"):
        if required not in names:
            raise ContractError(f"PLY vertex section is missing {required}")
    if face_count_type is None or face_index_type is None:
        raise ContractError("PLY mesh is missing a vertex-index face list")

    return _PlyHeader(
        format_name=format_name,
        vertex_count=vertex_count,
        face_count=face_count,
        vertex_properties=tuple(vertex_properties),
        face_count_type=face_count_type,
        face_index_type=face_index_type,
        data_offset=stream.tell(),
    )


def _read_mesh(path: Path, max_preview_faces: int):
    if type(max_preview_faces) is not int or max_preview_faces < 1:
        raise ContractError("max_preview_faces must be a positive integer")

    with path.open("rb") as stream:
        header = _read_mesh_header(stream)
        names = [name for _, name in header.vertex_properties]
        x_index, y_index, z_index = names.index("x"), names.index("y"), names.index("z")
        vertices = array("d")

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
                vertices.extend((
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                ))
        else:
            fmt = "<" + "".join(_PLY_SCALAR[dtype][0] for dtype, _ in header.vertex_properties)
            size = struct.calcsize(fmt)
            for _ in range(header.vertex_count):
                raw = stream.read(size)
                if len(raw) != size:
                    raise ContractError("Unexpected EOF in binary PLY vertices")
                values = struct.unpack(fmt, raw)
                vertices.extend((
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                ))

        face_stride = max(1, math.ceil(header.face_count / max_preview_faces))
        sampled_faces: list[tuple[int, int, int]] = []
        invalid_face_count = 0

        if header.format_name == "ascii":
            for face_index in range(header.face_count):
                raw = stream.readline()
                if not raw:
                    raise ContractError("Unexpected EOF in ASCII PLY faces")
                parts = raw.decode("ascii").split()
                if not parts:
                    raise ContractError("Malformed ASCII PLY face row")
                count = int(parts[0])
                if count != 3 or len(parts) < 4:
                    raise ContractError("Gate 6.5 requires triangular PLY faces")
                face = (int(parts[1]), int(parts[2]), int(parts[3]))
                if any(index < 0 or index >= header.vertex_count for index in face):
                    invalid_face_count += 1
                elif face_index % face_stride == 0:
                    sampled_faces.append(face)
        else:
            count_code = _PLY_SCALAR[header.face_count_type][0]
            count_size = _PLY_SCALAR[header.face_count_type][1]
            index_code = _PLY_SCALAR[header.face_index_type][0]
            index_size = _PLY_SCALAR[header.face_index_type][1]
            for face_index in range(header.face_count):
                raw = stream.read(count_size)
                if len(raw) != count_size:
                    raise ContractError("Unexpected EOF in binary PLY face list")
                count = struct.unpack("<" + count_code, raw)[0]
                if count != 3:
                    raise ContractError("Gate 6.5 requires triangular PLY faces")
                raw = stream.read(index_size * count)
                if len(raw) != index_size * count:
                    raise ContractError("Unexpected EOF in binary PLY face indices")
                face = tuple(int(v) for v in struct.unpack("<" + index_code * count, raw))
                if any(index < 0 or index >= header.vertex_count for index in face):
                    invalid_face_count += 1
                elif face_index % face_stride == 0:
                    sampled_faces.append(face)

    return header, vertices, tuple(sampled_faces), invalid_face_count


def _vertex(vertices: array, index: int) -> tuple[float, float, float]:
    base = index * 3
    return float(vertices[base]), float(vertices[base + 1]), float(vertices[base + 2])


def _bounds(vertices: array):
    xs = vertices[0::3]
    ys = vertices[1::3]
    zs = vertices[2::3]
    return {
        "x": [float(min(xs)), float(max(xs))],
        "y": [float(min(ys)), float(max(ys))],
        "z": [float(min(zs)), float(max(zs))],
    }


def _is_degenerate(a, b, c, scale: float) -> bool:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    area2_sq = cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2
    threshold = max(scale, 1.0) ** 4 * 1.0e-20
    return area2_sq <= threshold


def _project(value: float, lo: float, hi: float, start: float, size: float) -> float:
    if abs(hi - lo) < 1.0e-12:
        return start + size * 0.5
    return start + (value - lo) / (hi - lo) * size


def _render_panel(vertices, faces, bounds, *, axis_a, axis_b, title, x0, y0, size):
    names = ("x", "y", "z")
    lo_a, hi_a = bounds[names[axis_a]]
    lo_b, hi_b = bounds[names[axis_b]]
    pad = 26.0
    usable = size - 2.0 * pad
    out = [
        f'<rect x="{x0}" y="{y0}" width="{size}" height="{size}" fill="#151515" stroke="#555"/>',
        f'<text x="{x0 + 12}" y="{y0 + 20}" fill="#f0f0f0" font-size="14">{html.escape(title)}</text>',
    ]
    for face in faces:
        pts = [_vertex(vertices, index) for index in face]
        projected = []
        for point in pts:
            px = _project(point[axis_a], lo_a, hi_a, x0 + pad, usable)
            py = y0 + size - pad - (_project(point[axis_b], lo_b, hi_b, 0.0, usable))
            projected.append((px, py))
        path = " ".join(f"{x:.2f},{y:.2f}" for x, y in projected)
        out.append(
            f'<polygon points="{path}" fill="none" stroke="#9ecbff" '
            f'stroke-width="0.7" stroke-opacity="0.45"/>'
        )
    return "".join(out)


def analyze_and_render_mesh(
    mesh_path: str | Path,
    preview_path: str | Path,
    *,
    max_preview_faces: int = 12000,
) -> dict[str, object]:
    mesh_path = Path(mesh_path)
    preview_path = Path(preview_path)
    if not mesh_path.is_file():
        raise ContractError(f"Missing pre-fusion mesh: {mesh_path}")

    header, vertices, sampled_faces, invalid_face_count = _read_mesh(
        mesh_path,
        max_preview_faces,
    )
    bounds = _bounds(vertices)
    spans = {axis: values[1] - values[0] for axis, values in bounds.items()}
    max_span = max(spans.values())
    flattened = [
        axis for axis, span in spans.items()
        if max_span > 0.0 and span <= max_span * 1.0e-4
    ]

    degenerate = 0
    for face in sampled_faces:
        if _is_degenerate(
            _vertex(vertices, face[0]),
            _vertex(vertices, face[1]),
            _vertex(vertices, face[2]),
            max_span,
        ):
            degenerate += 1
    sampled_count = len(sampled_faces)
    degenerate_fraction = degenerate / float(sampled_count) if sampled_count else 0.0

    warnings = []
    if invalid_face_count:
        warnings.append("INVALID_FACE_INDEX")
    if flattened:
        warnings.append("FLATTENED_AXIS")
    if degenerate_fraction > 0.05:
        warnings.append("HIGH_DEGENERATE_FACE_SAMPLE")
    if header.face_count < max(1, header.vertex_count // 8):
        warnings.append("LOW_FACE_DENSITY")

    panel = 480
    gap = 14
    width = panel * 3 + gap * 4
    height = panel + 92
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0d0d0d"/>',
        f'<text x="14" y="24" fill="#ffffff" font-size="17">ConceptGhost Gate 6.5 — pre-fusion mesh · vertices {header.vertex_count:,} · faces {header.face_count:,}</text>',
        f'<text x="14" y="46" fill="#bdbdbd" font-size="12">Sampled faces {sampled_count:,} · degenerate sample {degenerate_fraction:.2%} · warnings {html.escape(",".join(warnings) if warnings else "none")}</text>',
    ]
    base_y = 68
    svg.append(_render_panel(vertices, sampled_faces, bounds, axis_a=0, axis_b=2, title="TOP XZ", x0=gap, y0=base_y, size=panel))
    svg.append(_render_panel(vertices, sampled_faces, bounds, axis_a=0, axis_b=1, title="FRONT XY", x0=panel + gap * 2, y0=base_y, size=panel))
    svg.append(_render_panel(vertices, sampled_faces, bounds, axis_a=2, axis_b=1, title="SIDE ZY", x0=panel * 2 + gap * 3, y0=base_y, size=panel))
    svg.append("</svg>")
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("".join(svg), encoding="utf-8")

    return {
        "vertex_count": header.vertex_count,
        "face_count": header.face_count,
        "face_vertex_ratio": header.face_count / float(header.vertex_count),
        "sampled_face_count": sampled_count,
        "invalid_face_index_count": invalid_face_count,
        "degenerate_face_sample_count": degenerate,
        "degenerate_face_sample_fraction": degenerate_fraction,
        "bounds": bounds,
        "spans": spans,
        "flattened_axes_warning": flattened,
        "warnings": warnings,
        "health_status": "WARN" if warnings else "PASS",
        "preview_path": str(preview_path.resolve()),
    }


def run_prefusion_meshing(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    poisson_depth: int = 10,
    poisson_trim: float = 10.0,
    point_weight: float = 1.0,
    overwrite_output: bool = False,
) -> dict[str, object]:
    plan = build_prefusion_mesh_plan(
        dataset_root,
        colmap_executable=colmap_executable,
        poisson_depth=poisson_depth,
        poisson_trim=poisson_trim,
        point_weight=point_weight,
        color=True,
    )
    executable = _resolve_executable(colmap_executable)

    if plan.mesh_path.exists():
        if not overwrite_output:
            raise ContractError(
                f"Refusing to overwrite completed pre-fusion mesh: {plan.mesh_path}"
            )
        plan.mesh_path.unlink()

    log_root = plan.dataset_root / "logs" / "gate6_5"
    log_root.mkdir(parents=True, exist_ok=True)
    executed = []

    for index, step in enumerate(plan.steps):
        argv = list(step.argv(executable))
        result = subprocess.run(
            argv,
            cwd=str(plan.dataset_root),
            capture_output=True,
            text=True,
            check=False,
        )
        log_path = log_root / f"{index:02d}_{step.command}.log"
        log_path.write_text(
            "COMMAND\n" + " ".join(argv)
            + "\n\nSTDOUT\n" + (result.stdout or "")
            + "\n\nSTDERR\n" + (result.stderr or ""),
            encoding="utf-8",
        )
        executed.append({
            "index": index,
            "command": step.command,
            "argv": argv,
            "returncode": int(result.returncode),
            "log_path": str(log_path.resolve()),
        })
        if result.returncode != 0:
            raise RuntimeError(
                f"COLMAP {step.command} failed with exit code {result.returncode}; "
                f"see {log_path}"
            )

    if not plan.mesh_path.is_file():
        raise ContractError("Poisson meshing completed without pre_fusion_mesh.ply")

    mesh_health = analyze_and_render_mesh(
        plan.mesh_path,
        plan.preview_path,
        max_preview_faces=12000,
    )

    dense_manifest_path = plan.dataset_root / "dense_reconstruction_manifest.json"
    source_dense = None
    if dense_manifest_path.is_file():
        try:
            source_dense = json.loads(dense_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            source_dense = None

    result_manifest = {
        "schema": "ConceptGhost.P10PreFusionMeshResult.v0.1",
        **plan.manifest(),
        "status": "PASS",
        "colmap_executable": executable,
        "executed": executed,
        "mesh_health": mesh_health,
        "visual_evidence_path": mesh_health["preview_path"],
        "diagnostic_log_root": str(log_root.resolve()),
        "source_dense_manifest_path": (
            str(dense_manifest_path.resolve()) if dense_manifest_path.is_file() else None
        ),
        "source_dense_vertex_count": (
            source_dense.get("fused_cloud", {}).get("vertex_count")
            if isinstance(source_dense, dict) else None
        ),
    }
    result_path = plan.dataset_root / "prefusion_mesh_manifest.json"
    result_path.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_manifest
