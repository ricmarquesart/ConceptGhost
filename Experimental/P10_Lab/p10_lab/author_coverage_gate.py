from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root, update_stage_status


_CATEGORY = "ConceptGhost/P10 Author Integration"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _load_positions(rail_path: Path):
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("CG-05 rail coverage requires NumPy") from error

    payload = json.loads(rail_path.read_text(encoding="utf-8"))
    w2c = np.asarray(payload, dtype=np.float64)
    if w2c.ndim != 3 or w2c.shape[1:] != (4, 4) or w2c.shape[0] < 2:
        raise ContractError(f"Invalid author rail matrix stack: {rail_path}")
    try:
        c2w = np.linalg.inv(w2c)
    except np.linalg.LinAlgError as error:
        raise ContractError(f"Author rail contains non-invertible camera matrix: {rail_path}") from error
    positions = c2w[:, :3, 3]
    rotations = c2w[:, :3, :3]
    return positions, rotations


def _route_metrics(positions, rotations) -> dict:
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("CG-05 rail coverage requires NumPy") from error

    deltas = positions[1:] - positions[:-1]
    segment = np.linalg.norm(deltas, axis=1)
    path_length = float(segment.sum())
    mins = positions.min(axis=0)
    maxs = positions.max(axis=0)
    span = maxs - mins
    start_end = float(np.linalg.norm(positions[-1] - positions[0]))
    start_radius = float(np.linalg.norm(positions[0]))
    end_radius = float(np.linalg.norm(positions[-1]))

    r0 = rotations[0]
    r1 = rotations[-1]
    rel = r0.T @ r1
    cos_angle = max(-1.0, min(1.0, float((np.trace(rel) - 1.0) * 0.5)))
    rotation_delta_deg = math.degrees(math.acos(cos_angle))
    close_threshold = max(0.05, 0.05 * max(path_length, 1.0e-6))
    closed_position = start_end <= close_threshold

    return {
        "frame_count": int(positions.shape[0]),
        "path_length": path_length,
        "bbox_min": [float(v) for v in mins],
        "bbox_max": [float(v) for v in maxs],
        "bbox_span": [float(v) for v in span],
        "max_axis_span": float(span.max()),
        "start_distance_from_origin": start_radius,
        "end_distance_from_origin": end_radius,
        "start_end_distance": start_end,
        "start_end_rotation_delta_deg": rotation_delta_deg,
        "closed_position_loop": bool(closed_position),
        "closed_loop_position_threshold": close_threshold,
        "nondegenerate": bool(path_length > 0.05 and float(span.max()) > 0.02),
    }


def _draw_top_view(path: Path, route_positions: list[tuple[str, object]]) -> None:
    try:
        from PIL import Image, ImageDraw
        import numpy as np
    except ImportError as error:
        raise RuntimeError("CG-05 preview requires Pillow and NumPy") from error

    width, height = 1400, 1000
    margin = 80
    all_points = np.concatenate([positions[:, [0, 2]] for _, positions in route_positions], axis=0)
    mins = all_points.min(axis=0)
    maxs = all_points.max(axis=0)
    span = np.maximum(maxs - mins, 1.0e-6)

    image = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(image)
    palette = [
        (230, 90, 90),
        (90, 180, 240),
        (120, 220, 130),
        (240, 190, 80),
        (190, 120, 240),
    ]

    def map_point(x, z):
        px = margin + (float(x) - float(mins[0])) / float(span[0]) * (width - 2 * margin)
        py = height - margin - (float(z) - float(mins[1])) / float(span[1]) * (height - 2 * margin)
        return px, py

    draw.text((30, 25), "ConceptGhost CG-05 · Author rail top view (X/Z)", fill=(255, 255, 255))
    for index, (name, positions) in enumerate(route_positions):
        points = [map_point(x, z) for x, _, z in positions]
        color = palette[index % len(palette)]
        if len(points) >= 2:
            draw.line(points, fill=color, width=4)
        sx, sy = points[0]
        ex, ey = points[-1]
        draw.ellipse((sx - 7, sy - 7, sx + 7, sy + 7), fill=(255, 255, 255))
        draw.rectangle((ex - 6, ey - 6, ex + 6, ey + 6), outline=color, width=3)
        draw.text((30, 60 + index * 28), f"{index + 1}. {name}", fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


class ConceptGhostP10AuthorCoverageGate:
    """Publish tangible CG-05 multi-route coverage and closed-loop evidence."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "rail_1": ("STRING", {"forceInput": True}),
                "rail_2": ("STRING", {"forceInput": True}),
                "rail_3": ("STRING", {"forceInput": True}),
                "rail_4": ("STRING", {"forceInput": True}),
                "rail_5": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("coverage_evidence_ready", "cg05_manifest_path", "diagnostics_json")
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        scene_contract_id: str,
        rail_1: str,
        rail_2: str,
        rail_3: str,
        rail_4: str,
        rail_5: str,
    ):
        attempt = Path(p10_attempt_root).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        scene_id = str(scene_contract_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("CG-05 attempt identity/path mismatch")

        attempt_manifest_path = attempt / "attempt_manifest.json"
        if not attempt_manifest_path.is_file():
            raise ContractError("CG-05 requires attempt_manifest.json")
        attempt_manifest = json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("CG-05 scene_contract_id does not match attempt")

        rail_paths = [Path(value).expanduser().resolve() for value in (rail_1, rail_2, rail_3, rail_4, rail_5)]
        if any(not path.is_file() for path in rail_paths):
            missing = [str(path) for path in rail_paths if not path.is_file()]
            raise ContractError(f"CG-05 missing author rail(s): {missing}")

        stage = stage_root(attempt, "CG_05")
        outputs, previews, manifests, logs = (
            stage / "OUTPUTS",
            stage / "PREVIEWS",
            stage / "MANIFESTS",
            stage / "LOGS",
        )
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        route_positions = []
        route_reports = []
        expected_frames = None
        for index, source in enumerate(rail_paths, start=1):
            positions, rotations = _load_positions(source)
            metrics = _route_metrics(positions, rotations)
            if expected_frames is None:
                expected_frames = metrics["frame_count"]
            elif metrics["frame_count"] != expected_frames:
                raise ContractError("CG-05 author rails do not share the same frame count")
            copied = outputs / f"route_{index:02d}_rail.json"
            shutil.copy2(source, copied)
            route_positions.append((f"route_{index:02d}", positions))
            route_reports.append({
                "route_index": index,
                "source_rail": str(source),
                "published_rail": str(copied),
                **metrics,
            })

        if expected_frames != 81:
            raise ContractError(f"CG-05 expected author 81-frame rails; got {expected_frames}")
        if not all(item["nondegenerate"] for item in route_reports):
            raise ContractError("CG-05 contains a degenerate camera route")

        # CSV is a tangible, application-independent camera position audit.
        csv_path = outputs / "combined_camera_positions.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["route", "frame", "x", "y", "z"])
            for route_index, (_, positions) in enumerate(route_positions, start=1):
                for frame, point in enumerate(positions):
                    writer.writerow([route_index, frame, float(point[0]), float(point[1]), float(point[2])])

        preview_path = previews / "combined_author_rail_top_view.png"
        _draw_top_view(preview_path, route_positions)

        starts = [item["start_distance_from_origin"] for item in route_reports]
        closed_routes = [
            item["route_index"] for item in route_reports if item["closed_position_loop"]
        ]
        payload = {
            "schema": "ConceptGhost.CG05AuthorCoverage.v0.1",
            "stage": "CG_05",
            "status": "PASS",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "author_frame_length": expected_frames,
            "route_count": len(route_reports),
            "all_routes_nondegenerate": True,
            "all_routes_start_at_panorama_origin": max(starts) <= 1.0e-4,
            "closed_position_loop_routes": closed_routes,
            "routes": route_reports,
            "combined_camera_positions_csv": str(csv_path),
            "combined_top_view_preview": str(preview_path),
            "artist_quality_status": "PENDING",
            "note": (
                "CG-05 proves tangible spatial camera coverage/rails. Hole-specific visual "
                "coverage remains artist/scene evidence and is not inferred from runtime success."
            ),
        }
        if not payload["all_routes_start_at_panorama_origin"]:
            raise ContractError("CG-05 author rails do not all start at the panorama origin")

        manifest_path = manifests / "cg05_author_coverage.json"
        manifest_path.write_text(_pretty(payload) + "\n", encoding="utf-8")
        (logs / "coverage.log").write_text(_pretty(payload) + "\n", encoding="utf-8")

        status = update_stage_status(
            attempt,
            p10_attempt_id=attempt_id,
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=scene_id,
            stage_code="CG_05",
            runtime_status="PASS",
            functional_status="PASS",
            artist_quality_status="PENDING",
            notes=[
                "Five physical 81-frame author rails validated and copied.",
                "Combined camera position CSV and top-view preview generated.",
                "Artist/scene-specific missing-region coverage remains pending review.",
            ],
        )

        diagnostics = {
            "status": "PASS",
            "stage": "CG_05",
            "manifest_path": str(manifest_path),
            "preview_path": str(preview_path),
            "closed_position_loop_routes": closed_routes,
            "stage_status_path": status["status_path"],
        }
        return True, str(manifest_path), _pretty(diagnostics)


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorCoverageGate": ConceptGhostP10AuthorCoverageGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorCoverageGate": "P10 · CG-05 · Author Rail Coverage + Closed-Loop Evidence",
}
