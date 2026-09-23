from __future__ import annotations
import argparse
import gc
import json
import os
import sys
import traceback
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch
from PIL import Image


def log(stage: str, message: str):
    print(f"[LOTUS_ADAPTER] {stage} — {message}", flush=True)


def cuda_stats():
    if not torch.cuda.is_available():
        return {"cuda_available": False}
    d = torch.cuda.current_device()
    p = torch.cuda.get_device_properties(d)
    return {
        "cuda_available": True,
        "device": torch.cuda.get_device_name(d),
        "total_vram_bytes": int(p.total_memory),
        "allocated_bytes": int(torch.cuda.memory_allocated(d)),
        "reserved_bytes": int(torch.cuda.memory_reserved(d)),
    }


def load_pipeline(source_root: Path, model_path: Path, memory_mode: str):
    sys.path.insert(0, str(source_root))
    from pipeline import LotusDPipeline

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    log("MODEL_LOAD_START", json.dumps({"model": str(model_path), "dtype": str(dtype), "memory_mode": memory_mode}))
    pipe = LotusDPipeline.from_pretrained(
        str(model_path),
        torch_dtype=dtype,
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    pipe.set_progress_bar_config(disable=True)

    if torch.cuda.is_available():
        total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        if memory_mode == "auto":
            memory_mode = "cpu_offload" if total_gb <= 13.0 else "full_cuda"
        if memory_mode == "cpu_offload":
            log("MEMORY_MODE", f"enable_model_cpu_offload on {total_gb:.2f} GB GPU")
            pipe.enable_model_cpu_offload(gpu_id=0)
        elif memory_mode == "full_cuda":
            log("MEMORY_MODE", f"full pipeline to CUDA on {total_gb:.2f} GB GPU")
            pipe = pipe.to(torch.device("cuda"))
        else:
            raise ValueError(f"Unsupported memory mode: {memory_mode}")
    else:
        memory_mode = "cpu"
        log("MEMORY_MODE", "CUDA unavailable; CPU inference")

    log("MODEL_LOAD_DONE", json.dumps(cuda_stats()))
    return pipe, memory_mode


def run_one(pipe, image_path: Path, task: str, processing_res: int, disparity: bool):
    from utils.image_utils import colorize_depth_map

    test_image = Image.open(image_path).convert("RGB")
    arr = np.asarray(test_image, dtype=np.float32)
    rgb = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    rgb = rgb / 127.5 - 1.0

    device = pipe._execution_device
    rgb = rgb.to(device)
    task_emb = torch.tensor([1, 0], dtype=torch.float32, device=device).unsqueeze(0)
    task_emb = torch.cat([torch.sin(task_emb), torch.cos(task_emb)], dim=-1)

    log("INFERENCE_START", json.dumps({"task": task, "processing_res": processing_res, "device": str(device), "cuda": cuda_stats()}))
    autocast_ctx = torch.autocast("cuda", dtype=torch.float16) if device.type == "cuda" else nullcontext()
    with torch.inference_mode(), autocast_ctx:
        pred = pipe(
            rgb_in=rgb,
            prompt="",
            num_inference_steps=1,
            generator=None,
            output_type="np",
            timesteps=[999],
            task_emb=task_emb,
            processing_res=processing_res,
            match_input_res=True,
            resample_method="bilinear",
        ).images[0]

    if task == "depth":
        out_npy = pred.mean(axis=-1).astype(np.float32)
        out_vis = colorize_depth_map(out_npy, reverse_color=disparity)
    else:
        out_npy = pred.astype(np.float32)
        out_vis = Image.fromarray(np.clip(out_npy * 255.0, 0, 255).astype(np.uint8))
    log("INFERENCE_DONE", json.dumps({"shape": list(out_npy.shape), "cuda": cuda_stats()}))
    return out_npy, out_vis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--model-path", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--task", choices=["depth", "normal"], required=True)
    ap.add_argument("--processing-res", type=int, default=768)
    ap.add_argument("--disparity", action="store_true")
    ap.add_argument("--memory-mode", choices=["auto", "cpu_offload", "full_cuda"], default="auto")
    args = ap.parse_args()

    source_root = Path(args.source_root).resolve()
    model_path = Path(args.model_path).resolve()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    vis_dir = output_dir / f"{args.task}_vis"
    npy_dir = output_dir / args.task
    vis_dir.mkdir(parents=True, exist_ok=True)
    npy_dir.mkdir(parents=True, exist_ok=True)

    log("PREFLIGHT", json.dumps({
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "source_root": str(source_root),
        "model_path": str(model_path),
        "model_index_exists": (model_path / "model_index.json").is_file(),
        "cuda": cuda_stats(),
    }))

    images = sorted(list(input_dir.rglob("*.png")) + list(input_dir.rglob("*.jpg")) + list(input_dir.rglob("*.jpeg")))
    if len(images) != 1:
        raise RuntimeError(f"Expected exactly one input image under {input_dir}; found {len(images)}")

    pipe = None
    try:
        pipe, used_mode = load_pipeline(source_root, model_path, args.memory_mode)
        out_npy, out_vis = run_one(pipe, images[0], args.task, args.processing_res, args.disparity)
        stem = images[0].stem
        np.save(npy_dir / f"{stem}.npy", out_npy)
        out_vis.save(vis_dir / f"{stem}.png")
        print(json.dumps({"status": "PASS", "task": args.task, "memory_mode": used_mode, "npy": str(npy_dir / f'{stem}.npy'), "vis": str(vis_dir / f'{stem}.png')}), flush=True)
    except Exception:
        log("FAIL", traceback.format_exc())
        raise
    finally:
        if pipe is not None:
            del pipe
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            log("CUDA_RELEASE", json.dumps(cuda_stats()))


if __name__ == "__main__":
    main()
