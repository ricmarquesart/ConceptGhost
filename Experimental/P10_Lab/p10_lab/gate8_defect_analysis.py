from __future__ import annotations

import json
import math
import struct
from enum import IntEnum
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .free_space_constraints import FreeSpaceState
from .prefusion_mesh import _PLY_SCALAR, _read_mesh_header


_SCHEMA = "ConceptGhost.P10Gate8DefectAnalysis.v0.1"


class Gate8DefectClass(IntEnum):
    SUPPORTED_SURFACE = 0
    VALID_OPENING = 1
    FALSE_SURFACE_IN_CONFIRMED_FREE = 2
    MISSING_SURFACE_UNKNOWN = 3
    LOW_CONFIDENCE_SURFACE = 4
    CONFLICT_REGION = 5


_CLASS_NAMES = {int(item): item.name for item in Gate8DefectClass}


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("Gate 8.1 defect analysis requires NumPy") from error
    return np


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _voxel_key(point, voxel_size: float) -> tuple[int, int, int]:
    return tuple(int(math.floor(float(v) / voxel_size)) for v in point)


def _load_vertices_and_selected_faces(path: Path, selected_mask, np):
    """Read all vertices but retain only selected triangular faces.

    Gate 8.1 may analyze a multi-million-face pre-fusion mesh. Holding all
    faces as Python tuples is wasteful, so this reader stores only faces that
    require bounded repair analysis. Vertices remain a compact float64 array.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"Gate 8.1 pre-fusion mesh is missing: {path}")

    with path.open("rb") as stream:
        header = _read_mesh_header(stream)
        if len(selected_mask) != header.face_count:
            raise ContractError(
                "Gate 8.1 protected-fusion face evidence does not match pre-fusion face count"
            )
        names = [name for _dtype, name in header.vertex_properties]
        x_index, y_index, z_index = names.index("x"), names.index("y"), names.index("z")
        vertices = np.empty((header.vertex_count, 3), dtype=np.float64)

        if header.format_name == "ascii":
            for index in range(header.vertex_count):
                raw = stream.readline()
                if not raw:
                    raise ContractError("Unexpected EOF in Gate 8.1 ASCII PLY vertices")
                parts = raw.decode("ascii").split()
                if len(parts) < len(header.vertex_properties):
                    raise ContractError("Malformed Gate 8.1 ASCII PLY vertex row")
                values = []
                for (dtype, _name), token in zip(header.vertex_properties, parts):
                    code = _PLY_SCALAR[dtype][0]
                    values.append(float(token) if code in {"f", "d"} else int(token))
                vertices[index] = (
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                )
        else:
            fmt = "<" + "".join(_PLY_SCALAR[dtype][0] for dtype, _ in header.vertex_properties)
            size = struct.calcsize(fmt)
            for index in range(header.vertex_count):
                raw = stream.read(size)
                if len(raw) != size:
                    raise ContractError("Unexpected EOF in Gate 8.1 binary PLY vertices")
                values = struct.unpack(fmt, raw)
                vertices[index] = (
                    float(values[x_index]),
                    float(values[y_index]),
                    float(values[z_index]),
                )

        selected: dict[int, tuple[int, int, int]] = {}
        if header.format_name == "ascii":
            for face_index in range(header.face_count):
                raw = stream.readline()
                if not raw:
                    raise ContractError("Unexpected EOF in Gate 8.1 ASCII PLY faces")
                parts = raw.decode("ascii").split()
                if not parts:
                    raise ContractError("Malformed Gate 8.1 ASCII PLY face row")
                count = int(parts[0])
                if count != 3 or len(parts) < 4:
                    raise ContractError("Gate 8.1 requires triangular pre-fusion faces")
                if selected_mask[face_index]:
                    face = (int(parts[1]), int(parts[2]), int(parts[3]))
                    if any(v < 0 or v >= header.vertex_count for v in face):
                        raise ContractError("Gate 8.1 encountered invalid face indices")
                    selected[face_index] = face
        else:
            count_code = _PLY_SCALAR[header.face_count_type][0]
            count_size = _PLY_SCALAR[header.face_count_type][1]
            index_code = _PLY_SCALAR[header.face_index_type][0]
            index_size = _PLY_SCALAR[header.face_index_type][1]
            for face_index in range(header.face_count):
                raw = stream.read(count_size)
                if len(raw) != count_size:
                    raise ContractError("Unexpected EOF in Gate 8.1 binary PLY face list")
                count = int(struct.unpack("<" + count_code, raw)[0])
                if count != 3:
                    raise ContractError("Gate 8.1 requires triangular pre-fusion faces")
                raw = stream.read(index_size * count)
                if len(raw) != index_size * count:
                    raise ContractError("Unexpected EOF in Gate 8.1 binary PLY face indices")
                if selected_mask[face_index]:
                    face = tuple(int(v) for v in struct.unpack("<" + index_code * count, raw))
                    if any(v < 0 or v >= header.vertex_count for v in face):
                        raise ContractError("Gate 8.1 encountered invalid face indices")
                    selected[face_index] = face

    return vertices, selected


class _UnionFind:
    def __init__(self, items):
        self.parent = {int(item): int(item) for item in items}
        self.rank = {int(item): 0 for item in items}

    def find(self, item: int) -> int:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _face_components(face_indices, face_vertices, vertices, class_name: str, np):
    indices = [int(v) for v in face_indices]
    if not indices:
        return []
    uf = _UnionFind(indices)
    first_by_vertex: dict[int, int] = {}
    for face_index in indices:
        face = face_vertices[face_index]
        for vertex_index in face:
            previous = first_by_vertex.get(vertex_index)
            if previous is None:
                first_by_vertex[vertex_index] = face_index
            else:
                uf.union(face_index, previous)

    grouped: dict[int, list[int]] = {}
    for face_index in indices:
        grouped.setdefault(uf.find(face_index), []).append(face_index)

    regions = []
    for members in sorted(grouped.values(), key=lambda values: min(values)):
        triangles = np.asarray([face_vertices[index] for index in members], dtype=np.int64)
        unique_vertices = np.unique(triangles.reshape(-1))
        points = vertices[unique_vertices]
        a = vertices[triangles[:, 0]]
        b = vertices[triangles[:, 1]]
        c = vertices[triangles[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        regions.append(
            {
                "class": class_name,
                "face_count": len(members),
                "source_face_index_min": int(min(members)),
                "source_face_index_max": int(max(members)),
                "source_face_indices": members if len(members) <= 512 else None,
                "source_face_indices_truncated": len(members) > 512,
                "bounds_min": [float(v) for v in np.min(points, axis=0)],
                "bounds_max": [float(v) for v in np.max(points, axis=0)],
                "centroid": [float(v) for v in np.mean(points, axis=0)],
                "surface_area_m2": float(np.sum(area)),
            }
        )
    return regions


def _voxel_components(keys, voxel_size: float, class_name: str):
    remaining = {tuple(int(v) for v in key) for key in keys}
    regions = []
    neighbors = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while remaining:
        seed = min(remaining)
        stack = [seed]
        remaining.remove(seed)
        component = []
        while stack:
            key = stack.pop()
            component.append(key)
            for dx, dy, dz in neighbors:
                nxt = (key[0] + dx, key[1] + dy, key[2] + dz)
                if nxt in remaining:
                    remaining.remove(nxt)
                    stack.append(nxt)
        lo = [min(key[axis] for key in component) * voxel_size for axis in range(3)]
        hi = [(max(key[axis] for key in component) + 1) * voxel_size for axis in range(3)]
        center = [(lo[i] + hi[i]) * 0.5 for i in range(3)]
        regions.append(
            {
                "class": class_name,
                "voxel_count": len(component),
                "voxel_keys": [list(key) for key in component] if len(component) <= 512 else None,
                "voxel_keys_truncated": len(component) > 512,
                "bounds_min": [float(v) for v in lo],
                "bounds_max": [float(v) for v in hi],
                "centroid": [float(v) for v in center],
            }
        )
    return regions


def analyze_gate8_defects(
    protected_fusion_manifest_path: str | Path,
    free_space_constraints_manifest_path: str | Path,
    geometry_confidence_manifest_path: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    """Classify bounded Gate 8.1 repair regions without editing geometry.

    The analysis consumes already-authoritative Gate 7 evidence. It never
    promotes a repair and never turns UNKNOWN into FREE/OCCUPIED by assumption.
    """
    np = _lazy_numpy()
    fusion_path = Path(protected_fusion_manifest_path).resolve()
    free_path = Path(free_space_constraints_manifest_path).resolve()
    confidence_path = Path(geometry_confidence_manifest_path).resolve()

    fusion = _read_json(fusion_path, "Gate 7.4 protected fusion manifest")
    free = _read_json(free_path, "Gate 7.3 free-space constraints")
    confidence = _read_json(confidence_path, "Gate 7.2C geometry confidence")

    if fusion.get("schema") != "ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1":
        raise ContractError("Gate 8.1 requires Gate 7.4 protected fusion schema v0.1")
    if free.get("schema") != "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1":
        raise ContractError("Gate 8.1 requires Gate 7.3 free-space constraints schema v0.1")
    if confidence.get("schema") != "ConceptGhost.P10Gate7GeometryConfidence.v0.1":
        raise ContractError("Gate 8.1 requires Gate 7.2C geometry confidence schema v0.1")
    for payload, label in ((fusion, "fusion"), (free, "free-space"), (confidence, "confidence")):
        if payload.get("status") != "PASS":
            raise ContractError(f"Gate 8.1 requires {label} status PASS")
        if payload.get("official_geometry_changed") is not False:
            raise ContractError(f"Gate 8.1 refuses {label} that changed official geometry")
        if payload.get("p9_authority_changed") is not False:
            raise ContractError(f"Gate 8.1 refuses {label} that changed P9 authority")

    if fusion.get("candidate_is_official_geometry") is not False:
        raise ContractError("Gate 8.1 requires a non-official Gate 7 candidate")
    if fusion.get("destructive_cleanup_performed") is not False:
        raise ContractError("Gate 8.1 cannot consume a candidate already cleaned destructively")

    for field in ("scene_contract_id", "p9_run_id", "p10_attempt_id"):
        expected = str(fusion.get(field) or "")
        for payload, label in ((free, "free-space"), (confidence, "confidence")):
            if str(payload.get(field) or "") != expected:
                raise ContractError(f"Gate 8.1 {label} identity mismatch for {field}")

    fusion_npz_path = Path(str(fusion.get("face_provenance_npz_path") or "")).resolve()
    if not fusion_npz_path.is_file():
        raise ContractError("Gate 8.1 protected-fusion face evidence is missing")
    with np.load(fusion_npz_path, allow_pickle=False) as evidence:
        required = {"p10_face_accept_mask", "p10_face_reason_code", "p10_face_confidence"}
        missing = required.difference(evidence.files)
        if missing:
            raise ContractError(f"Gate 8.1 protected-fusion evidence missing arrays: {sorted(missing)}")
        accepted = np.asarray(evidence["p10_face_accept_mask"], dtype=np.uint8).astype(bool)
        reason = np.asarray(evidence["p10_face_reason_code"], dtype=np.uint8)
        face_confidence = np.asarray(evidence["p10_face_confidence"], dtype=np.float32)
    if not (len(accepted) == len(reason) == len(face_confidence)):
        raise ContractError("Gate 8.1 protected-fusion evidence arrays do not align")

    reason_codes = fusion.get("reason_codes") if isinstance(fusion.get("reason_codes"), dict) else {}
    required_reasons = {
        "ACCEPTED_P10_MULTIVIEW",
        "CONFIRMED_FREE_VETO",
        "FREE_SPACE_CONFLICT",
        "P9_SOURCE_PROTECTED_OVERLAP",
        "INSUFFICIENT_PROVENANCE",
        "LOW_CONFIDENCE",
        "SUPPORT_DISTANCE",
        "DELAUNAY_DISAGREEMENT",
    }
    if not required_reasons.issubset(reason_codes):
        raise ContractError("Gate 8.1 protected-fusion reason-code contract is incomplete")

    face_class = np.full(len(reason), int(Gate8DefectClass.LOW_CONFIDENCE_SURFACE), dtype=np.uint8)
    supported_reasons = {
        int(reason_codes["ACCEPTED_P10_MULTIVIEW"]),
        int(reason_codes["P9_SOURCE_PROTECTED_OVERLAP"]),
    }
    for code in supported_reasons:
        face_class[reason == code] = int(Gate8DefectClass.SUPPORTED_SURFACE)
    face_class[reason == int(reason_codes["CONFIRMED_FREE_VETO"])] = int(
        Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE
    )
    face_class[reason == int(reason_codes["FREE_SPACE_CONFLICT"])] = int(
        Gate8DefectClass.CONFLICT_REGION
    )

    actionable = face_class != int(Gate8DefectClass.SUPPORTED_SURFACE)
    mesh_path = Path(str((fusion.get("inputs") or {}).get("p10_prefusion_mesh_path") or "")).resolve()
    vertices, selected_faces = _load_vertices_and_selected_faces(mesh_path, actionable, np)

    regions = []
    face_region_id = np.full(len(reason), -1, dtype=np.int32)
    next_region = 0
    for defect_class in (
        Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE,
        Gate8DefectClass.CONFLICT_REGION,
        Gate8DefectClass.LOW_CONFIDENCE_SURFACE,
    ):
        indices = np.flatnonzero(face_class == int(defect_class))
        components = _face_components(indices, selected_faces, vertices, defect_class.name, np)
        for component in components:
            component["region_id"] = f"G8R-{next_region:06d}"
            component["region_index"] = next_region
            component["source"] = "P10_PREFUSION_FACE_EVIDENCE"
            component["automatic_geometry_edit_allowed"] = False
            if defect_class == Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE:
                component["gate8_2_candidate_action"] = "REMOVE_FALSE_SURFACE_PRESERVE_FREE_SPACE"
                component["repair_candidate"] = True
            elif defect_class == Gate8DefectClass.LOW_CONFIDENCE_SURFACE:
                component["gate8_2_candidate_action"] = "BOUNDED_LOCAL_REMESH_REQUIRES_SAFETY_GATES"
                component["repair_candidate"] = True
            else:
                component["gate8_2_candidate_action"] = "HOLD_CONFLICT_REQUIRE_STRONGER_EVIDENCE"
                component["repair_candidate"] = False
            member_indices = component.get("source_face_indices")
            if member_indices is None:
                # Recompute membership by spatial component root would be costly here.
                # Large components keep class-level evidence in NPZ; region assignment
                # remains -1 for truncated JSON membership.
                pass
            else:
                face_region_id[np.asarray(member_indices, dtype=np.int64)] = next_region
            regions.append(component)
            if defect_class == Gate8DefectClass.FALSE_SURFACE_IN_CONFIRMED_FREE:
                opening = {
                    "region_id": f"G8R-{next_region + 1:06d}",
                    "region_index": next_region + 1,
                    "class": Gate8DefectClass.VALID_OPENING.name,
                    "source": "GATE7_CONFIRMED_FREE_VETO_COMPANION",
                    "companion_false_surface_region_id": component["region_id"],
                    "bounds_min": component["bounds_min"],
                    "bounds_max": component["bounds_max"],
                    "centroid": component["centroid"],
                    "repair_candidate": False,
                    "automatic_geometry_edit_allowed": False,
                    "gate8_2_candidate_action": "PRESERVE_NO_FILL",
                }
                regions.append(opening)
                next_region += 1
            next_region += 1

    free_npz_path = Path(str(free.get("constraints_npz_path") or "")).resolve()
    if not free_npz_path.is_file():
        raise ContractError("Gate 8.1 free-space constraints NPZ is missing")
    with np.load(free_npz_path, allow_pickle=False) as free_npz:
        free_keys = np.asarray(free_npz["voxel_keys"], dtype=np.int32)
        free_states = np.asarray(free_npz["state"], dtype=np.uint8)
    if len(free_keys) != len(free_states):
        raise ContractError("Gate 8.1 free-space arrays do not align")
    state_by_key = {tuple(int(v) for v in key): int(state) for key, state in zip(free_keys, free_states)}
    voxel = free.get("voxel") if isinstance(free.get("voxel"), dict) else {}
    voxel_size = float(voxel.get("voxel_size_m") or 0.0)
    if not math.isfinite(voxel_size) or voxel_size <= 0:
        raise ContractError("Gate 8.1 free-space voxel_size_m is invalid")

    confidence_npz_path = Path(str(confidence.get("evidence_npz_path") or "")).resolve()
    if not confidence_npz_path.is_file():
        raise ContractError("Gate 8.1 geometry-confidence NPZ is missing")
    with np.load(confidence_npz_path, allow_pickle=False) as confidence_npz:
        required = {"p10_points", "p10_confidence_virtual_hole_candidate"}
        missing = required.difference(confidence_npz.files)
        if missing:
            raise ContractError(f"Gate 8.1 confidence evidence missing arrays: {sorted(missing)}")
        p10_points = np.asarray(confidence_npz["p10_points"], dtype=np.float64)
        virtual_hole = np.asarray(
            confidence_npz["p10_confidence_virtual_hole_candidate"], dtype=np.uint8
        ).astype(bool)
    if len(p10_points) != len(virtual_hole):
        raise ContractError("Gate 8.1 confidence virtual-hole arrays do not align")

    missing_keys = set()
    for point in p10_points[virtual_hole]:
        key = _voxel_key(point, voxel_size)
        if state_by_key.get(key, int(FreeSpaceState.UNKNOWN)) == int(FreeSpaceState.UNKNOWN):
            missing_keys.add(key)

    missing_regions = _voxel_components(
        sorted(missing_keys),
        voxel_size,
        Gate8DefectClass.MISSING_SURFACE_UNKNOWN.name,
    )
    for component in missing_regions:
        component.update(
            {
                "region_id": f"G8R-{next_region:06d}",
                "region_index": next_region,
                "source": "GATE7_2C_VIRTUAL_HOLE_IN_UNKNOWN",
                "repair_candidate": True,
                "automatic_geometry_edit_allowed": False,
                "gate8_2_candidate_action": "LOCAL_REMESH_ONLY_IF_NEW_SUPPORT_PASSES_SAFETY_GATES",
                "unknown_is_not_free": True,
            }
        )
        regions.append(component)
        next_region += 1

    class_counts = {}
    for value, name in _CLASS_NAMES.items():
        face_count = int(np.count_nonzero(face_class == value)) if name not in {
            Gate8DefectClass.VALID_OPENING.name,
            Gate8DefectClass.MISSING_SURFACE_UNKNOWN.name,
        } else 0
        region_count = sum(1 for item in regions if item["class"] == name)
        class_counts[name] = {"face_count": face_count, "region_count": region_count}

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_out = output_root / "gate8_defect_analysis_evidence.npz"
    np.savez_compressed(
        evidence_out,
        p10_face_defect_class=face_class,
        p10_face_region_id=face_region_id,
        p10_face_gate7_reason_code=reason,
        p10_face_gate7_confidence=face_confidence,
        missing_surface_unknown_voxel_keys=np.asarray(sorted(missing_keys), dtype=np.int32).reshape((-1, 3)),
    )

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 8,
        "subgate": "8.1",
        "mode": "DIAGNOSTIC_BOUNDED_REGION_ANALYSIS_ONLY",
        "scene_contract_id": fusion.get("scene_contract_id"),
        "p9_run_id": fusion.get("p9_run_id"),
        "p10_attempt_id": fusion.get("p10_attempt_id"),
        "coordinate_space": fusion.get("coordinate_space"),
        "taxonomy": _CLASS_NAMES,
        "class_counts": class_counts,
        "regions": regions,
        "inputs": {
            "protected_fusion_manifest_path": str(fusion_path),
            "free_space_constraints_manifest_path": str(free_path),
            "geometry_confidence_manifest_path": str(confidence_path),
            "p10_prefusion_mesh_path": str(mesh_path),
        },
        "evidence_npz_path": str(evidence_out),
        "policies": {
            "confirmed_free": "NEVER_FILL_AUTOMATICALLY",
            "unknown": "NOT_FREE_NOT_A_DELETION_AUTHORITY",
            "conflict": "NO_AUTOMATIC_EDIT",
            "high_source_authority": "PROTECTED",
            "gate8_1_changes_geometry": False,
        },
        "official_geometry_changed": False,
        "p9_authority_changed": False,
        "destructive_cleanup_performed": False,
        "automatic_geometry_edit_allowed": False,
        "ready_for_gate8_2": True,
        "next_required": [
            "G8.2_LOCAL_REMESH_CLEANUP",
            "G8.2_STRUCTURAL_ANALYSIS_PREVIEW_DEFAULT_ON_APPLY_OFF",
        ],
    }
    manifest_out = output_root / "gate8_defect_analysis_manifest.json"
    manifest_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(manifest_out)
    return result
