from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "package"
CFG = PKG / "Config" / "geometry_assist_config.json"
PREP = PKG / "Runtime" / "worker" / "prepare_models.py"
WORKER = PKG / "Runtime" / "worker" / "geometry_assist_worker.py"


def main() -> int:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    adapter = cfg["models"]["ip_adapter"]

    assert adapter["repo_id"] == "h94/IP-Adapter"
    assert adapter["subfolder"] == "sdxl_models"
    assert adapter["weight_name"] == "ip-adapter_sdxl_vit-h.safetensors"
    assert adapter["image_encoder_folder"] == "models/image_encoder"
    assert adapter["image_encoder_family"] == "OpenCLIP-ViT-H-14"
    assert adapter["image_encoder_projection_dim"] == 1024
    assert adapter["pairing_contract"] == "SDXL_VIT_H_1024"

    prep = PREP.read_text(encoding="utf-8")
    assert "sdxl_models/ip-adapter_sdxl_vit-h.safetensors" in prep
    assert "sdxl_models/ip-adapter_sdxl.bin" not in prep

    worker = WORKER.read_text(encoding="utf-8")
    assert "ip-adapter_sdxl_vit-h.safetensors" in worker
    assert "IP-Adapter image encoder projection mismatch" in worker
    assert "IP-Adapter runtime projection mismatch" in worker
    assert "SDXL_VIT_H_1024" in worker

    print("Geometry Assist IP-Adapter pairing regression: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
