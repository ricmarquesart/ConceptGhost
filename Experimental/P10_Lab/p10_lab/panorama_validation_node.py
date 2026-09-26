from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root, update_stage_status
from .result_output_nodes import _image_to_pil, _make_contact_sheet, _save_image


_CATEGORY = "ConceptGhost/P10 Result Evidence"


def _tensor_image_from_pil(pil):
    try:
        import numpy as np
        import torch
    except ImportError as error:
        raise RuntimeError("CG-03 panorama validation requires NumPy and torch") from error
    array = np.asarray(pil.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array).unsqueeze(0)


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _reproject_erp_to_source(final_erp, *, width: int, height: int, fx: float, fy: float, cx: float, cy: float):
    """Sample an ERP back through the accepted P9 pinhole camera."""
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as error:
        raise RuntimeError("CG-03 panorama validation requires torch") from error

    erp = final_erp if final_erp.ndim == 4 else final_erp.unsqueeze(0)
    if erp.ndim != 4 or erp.shape[-1] < 3:
        raise ContractError("final_erp must be an IMAGE tensor [B,H,W,C]")
    erp = erp[..., :3].float().clamp(0.0, 1.0)
    batch, erp_h, erp_w, _ = erp.shape

    xs = torch.arange(width, dtype=torch.float32, device=erp.device)
    ys = torch.arange(height, dtype=torch.float32, device=erp.device)
    yy, xx = torch.meshgrid(ys, xs, indexing="ij")

    ray_x = (xx - float(cx)) / float(fx)
    ray_y = (float(cy) - yy) / float(fy)
    ray_z = torch.ones_like(ray_x)
    norm = torch.sqrt(ray_x * ray_x + ray_y * ray_y + ray_z * ray_z).clamp_min(1.0e-8)
    ray_x, ray_y, ray_z = ray_x / norm, ray_y / norm, ray_z / norm

    lon = torch.atan2(ray_x, ray_z)
    lat = torch.atan2(ray_y, torch.sqrt(ray_x * ray_x + ray_z * ray_z).clamp_min(1.0e-8))

    # Inverse of the author's ERP pixel-centre convention.
    u = (lon + torch.pi) / (2.0 * torch.pi) * float(erp_w) - 0.5
    v = (0.5 - lat / torch.pi) * float(erp_h) - 0.5
    gx = 2.0 * u / max(erp_w - 1, 1) - 1.0
    gy = 2.0 * v / max(erp_h - 1, 1) - 1.0
    grid = torch.stack([gx, gy], dim=-1).unsqueeze(0)
    if batch > 1:
        grid = grid.repeat(batch, 1, 1, 1)

    sampled = F.grid_sample(
        erp.permute(0, 3, 1, 2),
        grid,
        mode="bicubic",
        padding_mode="border",
        align_corners=True,
    ).clamp(0.0, 1.0)
    return sampled.permute(0, 2, 3, 1)


def _difference_metrics(source, reconstructed) -> dict:
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("CG-03 panorama validation requires torch") from error
    diff = (source.float() - reconstructed.float()).abs()
    flat = diff.reshape(-1)
    mae = float(diff.mean().item())
    p95 = float(torch.quantile(flat, 0.95).item()) if flat.numel() else 0.0
    maximum = float(diff.max().item()) if flat.numel() else 0.0
    mse = float(((source.float() - reconstructed.float()) ** 2).mean().item())
    psnr = 99.0 if mse <= 1.0e-12 else float(-10.0 * torch.log10(torch.tensor(mse)).item())
    return {"mae": mae, "p95_abs": p95, "max_abs": maximum, "mse": mse, "psnr_db": psnr}


def _seam_metrics(final_erp) -> dict:
    erp = final_erp if final_erp.ndim == 4 else final_erp.unsqueeze(0)
    rgb = erp[..., :3].float().clamp(0.0, 1.0)
    if rgb.shape[2] < 4:
        raise ContractError("final_erp width is too small for seam validation")
    wrap_jump = float((rgb[:, :, 0, :] - rgb[:, :, -1, :]).abs().mean().item())
    left_local = float((rgb[:, :, 1, :] - rgb[:, :, 0, :]).abs().mean().item())
    right_local = float((rgb[:, :, -1, :] - rgb[:, :, -2, :]).abs().mean().item())
    local_reference = max((left_local + right_local) * 0.5, 1.0e-6)
    return {
        "wrap_jump_mae": wrap_jump,
        "local_edge_gradient_mae": local_reference,
        "wrap_to_local_ratio": wrap_jump / local_reference,
    }


class ConceptGhostP10PanoramaValidation:
    """CG-03 source-camera regression + ERP seam validation.

    Downstream author 3DGS branches should consume validated_erp, not bypass
    this node, so a failed panorama cannot silently advance.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "source_p9_run_dir": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "final_erp": ("IMAGE",),
                "max_source_mae": ("FLOAT", {"default": 0.03, "min": 0.0, "max": 1.0, "step": 0.001}),
                "max_source_p95_abs": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.005}),
                "max_seam_wrap_ratio": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 20.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = (
        "validated_erp",
        "concept_reprojection",
        "difference_heatmap",
        "validation_pass",
        "cg03_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "validate"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def validate(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        source_p9_run_dir: str,
        scene_contract_id: str,
        final_erp,
        max_source_mae: float,
        max_source_p95_abs: float,
        max_seam_wrap_ratio: float,
    ):
        try:
            import torch
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("CG-03 panorama validation requires Pillow and torch") from error

        attempt = Path(str(p10_attempt_root)).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        scene_id = str(scene_contract_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("CG-03 attempt identity/path mismatch")

        attempt_manifest_path = attempt / "attempt_manifest.json"
        if not attempt_manifest_path.is_file():
            raise ContractError("CG-03 requires attempt_manifest.json")
        attempt_manifest = json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("CG-03 scene_contract_id does not match attempt")

        source_run = Path(source_p9_run_dir).expanduser().resolve()
        camera_path = source_run / "camera" / "camera.json"
        source_path = source_run / "source" / "source.png"
        if not camera_path.is_file() or not source_path.is_file():
            raise ContractError("CG-03 cannot find accepted P9 camera/source")

        camera = json.loads(camera_path.read_text(encoding="utf-8"))
        intr = camera.get("intrinsics") or {}
        width = int(camera.get("image_width") or 0)
        height = int(camera.get("image_height") or 0)
        fx = float(intr.get("fx_px") or 0.0)
        fy = float(intr.get("fy_px") or 0.0)
        cx = float(intr.get("cx_px") or 0.0)
        cy = float(intr.get("cy_px") or 0.0)
        if min(width, height) <= 0 or min(fx, fy) <= 0.0:
            raise ContractError("CG-03 P9 camera intrinsics are incomplete")

        with Image.open(source_path) as opened:
            source = _tensor_image_from_pil(opened)
        device = final_erp.device if hasattr(final_erp, "device") else "cpu"
        source = source.to(device)

        reprojection = _reproject_erp_to_source(
            final_erp,
            width=width,
            height=height,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
        )[:1]
        metrics = _difference_metrics(source, reprojection)
        seam = _seam_metrics(final_erp)

        source_pass = (
            metrics["mae"] <= float(max_source_mae)
            and metrics["p95_abs"] <= float(max_source_p95_abs)
        )
        seam_pass = seam["wrap_to_local_ratio"] <= float(max_seam_wrap_ratio)
        passed = bool(source_pass and seam_pass)

        heat = ((source - reprojection).abs() * 4.0).clamp(0.0, 1.0)

        stage = stage_root(attempt, "CG_03")
        outputs, previews, manifests, logs = (
            stage / "OUTPUTS",
            stage / "PREVIEWS",
            stage / "MANIFESTS",
            stage / "LOGS",
        )
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        artifacts = {
            "concept_reprojection": _save_image(
                outputs / "01_concept_camera_reprojection.png", reprojection
            ),
            "difference_heatmap": _save_image(
                outputs / "02_source_difference_heatmap.png", heat
            ),
            "final_erp_checked": _save_image(
                outputs / "03_final_erp_checked.png", final_erp
            ),
        }

        erp_pil = _image_to_pil(final_erp)
        strip = max(8, min(256, erp_pil.width // 32))
        seam_preview = Image.new("RGB", (strip * 2, erp_pil.height), (0, 0, 0))
        seam_preview.paste(
            erp_pil.crop((erp_pil.width - strip, 0, erp_pil.width, erp_pil.height)),
            (0, 0),
        )
        seam_preview.paste(erp_pil.crop((0, 0, strip, erp_pil.height)), (strip, 0))
        seam_preview_path = previews / "seam_wrap_left_right.png"
        seam_preview.save(seam_preview_path, format="PNG")

        source_tmp = outputs / "_source_tmp.png"
        _save_image(source_tmp, source)
        comparison_path = previews / "source_vs_reprojection.png"
        _make_contact_sheet(
            comparison_path,
            [
                ("ORIGINAL CONCEPT", source_tmp),
                ("ERP REPROJECTED TO P9 CAMERA", Path(artifacts["concept_reprojection"]["path"])),
                ("DIFFERENCE x4", Path(artifacts["difference_heatmap"]["path"])),
            ],
        )
        source_tmp.unlink(missing_ok=True)

        payload = {
            "schema": "ConceptGhost.CG03PanoramaValidation.v0.1",
            "stage": "CG_03",
            "status": "PASS" if passed else "FAIL",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "source_p9_run_dir": str(source_run),
            "source_camera_regression": {
                **metrics,
                "max_mae": float(max_source_mae),
                "max_p95_abs": float(max_source_p95_abs),
                "pass": source_pass,
            },
            "erp_seam_continuity": {
                **seam,
                "max_wrap_to_local_ratio": float(max_seam_wrap_ratio),
                "pass": seam_pass,
            },
            "artifacts": artifacts,
            "previews": {
                "source_vs_reprojection": str(comparison_path),
                "seam_wrap_left_right": str(seam_preview_path),
            },
            "downstream_author_pipeline_allowed": passed,
        }
        cg03_manifest = manifests / "cg03_panorama_validation.json"
        cg03_manifest.write_text(_pretty(payload) + "\n", encoding="utf-8")
        (logs / "validation.log").write_text(_pretty(payload) + "\n", encoding="utf-8")

        stage_status = update_stage_status(
            attempt,
            p10_attempt_id=attempt_id,
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=scene_id,
            stage_code="CG_03",
            runtime_status="PASS",
            functional_status="PASS" if passed else "FAIL",
            artist_quality_status="PENDING",
            notes=[
                "Concept-camera reprojection and ERP seam evidence generated.",
                "Downstream author 3DGS path is allowed only when numerical validation passes.",
            ],
        )

        diagnostics = {
            "status": payload["status"],
            "stage": "CG_03",
            "manifest_path": str(cg03_manifest),
            "stage_status_path": stage_status["status_path"],
            "source_camera_pass": source_pass,
            "seam_pass": seam_pass,
            "validation_pass": passed,
        }

        if not passed:
            raise ContractError(
                "CG-03 panorama validation failed after writing physical evidence to "
                f"{stage}. source_pass={source_pass}, seam_pass={seam_pass}"
            )

        return {
            "ui": {"text": [_pretty(diagnostics)]},
            "result": (
                final_erp,
                reprojection,
                heat,
                True,
                str(cg03_manifest),
                _pretty(diagnostics),
            ),
        }


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10PanoramaValidation": ConceptGhostP10PanoramaValidation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10PanoramaValidation": "P10 · CG-03 · Validate Source Lock + ERP Seam",
}
