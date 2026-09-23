from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import ContractError


@dataclass(frozen=True)
class DualMayaDeliverables:
    p9_maya: Path
    p10_refined_maya: Path

    def to_dict(self) -> dict[str,str]:
        return {
            "p9_maya":str(self.p9_maya),
            "p10_refined_maya":str(self.p10_refined_maya),
            "overwrite_policy":"P9_IMMUTABLE_P10_SEPARATE",
        }


def validate_dual_maya_targets(
    p9_maya: str | Path,
    p10_refined_maya: str | Path,
) -> DualMayaDeliverables:
    p9=Path(p9_maya).expanduser().resolve()
    p10=Path(p10_refined_maya).expanduser().resolve()
    if p9.suffix.lower()!=".ma" or p10.suffix.lower()!=".ma":
        raise ContractError("Both Maya deliverables must use .ma")
    if p9==p10:
        raise ContractError("P10 Refined Maya must never overwrite the P9 Maya file")
    return DualMayaDeliverables(p9_maya=p9,p10_refined_maya=p10)


def derive_p10_refined_maya_target(
    p9_maya: str | Path,
    *,
    output_dir: str | Path | None=None,
) -> Path:
    p9=Path(p9_maya).expanduser().resolve()
    if p9.suffix.lower()!=".ma":
        raise ContractError("P9 Maya source must use .ma")
    parent=Path(output_dir).expanduser().resolve() if output_dir is not None else p9.parent
    stem=p9.stem
    if stem.endswith("_P9"):
        stem=stem[:-3]
    target=parent/f"{stem}_P10_Refined.ma"
    return validate_dual_maya_targets(p9,target).p10_refined_maya
