from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconstructionAsset:
    key: str
    version: str
    archive_name: str
    download_url: str
    sha256: str
    archive_bytes: int
    estimated_installed_gb: float
    cuda_required: bool


COLMAP_WINDOWS_CUDA = ReconstructionAsset(
    key="colmap_windows_cuda",
    version="4.2.0",
    archive_name="colmap-x64-windows-cuda.zip",
    download_url="https://github.com/colmap/colmap/releases/download/4.2.0/colmap-x64-windows-cuda.zip",
    sha256="991e0bae403a496fcc4de0c1f1f428619bf12f8000978f77bc6799d9bfeac23e",
    archive_bytes=380_970_811,
    estimated_installed_gb=1.3,
    cuda_required=True,
)


def manifest() -> dict[str, object]:
    asset=COLMAP_WINDOWS_CUDA
    return {
        "schema":"ConceptGhost.P10ReconstructionAssets.v0.1",
        "colmap":{
            "key":asset.key,
            "version":asset.version,
            "archive_name":asset.archive_name,
            "download_url":asset.download_url,
            "sha256":asset.sha256,
            "archive_bytes":asset.archive_bytes,
            "archive_gb_decimal":asset.archive_bytes/1_000_000_000.0,
            "estimated_installed_gb":asset.estimated_installed_gb,
            "cuda_required":asset.cuda_required,
            "install_scope":"LOCALAPPDATA_CONCEPTGHOST_THIRDPARTY",
        },
        "spheresfm":{
            "required_for_primary_path":False,
            "role":"OPTIONAL_ERP_VALIDATION_OR_FALLBACK",
            "download_in_gate6":False,
        },
        "splatkit":{
            "required_for_primary_path":False,
            "role":"REFERENCE_AND_OPTIONAL_LATER_REFINEMENT",
            "download_in_gate6":False,
        },
    }
