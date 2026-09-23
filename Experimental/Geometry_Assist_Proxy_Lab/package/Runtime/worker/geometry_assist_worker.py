from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def validate_prompt_contract(tokenizers, prompt: str, negative_prompt: str, configured_max: int) -> dict:
    details = {}
    failures = []
    for name, tokenizer in tokenizers:
        if tokenizer is None:
            failures.append(f"{name}=MISSING")
            continue
        tokenizer_limit = int(getattr(tokenizer, "model_max_length", configured_max))
        effective_max = min(int(configured_max), tokenizer_limit)
        prompt_tokens = len(tokenizer(prompt, truncation=False, add_special_tokens=True)["input_ids"])
        negative_tokens = len(tokenizer(negative_prompt, truncation=False, add_special_tokens=True)["input_ids"])
        details[name] = {
            "prompt_tokens": prompt_tokens,
            "negative_prompt_tokens": negative_tokens,
            "max_tokens": effective_max,
        }
        if prompt_tokens > effective_max or negative_tokens > effective_max:
            failures.append(
                f"{name}: prompt={prompt_tokens}, negative={negative_tokens}, max={effective_max}"
            )
    if failures:
        raise RuntimeError("Prompt contract exceeded CLIP context: " + "; ".join(failures))
    return details

def set_private_env(root: Path) -> None:
    cache = root / "Cache"
    temp = root / "Temp"
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["HF_HOME"] = str(cache / "huggingface")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache / "huggingface" / "hub")
    os.environ["TORCH_HOME"] = str(cache / "torch")
    os.environ["XDG_CACHE_HOME"] = str(cache)
    os.environ["TEMP"] = str(temp)
    os.environ["TMP"] = str(temp)
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

def self_test(root: Path) -> int:
    set_private_env(root)
    import torch
    import diffusers
    import transformers
    import accelerate
    import cv2
    import controlnet_aux
    from PIL import Image
    import skimage

    required = [
        root / "Models" / "sdxl_base" / "model_index.json",
        root / "Models" / "sdxl_base" / "unet" / "diffusion_pytorch_model.fp16.safetensors",
        root / "Models" / "controlnet_canny_sdxl_small" / "config.json",
        root / "Models" / "controlnet_canny_sdxl_small" / "diffusion_pytorch_model.fp16.safetensors",
        root / "Models" / "ip_adapter" / "sdxl_models" / "ip-adapter_sdxl.bin",
        root / "Models" / "ip_adapter" / "models" / "image_encoder" / "model.safetensors",
        root / "Models" / "sdxl_base" / "tokenizer" / "tokenizer_config.json",
        root / "Models" / "sdxl_base" / "tokenizer_2" / "tokenizer_config.json",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    payload = {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if torch.cuda.is_available() else None,
        "diffusers": diffusers.__version__,
        "transformers": transformers.__version__,
        "accelerate": accelerate.__version__,
        "controlnet_aux": getattr(controlnet_aux, "__version__", "import-ok"),
        "opencv": cv2.__version__,
        "skimage": skimage.__version__,
        "missing_model_files": missing,
        "isolated_runtime": str(root),
    }
    print(json.dumps(payload, indent=2))
    if not torch.cuda.is_available():
        print("ERROR: CUDA GPU is required for the intended diagnostic profile.")
        return 2
    if missing:
        print("ERROR: private model materialization is incomplete.")
        return 3

    try:
        from transformers import CLIPTokenizer
        cfg = load_json(root / "Manifests" / "geometry_assist_config.json")
        configured_max = int(cfg["defaults"].get("prompt_max_tokens", 77))
        tokenizer_1 = CLIPTokenizer.from_pretrained(
            str(root / "Models" / "sdxl_base" / "tokenizer"),
            local_files_only=True,
        )
        tokenizer_2 = CLIPTokenizer.from_pretrained(
            str(root / "Models" / "sdxl_base" / "tokenizer_2"),
            local_files_only=True,
        )
        prompt_contract = validate_prompt_contract(
            [("tokenizer", tokenizer_1), ("tokenizer_2", tokenizer_2)],
            cfg["prompt"],
            cfg["negative_prompt"],
            configured_max,
        )
        payload["prompt_tokenizers"] = prompt_contract
        print("Prompt contract: PASS")
        print(json.dumps(prompt_contract, indent=2))
    except Exception as exc:
        print(f"ERROR: prompt contract self-test failed: {type(exc).__name__}: {exc}")
        return 4
    return 0

def fit_work_size(w: int, h: int, max_dim: int) -> tuple[int, int]:
    # ControlNet Aux resize_image quantizes to 64-pixel blocks. Keep the img2img
    # image and control image on the same 64-aligned canvas so latent/control
    # feature maps cannot diverge.
    scale = min(1.0, float(max_dim) / float(max(w, h)))
    nw = max(64, int(round((w * scale) / 64.0)) * 64)
    nh = max(64, int(round((h * scale) / 64.0)) * 64)
    return nw, nh

def label_image(img, label: str):
    from PIL import Image, ImageDraw
    canvas = Image.new("RGB", (img.width, img.height + 34), "black")
    canvas.paste(img, (0, 34))
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), label, fill="white")
    return canvas

def make_side_by_side(a, b):
    from PIL import Image
    la = label_image(a, "ORIGINAL")
    lb = label_image(b, "GEOMETRY ASSIST PROXY")
    out = Image.new("RGB", (la.width + lb.width, max(la.height, lb.height)), "black")
    out.paste(la, (0, 0))
    out.paste(lb, (la.width, 0))
    return out

def edge_metrics(src, proxy):
    import cv2
    import numpy as np
    s = cv2.cvtColor(np.asarray(src), cv2.COLOR_RGB2GRAY)
    p = cv2.cvtColor(np.asarray(proxy), cv2.COLOR_RGB2GRAY)
    es = cv2.Canny(s, 100, 200)
    ep = cv2.Canny(p, 100, 200)
    kernel = np.ones((3, 3), np.uint8)
    esd = cv2.dilate(es, kernel, iterations=1)
    epd = cv2.dilate(ep, kernel, iterations=1)
    tp_p = int(((ep > 0) & (esd > 0)).sum())
    tp_r = int(((es > 0) & (epd > 0)).sum())
    pred = max(1, int((ep > 0).sum()))
    truth = max(1, int((es > 0).sum()))
    precision = tp_p / pred
    recall = tp_r / truth
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    vis = np.zeros((es.shape[0], es.shape[1], 3), dtype=np.uint8)
    vis[(es > 0) & (epd > 0)] = (0, 255, 0)
    vis[(es > 0) & ~(epd > 0)] = (255, 0, 0)
    vis[(ep > 0) & ~(esd > 0)] = (0, 0, 255)
    return {"precision": precision, "recall": recall, "f1": f1}, vis

def run(root: Path, input_path: Path) -> int:
    set_private_env(root)
    from PIL import Image, ImageChops, ImageEnhance
    import numpy as np
    import torch
    import cv2
    from skimage.metrics import structural_similarity
    from diffusers import ControlNetModel, StableDiffusionXLControlNetImg2ImgPipeline

    cfg = load_json(root / "Manifests" / "geometry_assist_config.json")
    d = cfg["defaults"]
    source = Image.open(input_path).convert("RGB")
    original_size = source.size
    work_size = fit_work_size(*original_size, int(d["max_dimension"]))
    work = source.resize(work_size, Image.Resampling.LANCZOS)

    run_id = utc_now()
    run_dir = root / "Outputs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "run.log"
    def log(msg: str):
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    manifest = {
        "schema": "ConceptGhost.GeometryAssistDiagnostic.Run.v1",
        "run_id": run_id,
        "authority": "DIAGNOSTIC_ONLY",
        "official_pipeline_impact": "NONE",
        "source": str(input_path),
        "original_size": list(original_size),
        "working_size": list(work_size),
        "parameters": d,
        "models": cfg["models"],
        "prompt": cfg["prompt"],
        "negative_prompt": cfg["negative_prompt"],
        "status": "STARTED",
    }
    save_json(run_dir / "manifest.json", manifest)

    source.save(run_dir / "00_original.png")

    try:
        log(f"Input: {input_path}")
        log(f"Working resolution: {work_size[0]}x{work_size[1]}")

        # ControlNet Aux Canny is preferred. OpenCV is a deterministic safety fallback.
        preprocessor = "controlnet_aux.CannyDetector"
        try:
            from controlnet_aux import CannyDetector
            detector = CannyDetector()
            control_resolution = min(work_size)
            hint = detector(
                work,
                low_threshold=int(d["canny_low"]),
                high_threshold=int(d["canny_high"]),
                detect_resolution=control_resolution,
                image_resolution=control_resolution,
                output_type="pil",
            )
            if not isinstance(hint, Image.Image):
                hint = Image.fromarray(np.asarray(hint))
            hint = hint.convert("RGB")
        except Exception as exc:
            preprocessor = f"opencv_fallback:{type(exc).__name__}"
            arr = np.asarray(work)
            edge = cv2.Canny(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY), int(d["canny_low"]), int(d["canny_high"]))
            hint = Image.fromarray(np.repeat(edge[..., None], 3, axis=2), mode="RGB")
        # Final hard alignment guard. The Diffusers ControlNet img2img pipeline
        # requires control features to align with the image latent geometry.
        if hint.size != work.size:
            log(f"Control hint resize guard: {hint.size[0]}x{hint.size[1]} -> {work.width}x{work.height}")
            hint = hint.resize(work.size, Image.Resampling.NEAREST)
        if hint.size != work.size:
            raise RuntimeError(f"Control hint alignment failed: image={work.size}, hint={hint.size}")
        hint_up = hint.resize(original_size, Image.Resampling.NEAREST)
        hint_up.save(run_dir / "01_control_hint_canny.png")
        log(f"Structural preprocessor: {preprocessor}")
        log(f"Aligned control hint: {hint.width}x{hint.height}")

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU is unavailable.")
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        models = root / "Models"
        dtype = torch.float16
        log("Loading private ControlNet...")
        controlnet = ControlNetModel.from_pretrained(
            str(models / "controlnet_canny_sdxl_small"),
            torch_dtype=dtype,
            variant="fp16",
            use_safetensors=True,
            local_files_only=True,
        )

        log("Loading private SDXL img2img + ControlNet pipeline...")
        pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
            str(models / "sdxl_base"),
            controlnet=controlnet,
            torch_dtype=dtype,
            variant="fp16",
            use_safetensors=True,
            local_files_only=True,
        )

        log("Loading private IP-Adapter...")
        pipe.load_ip_adapter(
            str(models / "ip_adapter"),
            subfolder=cfg["models"]["ip_adapter"]["subfolder"],
            weight_name=cfg["models"]["ip_adapter"]["weight_name"],
            image_encoder_folder=cfg["models"]["ip_adapter"]["image_encoder_folder"],
        )
        pipe.set_ip_adapter_scale(float(d["ip_adapter_scale"]))
        pipe.enable_vae_slicing()
        pipe.enable_vae_tiling()
        pipe.enable_model_cpu_offload()

        generator = torch.Generator(device="cpu").manual_seed(int(d["seed"]))
        start = time.perf_counter()
        max_prompt_tokens = int(d.get("prompt_max_tokens", 77))
        prompt_contract = validate_prompt_contract(
            [("tokenizer", pipe.tokenizer), ("tokenizer_2", getattr(pipe, "tokenizer_2", None))],
            cfg["prompt"],
            cfg["negative_prompt"],
            max_prompt_tokens,
        )
        for tokenizer_name, counts in prompt_contract.items():
            log(
                f"CLIP token counts [{tokenizer_name}]: "
                f"prompt={counts['prompt_tokens']}, negative={counts['negative_prompt_tokens']}, "
                f"max={counts['max_tokens']}"
            )

        log("Starting conservative proxy generation...")
        result = pipe(
            prompt=cfg["prompt"],
            negative_prompt=cfg["negative_prompt"],
            image=work,
            control_image=hint,
            ip_adapter_image=work,
            height=work.height,
            width=work.width,
            strength=float(d["strength"]),
            controlnet_conditioning_scale=float(d["controlnet_scale"]),
            num_inference_steps=int(d["steps"]),
            guidance_scale=float(d["guidance_scale"]),
            generator=generator,
        ).images[0].convert("RGB")
        elapsed = time.perf_counter() - start
        peak_vram = round(torch.cuda.max_memory_allocated() / 1024**3, 3)

        proxy = result.resize(original_size, Image.Resampling.LANCZOS)
        proxy.save(run_dir / "02_geometry_assist_proxy.png")
        proxy.save(run_dir / "02_geometry_assist_proxy.jpg", quality=int(d["jpeg_quality"]), subsampling=0)
        make_side_by_side(source, proxy).save(run_dir / "03_side_by_side.png")

        diff = ImageChops.difference(source, proxy)
        boosted = ImageEnhance.Contrast(diff).enhance(2.0)
        overlay = Image.blend(source, boosted.convert("RGB"), 0.55)
        overlay.save(run_dir / "04_difference_overlay.png")

        edge_stats, edge_vis = edge_metrics(source, proxy)
        Image.fromarray(edge_vis).save(run_dir / "05_edge_comparison.png")

        src_arr = np.asarray(source)
        proxy_arr = np.asarray(proxy)
        ssim = float(structural_similarity(src_arr, proxy_arr, channel_axis=2, data_range=255))
        mae = float(np.abs(src_arr.astype(np.float32) - proxy_arr.astype(np.float32)).mean())

        warnings = []
        if ssim < 0.55:
            warnings.append("LOW_SOURCE_SSIM")
        if edge_stats["f1"] < 0.70:
            warnings.append("LOW_EDGE_OVERLAP")

        manifest.update({
            "status": "PASS",
            "preprocessor": preprocessor,
            "control_hint_working_size": [hint.width, hint.height],
            "prompt_tokenizers": prompt_contract,
            "runtime_seconds": round(elapsed, 3),
            "peak_cuda_allocated_gb": peak_vram,
            "metrics": {
                "ssim_rgb": ssim,
                "mean_absolute_pixel_difference_0_255": mae,
                "edge_precision_tolerance_1px": edge_stats["precision"],
                "edge_recall_tolerance_1px": edge_stats["recall"],
                "edge_f1_tolerance_1px": edge_stats["f1"],
            },
            "drift_warnings": warnings,
            "output_proxy_png": str(run_dir / "02_geometry_assist_proxy.png"),
            "output_proxy_jpg": str(run_dir / "02_geometry_assist_proxy.jpg"),
        })
        save_json(run_dir / "manifest.json", manifest)
        log(f"PASS. Runtime {elapsed:.1f}s, peak allocated CUDA {peak_vram:.2f} GB, SSIM {ssim:.4f}, edge F1 {edge_stats['f1']:.4f}")
        log(f"Proxy PNG: {run_dir / '02_geometry_assist_proxy.png'}")
        return 0
    except Exception as exc:
        manifest.update({
            "status": "FAILED_RETAINED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
        save_json(run_dir / "manifest.json", manifest)
        log(f"FAILED_RETAINED: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return 1

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--input")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    root = Path(args.runtime_root)
    if not root.is_dir():
        print(f"Runtime root not found: {root}")
        return 2
    if args.self_test:
        return self_test(root)
    if not args.input:
        print("--input is required unless --self-test is used")
        return 2
    p = Path(args.input.strip('"'))
    if not p.is_file():
        print(f"Input image not found: {p}")
        return 2
    return run(root, p)

if __name__ == "__main__":
    raise SystemExit(main())
