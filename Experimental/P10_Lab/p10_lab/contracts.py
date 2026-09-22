from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any
import json


CONTRACT_VERSION = "p10-p9-baseline-equivalent/0.2"
REQUIRED_KEYS = {
    "contract_version",
    "source_stage",
    "source_equivalent_to",
    "source_run_id",
    "source_image",
    "camera",
    "primary_mesh",
    "run_metadata",
}
ACCEPTED_SOURCE_STAGES = {"p9", "baseline"}


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class CompletionBundle:
    root: Path
    source_stage: str
    source_run_id: str
    source_image: Path
    camera: Path
    primary_mesh: Path
    run_metadata: Path
    optional: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, root: str | Path) -> "CompletionBundle":
        root = Path(root).resolve()
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise ContractError(f"Missing manifest: {manifest_path}")

        data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
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

        def required_file(key: str) -> Path:
            path = (root / data[key]).resolve()
            if not path.is_file():
                raise ContractError(f"Missing required file for {key}: {path}")
            if root not in path.parents:
                raise ContractError(f"Path escapes bundle root: {path}")
            return path

        optional: dict[str, Path] = {}
        for key, rel in (data.get("optional") or {}).items():
            path = (root / rel).resolve()
            if path.is_file() and root in path.parents:
                optional[key] = path

        return cls(
            root=root,
            source_stage=source_stage,
            source_run_id=str(data["source_run_id"]),
            source_image=required_file("source_image"),
            camera=required_file("camera"),
            primary_mesh=required_file("primary_mesh"),
            run_metadata=required_file("run_metadata"),
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
