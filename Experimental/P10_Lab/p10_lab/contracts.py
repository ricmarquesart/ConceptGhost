from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any
import json
import re


CONTRACT_VERSION = "p10-p9-baseline-equivalent/0.3"
REQUIRED_KEYS = {
    "contract_version",
    "source_stage",
    "source_equivalent_to",
    "source_run_id",
    "scene_contract_id",
    "source_branch_mode",
    "source_manifest_schema",
    "identity_status",
    "source_image",
    "camera",
    "primary_mesh",
    "run_metadata",
    "file_sha256",
}
ACCEPTED_SOURCE_STAGES = {"p9", "baseline"}
EXPECTED_BRANCH_MODE = {
    "baseline": "Baseline / P9",
    "p9": "Refined / P9 Clone",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    pass


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object: {path}")
    return value


@dataclass(frozen=True)
class CompletionBundle:
    root: Path
    source_stage: str
    source_equivalent_to: str
    source_run_id: str
    scene_contract_id: str
    source_branch_mode: str
    source_manifest_schema: str
    source_image: Path
    camera: Path
    primary_mesh: Path
    run_metadata: Path
    file_sha256: dict[str, str]
    optional: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, root: str | Path) -> "CompletionBundle":
        root = Path(root).resolve()
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise ContractError(f"Missing manifest: {manifest_path}")

        data = _read_json_object(manifest_path, "completion manifest")
        missing = sorted(REQUIRED_KEYS - data.keys())
        if missing:
            raise ContractError(f"Manifest missing keys: {missing}")
        if data["contract_version"] != CONTRACT_VERSION:
            raise ContractError(
                f"Unsupported contract_version={data['contract_version']!r}; "
                f"expected {CONTRACT_VERSION!r}"
            )

        source_stage = str(data["source_stage"])
        if source_stage not in ACCEPTED_SOURCE_STAGES:
            raise ContractError(
                f"Unsupported source_stage={source_stage!r}; "
                f"expected one of {sorted(ACCEPTED_SOURCE_STAGES)!r}"
            )
        if data["source_equivalent_to"] != "baseline":
            raise ContractError(
                "P10-Lab requires source_equivalent_to='baseline'; "
                "P9 must remain Baseline-equivalent before P10 starts"
            )
        expected_branch = EXPECTED_BRANCH_MODE[source_stage]
        if data["source_branch_mode"] != expected_branch:
            raise ContractError(
                f"source_stage={source_stage!r} requires source_branch_mode={expected_branch!r}"
            )
        if data["identity_status"] != "PASS":
            raise ContractError("Completion bundle identity_status must be PASS")

        scene_contract_id = str(data["scene_contract_id"] or "").strip()
        source_run_id = str(data["source_run_id"] or "").strip()
        source_manifest_schema = str(data["source_manifest_schema"] or "").strip()
        if not scene_contract_id or not source_run_id or not source_manifest_schema:
            raise ContractError("Completion bundle identity fields must be nonempty")

        hashes = data["file_sha256"]
        if not isinstance(hashes, dict):
            raise ContractError("file_sha256 must be an object")
        normalized_hashes: dict[str, str] = {}
        for key, value in hashes.items():
            if not isinstance(key, str) or not _SHA256_PATTERN.fullmatch(str(value)):
                raise ContractError(f"Invalid SHA-256 entry for {key!r}")
            normalized_hashes[key] = str(value)

        def resolve_file(key: str, rel: object) -> Path:
            if not isinstance(rel, str) or not rel.strip():
                raise ContractError(f"Invalid path for {key}")
            path = (root / rel).resolve()
            if not path.is_file():
                raise ContractError(f"Missing required file for {key}: {path}")
            if root not in path.parents:
                raise ContractError(f"Path escapes bundle root: {path}")
            expected_digest = normalized_hashes.get(key)
            if expected_digest is None:
                raise ContractError(f"Missing SHA-256 for {key}")
            actual_digest = _hash_file(path)
            if actual_digest != expected_digest:
                raise ContractError(
                    f"SHA-256 mismatch for {key}: expected {expected_digest}, got {actual_digest}"
                )
            return path

        source_image = resolve_file("source_image", data["source_image"])
        camera = resolve_file("camera", data["camera"])
        primary_mesh = resolve_file("primary_mesh", data["primary_mesh"])
        run_metadata = resolve_file("run_metadata", data["run_metadata"])
        if primary_mesh.suffix.lower() not in {".npz", ".ply", ".obj"}:
            raise ContractError(f"Unsupported primary mesh format: {primary_mesh.suffix}")

        optional: dict[str, Path] = {}
        for key, rel in (data.get("optional") or {}).items():
            path = resolve_file(str(key), rel)
            optional[str(key)] = path

        camera_data = _read_json_object(camera, "camera")
        if camera_data.get("valid") is not True:
            raise ContractError("Completion bundle camera must be valid")
        if str(camera_data.get("scene_contract_id") or "") != scene_contract_id:
            raise ContractError("Camera scene_contract_id does not match completion manifest")
        if int(camera_data.get("image_width") or 0) <= 0 or int(camera_data.get("image_height") or 0) <= 0:
            raise ContractError("Camera image dimensions must be positive")
        if not isinstance(camera_data.get("intrinsics"), dict) or not isinstance(camera_data.get("extrinsics"), dict):
            raise ContractError("Camera intrinsics/extrinsics are required")

        metadata = _read_json_object(run_metadata, "run metadata")
        expected_metadata = {
            "source_stage": source_stage,
            "source_equivalent_to": "baseline",
            "source_run_id": source_run_id,
            "scene_contract_id": scene_contract_id,
            "source_branch_mode": str(data["source_branch_mode"]),
        }
        for key, expected in expected_metadata.items():
            if metadata.get(key) != expected:
                raise ContractError(f"run_metadata {key} mismatch: {metadata.get(key)!r} != {expected!r}")

        return cls(
            root=root,
            source_stage=source_stage,
            source_equivalent_to="baseline",
            source_run_id=source_run_id,
            scene_contract_id=scene_contract_id,
            source_branch_mode=str(data["source_branch_mode"]),
            source_manifest_schema=source_manifest_schema,
            source_image=source_image,
            camera=camera,
            primary_mesh=primary_mesh,
            run_metadata=run_metadata,
            file_sha256=normalized_hashes,
            optional=optional,
        )


@dataclass(frozen=True)
class SceneScale:
    radius: float
    units: str = "scene"

    def __post_init__(self) -> None:
        if (
            isinstance(self.radius, bool)
            or not isinstance(self.radius, (int, float))
            or not isfinite(self.radius)
            or self.radius <= 0
        ):
            raise ContractError("Scene radius must be finite and positive")
