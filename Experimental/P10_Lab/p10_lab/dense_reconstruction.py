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
from .colmap_dense_io import (
    colmap_camera_center,
    load_colmap_sparse_images,
    qvec_to_rotation_matrix,
)


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



def _read_dataset_frames(dataset_root: Path) -> dict[str, dict[str, object]]:
    manifest_path=dataset_root/"dataset_manifest.json"
    try:
        payload=json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read Gate 6 dataset manifest for dense source selection: {error}") from error
    frames=payload.get("frames")
    if not isinstance(frames,list) or not frames:
        raise ContractError("Dense source selection requires dataset_manifest frames")
    result={}
    for frame in frames:
        if not isinstance(frame,dict):
            continue
        name=str(frame.get("image_name") or "").strip()
        if name:
            result[name]=frame
    return result


def _camera_forward_world(image_row) -> tuple[float,float,float]:
    rotation=qvec_to_rotation_matrix(image_row["qvec"])
    # COLMAP camera +Z points forward. For world->camera R, world forward is R^T * Z.
    return (
        float(rotation[2][0]),
        float(rotation[2][1]),
        float(rotation[2][2]),
    )


def _dot3(a,b) -> float:
    return sum(float(a[index])*float(b[index]) for index in range(3))


def _distance3(a,b) -> float:
    return math.sqrt(sum((float(a[index])-float(b[index]))**2 for index in range(3)))


def _select_patch_match_sources(
    image_rows,
    frame_by_name: dict[str, dict[str, object]],
    *,
    max_sources: int=20,
    same_route_budget: int=12,
    cross_route_budget: int=8,
) -> dict[str, tuple[str,...]]:
    if type(max_sources) is not int or max_sources < 2:
        raise ContractError("PatchMatch max_sources must be an integer >= 2")
    rows=tuple(image_rows)
    if len(rows)<3:
        raise ContractError("Explicit PatchMatch source selection requires at least 3 registered images")

    info={}
    for row in rows:
        name=str(row["name"])
        frame=frame_by_name.get(name,{})
        info[name]={
            "row":row,
            "center":colmap_camera_center(row["qvec"],row["tvec"]),
            "forward":_camera_forward_world(row),
            "route":str(frame.get("path_name") or ""),
            "index":int(frame.get("global_frame_index") or 0),
        }

    selected={}
    for name,current in info.items():
        candidates=[]
        for other_name,other in info.items():
            if other_name==name:
                continue
            distance=_distance3(current["center"],other["center"])
            dot=max(-1.0,min(1.0,_dot3(current["forward"],other["forward"])))
            same_route=bool(current["route"]) and current["route"]==other["route"]
            index_distance=abs(int(current["index"])-int(other["index"]))
            # Same-route temporal neighbors are strongest continuity evidence.
            # Cross-route candidates are ranked by metric proximity with a mild
            # viewing-direction penalty, so every reference also gets independent
            # baseline evidence instead of relying on one fragmented sparse component.
            score=(
                index_distance*0.25 + distance*0.05
                if same_route
                else distance*(1.5-0.5*dot)
            )
            candidates.append({
                "name":other_name,
                "same_route":same_route,
                "index_distance":index_distance,
                "distance":distance,
                "view_dot":dot,
                "score":score,
            })

        same=sorted(
            (item for item in candidates if item["same_route"]),
            key=lambda item:(item["index_distance"],item["distance"],item["name"]),
        )
        cross=sorted(
            (item for item in candidates if not item["same_route"]),
            key=lambda item:(item["score"],item["distance"],item["name"]),
        )
        chosen=[]
        for item in same[:same_route_budget]:
            if item["name"] not in chosen:
                chosen.append(item["name"])
        for item in cross[:cross_route_budget]:
            if item["name"] not in chosen:
                chosen.append(item["name"])
        for item in sorted(candidates,key=lambda item:(item["score"],item["distance"],item["name"])):
            if len(chosen)>=max_sources:
                break
            if item["name"] not in chosen:
                chosen.append(item["name"])
        chosen=chosen[:max_sources]
        if len(chosen)<2:
            raise ContractError(f"PatchMatch reference {name} has fewer than two explicit sources")
        selected[name]=tuple(chosen)
    return selected


def _read_sparse_points_xyz(dataset_root: Path, *, max_points: int=5000):
    path=dataset_root/"sparse"/"triangulated_txt"/"points3D.txt"
    if not path.is_file():
        return ()
    points=[]
    for raw in path.read_text(encoding="utf-8",errors="replace").splitlines():
        line=raw.strip()
        if not line or line.startswith("#"):
            continue
        parts=line.split()
        if len(parts)<4:
            continue
        try:
            xyz=(float(parts[1]),float(parts[2]),float(parts[3]))
        except ValueError:
            continue
        if all(math.isfinite(value) for value in xyz):
            points.append(xyz)
    if len(points)>max_points:
        stride=max(1,math.ceil(len(points)/max_points))
        points=points[::stride][:max_points]
    return tuple(points)


def _estimate_patch_match_depth_range(
    dataset_root: Path,
    image_rows,
) -> tuple[float,float,str]:
    points=_read_sparse_points_xyz(dataset_root)
    positive=[]
    if points:
        for row in image_rows:
            rotation=qvec_to_rotation_matrix(row["qvec"])
            tvec=row["tvec"]
            for point in points:
                depth=(
                    rotation[2][0]*point[0]
                    + rotation[2][1]*point[1]
                    + rotation[2][2]*point[2]
                    + float(tvec[2])
                )
                if math.isfinite(depth) and depth>1.0e-4:
                    positive.append(float(depth))
    if positive:
        depth_min=max(0.01,_quantile(positive,0.01)*0.5)
        depth_max=max(depth_min*10.0,_quantile(positive,0.99)*1.5)
        return float(depth_min),float(depth_max),"SPARSE_POSITIVE_DEPTH_P01_P99_EXPANDED"

    centers=[colmap_camera_center(row["qvec"],row["tvec"]) for row in image_rows]
    max_span=0.0
    for axis in range(3):
        values=[center[axis] for center in centers]
        if values:
            max_span=max(max_span,max(values)-min(values))
    depth_min=0.01
    depth_max=max(10.0,max_span*4.0)
    return depth_min,depth_max,"CAMERA_SPAN_FALLBACK"


def _patch_match_reference_count(path: Path) -> int:
    if not path.is_file():
        return 0
    lines=[line.strip() for line in path.read_text(encoding="utf-8",errors="replace").splitlines() if line.strip()]
    return len(lines)//2


def write_explicit_patch_match_config(
    dataset_root: str | Path,
    dense_root: str | Path,
    *,
    max_sources: int=20,
) -> dict[str, object]:
    """Replace COLMAP auto-neighbor selection with bounded explicit known-camera sources.

    ConceptGhost uses artist-authored/P9-derived known cameras. The sparse point
    cloud can be fragmented enough that COLMAP's auto source selection omits
    otherwise valid registered reference views. Gate 7 needs geometric evidence
    per registered view, so the dense stage explicitly enumerates all registered
    references with bounded same-route + cross-route sources.
    """

    dataset_root=Path(dataset_root).resolve()
    dense_root=Path(dense_root).resolve()
    sparse_root=dense_root/"sparse"
    image_rows,storage=load_colmap_sparse_images(sparse_root)
    frame_by_name=_read_dataset_frames(dataset_root)
    registered_names={str(row["name"]) for row in image_rows}
    missing_dataset=sorted(registered_names-set(frame_by_name))
    if missing_dataset:
        raise ContractError(
            "Dense registered images are missing from authoritative dataset manifest: "
            f"{missing_dataset[:10]}"
        )

    sources=_select_patch_match_sources(
        image_rows,
        frame_by_name,
        max_sources=max_sources,
    )
    config_path=dense_root/"stereo"/"patch-match.cfg"
    config_path.parent.mkdir(parents=True,exist_ok=True)
    original_reference_count=_patch_match_reference_count(config_path)
    backup_path=dense_root/"stereo"/"patch-match.auto.cfg"
    if config_path.is_file() and not backup_path.is_file():
        shutil.copy2(config_path,backup_path)

    ordered=sorted(
        image_rows,
        key=lambda row:(
            int(frame_by_name[str(row["name"])].get("global_frame_index") or 0),
            str(row["name"]),
        ),
    )
    rows=[]
    cross_route_counts=[]
    source_counts=[]
    for row in ordered:
        name=str(row["name"])
        chosen=sources[name]
        rows.append(name)
        rows.append(", ".join(chosen))
        source_counts.append(len(chosen))
        route=str(frame_by_name[name].get("path_name") or "")
        cross_route_counts.append(sum(
            1 for source in chosen
            if str(frame_by_name[source].get("path_name") or "")!=route
        ))
    config_path.write_text("\n".join(rows)+"\n",encoding="utf-8")

    depth_min,depth_max,depth_policy=_estimate_patch_match_depth_range(
        dataset_root,
        image_rows,
    )
    diagnostics={
        "schema":"ConceptGhost.P10PatchMatchSourceConfig.v0.1",
        "policy":"EXPLICIT_KNOWN_CAMERA_SAME_ROUTE_PLUS_CROSS_ROUTE",
        "camera_model_storage":storage,
        "registered_image_count":len(image_rows),
        "original_auto_reference_count":original_reference_count,
        "explicit_reference_count":len(ordered),
        "max_sources":int(max_sources),
        "min_source_count":min(source_counts) if source_counts else 0,
        "max_source_count":max(source_counts) if source_counts else 0,
        "min_cross_route_source_count":min(cross_route_counts) if cross_route_counts else 0,
        "max_cross_route_source_count":max(cross_route_counts) if cross_route_counts else 0,
        "depth_min":float(depth_min),
        "depth_max":float(depth_max),
        "depth_policy":depth_policy,
        "config_path":str(config_path),
        "auto_config_backup_path":str(backup_path) if backup_path.is_file() else None,
        "p9_authority_changed":False,
    }
    diag_path=dense_root/"patch_match_source_config.json"
    diag_path.write_text(json.dumps(diagnostics,indent=2,sort_keys=True),encoding="utf-8")
    diagnostics["manifest_path"]=str(diag_path)
    return diagnostics


def _matching_image_names(root: Path, suffix: str) -> set[str]:
    if not root.is_dir():
        return set()
    result=set()
    for path in root.rglob(f"*{suffix}"):
        if path.is_file():
            name=path.name
            if name.endswith(suffix):
                result.add(name[:-len(suffix)])
    return result


def inspect_dense_geometric_evidence(
    dataset_root: str | Path,
    *,
    min_coverage_ratio: float=0.70,
) -> dict[str, object]:
    dataset_root=Path(dataset_root).resolve()
    dense_root=dataset_root/"dense"
    image_rows,_=load_colmap_sparse_images(dense_root/"sparse")
    registered_names={str(row["name"]) for row in image_rows}
    depth_names=_matching_image_names(dense_root/"stereo"/"depth_maps",".geometric.bin")
    graph_names=_matching_image_names(dense_root/"stereo"/"consistency_graphs",".geometric.bin")
    normal_names=_matching_image_names(dense_root/"stereo"/"normal_maps",".geometric.bin")
    usable=registered_names & depth_names & graph_names
    registered_count=len(registered_names)
    ratio=len(usable)/float(registered_count) if registered_count else 0.0
    return {
        "schema":"ConceptGhost.P10DenseGeometricEvidenceStatus.v0.1",
        "registered_image_count":registered_count,
        "geometric_depth_map_file_count":len(depth_names),
        "geometric_normal_map_file_count":len(normal_names),
        "geometric_consistency_graph_file_count":len(graph_names),
        "usable_registered_geometric_image_count":len(usable),
        "geometric_evidence_coverage_ratio":ratio,
        "min_coverage_ratio":float(min_coverage_ratio),
        "missing_geometric_registered_images":sorted(registered_names-usable),
        "gate7_geometric_evidence_ready":bool(
            registered_count>0 and ratio>=float(min_coverage_ratio)
        ),
    }


def _run_dense_command(
    argv: list[str],
    *,
    cwd: Path,
    log_path: Path,
) -> dict[str, object]:
    result=subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.parent.mkdir(parents=True,exist_ok=True)
    log_path.write_text(
        "COMMAND\n"+" ".join(argv)
        +"\n\nSTDOUT\n"+(result.stdout or "")
        +"\n\nSTDERR\n"+(result.stderr or ""),
        encoding="utf-8",
    )
    record={
        "command":argv[1] if len(argv)>1 else "",
        "argv":argv,
        "returncode":int(result.returncode),
        "log_path":str(log_path),
    }
    if result.returncode!=0:
        raise RuntimeError(
            f"COLMAP {record['command']} failed with exit code {result.returncode}; "
            f"see {log_path}"
        )
    return record


def repair_dense_geometric_evidence(
    dataset_root: str | Path,
    *,
    colmap_executable: str="colmap",
    min_coverage_ratio: float=0.70,
    max_sources: int=20,
    max_image_size: int=832,
    patch_match_cache_gb: float=4.0,
    fusion_cache_gb: float=4.0,
    min_num_pixels: int=2,
) -> dict[str, object]:
    """Repair an existing dense workspace without rebuilding WAN or sparse cameras."""

    dataset_root=Path(dataset_root).resolve()
    dense_root=dataset_root/"dense"
    if not dense_root.is_dir():
        raise ContractError(f"Dense workspace is missing for Gate 7 repair: {dense_root}")
    executable=_resolve_executable(colmap_executable)
    before=inspect_dense_geometric_evidence(
        dataset_root,
        min_coverage_ratio=min_coverage_ratio,
    )
    if before["gate7_geometric_evidence_ready"]:
        return {
            "status":"REUSED",
            "before":before,
            "after":before,
            "commands":[],
        }

    setup=write_explicit_patch_match_config(
        dataset_root,
        dense_root,
        max_sources=max_sources,
    )
    log_root=dataset_root/"logs"/"gate6_4_repair"
    patch_argv=[
        executable,
        "patch_match_stereo",
        "--workspace_path",str(dense_root),
        "--workspace_format","COLMAP",
        "--PatchMatchStereo.geom_consistency","1",
        "--PatchMatchStereo.write_consistency_graph","1",
        "--PatchMatchStereo.max_image_size",str(int(max_image_size)),
        "--PatchMatchStereo.cache_size",f"{float(patch_match_cache_gb):g}",
        "--PatchMatchStereo.gpu_index","0",
        "--PatchMatchStereo.num_iterations","3",
        "--PatchMatchStereo.depth_min",f"{float(setup['depth_min']):.17g}",
        "--PatchMatchStereo.depth_max",f"{float(setup['depth_max']):.17g}",
    ]
    commands=[
        _run_dense_command(
            patch_argv,
            cwd=dataset_root,
            log_path=log_root/"00_patch_match_stereo_explicit_sources.log",
        )
    ]

    fused=dense_root/"fused.ply"
    if fused.is_file():
        fused.unlink()
    fusion_argv=[
        executable,
        "stereo_fusion",
        "--workspace_path",str(dense_root),
        "--workspace_format","COLMAP",
        "--input_type","geometric",
        "--output_type","PLY",
        "--output_path",str(fused),
        "--StereoFusion.max_image_size",str(int(max_image_size)),
        "--StereoFusion.cache_size",f"{float(fusion_cache_gb):g}",
        "--StereoFusion.min_num_pixels",str(int(min_num_pixels)),
    ]
    commands.append(
        _run_dense_command(
            fusion_argv,
            cwd=dataset_root,
            log_path=log_root/"01_stereo_fusion_after_evidence_repair.log",
        )
    )
    if not fused.is_file():
        raise ContractError("Gate 7 dense evidence repair completed without fused.ply")

    after=inspect_dense_geometric_evidence(
        dataset_root,
        min_coverage_ratio=min_coverage_ratio,
    )
    cloud_health=analyze_and_render_fused_cloud(
        fused,
        dense_root/"dense_fused_preview.svg",
        max_preview_points=50000,
    )

    manifest_path=dataset_root/"dense_reconstruction_manifest.json"
    existing={}
    if manifest_path.is_file():
        try:
            candidate=json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(candidate,dict):
                existing=candidate
        except (OSError,json.JSONDecodeError):
            existing={}
    existing.update(after)
    existing.update({
        "schema":"ConceptGhost.P10DenseReconstructionResult.v0.4",
        "status":"PASS" if after["gate7_geometric_evidence_ready"] else "FAIL",
        "gate7_geometric_evidence_ready":bool(after["gate7_geometric_evidence_ready"]),
        "patch_match_source_config":setup,
        "gate7_geometric_evidence_repair":{
            "status":"PASS" if after["gate7_geometric_evidence_ready"] else "FAIL",
            "before":before,
            "after":after,
            "commands":commands,
            "p9_authority_changed":False,
        },
        "fused_cloud":cloud_health,
        "fused_ply_path":str(fused),
        "visual_evidence_path":cloud_health["preview_path"],
        "diagnostic_log_root":str(log_root),
    })
    manifest_path.write_text(
        json.dumps(existing,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    if not after["gate7_geometric_evidence_ready"]:
        raise ContractError(
            "Gate 7 dense evidence repair remained below coverage threshold: "
            f"{after['usable_registered_geometric_image_count']}/"
            f"{after['registered_image_count']}="
            f"{after['geometric_evidence_coverage_ratio']:.3f} "
            f"< {float(min_coverage_ratio):.3f}; "
            f"missing={after['missing_geometric_registered_images'][:10]}"
        )
    return {
        "status":"REPAIRED",
        "before":before,
        "after":after,
        "source_config":setup,
        "commands":commands,
        "dense_manifest_path":str(manifest_path),
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
    patch_match_setup=None
    for index, step in enumerate(plan.steps):
        argv = list(step.argv(executable))
        if step.command=="patch_match_stereo":
            if patch_match_setup is None:
                patch_match_setup=write_explicit_patch_match_config(
                    plan.dataset_root,
                    plan.dense_root,
                    max_sources=20,
                )
            argv.extend((
                "--PatchMatchStereo.depth_min",f"{float(patch_match_setup['depth_min']):.17g}",
                "--PatchMatchStereo.depth_max",f"{float(patch_match_setup['depth_max']):.17g}",
            ))
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
        if step.command=="image_undistorter":
            patch_match_setup=write_explicit_patch_match_config(
                plan.dataset_root,
                plan.dense_root,
                max_sources=20,
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
    depth_map_count = _count_matching_files(depth_map_root, ".bin")
    normal_map_count = _count_matching_files(normal_map_root, ".bin")
    evidence_status=inspect_dense_geometric_evidence(
        plan.dataset_root,
        min_coverage_ratio=0.70,
    )
    geometric_depth_map_count=int(evidence_status["geometric_depth_map_file_count"])
    geometric_normal_map_count=int(evidence_status["geometric_normal_map_file_count"])
    consistency_graph_count=int(evidence_status["geometric_consistency_graph_file_count"])

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
        "registered_image_count":evidence_status["registered_image_count"],
        "usable_registered_geometric_image_count":evidence_status["usable_registered_geometric_image_count"],
        "geometric_evidence_coverage_ratio":evidence_status["geometric_evidence_coverage_ratio"],
        "missing_geometric_registered_images":evidence_status["missing_geometric_registered_images"],
        "gate7_geometric_evidence_ready":bool(evidence_status["gate7_geometric_evidence_ready"]),
        "patch_match_source_config":patch_match_setup,
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
    result_manifest["schema"]="ConceptGhost.P10DenseReconstructionResult.v0.4"
    result_manifest["status"]=(
        "PASS" if evidence_status["gate7_geometric_evidence_ready"] else "FAIL"
    )
    result_path.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if not evidence_status["gate7_geometric_evidence_ready"]:
        raise ContractError(
            "COLMAP dense geometric-evidence coverage below Gate 7 threshold after "
            "explicit known-camera source configuration: "
            f"{evidence_status['usable_registered_geometric_image_count']}/"
            f"{evidence_status['registered_image_count']}="
            f"{evidence_status['geometric_evidence_coverage_ratio']:.3f} < 0.700; "
            f"missing={evidence_status['missing_geometric_registered_images'][:10]}"
        )
    return result_manifest
