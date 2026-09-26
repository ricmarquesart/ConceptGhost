from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .p9_boundary import validate_official_run


_SCHEMA = "ConceptGhost.ResultOutputContract.v0.1"
_STATUS_SCHEMA = "ConceptGhost.ResultStageStatus.v0.1"

# These are artist/result milestones, not historical implementation gates.
# Every new P10 attempt owns this tree inside the ComfyUI output directory.
_RESULT_STAGES: tuple[tuple[str, str, str], ...] = (
    ("CG_00", "CG_00_P9_AUTHORITY", "Accepted P9 source/camera authority"),
    ("CG_01", "CG_01_PRIVATE_AUTHOR_BASELINE", "Private author implementation baseline"),
    ("CG_02", "CG_02_PANORAMA_360", "Mandatory source-locked 360 panorama"),
    ("CG_03", "CG_03_PANORAMA_VALIDATION", "360 seam + concept-camera regression"),
    ("CG_04", "CG_04_CAMERA_RAILS", "Author-style persistent camera rails"),
    ("CG_05", "CG_05_CAMERA_COVERAGE", "Camera coverage + closed-loop consistency"),
    ("CG_06", "CG_06_WAN_COMPLETION", "Masked WAN world completion"),
    ("CG_07", "CG_07_HIRES_COMPOSITE", "Source-preserving HiRes composite"),
    ("CG_08", "CG_08_MULTIVIEW_DATASET", "Extendable SphereSfM/COLMAP dataset"),
    ("CG_09", "CG_09_WORLD_3DGS", "First functional explorable 360 world"),
    ("CG_10", "CG_10_COVERAGE_EXTENSION", "Targeted dataset/world coverage extension"),
    ("CG_11", "CG_11_P9_WORLD_REGISTRATION", "P9/world metric registration"),
    ("CG_12", "CG_12_POLYGON_WORLD", "First useful polygonal world"),
    ("CG_13", "CG_13_HOLE_FILL_ACCEPTANCE", "Useful hole-fill acceptance"),
    ("CG_14", "CG_14_P9_P10_FUSION", "Protected P9 + P10 comparison/fusion"),
    ("CG_15", "CG_15_GEOMETRY_CLEANUP", "Geometry cleanup/regularization"),
    ("CG_16", "CG_16_TEXTURE_PROVENANCE", "Texture + provenance regression"),
    ("CG_17", "CG_17_MAYA_360", "Navigable Maya 360 scene"),
    ("CG_18", "CG_18_COMPLETE_RELEASE", "Complete final bundle"),
)

_EVIDENCE_DIRS = ("OUTPUTS", "PREVIEWS", "LOGS", "MANIFESTS")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def result_root(attempt_root: str | Path) -> Path:
    return Path(attempt_root).expanduser().resolve() / "RESULTS"


def _stage_spec(stage_code: str) -> tuple[str, str, str]:
    code = str(stage_code or "").strip().upper()
    for item in _RESULT_STAGES:
        if item[0] == code:
            return item
    raise ContractError(f"Unknown result stage: {stage_code!r}")


def stage_root(attempt_root: str | Path, stage_code: str) -> Path:
    _, folder, _ = _stage_spec(stage_code)
    return result_root(attempt_root) / folder


def _stage_status_payload(
    attempt_root: Path,
    p10_attempt_id: str,
    p9_run_id: str,
    scene_contract_id: str,
    stage_code: str,
    *,
    runtime_status: str = "PENDING",
    functional_status: str = "PENDING",
    artist_quality_status: str = "PENDING",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    code, folder, title = _stage_spec(stage_code)
    root = result_root(attempt_root) / folder
    return {
        "schema": _STATUS_SCHEMA,
        "stage_code": code,
        "stage_title": title,
        "p10_attempt_id": p10_attempt_id,
        "parent_p9_run_id": p9_run_id,
        "scene_contract_id": scene_contract_id,
        "stage_root": str(root),
        "runtime_status": runtime_status,
        "functional_status": functional_status,
        "artist_quality_status": artist_quality_status,
        "result_first_rule": (
            "A stage cannot be closed by executable/CI success alone. "
            "Physical OUTPUTS + PREVIEWS + MANIFESTS are required."
        ),
        "manual_backfill_required": False,
        "updated_at_utc": _utc_now(),
        "notes": list(notes or []),
    }


def _refresh_index(
    attempt_root: Path,
    p10_attempt_id: str,
    p9_run_id: str,
    scene_contract_id: str,
) -> Path:
    root = result_root(attempt_root)
    stages: list[dict[str, Any]] = []
    for code, folder, title in _RESULT_STAGES:
        status_path = root / folder / "STATUS.json"
        if status_path.is_file():
            try:
                status = json.loads(status_path.read_text(encoding="utf-8"))
            except Exception:
                status = {}
        else:
            status = {}
        stages.append(
            {
                "stage_code": code,
                "stage_title": title,
                "folder": folder,
                "runtime_status": status.get("runtime_status", "PENDING"),
                "functional_status": status.get("functional_status", "PENDING"),
                "artist_quality_status": status.get("artist_quality_status", "PENDING"),
                "status_path": str(status_path),
            }
        )
    index = {
        "schema": _SCHEMA,
        "p10_attempt_id": p10_attempt_id,
        "parent_p9_run_id": p9_run_id,
        "scene_contract_id": scene_contract_id,
        "result_root": str(root),
        "result_tree_location_policy": "INSIDE_COMFYUI_OUTPUT_ATTEMPT_FROM_CREATION",
        "manual_backfill_required": False,
        "stage_close_requires_physical_evidence": True,
        "evidence_directories": list(_EVIDENCE_DIRS),
        "stages": stages,
        "updated_at_utc": _utc_now(),
    }
    path = root / "RESULT_INDEX.json"
    _write_json(path, index)
    return path


def initialize_result_output_tree(
    attempt_root: str | Path,
    *,
    p10_attempt_id: str,
    p9_run_id: str,
    scene_contract_id: str,
    source_p9_run_dir: str | Path,
) -> dict[str, Any]:
    """Create the artist-visible result tree at attempt creation time.

    The tree lives under:
      <ComfyUI output>/conceptghost/p10_attempts/<P9_RUN_ID>/<ATTEMPT_ID>/RESULTS

    This is deliberately created before panorama/WAN/reconstruction begins so no
    later helper or backfill script is required to discover official evidence.
    """

    attempt = Path(attempt_root).expanduser().resolve()
    if not attempt.is_dir():
        raise ContractError(f"P10 attempt root does not exist: {attempt}")

    root = result_root(attempt)
    root.mkdir(parents=True, exist_ok=True)

    for code, folder, _ in _RESULT_STAGES:
        stage = root / folder
        stage.mkdir(parents=True, exist_ok=True)
        for name in _EVIDENCE_DIRS:
            (stage / name).mkdir(parents=True, exist_ok=True)
        status_path = stage / "STATUS.json"
        if not status_path.is_file():
            _write_json(
                status_path,
                _stage_status_payload(
                    attempt,
                    p10_attempt_id,
                    p9_run_id,
                    scene_contract_id,
                    code,
                ),
            )

    # Seed CG_00 with physical, human-inspectable P9 authority evidence.
    boundary = validate_official_run(source_p9_run_dir)
    if boundary.run_id != p9_run_id:
        raise ContractError(
            f"Result output P9 run mismatch: {boundary.run_id!r} != {p9_run_id!r}"
        )
    if boundary.scene_contract_id != scene_contract_id:
        raise ContractError("Result output scene_contract_id does not match accepted P9")

    cg00 = stage_root(attempt, "CG_00")
    source_copy = cg00 / "OUTPUTS" / "source_concept.png"
    camera_copy = cg00 / "OUTPUTS" / "camera.json"
    preview_copy = cg00 / "PREVIEWS" / "source_concept.png"
    shutil.copy2(boundary.source_image, source_copy)
    shutil.copy2(boundary.camera, camera_copy)
    shutil.copy2(boundary.source_image, preview_copy)
    authority_manifest = {
        "schema": "ConceptGhost.ResultP9AuthorityEvidence.v0.1",
        "p10_attempt_id": p10_attempt_id,
        "parent_p9_run_id": p9_run_id,
        "scene_contract_id": scene_contract_id,
        "source_concept_path": str(source_copy),
        "camera_path": str(camera_copy),
        "primary_mesh_authority_path": str(boundary.primary_mesh),
        "source_sha256": _sha256(source_copy),
        "camera_sha256": _sha256(camera_copy),
        "p9_is_immutable": True,
        "created_at_utc": _utc_now(),
    }
    _write_json(cg00 / "MANIFESTS" / "p9_authority_evidence.json", authority_manifest)
    _write_json(
        cg00 / "STATUS.json",
        _stage_status_payload(
            attempt,
            p10_attempt_id,
            p9_run_id,
            scene_contract_id,
            "CG_00",
            runtime_status="PASS",
            functional_status="PASS",
            artist_quality_status="ACCEPTED",
            notes=["Exact source concept and accepted camera copied as physical evidence."],
        ),
    )

    index_path = _refresh_index(attempt, p10_attempt_id, p9_run_id, scene_contract_id)
    return {
        "schema": _SCHEMA,
        "result_root": str(root),
        "result_index_path": str(index_path),
        "stage_count": len(_RESULT_STAGES),
        "stage_codes": [item[0] for item in _RESULT_STAGES],
        "manual_backfill_required": False,
        "cg00_authority_manifest": str(cg00 / "MANIFESTS" / "p9_authority_evidence.json"),
    }


def stage_evidence_summary(attempt_root: str | Path, stage_code: str) -> dict[str, Any]:
    root = stage_root(attempt_root, stage_code)
    counts: dict[str, int] = {}
    files: dict[str, list[str]] = {}
    for name in _EVIDENCE_DIRS:
        folder = root / name
        items = sorted(
            str(path.relative_to(root))
            for path in folder.rglob("*")
            if path.is_file()
        )
        counts[name] = len(items)
        files[name] = items
    return {"stage_root": str(root), "counts": counts, "files": files}


def update_stage_status(
    attempt_root: str | Path,
    *,
    p10_attempt_id: str,
    p9_run_id: str,
    scene_contract_id: str,
    stage_code: str,
    runtime_status: str,
    functional_status: str,
    artist_quality_status: str,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Update one stage, refusing a false PASS without physical evidence.

    A functional PASS requires at least one physical file in OUTPUTS, PREVIEWS
    and MANIFESTS. This is the core guard against 'the executable ran' being
    mistaken for 'the stage produced an inspectable result'.
    """

    attempt = Path(attempt_root).expanduser().resolve()
    summary = stage_evidence_summary(attempt, stage_code)
    functional = str(functional_status or "").strip().upper()
    artist = str(artist_quality_status or "").strip().upper()
    if functional == "PASS":
        missing = [
            name
            for name in ("OUTPUTS", "PREVIEWS", "MANIFESTS")
            if int(summary["counts"].get(name, 0)) < 1
        ]
        if missing:
            raise ContractError(
                f"{stage_code} cannot be functional PASS without physical evidence in: "
                + ", ".join(missing)
            )
    if artist in {"ACCEPTED", "PASS"} and functional != "PASS":
        raise ContractError(
            f"{stage_code} cannot be artist accepted unless functional_status is PASS"
        )

    payload = _stage_status_payload(
        attempt,
        p10_attempt_id,
        p9_run_id,
        scene_contract_id,
        stage_code,
        runtime_status=str(runtime_status or "PENDING").upper(),
        functional_status=functional or "PENDING",
        artist_quality_status=artist or "PENDING",
        notes=notes,
    )
    payload["evidence"] = summary
    status_path = stage_root(attempt, stage_code) / "STATUS.json"
    _write_json(status_path, payload)
    index_path = _refresh_index(attempt, p10_attempt_id, p9_run_id, scene_contract_id)
    return {
        "status_path": str(status_path),
        "result_index_path": str(index_path),
        "evidence": summary,
    }
