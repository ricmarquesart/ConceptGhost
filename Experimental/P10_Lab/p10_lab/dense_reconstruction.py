from __future__ import annotations

from dataclasses import dataclass
import html
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
from typing import Iterable

from .contracts import ContractError


@dataclass(frozen=True)
class ColmapDenseStep:
    command: str
    args: tuple[str, ...]

    def argv(self, executable: str) -> tuple[str, ...]:
        return (executable, self.command, *self.args)


@dataclass(frozen=True)
class DenseReconstructionPlan:
    dataset_root: Path
    sparse_model_path: Path
    dense_root: Path
    fused_ply_path: Path
    preview_path: Path
    max_image_size: int
    patch_match_cache_gb: float
    fusion_cache_gb: float
    min_num_pixels: int
    geom_consistency: bool
    steps: tuple[ColmapDenseStep, ...]

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10DenseReconstructionPlan.v0.1",
            "dataset_root": str(self.dataset_root),
            "sparse_model_path": str(self.sparse_model_path),
            "dense_root": str(self.dense_root),
            "fused_ply_path": str(self.fused_ply_path),
            "preview_path": str(self.preview_path),
            "max_image_size": self.max_image_size,
            "patch_match_cache_gb": self.patch_match_cache_gb,
            "fusion_cache_gb": self.fusion_cache_gb,
            "min_num_pixels": self.min_num_pixels,
            "geom_consistency": self.geom_consistency,
            "hardware_profile": "RTX_2080_TI_11GB_FIRST_PASS",
            "visual_evidence": "THREE_ORTHOGRAPHIC_POINT_PROJECTIONS_SVG",
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


def build_dense_plan(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    max_image_size: int = 832,
    patch_match_cache_gb: float = 4.0,
    fusion_cache_gb: float = 4.0,
    min_num_pixels: int = 2,
    geom_consistency: bool = True,
) -> DenseReconstructionPlan:
    dataset_root = Path(dataset_root).resolve()
    images_dir = dataset_root / "images"
    sparse_model = dataset_root / "sparse" / "triangulated"

    if not images_dir.is_dir():
        raise ContractError(f"Missing Gate 6 images directory: {images_dir}")
    if not sparse_model.is_dir():
        raise ContractError(f"Missing triangulated sparse model: {sparse_model}")
    for name in ("cameras.bin", "images.bin", "points3D.bin"):
        if not (sparse_model / name).is_file():
            raise ContractError(f"Incomplete triangulated sparse model: missing {name}")

    if type(max_image_size) is not int or max_image_size < 256:
        raise ContractError("max_image_size must be an integer >= 256")
    if float(patch_match_cache_gb) <= 0.0 or float(fusion_cache_gb) <= 0.0:
        raise ContractError("dense cache sizes must be positive")
    if type(min_num_pixels) is not int or min_num_pixels < 1:
        raise ContractError("min_num_pixels must be a positive integer")

    dense_root = dataset_root / "dense"
    fused_ply = dense_root / "fused.ply"
    preview_path = dense_root / "dense_fused_preview.svg"

    steps = (
        ColmapDenseStep(
            "image_undistorter",
            (
                "--image_path", str(images_dir),
                "--input_path", str(sparse_model),
                "--output_path", str(dense_root),
                "--output_type", "COLMAP",
                "--max_image_size", str(max_image_size),
            ),
        ),
        ColmapDenseStep(
            "patch_match_stereo",
            (
                "--workspace_path", str(dense_root),
                "--workspace_format", "COLMAP",
                # COLMAP CLI boolean parsing has varied across releases; use 1/0
                # instead of true/false so geometric mode cannot silently become OFF.
                "--PatchMatchStereo.geom_consistency", "1" if geom_consistency else "0",
                # Gate 7 free-space authority consumes the geometric consistency graph.
                # COLMAP does not write it by default, even when geom_consistency is ON.
                "--PatchMatchStereo.write_consistency_graph", "1" if geom_consistency else "0",
                "--PatchMatchStereo.max_image_size", str(max_image_size),
                "--PatchMatchStereo.cache_size", f"{float(patch_match_cache_gb):g}",
                "--PatchMatchStereo.gpu_index", "0",
                "--PatchMatchStereo.num_iterations", "3",
            ),
        ),
        ColmapDenseStep(
            "stereo_fusion",
            (
                "--workspace_path", str(dense_root),
                "--workspace_format", "COLMAP",
                "--input_type", "geometric" if geom_consistency else "photometric",
                "--output_type", "PLY",
                "--output_path", str(fused_ply),
                "--StereoFusion.max_image_size", str(max_image_size),
                "--StereoFusion.cache_size", f"{float(fusion_cache_gb):g}",
                "--StereoFusion.min_num_pixels", str(min_num_pixels),
            ),
        ),
    )

    return DenseReconstructionPlan(
        dataset_root=dataset_root,
        sparse_model_path=sparse_model,
        dense_root=dense_root,
        fused_ply_path=fused_ply,
        preview_path=preview_path,
        max_image_size=max_image_size,
        patch_match_cache_gb=float(patch_match_cache_gb),
        fusion_cache_gb=float(fusion_cache_gb),
        min_num_pixels=min_num_pixels,
        geom_consistency=bool(geom_consistency),
        steps=steps,
    )


_PLY_TYPE_INFO = {
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


def _read_ply_header(stream):
    first = stream.readline()
    if first != b"ply\n" and first.strip() != b"ply":
        raise ContractError("Invalid PLY header")
    format_name = None
    vertex_count = None
    in_vertex = False
    vertex_properties = []

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
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                vertex_count = int(parts[2])
        elif parts[0] == "property" and in_vertex:
            if len(parts) != 3:
                raise ContractError("List properties are not supported in PLY vertex section")
            dtype, name = parts[1], parts[2]
            if dtype not in _PLY_TYPE_INFO:
                raise ContractError(f"Unsupported PLY vertex type: {dtype}")
            vertex_properties.append((dtype, name))

    if format_name not in {"ascii", "binary_little_endian"}:
        raise ContractError(f"Unsupported PLY format: {format_name}")
    if vertex_count is None or vertex_count < 0:
        raise ContractError("PLY is missing a valid vertex count")
    names = [name for _, name in vertex_properties]
    for required in ("x", "y", "z"):
        if required not in names:
            raise ContractError(f"PLY vertex section is missing {required}")
    return format_name, vertex_count, tuple(vertex_properties), stream.tell()


def _sample_ply_points(path: Path, max_points: int):
    if type(max_points) is not int or max_points < 1:
        raise ContractError("max_points must be a positive integer")
    with path.open("rb") as stream:
        format_name, vertex_count, properties, data_offset = _read_ply_header(stream)
        if vertex_count == 0:
            return vertex_count, []

        stride = max(1, math.ceil(vertex_count / max_points))
        names = [name for _, name in properties]
        x_index, y_index, z_index = (names.index("x"), names.index("y"), names.index("z"))
        r_index = names.index("red") if "red" in names else None
        g_index = names.index("green") if "green" in names else None
        b_index = names.index("blue") if "blue" in names else None

        sampled = []
        if format_name == "ascii":
            stream.seek(data_offset)
            for index in range(vertex_count):
                line = stream.readline()
                if not line:
                    raise ContractError("Unexpected EOF in ASCII PLY vertices")
                if index % stride:
                    continue
                parts = line.decode("ascii").split()
                if len(parts) < len(properties):
                    raise ContractError("Malformed ASCII PLY vertex row")
                values = []
                for (dtype, _), token in zip(properties, parts):
                    code = _PLY_TYPE_INFO[dtype][0]
                    values.append(float(token) if code in {"f", "d"} else int(token))
                color = (
                    int(values[r_index]) if r_index is not None else 210,
                    int(values[g_index]) if g_index is not None else 210,
                    int(values[b_index]) if b_index is not None else 210,
                )
                sampled.append((
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                    color,
                ))
        else:
            fmt = "<" + "".join(_PLY_TYPE_INFO[dtype][0] for dtype, _ in properties)
            record_size = struct.calcsize(fmt)
            for index in range(0, vertex_count, stride):
                stream.seek(data_offset + index * record_size)
                raw = stream.read(record_size)
                if len(raw) != record_size:
                    raise ContractError("Unexpected EOF in binary PLY vertices")
                values = struct.unpack(fmt, raw)
                color = (
                    int(values[r_index]) if r_index is not None else 210,
                    int(values[g_index]) if g_index is not None else 210,
                    int(values[b_index]) if b_index is not None else 210,
                )
                sampled.append((
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                    color,
                ))
        return vertex_count, sampled


def _axis_bounds(points, axis_index):
    values = [point[axis_index] for point in points]
    return min(values), max(values)


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise ContractError("Cannot compute quantile of empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    amount = position - lo
    return ordered[lo] * (1.0 - amount) + ordered[hi] * amount


def _projection_bounds(points, axis_a: int, axis_b: int):
    a_values = [p[axis_a] for p in points]
    b_values = [p[axis_b] for p in points]
    a0, a1 = _quantile(a_values, 0.01), _quantile(a_values, 0.99)
    b0, b1 = _quantile(b_values, 0.01), _quantile(b_values, 0.99)
    if abs(a1 - a0) < 1e-9:
        a0 -= 0.5
        a1 += 0.5
    if abs(b1 - b0) < 1e-9:
        b0 -= 0.5
        b1 += 0.5
    return a0, a1, b0, b1


def _svg_projection(points, *, x_axis, y_axis, title, x0, y0, size):
    lo_x, hi_x, lo_y, hi_y = _projection_bounds(points, x_axis, y_axis)
    pad = 26.0
    usable = size - 2.0 * pad
    items = [
        f'<rect x="{x0}" y="{y0}" width="{size}" height="{size}" fill="#151515" stroke="#555"/>',
        f'<text x="{x0 + 12}" y="{y0 + 20}" fill="#f0f0f0" font-size="14">{html.escape(title)}</text>',
    ]
    max_draw = 9000
    draw_stride = max(1, math.ceil(len(points) / max_draw))
    for point in points[::draw_stride]:
        px = x0 + pad + (point[x_axis] - lo_x) / (hi_x - lo_x) * usable
        py = y0 + size - pad - (point[y_axis] - lo_y) / (hi_y - lo_y) * usable
        red, green, blue = point[3]
        items.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.15" '
            f'fill="rgb({red},{green},{blue})" fill-opacity="0.75"/>'
        )
    return "".join(items)


def analyze_and_render_fused_cloud(
    fused_ply_path: str | Path,
    preview_path: str | Path,
    *,
    max_preview_points: int = 50000,
) -> dict[str, object]:
    fused_ply_path = Path(fused_ply_path)
    preview_path = Path(preview_path)
    if not fused_ply_path.is_file():
        raise ContractError(f"Missing fused PLY: {fused_ply_path}")

    vertex_count, points = _sample_ply_points(fused_ply_path, max_preview_points)
    if vertex_count <= 0 or not points:
        raise ContractError("Dense fused point cloud contains no vertices")

    bounds = {
        "x": list(_axis_bounds(points, 0)),
        "y": list(_axis_bounds(points, 1)),
        "z": list(_axis_bounds(points, 2)),
    }
    spans = {axis: values[1] - values[0] for axis, values in bounds.items()}
    max_span = max(spans.values())
    flattened_axes = [
        axis for axis, span in spans.items()
        if max_span > 0.0 and span <= max_span * 1.0e-4
    ]

    panel = 480
    gap = 14
    width = panel * 3 + gap * 4
    height = panel + 86
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0d0d0d"/>',
        f'<text x="14" y="24" fill="#ffffff" font-size="17">ConceptGhost Gate 6.4 — dense fused cloud · vertices {vertex_count:,} · sampled {len(points):,}</text>',
        f'<text x="14" y="46" fill="#bdbdbd" font-size="12">Sampled bounds X {bounds["x"][0]:.3g}..{bounds["x"][1]:.3g} · Y {bounds["y"][0]:.3g}..{bounds["y"][1]:.3g} · Z {bounds["z"][0]:.3g}..{bounds["z"][1]:.3g}</text>',
    ]
    base_y = 64
    svg.append(_svg_projection(points, x_axis=0, y_axis=2, title="TOP XZ", x0=gap, y0=base_y, size=panel))
    svg.append(_svg_projection(points, x_axis=0, y_axis=1, title="FRONT XY", x0=panel + gap * 2, y0=base_y, size=panel))
    svg.append(_svg_projection(points, x_axis=2, y_axis=1, title="SIDE ZY", x0=panel * 2 + gap * 3, y0=base_y, size=panel))
    svg.append("</svg>")

    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("".join(svg), encoding="utf-8")
    return {
        "vertex_count": vertex_count,
        "sampled_point_count": len(points),
        "sampled_bounds_are_approximate": vertex_count > len(points),
        "bounds": bounds,
        "spans": spans,
        "flattened_axes_warning": flattened_axes,
        "preview_path": str(preview_path.resolve()),
    }


def _count_matching_files(root: Path, suffix: str) -> int:
    if not root.is_dir():
        return 0
    return sum(1 for path in root.rglob(f"*{suffix}") if path.is_file())


def run_dense_reconstruction(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    max_image_size: int = 832,
    patch_match_cache_gb: float = 4.0,
    fusion_cache_gb: float = 4.0,
    min_num_pixels: int = 2,
    overwrite_output: bool = False,
) -> dict[str, object]:
    plan = build_dense_plan(
        dataset_root,
        colmap_executable=colmap_executable,
        max_image_size=max_image_size,
        patch_match_cache_gb=patch_match_cache_gb,
        fusion_cache_gb=fusion_cache_gb,
        min_num_pixels=min_num_pixels,
        geom_consistency=True,
    )
    executable = _resolve_executable(colmap_executable)

    if plan.fused_ply_path.exists():
        if not overwrite_output:
            raise ContractError(
                f"Refusing to overwrite completed dense fused cloud: {plan.fused_ply_path}"
            )
        shutil.rmtree(plan.dense_root)

    plan.dense_root.mkdir(parents=True, exist_ok=True)
    log_root = plan.dataset_root / "logs" / "gate6_4"
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
            "log_path": str(log_path),
        })
        if result.returncode != 0:
            raise RuntimeError(
                f"COLMAP {step.command} failed with exit code {result.returncode}; "
                f"see {log_path}"
            )

    if not plan.fused_ply_path.is_file():
        raise ContractError("COLMAP dense fusion completed without fused.ply")

    cloud_health = analyze_and_render_fused_cloud(
        plan.fused_ply_path,
        plan.preview_path,
        max_preview_points=50000,
    )
    depth_map_root = plan.dense_root / "stereo" / "depth_maps"
    normal_map_root = plan.dense_root / "stereo" / "normal_maps"
    consistency_root = plan.dense_root / "stereo" / "consistency_graphs"
    depth_map_count = _count_matching_files(depth_map_root, ".bin")
    normal_map_count = _count_matching_files(normal_map_root, ".bin")
    geometric_depth_map_count = _count_matching_files(depth_map_root, ".geometric.bin")
    geometric_normal_map_count = _count_matching_files(normal_map_root, ".geometric.bin")
    consistency_graph_count = _count_matching_files(consistency_root, ".geometric.bin")

    # A successful COLMAP return code is not sufficient for Gate 7.  Gate 7.3
    # explicitly requires geometric depth plus consistency-graph evidence.
    if plan.geom_consistency and geometric_depth_map_count <= 0:
        raise ContractError(
            "COLMAP dense reconstruction produced no geometric depth maps; "
            "Gate 7 free-space evidence cannot run"
        )
    if plan.geom_consistency and consistency_graph_count <= 0:
        raise ContractError(
            "COLMAP dense reconstruction produced no geometric consistency graphs; "
            "PatchMatchStereo.write_consistency_graph must be enabled for Gate 7"
        )

    sparse_manifest_path=plan.dataset_root/"sparse_triangulation_manifest.json"
    sparse_manifest=None
    if sparse_manifest_path.is_file():
        try:
            candidate=json.loads(sparse_manifest_path.read_text(encoding="utf-8"))
            if isinstance(candidate,dict):
                sparse_manifest=candidate
        except (OSError,json.JSONDecodeError):
            sparse_manifest=None

    result_manifest = {
        "schema": "ConceptGhost.P10DenseReconstructionResult.v0.3",
        **plan.manifest(),
        "status": "PASS",
        "colmap_executable": executable,
        "executed": executed,
        "depth_map_file_count": depth_map_count,
        "normal_map_file_count": normal_map_count,
        "geometric_depth_map_file_count": geometric_depth_map_count,
        "geometric_normal_map_file_count": geometric_normal_map_count,
        "geometric_consistency_graph_file_count": consistency_graph_count,
        "gate7_geometric_evidence_ready": bool(
            geometric_depth_map_count > 0 and consistency_graph_count > 0
        ),
        "fused_cloud": cloud_health,
        "source_sparse_manifest_path":(
            str(sparse_manifest_path.resolve()) if sparse_manifest_path.is_file() else None
        ),
        "verified_sparse_component_count":(
            sparse_manifest.get("verified_component_count")
            if isinstance(sparse_manifest,dict) else None
        ),
        "mission_contribution":(
            sparse_manifest.get("mission_contribution",[])
            if isinstance(sparse_manifest,dict) else []
        ),
        "sparse_quality_status":(
            sparse_manifest.get("quality_status")
            if isinstance(sparse_manifest,dict) else None
        ),
        "visual_evidence_path": cloud_health["preview_path"],
        "diagnostic_log_root": str(log_root.resolve()),
    }
    result_path = plan.dataset_root / "dense_reconstruction_manifest.json"
    result_path.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_manifest
