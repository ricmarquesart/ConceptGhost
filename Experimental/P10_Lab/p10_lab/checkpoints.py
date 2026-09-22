from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Mapping

from .contracts import ContractError
from .pipeline import Stage


class PreviewRole(str, Enum):
    CONTROL_VIDEO = "control_video"
    HOLE_MASK_VIDEO = "hole_mask_video"
    WAN_FILLED_VIDEO = "wan_filled_video"
    SOURCE_COMPOSITE_VIDEO = "source_composite_video"


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FLIGHT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_WINDOWS_FORBIDDEN_PATH_CHARS = frozenset('<>:"\\|?*')


_REQUIRED_STAGE_PREVIEWS = (
    (Stage.CONTROL_RENDER, PreviewRole.CONTROL_VIDEO),
    (Stage.DISOCCLUSION_MASK, PreviewRole.HOLE_MASK_VIDEO),
    (Stage.WAN_COMPLETION, PreviewRole.WAN_FILLED_VIDEO),
    (Stage.SOURCE_COMPOSITE, PreviewRole.SOURCE_COMPOSITE_VIDEO),
)


def required_preview_roles() -> tuple[PreviewRole, ...]:
    return tuple(role for _, role in _REQUIRED_STAGE_PREVIEWS)


def _file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_flight_id(value: object) -> str:
    if type(value) is not str or not _FLIGHT_ID_PATTERN.fullmatch(value):
        raise ContractError(
            "flight_id must contain only portable letters, digits, underscores, "
            "or hyphens and must start with a letter or digit"
        )
    if value.upper() in _WINDOWS_RESERVED_NAMES:
        raise ContractError(f"flight_id is reserved on Windows: {value!r}")
    return value


def _validate_sha256(value: object, field_name: str) -> str:
    if type(value) is not str or not _SHA256_PATTERN.fullmatch(value):
        raise ContractError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return value


def _require_nonempty_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError(f"{field_name} must be a nonempty string")
    return value


def _validate_relative_artifact_path(value: object) -> str:
    path = _require_nonempty_string(value, "relative_path")
    if "\\" in path:
        raise ContractError("relative_path must use portable forward slashes")
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ContractError("relative_path must stay inside the checkpoint root")
    for part in pure_path.parts:
        if (
            any(ord(character) < 32 for character in part)
            or any(character in _WINDOWS_FORBIDDEN_PATH_CHARS for character in part)
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES
        ):
            raise ContractError("relative_path contains a non-portable path component")
    return pure_path.as_posix()


def checkpoint_context_digest(
    *,
    source_run_id: str,
    source_inputs: Mapping[str, Any],
    flight_definition: Mapping[str, Any],
    control_policy: Mapping[str, Any],
    adapter_versions: Mapping[str, Any],
) -> str:
    payload = {
        "source_run_id": _require_nonempty_string(source_run_id, "source_run_id"),
        "source_inputs": dict(source_inputs),
        "flight_definition": dict(flight_definition),
        "control_policy": dict(control_policy),
        "adapter_versions": dict(adapter_versions),
    }
    try:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ContractError(f"Checkpoint context must be canonical JSON: {error}") from error
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PreviewArtifact:
    role: PreviewRole
    relative_path: str
    media_type: str
    sha256: str
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, PreviewRole):
            raise ContractError("Preview artifact role is invalid")
        object.__setattr__(
            self,
            "relative_path",
            _validate_relative_artifact_path(self.relative_path),
        )
        _require_nonempty_string(self.media_type, "media_type")
        _validate_sha256(self.sha256, "artifact sha256")
        _require_nonempty_string(self.provenance, "provenance")

    @classmethod
    def from_file(
        cls,
        *,
        root: str | Path,
        role: PreviewRole,
        path: str | Path,
        media_type: str,
        provenance: str,
    ) -> "PreviewArtifact":
        root_path = Path(root).resolve()
        artifact_path = Path(path).resolve()
        if not artifact_path.is_file():
            raise ContractError(f"Preview artifact does not exist: {artifact_path}")
        if root_path not in artifact_path.parents:
            raise ContractError(f"Preview path escapes checkpoint root: {artifact_path}")
        if not media_type:
            raise ContractError("Preview media_type is required")
        if not provenance:
            raise ContractError("Preview provenance is required")
        return cls(
            role=role,
            relative_path=artifact_path.relative_to(root_path).as_posix(),
            media_type=media_type,
            sha256=_file_digest(artifact_path),
            provenance=provenance,
        )

    def matches(self, root: str | Path) -> bool:
        try:
            root_path = Path(root).resolve()
            artifact_path = (root_path / self.relative_path).resolve()
            if root_path not in artifact_path.parents or not artifact_path.is_file():
                return False
            return _file_digest(artifact_path) == self.sha256
        except (OSError, RuntimeError, ValueError):
            return False

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role.value,
            "relative_path": self.relative_path,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreviewArtifact":
        try:
            if type(data) is not dict:
                raise ContractError("Preview artifact must be an object")
            if type(data.get("role")) is not str:
                raise ContractError("Preview artifact role must be a string")
            return cls(
                role=PreviewRole(data["role"]),
                relative_path=data["relative_path"],
                media_type=data["media_type"],
                sha256=data["sha256"],
                provenance=data["provenance"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError(f"Invalid preview artifact manifest: {error}") from error


@dataclass(frozen=True)
class VisualCheckpoint:
    stage: Stage
    flight_id: str
    artifacts: tuple[PreviewArtifact, ...]
    validated: bool
    context_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, Stage):
            raise ContractError("Checkpoint stage is invalid")
        _validate_flight_id(self.flight_id)
        if type(self.validated) is not bool:
            raise ContractError("Checkpoint validated must be a boolean")
        _validate_sha256(self.context_digest, "context_digest")
        if not self.artifacts:
            raise ContractError("Checkpoint must contain at least one artifact")
        expected_prefix = ("flights", self.flight_id)
        for artifact in self.artifacts:
            if not isinstance(artifact, PreviewArtifact):
                raise ContractError("Checkpoint artifacts must be PreviewArtifact values")
            if PurePosixPath(artifact.relative_path).parts[:2] != expected_prefix:
                raise ContractError(
                    "Checkpoint artifact must belong to its declared flight directory"
                )
        expected = dict(_REQUIRED_STAGE_PREVIEWS).get(self.stage)
        roles = {artifact.role for artifact in self.artifacts}
        if expected is not None and expected not in roles:
            raise ContractError(
                f"Checkpoint stage {self.stage.value!r} requires preview role "
                f"{expected.value!r}"
            )

    def can_resume(self, root: str | Path, expected_context_digest: str) -> bool:
        try:
            expected = _validate_sha256(expected_context_digest, "expected_context_digest")
        except ContractError:
            return False
        return (
            self.validated
            and self.context_digest == expected
            and all(artifact.matches(root) for artifact in self.artifacts)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_version": 1,
            "stage": self.stage.value,
            "flight_id": self.flight_id,
            "validated": self.validated,
            "context_digest": self.context_digest,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualCheckpoint":
        try:
            if type(data) is not dict:
                raise ContractError("Checkpoint manifest root must be an object")
            if type(data.get("checkpoint_version")) is not int or data["checkpoint_version"] != 1:
                raise ContractError(
                    f"Unsupported checkpoint_version={data.get('checkpoint_version')!r}"
                )
            if type(data.get("stage")) is not str:
                raise ContractError("Checkpoint stage must be a string")
            if type(data.get("flight_id")) is not str:
                raise ContractError("Checkpoint flight_id must be a string")
            if type(data.get("validated")) is not bool:
                raise ContractError("Checkpoint validated must be a boolean")
            if type(data.get("context_digest")) is not str:
                raise ContractError("Checkpoint context_digest must be a string")
            if type(data.get("artifacts")) is not list:
                raise ContractError("Checkpoint artifacts must be an array")
            return cls(
                stage=Stage(data["stage"]),
                flight_id=data["flight_id"],
                artifacts=tuple(
                    PreviewArtifact.from_dict(item) for item in data["artifacts"]
                ),
                validated=data["validated"],
                context_digest=data["context_digest"],
            )
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError(f"Invalid checkpoint manifest: {error}") from error


def write_checkpoint_manifest(
    root: str | Path,
    checkpoint: VisualCheckpoint,
) -> Path:
    root_path = Path(root).resolve()
    flights_root = root_path / "flights"
    manifest_dir = flights_root / checkpoint.flight_id
    try:
        root_path.mkdir(parents=True, exist_ok=True)
        for directory in (flights_root, manifest_dir):
            is_junction = getattr(directory, "is_junction", lambda: False)
            if directory.is_symlink() or is_junction():
                raise ContractError(
                    f"Checkpoint directory cannot be a link or junction: {directory}"
                )
            directory.mkdir(exist_ok=True)
            resolved_directory = directory.resolve(strict=True)
            if root_path not in resolved_directory.parents:
                raise ContractError(
                    f"Checkpoint directory escapes checkpoint root: {directory}"
                )
    except ContractError:
        raise
    except (OSError, RuntimeError) as error:
        raise ContractError(f"Cannot create checkpoint directory: {error}") from error

    manifest_path = manifest_dir / f"{checkpoint.stage.value}.checkpoint.json"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=manifest_dir,
            prefix=f".{checkpoint.stage.value}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(json.dumps(checkpoint.to_dict(), indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, manifest_path)
    except (OSError, RuntimeError, ValueError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise ContractError(f"Cannot write checkpoint manifest: {error}") from error
    return manifest_path


def load_checkpoint_manifest(path: str | Path) -> VisualCheckpoint:
    manifest_path = Path(path)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read checkpoint manifest {manifest_path}: {error}") from error
    if not isinstance(data, dict):
        raise ContractError("Checkpoint manifest root must be an object")
    return VisualCheckpoint.from_dict(data)
