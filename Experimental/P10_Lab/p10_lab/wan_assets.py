from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WanAsset:
    key: str
    relative_path: str
    repo_id: str
    repo_filename: str
    sha256: str
    approx_gb: float


WAN_GATE5_ASSETS = (
    WanAsset(
        key="i2v_unet",
        relative_path="diffusion_models/wan/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
        repo_id="Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        repo_filename="split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
        sha256="b2051cd29d6b2f0c924fa7a3e78a4772f0134d7b059f21590dcce416f4f6cbe8",
        approx_gb=16.4,
    ),
    WanAsset(
        key="text_encoder",
        relative_path="text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        repo_id="Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        repo_filename="split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        sha256="c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68",
        approx_gb=6.74,
    ),
    WanAsset(
        key="vae",
        relative_path="vae/wan_2.1_vae.safetensors",
        repo_id="Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        repo_filename="split_files/vae/wan_2.1_vae.safetensors",
        sha256="2fc39d31359a4b0a64f55876d8ff7fa8d780956ae2cb13463b0223e15148976b",
        approx_gb=0.254,
    ),
    WanAsset(
        key="lightx2v_lora",
        relative_path="loras/wan/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors",
        repo_id="Kijai/WanVideo_comfy",
        repo_filename="Lightx2v/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors",
        sha256="37d49218544b9e0bfb8e831d1399f451fbc5068aff6474f42a90c928363c3573",
        approx_gb=0.631,
    ),
)


def manifest() -> dict[str, object]:
    return {
        "schema": "ConceptGhost.P10WanAssets.v0.1",
        "asset_count": len(WAN_GATE5_ASSETS),
        "approx_total_gb": sum(asset.approx_gb for asset in WAN_GATE5_ASSETS),
        "assets": [
            {
                "key": asset.key,
                "relative_path": asset.relative_path,
                "repo_id": asset.repo_id,
                "repo_filename": asset.repo_filename,
                "sha256": asset.sha256,
                "approx_gb": asset.approx_gb,
            }
            for asset in WAN_GATE5_ASSETS
        ],
    }
