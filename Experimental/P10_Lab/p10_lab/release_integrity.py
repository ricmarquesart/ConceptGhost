from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


class ReleaseIntegrityError(ValueError):
    pass


REQUIRED_GATE6_PATHS = (
    "PROJECT_CONTROL.md",
    "ENVIRONMENT_LOCK.json",
    "PROTECTED_PROJECTS.json",
    "README.md",
    "00_READ_PROJECT_CONTROL.bat",
    "01_CAPTURE_ENVIRONMENT.bat",
    "02_OPTIONAL_RECOVER_SHARED_ENVIRONMENT.bat",
    "03_INSTALL_ALL.bat",
    "04_VERIFY_INSTALL.bat",
    "05_RUN_CONCEPTGHOST.bat",
    "LOCKS.json",
    "RELEASE.json",
    "BUNDLE_MANIFEST.json",
    "SHA256SUMS.txt",
    "P10_GATE6_RELEASE.json",
    "P10_GATE6_CODE_MANIFEST.json",
    "P10_GATE6_BUNDLE_MANIFEST.json",
    "P10_GATE6_VALIDATION.txt",
    "Installer/install_gate6.ps1",
    "Installer/test_gate6_bundle.py",
    "Payload/custom_nodes/ConceptGhost_Stage68/__init__.py",
    "Payload/custom_nodes/ConceptGhost_Stage68/nodes.py",
    "Payload/custom_nodes/ConceptGhost_Stage68/web/fast_draft_preview.js",
    "Payload/custom_nodes/ConceptGhost_Stage68/web/scene_authority_controls.js",
    "Payload/custom_nodes/ConceptGhost_Stage68/web/manual_metric_scale.js",
    "Payload/custom_nodes/ConceptGhost_P10_Lab/__init__.py",
    "Payload/custom_nodes/ConceptGhost_P10_Lab/wan_sequence.py",
    "Payload/custom_nodes/ConceptGhost_P10_Lab/sparse_triangulation.py",
    "Payload/custom_nodes/ConceptGhost_P10_Lab/reconstruction_runtime.py",
    "Payload/custom_nodes/ConceptGhost_P10_Lab/reconstruction_node.py",
    "Runtime/MoGeRuntime/SOURCE_LOCK.json",
    "Runtime/MoGeRuntime/worker/moge_worker.py",
    "Runtime/MoGeRuntime/worker/precache_moge3_models.py",
    "Runtime/MoGeRuntime/worker/verify_moge3_runtime.py",
    "Runtime/MoGeRuntime/worker/verify_vitg_runtime.py",
)

MIN_COUNTS = {
    "Installer": 50,
    "Payload/custom_nodes/ConceptGhost_P10_Lab": 31,
    "Payload/custom_nodes/ConceptGhost_Stage68": 29,
    "Payload/custom_nodes/ConceptGhost_Stage68/web": 3,
    "Payload/docs": 3,
    "Payload/workflows": 2,
}


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseIntegrityError(f"Cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReleaseIntegrityError(f"JSON root must be an object: {path}")
    return value


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _verify_sha256s(root: Path) -> None:
    sums = root / "SHA256SUMS.txt"
    for number, raw in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            raise ReleaseIntegrityError(f"Malformed SHA256SUMS line {number}: {raw}")
        relative = parts[1].strip().lstrip("*")
        target = root / relative
        if not target.is_file():
            raise ReleaseIntegrityError(f"SHA256SUMS references missing file: {relative}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual.lower() != parts[0].lower():
            raise ReleaseIntegrityError(f"SHA-256 mismatch: {relative}")


def validate_gate6_complete_bundle(
    bundle_root: str | Path,
    *,
    expected_revision: str | None = None,
    verify_sha256: bool = True,
) -> dict[str, object]:
    root = Path(bundle_root).resolve()
    if not root.is_dir():
        raise ReleaseIntegrityError(f"Bundle root does not exist: {root}")

    missing = [relative for relative in REQUIRED_GATE6_PATHS if not (root / relative).is_file()]
    if missing:
        raise ReleaseIntegrityError(
            "Gate 6 complete bundle is missing required files: " + ", ".join(missing)
        )

    masters = sorted(root.glob("ConceptGhost_Master_v*.json"))
    if len(masters) != 1:
        raise ReleaseIntegrityError(
            f"Expected exactly one root ConceptGhost Master workflow, found {len(masters)}"
        )

    counts: dict[str, int] = {}
    for relative, minimum in MIN_COUNTS.items():
        folder = root / relative
        if not folder.is_dir():
            raise ReleaseIntegrityError(f"Missing required bundle folder: {relative}")
        count = sum(1 for child in folder.iterdir() if child.is_file())
        counts[relative] = count
        if count < minimum:
            raise ReleaseIntegrityError(
                f"Incomplete bundle folder {relative}: {count} files, expected at least {minimum}"
            )

    release = _load_json(root / "P10_GATE6_RELEASE.json")
    release_name = str(release.get("release") or "")
    match = re.search(r"_(r\d+)$", release_name)
    if not match:
        raise ReleaseIntegrityError("P10_GATE6_RELEASE.release has no rN revision suffix")
    revision = match.group(1)
    if expected_revision is not None and revision != expected_revision:
        raise ReleaseIntegrityError(
            f"Release revision mismatch: manifest={revision}, expected={expected_revision}"
        )

    workflow_rel = str(release.get("workflow") or "")
    workflow = root / workflow_rel
    if not workflow_rel or not workflow.is_file():
        raise ReleaseIntegrityError(f"Release workflow is missing: {workflow_rel!r}")
    if revision not in workflow.name:
        raise ReleaseIntegrityError(
            f"Workflow revision mismatch: release={revision}, workflow={workflow.name}"
        )

    install_banner = (root / "03_INSTALL_ALL.bat").read_text(
        encoding="utf-8", errors="replace"
    )
    readme = (root / "README_P10_GATE6_RECONSTRUCTION.md").read_text(
        encoding="utf-8", errors="replace"
    )
    if revision not in install_banner:
        raise ReleaseIntegrityError(f"03_INSTALL_ALL.bat does not identify {revision}")
    if revision not in readme:
        raise ReleaseIntegrityError(f"Gate 6 README does not identify {revision}")

    sparse = root / "Payload/custom_nodes/ConceptGhost_P10_Lab/sparse_triangulation.py"
    expected_blob = str(release.get("installed_sparse_authority_git_blob_sha1") or "").strip()
    if expected_blob:
        actual_blob = _git_blob_sha1(sparse)
        if actual_blob != expected_blob:
            raise ReleaseIntegrityError(
                "Packaged sparse_triangulation.py does not match the release's "
                f"authoritative git blob: {actual_blob} != {expected_blob}"
            )

    if verify_sha256:
        _verify_sha256s(root)

    return {
        "schema": "ConceptGhost.P10Gate6CompleteBundleIntegrity.v0.1",
        "status": "PASS",
        "revision": revision,
        "root": str(root),
        "workflow": workflow_rel,
        "root_master": masters[0].name,
        "counts": counts,
        "sha256_verified": verify_sha256,
    }
