from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any
import zipfile

from .contracts import CONTRACT_VERSION, CompletionBundle, ContractError


_BRANCH_TO_STAGE = {
    "Baseline / P9": "baseline",
    "Refined / P9 Clone": "p9",
    "Refined / P9 Clone · P10 Reserved": "p9",
}
_IDENTITY_FIELDS = (
    "scene_contract_id",
    "camera_scene_contract_id",
    "canonical_geometry_scene_contract_id",
    "primary_mesh_scene_contract_id",
)
_MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(data, dict):
        raise ContractError(f"{label} must be a JSON object: {path}")
    return data


def _required_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise ContractError(f"Missing {label}: {path}")
    return path.resolve()


def _find_primary_mesh(run: Path) -> Path:
    candidates = sorted((run / "maya").glob("ConceptGhost_*_PrimaryMesh.npz"))
    if len(candidates) != 1:
        raise ContractError(
            f"Expected exactly one official PrimaryMesh NPZ, found {len(candidates)} in {run / 'maya'}"
        )
    return candidates[0].resolve()


@dataclass(frozen=True)
class OfficialRunBoundary:
    root: Path
    source_stage: str
    branch_mode: str
    run_id: str
    scene_contract_id: str
    manifest: dict[str, Any]
    camera: Path
    source_image: Path
    primary_mesh: Path
    primary_mesh_payload: Path
    official_outputs_contract: Path
    output_index: Path
    optional: dict[str, Path]


@dataclass(frozen=True)
class BundleBuildResult:
    zip_path: Path
    source_run_id: str
    scene_contract_id: str
    source_stage: str
    bundle_sha256: str


@dataclass(frozen=True)
class IdentityComparison:
    passed: bool
    mismatches: tuple[str, ...]
    baseline_run_id: str
    p9_run_id: str


def validate_official_run(run_dir: str | Path) -> OfficialRunBoundary:
    run = Path(run_dir).resolve()
    if not run.is_dir():
        raise ContractError(f"Official run folder does not exist: {run}")

    manifest_path = _required_file(run / "manifest.json", "official manifest")
    manifest = _read_json(manifest_path, "official manifest")
    schema = str(manifest.get("schema") or "")
    if not schema.startswith("ConceptGhost.Manifest."):
        raise ContractError(f"Unsupported official manifest schema: {schema!r}")

    run_id = str(manifest.get("run_id") or "").strip()
    if not run_id:
        raise ContractError("Official manifest is missing run_id")
    if run_id != run.name:
        raise ContractError(f"Official run_id does not match folder name: {run_id!r} != {run.name!r}")

    branch_mode = str(manifest.get("branch_mode") or "")
    source_stage = _BRANCH_TO_STAGE.get(branch_mode)
    if source_stage is None:
        raise ContractError(f"Unsupported P9 boundary branch_mode: {branch_mode!r}")

    scene_contract_id = str(manifest.get("scene_contract_id") or "").strip()
    if not scene_contract_id:
        raise ContractError("Official manifest is missing scene_contract_id")
    identity = manifest.get("identity_chain")
    if not isinstance(identity, dict) or identity.get("status") != "PASS":
        raise ContractError("Official run identity_chain must be PASS")
    for key in _IDENTITY_FIELDS:
        if str(identity.get(key) or "") != scene_contract_id:
            raise ContractError(
                f"Official run identity mismatch for {key}: {identity.get(key)!r} != {scene_contract_id!r}"
            )

    status = manifest.get("status") or {}
    if not isinstance(status, dict) or status.get("authoritative") is not True:
        raise ContractError("Official run must be authoritative at the P9 boundary")
    scale = manifest.get("scale_authority") or {}
    if isinstance(scale, dict) and scale.get("p10_scale_override_allowed") is True:
        raise ContractError("P10 cannot accept a boundary that permits global scale override")

    source_image = _required_file(run / "source" / "source.png", "source image")
    camera_path = _required_file(run / "camera" / "camera.json", "camera")
    camera = _read_json(camera_path, "camera")
    if camera.get("valid") is not True:
        raise ContractError("Official camera is not valid")
    if str(camera.get("scene_contract_id") or "") != scene_contract_id:
        raise ContractError("Official camera scene_contract_id does not match run identity")

    primary_mesh = _find_primary_mesh(run)
    payload_path = _required_file(run / "maya" / "primary_mesh_payload.json", "PrimaryMesh payload")
    payload = _read_json(payload_path, "PrimaryMesh payload")
    if str(payload.get("scene_contract_id") or "") != scene_contract_id:
        raise ContractError("PrimaryMesh payload scene_contract_id does not match run identity")
    if payload.get("normal_gate") not in {None, "PASS"}:
        raise ContractError("PrimaryMesh normal gate did not pass")

    official_path = _required_file(
        run / "package" / "official_outputs_contract.json",
        "official outputs contract",
    )
    official = _read_json(official_path, "official outputs contract")
    if official.get("missing_core") not in ([], None):
        raise ContractError(f"Official run pack has missing core outputs: {official.get('missing_core')!r}")
    if str(official.get("branch_mode") or branch_mode) != branch_mode:
        raise ContractError("Official outputs branch_mode does not match manifest")

    output_index = _required_file(run / "output_index.json", "output index")
    index = _read_json(output_index, "output index")
    if str(index.get("run_id") or "") != run_id:
        raise ContractError("Output index run_id does not match official manifest")
    if str(index.get("scene_contract_id") or "") != scene_contract_id:
        raise ContractError("Output index scene_contract_id does not match official manifest")

    optional_candidates = {
        "point_cloud": run / "geometry" / "canonical" / "pointcloud.ply",
        "geometry_health": run / "diagnostics" / "geometry_health.json",
        "primary_mesh_payload": payload_path,
        "official_outputs_contract": official_path,
        "output_index": output_index,
    }
    optional = {
        key: path.resolve()
        for key, path in optional_candidates.items()
        if path.is_file()
    }
    return OfficialRunBoundary(
        root=run,
        source_stage=source_stage,
        branch_mode=branch_mode,
        run_id=run_id,
        scene_contract_id=scene_contract_id,
        manifest=manifest,
        camera=camera_path,
        source_image=source_image,
        primary_mesh=primary_mesh,
        primary_mesh_payload=payload_path,
        official_outputs_contract=official_path,
        output_index=output_index,
        optional=optional,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_completion_bundle(
    run_dir: str | Path,
    output_zip: str | Path,
) -> BundleBuildResult:
    boundary = validate_official_run(run_dir)
    output = Path(output_zip).resolve()
    if output.suffix.lower() != ".zip":
        raise ContractError("Completion Bundle output must use .zip")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".p10-bundle-", dir=output.parent) as temp_dir:
        root = Path(temp_dir)
        required_sources = {
            "source_image": (boundary.source_image, "source_image.png"),
            "camera": (boundary.camera, "camera.json"),
            "primary_mesh": (boundary.primary_mesh, "primary_mesh.npz"),
        }
        for source, name in required_sources.values():
            shutil.copy2(source, root / name)

        run_metadata = {
            "schema": "ConceptGhost.P10RunMetadata.v0.3",
            "source_stage": boundary.source_stage,
            "source_equivalent_to": "baseline",
            "source_run_id": boundary.run_id,
            "scene_contract_id": boundary.scene_contract_id,
            "source_branch_mode": boundary.branch_mode,
            "source_manifest_schema": boundary.manifest.get("schema"),
            "geometry_profile": boundary.manifest.get("geometry_profile"),
            "coordinate_convention": boundary.manifest.get("coordinate_convention") or {},
            "scale_authority": boundary.manifest.get("scale_authority") or {},
            "identity_chain": boundary.manifest.get("identity_chain") or {},
            "source_status": boundary.manifest.get("status") or {},
        }
        _write_json(root / "run_metadata.json", run_metadata)

        optional_manifest: dict[str, str] = {}
        optional_names = {
            "point_cloud": "point_cloud.ply",
            "geometry_health": "geometry_health.json",
            "primary_mesh_payload": "primary_mesh_payload.json",
            "official_outputs_contract": "official_outputs_contract.json",
            "output_index": "output_index.json",
        }
        for key, source in boundary.optional.items():
            name = optional_names[key]
            shutil.copy2(source, root / name)
            optional_manifest[key] = name

        paths = {
            "source_image": root / "source_image.png",
            "camera": root / "camera.json",
            "primary_mesh": root / "primary_mesh.npz",
            "run_metadata": root / "run_metadata.json",
            **{key: root / rel for key, rel in optional_manifest.items()},
        }
        file_hashes = {key: sha256_file(path) for key, path in paths.items()}
        manifest = {
            "contract_version": CONTRACT_VERSION,
            "source_stage": boundary.source_stage,
            "source_equivalent_to": "baseline",
            "source_run_id": boundary.run_id,
            "scene_contract_id": boundary.scene_contract_id,
            "source_branch_mode": boundary.branch_mode,
            "source_manifest_schema": boundary.manifest.get("schema"),
            "identity_status": "PASS",
            "source_image": "source_image.png",
            "camera": "camera.json",
            "primary_mesh": "primary_mesh.npz",
            "run_metadata": "run_metadata.json",
            "optional": optional_manifest,
            "file_sha256": file_hashes,
        }
        _write_json(root / "manifest.json", manifest)
        CompletionBundle.from_directory(root)

        temporary_zip = output.with_name(f".{output.name}.tmp")
        temporary_zip.unlink(missing_ok=True)
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(root.iterdir(), key=lambda item: item.name):
                if path.is_file():
                    archive.write(path, arcname=path.name)
        temporary_zip.replace(output)

    return BundleBuildResult(
        zip_path=output,
        source_run_id=boundary.run_id,
        scene_contract_id=boundary.scene_contract_id,
        source_stage=boundary.source_stage,
        bundle_sha256=sha256_file(output),
    )


def _safe_zip_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename
    if "\\" in name:
        raise ContractError(f"Completion Bundle contains non-portable zip path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"Completion Bundle contains unsafe zip path: {name!r}")
    unix_mode = (info.external_attr >> 16) & 0o170000
    if unix_mode == 0o120000:
        raise ContractError(f"Completion Bundle cannot contain symlinks: {name!r}")
    return path


def load_completion_bundle(
    bundle_path: str | Path,
    *,
    extract_root: str | Path | None = None,
) -> CompletionBundle:
    path = Path(bundle_path).resolve()
    if path.is_dir():
        return CompletionBundle.from_directory(path)
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ContractError(f"Completion Bundle must be a directory or .zip: {path}")

    cache_root = Path(extract_root).resolve() if extract_root is not None else path.parent / ".p10_bundle_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / f"bundle_{sha256_file(path)[:16]}"
    if target.is_dir():
        try:
            return CompletionBundle.from_directory(target)
        except ContractError:
            shutil.rmtree(target, ignore_errors=True)

    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if not infos:
            raise ContractError("Completion Bundle zip is empty")
        total = sum(info.file_size for info in infos)
        if total > _MAX_UNCOMPRESSED_BYTES:
            raise ContractError("Completion Bundle exceeds safe extraction budget")
        members = [(info, _safe_zip_member(info)) for info in infos]
        with tempfile.TemporaryDirectory(prefix=".extract-", dir=cache_root) as temp_dir:
            temp = Path(temp_dir)
            for info, relative in members:
                destination = temp.joinpath(*relative.parts)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, destination.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
            CompletionBundle.from_directory(temp)
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            temp.rename(target)
            return CompletionBundle.from_directory(target)


def _normalized_scale_authority(manifest: dict[str, Any]) -> dict[str, Any]:
    scale = manifest.get("scale_authority") or {}
    if not isinstance(scale, dict):
        return {}
    return {
        key: scale.get(key)
        for key in (
            "authority",
            "global_scale_factor",
            "known_distance_m",
            "manual_metric_contract_id",
            "p10_scale_override_allowed",
        )
    }


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def compare_baseline_p9_identity(
    baseline_run: str | Path,
    p9_run: str | Path,
) -> IdentityComparison:
    baseline = validate_official_run(baseline_run)
    refined = validate_official_run(p9_run)
    if baseline.source_stage != "baseline":
        raise ContractError("First identity input must be a Baseline / P9 run")
    if refined.source_stage != "p9":
        raise ContractError("Second identity input must be a Refined / P9 Clone run")

    checks = {
        "scene_contract_id": (baseline.scene_contract_id, refined.scene_contract_id),
        "source_image": (sha256_file(baseline.source_image), sha256_file(refined.source_image)),
        "camera": (
            _canonical_json_digest(_read_json(baseline.camera, "baseline camera")),
            _canonical_json_digest(_read_json(refined.camera, "P9 camera")),
        ),
        "primary_mesh": (sha256_file(baseline.primary_mesh), sha256_file(refined.primary_mesh)),
        "geometry_profile": (
            baseline.manifest.get("geometry_profile"),
            refined.manifest.get("geometry_profile"),
        ),
        "coordinate_convention": (
            _canonical_json_digest(baseline.manifest.get("coordinate_convention") or {}),
            _canonical_json_digest(refined.manifest.get("coordinate_convention") or {}),
        ),
        "scale_authority": (
            _canonical_json_digest(_normalized_scale_authority(baseline.manifest)),
            _canonical_json_digest(_normalized_scale_authority(refined.manifest)),
        ),
    }
    mismatches = tuple(key for key, pair in checks.items() if pair[0] != pair[1])
    return IdentityComparison(
        passed=not mismatches,
        mismatches=mismatches,
        baseline_run_id=baseline.run_id,
        p9_run_id=refined.run_id,
    )
