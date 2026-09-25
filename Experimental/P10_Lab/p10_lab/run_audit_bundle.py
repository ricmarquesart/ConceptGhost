from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError


_SCHEMA = "ConceptGhost.P10RunAuditBundle.v0.2"
_SAFE_SUFFIXES = {
    ".json", ".txt", ".log", ".md", ".csv", ".tsv",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
}
_P9_AUDIT_DIRS = (
    "acceptance",
    "benchmark",
    "camera",
    "diagnostics",
    "logs",
    "package",
    "validation",
    "maya",
    "geometry/native",
)
_P9_ROOT_FILES = (
    "manifest.json",
    "RUN_PARAMETERS.txt",
    "output_index.json",
    "official_outputs_contract.json",
)


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_file(path: Path, *, max_file_bytes: int) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, "NOT_A_FILE"
    if path.suffix.lower() not in _SAFE_SUFFIXES:
        return False, "HEAVY_OR_UNSUPPORTED_EXTENSION"
    try:
        size = path.stat().st_size
    except OSError:
        return False, "STAT_FAILED"
    if size > max_file_bytes:
        return False, "PER_FILE_SIZE_LIMIT"
    return True, None


def _archive_name(path: Path, attempt_root: Path, p9_run_dir: Path) -> str:
    if _is_within(path, attempt_root):
        return "p10_attempt/" + path.relative_to(attempt_root).as_posix()
    if _is_within(path, p9_run_dir):
        return "p9_authority/" + path.relative_to(p9_run_dir).as_posix()
    return "referenced/" + path.name


def _bulk_generated_frame_reason(path: Path, root: Path) -> str | None:
    """Exclude regenerable frame sequences while retaining previews/manifests.

    The audit ZIP is a diagnostic handoff, not a second copy of every generated
    P10 frame.  Previous runs could spend almost the entire 250 MiB budget on
    Gate 4/5/6 PNG sequences, leaving little headroom for later diagnostics.
    """
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = tuple(part.lower() for part in relative.parts)
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        return None
    if "dense" in parts and "images" in parts:
        return "BULK_DENSE_IMAGE_EXCLUDED_KEEP_MANIFEST_LOGS_PREVIEWS"
    if "dataset" in parts and "images" in parts:
        return "BULK_DATASET_IMAGE_EXCLUDED_KEEP_MANIFEST_LOGS_PREVIEWS"
    if "control_sequence" in parts and "frames" in parts:
        return "BULK_CONTROL_FRAME_EXCLUDED_KEEP_GIF_CONTACT_SHEET"
    return None


def _walk_safe(root: Path, *, max_file_bytes: int):
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        bulk_reason = _bulk_generated_frame_reason(path, root)
        if bulk_reason is not None:
            yield path, False, bulk_reason
            continue
        ok, reason = _safe_file(path, max_file_bytes=max_file_bytes)
        yield path, ok, reason


def _extract_referenced_paths(value: Any):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _extract_referenced_paths(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _extract_referenced_paths(nested)
    elif isinstance(value, str):
        text = value.strip()
        if not text or len(text) > 4096:
            return
        try:
            candidate = Path(text).expanduser()
        except Exception:
            return
        if candidate.is_absolute():
            yield candidate.resolve()


def default_project_audit_root(
    p9_run_dir: str | Path,
    p10_attempt_id: str,
) -> Path:
    """Store the audit bundle directly in the dynamically-created P9 run folder.

    The P9 run folder is already derived from the artist-selected output_root +
    scene_name + run_id, so this path is never hard-coded to a particular project.
    Later Gate 7 rebuilds replace the run-local audit ZIP with richer evidence.
    Immutable P10 attempt data remains under the P10 attempt root.
    """
    return Path(p9_run_dir).expanduser().resolve()


def _write_latest_pointers(
    audit_root: Path,
    bundle_path: Path,
    manifest_path: Path,
    *,
    status: str,
    p9_run_id: str | None,
    p10_attempt_id: str | None,
) -> None:
    """Write latest-audit pointers directly beside the P9 run outputs."""
    project_run_root = audit_root.resolve()
    project_run_root.mkdir(parents=True, exist_ok=True)
    (project_run_root / "LATEST_AUDIT.txt").write_text(
        str(bundle_path) + "\n", encoding="utf-8"
    )
    (project_run_root / "LATEST_AUDIT_MANIFEST.txt").write_text(
        str(manifest_path) + "\n", encoding="utf-8"
    )
    (project_run_root / "LATEST_AUDIT_INDEX.json").write_text(
        json.dumps(
            {
                "schema": "ConceptGhost.P10LatestAuditPointer.v0.2",
                "status": status,
                "p9_run_id": p9_run_id,
                "p10_attempt_id": p10_attempt_id,
                "bundle_path": str(bundle_path),
                "manifest_path": str(manifest_path),
                "storage": "P9_RUN_ROOT_DYNAMIC_FROM_MASTER_OUTPUT_ROOT",
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _build_core(
    *,
    gate6_runtime: Path,
    p9_run_dir: Path,
    attempt_root: Path,
    p9_run_id: str | None,
    p10_attempt_id: str | None,
    scene_contract_id: str | None,
    gate7_path: Path | None,
    visual_pack_path: Path | None,
    failure_manifest_path: Path | None,
    status: str,
    output_root: str | Path | None,
    max_file_bytes: int,
    max_total_bytes: int,
) -> dict[str, Any]:
    if not gate6_runtime.is_file():
        raise ContractError(
            f"Required reconstruction_runtime_manifest.json is missing: {gate6_runtime}"
        )

    audit_root = (
        Path(output_root).expanduser().resolve()
        if output_root is not None and str(output_root).strip()
        else default_project_audit_root(p9_run_dir, str(p10_attempt_id or "UNKNOWN_ATTEMPT"))
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    zip_path = audit_root / "RUN_AUDIT_BUNDLE.zip"
    manifest_path = audit_root / "RUN_AUDIT_BUNDLE_manifest.json"

    included: dict[str, Path] = {}
    omitted: list[dict[str, Any]] = []

    def add(path: Path, *, required: bool = False):
        path = path.expanduser().resolve()
        if path == zip_path or path == manifest_path:
            return
        ok, skip_reason = _safe_file(path, max_file_bytes=max_file_bytes)
        if not ok:
            if required:
                raise ContractError(f"Required audit file is not collectable: {path}: {skip_reason}")
            omitted.append({"path": str(path), "reason": skip_reason})
            return
        arc = _archive_name(path, attempt_root, p9_run_dir)
        included.setdefault(arc, path)

    add(gate6_runtime, required=True)
    if gate7_path is not None:
        add(gate7_path, required=True)
    if visual_pack_path is not None:
        add(visual_pack_path, required=True)
    if failure_manifest_path is not None:
        add(failure_manifest_path, required=True)

    for path, ok, skip_reason in _walk_safe(attempt_root, max_file_bytes=max_file_bytes):
        if _is_within(path, audit_root):
            continue
        if ok:
            add(path)
        else:
            omitted.append({"path": str(path), "reason": skip_reason})

    for name in _P9_ROOT_FILES:
        candidate = p9_run_dir / name
        if candidate.is_file():
            add(candidate)
    for relative in _P9_AUDIT_DIRS:
        root = p9_run_dir / relative
        if not root.exists():
            continue
        for path, ok, skip_reason in _walk_safe(root, max_file_bytes=max_file_bytes):
            if ok:
                add(path)
            else:
                omitted.append({"path": str(path), "reason": skip_reason})

    reference_sources = [gate6_runtime]
    for candidate in (gate7_path, visual_pack_path, failure_manifest_path):
        if candidate is not None:
            reference_sources.append(candidate)
    for source in reference_sources:
        payload = _read_json(source, source.name)
        for referenced in _extract_referenced_paths(payload):
            if _is_within(referenced, attempt_root) or _is_within(referenced, p9_run_dir):
                add(referenced)

    rows = []
    total = 0
    final_included: list[tuple[str, Path]] = []

    # Required audit evidence must be admitted before optional discoveries.
    # P9 authority logs/manifests are the next priority: the audit bundle exists
    # specifically so a target-PC failure can be diagnosed together with the
    # immutable upstream run that fed P10.
    # The previous alphabetical pass could consume max_total_bytes first and
    # then reject reconstruction_runtime_manifest.json even though it was a
    # hard requirement. Reserve/admit required files first, then fill the
    # remaining budget with optional evidence.
    required_paths = [gate6_runtime]
    for candidate in (gate7_path, visual_pack_path, failure_manifest_path):
        if candidate is not None:
            required_paths.append(candidate)
    required_arcs = {
        _archive_name(path.resolve(), attempt_root, p9_run_dir)
        for path in required_paths
    }

    ordered_items = sorted(
        included.items(),
        key=lambda item: (
            0 if item[0] in required_arcs else
            1 if item[0].startswith("p9_authority/") else
            2,
            item[0],
        ),
    )
    for arc, path in ordered_items:
        size = path.stat().st_size
        required = arc in required_arcs
        if total + size > max_total_bytes:
            if required:
                raise ContractError(
                    "RUN_AUDIT_BUNDLE total-size limit is too small for required core evidence: "
                    f"{path}"
                )
            omitted.append({"path": str(path), "reason": "TOTAL_SIZE_LIMIT"})
            continue
        total += size
        final_included.append((arc, path))
        rows.append({
            "archive_path": arc,
            "source_path": str(path),
            "bytes": size,
            "sha256": _sha256(path),
            "required": required,
        })

    gate6_arc = _archive_name(gate6_runtime, attempt_root, p9_run_dir)
    if not any(arc == gate6_arc for arc, _ in final_included):
        raise ContractError("RUN_AUDIT_BUNDLE would omit reconstruction_runtime_manifest.json")

    created = datetime.now(timezone.utc).isoformat()
    internal_index = {
        "schema": _SCHEMA,
        "created_at_utc": created,
        "status": status,
        "scene_contract_id": scene_contract_id,
        "p9_run_id": p9_run_id,
        "p10_attempt_id": p10_attempt_id,
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_root": str(attempt_root),
        "project_audit_root": str(audit_root),
        "reconstruction_runtime_manifest_path": str(gate6_runtime),
        "reconstruction_runtime_manifest_included": True,
        "gate7_runtime_manifest_path": str(gate7_path) if gate7_path else None,
        "visual_pack_manifest_path": str(visual_pack_path) if visual_pack_path else None,
        "failure_manifest_path": str(failure_manifest_path) if failure_manifest_path else None,
        "growth_policy": (
            "AUTO_AT_GATE7_SUCCESS_OR_FAILURE; TERMINAL_NODE_REBUILDS_WITH_LATER_VISUAL_EVIDENCE; "
            "AUTO_INCLUDE_SAFE_JSON_LOG_TEXT_AND_PREVIEW_EVIDENCE_UNDER_IMMUTABLE_P10_ATTEMPT"
        ),
        "storage_policy": (
            "DRIVE_VISIBLE_RUN_LOCAL_BUNDLE_DIRECTLY_AT_<P9_RUN>/RUN_AUDIT_BUNDLE.zip; "
            "P9_RUN_IS_DYNAMIC_FROM_MASTER_OUTPUT_ROOT_PLUS_SCENE_PLUS_RUN_ID; "
            "EXISTING_P9_AUTHORITY_FILES_REMAIN_UNMODIFIED"
        ),
        "heavy_payload_policy": (
            "EXCLUDE_PLY_NPZ_FBX_MA_USDA_AND_OTHER_HEAVY_GEOMETRY; "
            "EXCLUDE_REGENERABLE_BULK_FRAME_SEQUENCES; KEEP_LOGS_MANIFESTS_GIFS_CONTACT_SHEETS_AND_PREVIEWS"
        ),
        "limits": {
            "max_file_bytes": int(max_file_bytes),
            "max_total_bytes": int(max_total_bytes),
        },
        "included_file_count": len(rows),
        "included_bytes": total,
        "files": rows,
        "omitted": omitted,
    }
    readme = (
        "ConceptGhost RUN_AUDIT_BUNDLE\n"
        "===============================\n"
        f"Status: {status}\n"
        "Required core: reconstruction_runtime_manifest.json.\n"
        "This bundle is generated automatically by Gate 7 even when Gate 7 fails.\n"
        "The terminal audit node rebuilds it with richer visual evidence after a successful run.\n"
        "Heavy geometry/DCC payloads are intentionally excluded.\n"
    )

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(
            "RUN_AUDIT_BUNDLE_index.json",
            json.dumps(internal_index, indent=2, sort_keys=True),
        )
        archive.writestr("README_RUN_AUDIT_BUNDLE.txt", readme)
        for arc, path in final_included:
            archive.write(path, arcname=arc)

    result = {
        **internal_index,
        "bundle_path": str(zip_path),
        "bundle_bytes": zip_path.stat().st_size,
        "bundle_sha256": _sha256(zip_path),
        "manifest_path": str(manifest_path),
    }
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_latest_pointers(
        audit_root,
        zip_path,
        manifest_path,
        status=status,
        p9_run_id=p9_run_id,
        p10_attempt_id=p10_attempt_id,
    )
    return result


def build_run_audit_bundle(
    gate7_runtime_manifest_path: str | Path,
    visual_pack_manifest_path: str | Path | None = None,
    *,
    output_root: str | Path | None = None,
    max_file_bytes: int = 50 * 1024 * 1024,
    max_total_bytes: int = 250 * 1024 * 1024,
) -> dict[str, Any]:
    """Build/rebuild the canonical project-side audit ZIP for a successful Gate 7 run."""

    gate7_path = Path(gate7_runtime_manifest_path).expanduser().resolve()
    gate7 = _read_json(gate7_path, "Gate 7 runtime manifest")
    if gate7.get("schema") != "ConceptGhost.P10Gate7Runtime.v0.1":
        raise ContractError("RUN_AUDIT_BUNDLE requires ConceptGhost.P10Gate7Runtime.v0.1")
    if gate7.get("status") != "PASS":
        raise ContractError("RUN_AUDIT_BUNDLE success path requires Gate 7 runtime status PASS")

    attempt_root_raw = gate7.get("p10_attempt_root")
    p9_run_dir_raw = gate7.get("p9_run_dir")
    gate6_runtime_raw = gate7.get("gate6_runtime_manifest_path")
    if not attempt_root_raw or not p9_run_dir_raw or not gate6_runtime_raw:
        raise ContractError("Gate 7 runtime is missing p10_attempt_root / p9_run_dir / Gate 6 runtime")

    visual_pack_path = None
    if visual_pack_manifest_path is not None and str(visual_pack_manifest_path).strip():
        visual_pack_path = Path(str(visual_pack_manifest_path)).expanduser().resolve()
        if not visual_pack_path.is_file():
            raise ContractError(f"Visual evidence pack manifest is missing: {visual_pack_path}")

    return _build_core(
        gate6_runtime=Path(str(gate6_runtime_raw)).expanduser().resolve(),
        p9_run_dir=Path(str(p9_run_dir_raw)).expanduser().resolve(),
        attempt_root=Path(str(attempt_root_raw)).expanduser().resolve(),
        p9_run_id=str(gate7.get("p9_run_id") or "") or None,
        p10_attempt_id=str(gate7.get("p10_attempt_id") or "") or None,
        scene_contract_id=str(gate7.get("scene_contract_id") or "") or None,
        gate7_path=gate7_path,
        visual_pack_path=visual_pack_path,
        failure_manifest_path=None,
        status="PASS",
        output_root=output_root,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )


def build_partial_run_audit_bundle(
    p9_run_dir: str | Path,
    reconstruction_runtime_manifest_path: str | Path,
    *,
    gate7_failure_manifest_path: str | Path | None = None,
    output_root: str | Path | None = None,
    max_file_bytes: int = 50 * 1024 * 1024,
    max_total_bytes: int = 250 * 1024 * 1024,
) -> dict[str, Any]:
    """Create an audit bundle after Gate 6 even if Gate 7 fails."""

    gate6_runtime = Path(reconstruction_runtime_manifest_path).expanduser().resolve()
    gate6 = _read_json(gate6_runtime, "Gate 6 reconstruction runtime manifest")
    attempt_root_raw = gate6.get("p10_attempt_root")
    if not attempt_root_raw:
        raise ContractError("Partial RUN_AUDIT_BUNDLE cannot resolve p10_attempt_root from Gate 6")
    p9 = Path(p9_run_dir).expanduser().resolve()
    failure_path = None
    if gate7_failure_manifest_path is not None and str(gate7_failure_manifest_path).strip():
        failure_path = Path(gate7_failure_manifest_path).expanduser().resolve()
        if not failure_path.is_file():
            raise ContractError(f"Gate 7 failure manifest is missing: {failure_path}")

    return _build_core(
        gate6_runtime=gate6_runtime,
        p9_run_dir=p9,
        attempt_root=Path(str(attempt_root_raw)).expanduser().resolve(),
        p9_run_id=str(gate6.get("run_id") or p9.name),
        p10_attempt_id=str(gate6.get("p10_attempt_id") or "") or None,
        scene_contract_id=None,
        gate7_path=None,
        visual_pack_path=None,
        failure_manifest_path=failure_path,
        status="PARTIAL_FAILURE",
        output_root=output_root,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )
