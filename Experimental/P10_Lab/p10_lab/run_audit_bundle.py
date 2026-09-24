from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError


_SCHEMA = "ConceptGhost.P10RunAuditBundle.v0.1"
_SAFE_SUFFIXES = {
    ".json", ".txt", ".log", ".md", ".csv", ".tsv",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
}
_P9_AUDIT_DIRS = (
    "acceptance",
    "benchmark",
    "camera",
    "diagnostics",
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


def _walk_safe(root: Path, *, max_file_bytes: int):
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
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


def build_run_audit_bundle(
    gate7_runtime_manifest_path: str | Path,
    visual_pack_manifest_path: str | Path | None = None,
    *,
    output_root: str | Path | None = None,
    max_file_bytes: int = 50 * 1024 * 1024,
    max_total_bytes: int = 250 * 1024 * 1024,
) -> dict[str, Any]:
    """Build a compact, future-growing audit ZIP for one P10 attempt.

    The bundle is intentionally evidence-only. Heavy geometry / DCC payloads
    such as PLY, NPZ, FBX, MA and USDA are never copied. Every future gate that
    persists JSON/log/preview evidence under the same immutable p10_attempt_root
    is discovered automatically, so the audit bundle becomes richer as the
    pipeline grows without changing its basic contract.
    """

    gate7_path = Path(gate7_runtime_manifest_path).expanduser().resolve()
    gate7 = _read_json(gate7_path, "Gate 7 runtime manifest")
    if gate7.get("schema") != "ConceptGhost.P10Gate7Runtime.v0.1":
        raise ContractError("RUN_AUDIT_BUNDLE requires ConceptGhost.P10Gate7Runtime.v0.1")
    if gate7.get("status") != "PASS":
        raise ContractError("RUN_AUDIT_BUNDLE requires Gate 7 runtime status PASS")

    attempt_root_raw = gate7.get("p10_attempt_root")
    p9_run_dir_raw = gate7.get("p9_run_dir")
    gate6_runtime_raw = gate7.get("gate6_runtime_manifest_path")
    if not attempt_root_raw or not p9_run_dir_raw or not gate6_runtime_raw:
        raise ContractError("Gate 7 runtime is missing p10_attempt_root / p9_run_dir / Gate 6 runtime")

    attempt_root = Path(str(attempt_root_raw)).expanduser().resolve()
    p9_run_dir = Path(str(p9_run_dir_raw)).expanduser().resolve()
    gate6_runtime = Path(str(gate6_runtime_raw)).expanduser().resolve()
    if not gate6_runtime.is_file():
        raise ContractError(
            f"Required reconstruction_runtime_manifest.json is missing: {gate6_runtime}"
        )

    visual_pack = None
    visual_pack_path = None
    if visual_pack_manifest_path is not None and str(visual_pack_manifest_path).strip():
        visual_pack_path = Path(str(visual_pack_manifest_path)).expanduser().resolve()
        if not visual_pack_path.is_file():
            raise ContractError(f"Visual evidence pack manifest is missing: {visual_pack_path}")
        visual_pack = _read_json(visual_pack_path, "Gate 7 visual evidence manifest")

    audit_root = (
        Path(output_root).expanduser().resolve()
        if output_root is not None and str(output_root).strip()
        else attempt_root / "audit"
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    zip_path = audit_root / "RUN_AUDIT_BUNDLE.zip"
    manifest_path = audit_root / "RUN_AUDIT_BUNDLE_manifest.json"

    included: dict[str, Path] = {}
    omitted: list[dict[str, Any]] = []

    def add(path: Path, *, required: bool = False, reason: str = "DISCOVERED"):
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

    # Hard requirements. The Gate 6 runtime manifest is the primary numerical
    # reconstruction audit requested by the project owner.
    add(gate6_runtime, required=True, reason="REQUIRED_GATE6_RUNTIME")
    add(gate7_path, required=True, reason="REQUIRED_GATE7_RUNTIME")
    if visual_pack_path is not None:
        add(visual_pack_path, required=True, reason="REQUIRED_GATE7_VISUAL_PACK")

    # Future-growing P10 evidence policy: every safe manifest/log/preview under
    # the immutable attempt is included automatically.
    for path, ok, skip_reason in _walk_safe(attempt_root, max_file_bytes=max_file_bytes):
        if _is_within(path, audit_root):
            continue
        if ok:
            add(path)
        else:
            omitted.append({"path": str(path), "reason": skip_reason})

    # Preserve the accepted P9 authority audit without duplicating heavy assets.
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

    # Follow explicit file references from the main manifests, but only if they
    # resolve inside the immutable P10 attempt or the accepted P9 run.
    reference_sources = [gate6_runtime, gate7_path]
    if visual_pack_path is not None:
        reference_sources.append(visual_pack_path)
    for source in reference_sources:
        payload = _read_json(source, source.name)
        for referenced in _extract_referenced_paths(payload):
            if _is_within(referenced, attempt_root) or _is_within(referenced, p9_run_dir):
                add(referenced)

    rows = []
    total = 0
    final_included: list[tuple[str, Path]] = []
    for arc, path in sorted(included.items()):
        size = path.stat().st_size
        if total + size > max_total_bytes:
            omitted.append({"path": str(path), "reason": "TOTAL_SIZE_LIMIT"})
            continue
        total += size
        final_included.append((arc, path))
        rows.append({
            "archive_path": arc,
            "source_path": str(path),
            "bytes": size,
            "sha256": _sha256(path),
        })

    gate6_arc = _archive_name(gate6_runtime, attempt_root, p9_run_dir)
    reconstruction_included = any(arc == gate6_arc for arc, _ in final_included)
    if not reconstruction_included:
        raise ContractError("RUN_AUDIT_BUNDLE would omit reconstruction_runtime_manifest.json")

    created = datetime.now(timezone.utc).isoformat()
    internal_index = {
        "schema": _SCHEMA,
        "created_at_utc": created,
        "status": "PASS",
        "scene_contract_id": gate7.get("scene_contract_id"),
        "p9_run_id": gate7.get("p9_run_id"),
        "p10_attempt_id": gate7.get("p10_attempt_id"),
        "p9_run_dir": str(p9_run_dir),
        "p10_attempt_root": str(attempt_root),
        "reconstruction_runtime_manifest_path": str(gate6_runtime),
        "reconstruction_runtime_manifest_included": True,
        "gate7_runtime_manifest_path": str(gate7_path),
        "visual_pack_manifest_path": str(visual_pack_path) if visual_pack_path else None,
        "growth_policy": (
            "TERMINAL_AUDIT_NODE; AUTO_INCLUDE_SAFE_JSON_LOG_TEXT_AND_PREVIEW_EVIDENCE_"
            "UNDER_IMMUTABLE_P10_ATTEMPT; ADD_FUTURE_GATE_EVIDENCE_AS_PIPELINE_GROWS"
        ),
        "heavy_payload_policy": "EXCLUDE_PLY_NPZ_FBX_MA_USDA_AND_OTHER_HEAVY_GEOMETRY",
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
        "Purpose: compact evidence bundle for remote audit of one immutable P10 attempt.\n\n"
        "Required core: reconstruction_runtime_manifest.json.\n"
        "Also included: Gate 7 runtime, gate-specific manifests, logs, previews, "
        "selected accepted P9 authority diagnostics and future safe gate evidence.\n\n"
        "Heavy geometry/DCC payloads are intentionally excluded.\n"
        "The audit node must remain the terminal diagnostic node as later gates are added; "
        "that makes this ZIP grow automatically with the pipeline.\n"
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
    return result
