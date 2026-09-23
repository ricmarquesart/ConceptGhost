from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download

BASE_PATTERNS = [
    "model_index.json",
    "scheduler/*",
    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",
    "text_encoder_2/config.json",
    "text_encoder_2/model.fp16.safetensors",
    "tokenizer/*",
    "tokenizer_2/*",
    "unet/config.json",
    "unet/diffusion_pytorch_model.fp16.safetensors",
    "vae/config.json",
    "vae/diffusion_pytorch_model.fp16.safetensors",
    "feature_extractor/*",
]
CONTROL_PATTERNS = [
    "config.json",
    "diffusion_pytorch_model.fp16.safetensors",
]
IP_PATTERNS = [
    "sdxl_models/ip-adapter_sdxl_vit-h.safetensors",
    "models/image_encoder/config.json",
    "models/image_encoder/model.safetensors",
]

def download(repo_id: str, target: Path, cache: Path, patterns: list[str]) -> str:
    target.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        repo_id=repo_id,
        local_dir=str(target),
        cache_dir=str(cache),
        allow_patterns=patterns,
        resume_download=True,
    )
    try:
        path = snapshot_download(local_dir_use_symlinks=False, **kwargs)
    except TypeError:
        path = snapshot_download(**kwargs)
    return str(path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    args = ap.parse_args()
    root = Path(args.runtime_root)
    cfg = json.loads((root / "Manifests" / "geometry_assist_config.json").read_text(encoding="utf-8"))
    cache = root / "Cache" / "huggingface"
    models = root / "Models"
    cache.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(cache)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache / "hub")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    records = {}
    records["base"] = download(cfg["models"]["base"]["repo_id"], models / "sdxl_base", cache, BASE_PATTERNS)
    records["controlnet"] = download(cfg["models"]["controlnet"]["repo_id"], models / "controlnet_canny_sdxl_small", cache, CONTROL_PATTERNS)
    records["ip_adapter"] = download(cfg["models"]["ip_adapter"]["repo_id"], models / "ip_adapter", cache, IP_PATTERNS)

    required = [
        models / "sdxl_base" / "model_index.json",
        models / "sdxl_base" / "unet" / "diffusion_pytorch_model.fp16.safetensors",
        models / "controlnet_canny_sdxl_small" / "config.json",
        models / "controlnet_canny_sdxl_small" / "diffusion_pytorch_model.fp16.safetensors",
        models / "ip_adapter" / "sdxl_models" / "ip-adapter_sdxl_vit-h.safetensors",
        models / "ip_adapter" / "models" / "image_encoder" / "config.json",
        models / "ip_adapter" / "models" / "image_encoder" / "model.safetensors",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("Model materialization incomplete:\n" + "\n".join(missing))

    out = {
        "schema": "ConceptGhost.GeometryAssistDiagnostic.Models.v1",
        "models": cfg["models"],
        "materialized": records,
        "required_files_present": True,
    }
    (root / "Manifests" / "model_manifest.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
