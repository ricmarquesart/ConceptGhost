from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "package"

def must(path: str) -> Path:
    p = PKG / path
    assert p.is_file(), f"missing {path}"
    return p

def main() -> int:
    required = [
        "README.md",
        "01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat",
        "02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat",
        "03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat",
        "04_OPEN_GEOMETRY_ASSIST_OUTPUTS.bat",
        "05_UNINSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat",
        "Config/geometry_assist_config.json",
        "Installer/install_geometry_assist.ps1",
        "Runtime/requirements_runtime.txt",
        "Runtime/worker/prepare_models.py",
        "Runtime/worker/geometry_assist_worker.py",
    ]
    for x in required:
        must(x)

    cfg = json.loads(must("Config/geometry_assist_config.json").read_text(encoding="utf-8"))
    assert cfg["runtime_root"].endswith("ConceptGhost-GeometryAssistDiagnostic")
    assert cfg["host_policy"]["shared_comfy_mutation"] == "FORBIDDEN"
    assert cfg["host_policy"]["shared_python_pip_install"] == "FORBIDDEN"
    assert cfg["host_policy"]["shared_model_install"] == "FORBIDDEN"
    assert cfg["host_policy"]["official_pipeline_mutation"] == "FORBIDDEN"
    assert cfg["defaults"]["strength"] <= 0.30
    assert cfg["defaults"]["control_hint_alignment"] == "EXACT_WORKING_SIZE"
    assert cfg["schema"] == "ConceptGhost.GeometryAssistDiagnostic.Config.v4"
    assert cfg["defaults"]["prompt_max_tokens"] == 77
    assert cfg["defaults"]["prompt_contract"] == "BOTH_SDXL_CLIP_TOKENIZERS"
    # Keep a large lexical safety margin. Runtime/self-test enforce the actual
    # tokenizer contract against both SDXL CLIP tokenizers.
    assert len(cfg["prompt"].split()) < 35
    assert len(cfg["negative_prompt"].split()) < 35
    assert cfg["defaults"]["controlnet_scale"] >= 0.90
    assert cfg["models"]["controlnet"]["repo_id"] == "diffusers/controlnet-canny-sdxl-1.0-small"
    assert cfg["models"]["ip_adapter"]["repo_id"] == "h94/IP-Adapter"
    assert cfg["models"]["ip_adapter"]["weight_name"] == "ip-adapter_sdxl_vit-h.safetensors"
    assert cfg["models"]["ip_adapter"]["image_encoder_folder"] == "models/image_encoder"
    assert cfg["models"]["ip_adapter"]["image_encoder_projection_dim"] == 1024
    assert cfg["models"]["ip_adapter"]["pairing_contract"] == "SDXL_VIT_H_1024"

    installer = must("Installer/install_geometry_assist.ps1").read_text(encoding="utf-8")
    assert "ConceptGhost-GeometryAssistDiagnostic" in installer
    assert "ComfyUI\\custom_nodes" not in installer
    assert "ConceptGhost-MoGeRuntime-v1" in installer
    assert "ConceptGhost-LotusDiagnostic" in installer
    assert "pip install" in installer
    assert "$PythonExe -m pip install" in installer
    assert "25GB" in installer

    worker = must("Runtime/worker/geometry_assist_worker.py").read_text(encoding="utf-8")
    for marker in [
        "StableDiffusionXLControlNetImg2ImgPipeline",
        "ControlNetModel",
        "load_ip_adapter",
        "detect_resolution=control_resolution",
        "image_resolution=control_resolution",
        "height=work.height",
        "width=work.width",
        "Control hint alignment failed",
        "Prompt contract exceeded CLIP context",
        "validate_prompt_contract",
        "CLIPTokenizer",
        "tokenizer_2",
        "prompt_tokenizers",
        "IP-Adapter pairing",
        "image_encoder_projection_dim",
        "CannyDetector",
        "02_geometry_assist_proxy.png",
        "03_side_by_side.png",
        "04_difference_overlay.png",
        "05_edge_comparison.png",
        "DIAGNOSTIC_ONLY",
        "official_pipeline_impact",
    ]:
        assert marker in worker, marker

    readme = must("README.md").read_text(encoding="utf-8")
    assert "official P9/P10 pipeline" in readme
    assert "never connects the proxy to P9 automatically" in readme

    print("Geometry Assist isolated static contract: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
