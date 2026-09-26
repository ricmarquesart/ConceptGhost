from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root, update_stage_status


_CATEGORY = "ConceptGhost/P10 Result Evidence"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_to_pil(image, *, grayscale: bool = False):
    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Result evidence image export requires NumPy and Pillow") from error

    array = image.detach().cpu().numpy() if hasattr(image, "detach") else np.asarray(image)
    if array.ndim == 4:
        array = array[0]
    if grayscale:
        if array.ndim == 3:
            array = array[..., 0]
        array = (np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        return Image.fromarray(array, mode="L")

    if array.ndim == 2:
        array = np.repeat(array[..., None], 3, axis=2)
    if array.shape[-1] > 3:
        array = array[..., :3]
    array = (np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(array, mode="RGB")


def _save_image(path: Path, image, *, grayscale: bool = False) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    pil = _image_to_pil(image, grayscale=grayscale)
    pil.save(path, format="PNG")
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "width": pil.width,
        "height": pil.height,
        "mode": pil.mode,
    }


def _make_contact_sheet(path: Path, panels: list[tuple[str, Path]]) -> dict:
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError("Result evidence preview requires Pillow") from error

    opened = [(label, Image.open(source).convert("RGB")) for label, source in panels]
    try:
        thumb_w = 640
        label_h = 30
        rendered = []
        for label, image in opened:
            ratio = thumb_w / max(1, image.width)
            thumb_h = max(1, int(round(image.height * ratio)))
            thumb = image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            panel = Image.new("RGB", (thumb_w, thumb_h + label_h), (0, 0, 0))
            panel.paste(thumb, (0, label_h))
            draw = ImageDraw.Draw(panel)
            draw.text((8, 7), label, fill=(255, 255, 255))
            rendered.append(panel)
        total_h = sum(item.height for item in rendered)
        sheet = Image.new("RGB", (thumb_w, total_h), (0, 0, 0))
        y = 0
        for panel in rendered:
            sheet.paste(panel, (0, y))
            y += panel.height
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path, format="PNG")
    finally:
        for _, image in opened:
            image.close()
    return {"path": str(path), "sha256": _sha256(path)}


class ConceptGhostP10PanoramaResultPublisher:
    """Persist tangible CG-02 panorama evidence inside the active P10 attempt.

    This node is intentionally an OUTPUT_NODE. It is designed to sit on the
    private author panorama graph as a side branch and materialize the actual
    intermediate/final images while the graph executes. It does not backfill
    after the run and it never mutates P9.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "source_p9_run_dir": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "raw_generated_erp": ("IMAGE",),
                "harmonized_erp": ("IMAGE",),
                "source_locked_erp": ("IMAGE",),
                "seam_before": ("IMAGE",),
                "seam_after": ("IMAGE",),
                "final_erp": ("IMAGE",),
                "source_lock_mask": ("MASK",),
                "generation_mask": ("MASK",),
            },
            "optional": {
                "settings_json": ("STRING", {"default": "{}"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("final_erp", "cg02_manifest_path", "diagnostics_json")
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        source_p9_run_dir: str,
        scene_contract_id: str,
        raw_generated_erp,
        harmonized_erp,
        source_locked_erp,
        seam_before,
        seam_after,
        final_erp,
        source_lock_mask,
        generation_mask,
        settings_json: str = "{}",
    ):
        attempt = Path(str(p10_attempt_root)).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        scene_id = str(scene_contract_id or "").strip()
        if not attempt.is_dir():
            raise ContractError(f"P10 attempt root does not exist: {attempt}")
        if attempt.name != attempt_id:
            raise ContractError(
                f"Panorama result attempt mismatch: {attempt.name!r} != {attempt_id!r}"
            )
        if not scene_id:
            raise ContractError("Panorama result publisher requires scene_contract_id")

        manifest_path = attempt / "attempt_manifest.json"
        if not manifest_path.is_file():
            raise ContractError(f"P10 attempt manifest is missing: {manifest_path}")
        attempt_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("Panorama result scene_contract_id does not match attempt")
        if str(Path(attempt_manifest.get("source_p9_run_dir") or "").resolve()) != str(
            Path(source_p9_run_dir).expanduser().resolve()
        ):
            raise ContractError("Panorama result P9 source does not match attempt authority")

        stage = stage_root(attempt, "CG_02")
        outputs = stage / "OUTPUTS"
        previews = stage / "PREVIEWS"
        manifests = stage / "MANIFESTS"
        logs = stage / "LOGS"
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        artifacts = {
            "raw_generated_erp": _save_image(
                outputs / "01_raw_generated_erp.png", raw_generated_erp
            ),
            "harmonized_erp": _save_image(
                outputs / "02_harmonized_erp.png", harmonized_erp
            ),
            "source_locked_erp": _save_image(
                outputs / "03_source_locked_erp.png", source_locked_erp
            ),
            "seam_before": _save_image(
                outputs / "04_seam_centered_before_inpaint.png", seam_before
            ),
            "seam_after": _save_image(
                outputs / "05_seam_centered_after_inpaint.png", seam_after
            ),
            "final_erp": _save_image(
                outputs / "06_final_erp.png", final_erp
            ),
            "source_lock_mask": _save_image(
                outputs / "07_source_lock_mask.png", source_lock_mask, grayscale=True
            ),
            "generation_mask": _save_image(
                outputs / "08_generation_mask.png", generation_mask, grayscale=True
            ),
        }

        # Human-visible proof: final ERP plus a vertical before/after process sheet.
        final_preview = previews / "final_erp.png"
        _save_image(final_preview, final_erp)
        contact = _make_contact_sheet(
            previews / "panorama_process_contact_sheet.png",
            [
                ("RAW GENERATED ERP", Path(artifacts["raw_generated_erp"]["path"])),
                ("HARMONIZED ERP", Path(artifacts["harmonized_erp"]["path"])),
                ("SOURCE LOCKED ERP", Path(artifacts["source_locked_erp"]["path"])),
                ("SEAM BEFORE", Path(artifacts["seam_before"]["path"])),
                ("SEAM AFTER", Path(artifacts["seam_after"]["path"])),
                ("FINAL ERP", Path(artifacts["final_erp"]["path"])),
            ],
        )

        try:
            settings = json.loads(str(settings_json or "{}"))
            if not isinstance(settings, dict):
                settings = {"raw": settings}
        except Exception:
            settings = {"raw": str(settings_json)}

        payload = {
            "schema": "ConceptGhost.CG02PanoramaResult.v0.1",
            "status": "PASS",
            "stage": "CG_02",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "source_p9_run_dir": str(Path(source_p9_run_dir).expanduser().resolve()),
            "source_authority_preserved_by_contract": True,
            "panorama_role": "MANDATORY_SHARED_360_WORLD_PRIOR",
            "projection": "EQUIRECTANGULAR_2_TO_1",
            "artifacts": artifacts,
            "previews": {
                "final_erp": str(final_preview),
                "process_contact_sheet": contact,
            },
            "settings": settings,
            "cg03_validation_required": True,
            "note": (
                "CG-02 proves physical panorama production. CG-03 separately proves "
                "source-camera reprojection and ERP seam continuity."
            ),
        }
        cg02_manifest = manifests / "cg02_panorama_result.json"
        cg02_manifest.write_text(_pretty(payload) + "\n", encoding="utf-8")
        (logs / "publisher.log").write_text(
            "CG-02 physical panorama evidence published during workflow execution.\n"
            f"attempt={attempt_id}\n"
            f"final_erp={artifacts['final_erp']['path']}\n",
            encoding="utf-8",
        )

        status = update_stage_status(
            attempt,
            p10_attempt_id=attempt_id,
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=scene_id,
            stage_code="CG_02",
            runtime_status="PASS",
            functional_status="PASS",
            artist_quality_status="PENDING",
            notes=[
                "Physical panorama outputs, previews and manifest exist.",
                "Artist/source-camera validation remains CG-03.",
            ],
        )
        diagnostics = {
            "status": "PASS",
            "stage": "CG_02",
            "manifest_path": str(cg02_manifest),
            "result_root": str(stage),
            "stage_status_path": status["status_path"],
            "functional_result_proven": True,
            "artist_quality_status": "PENDING",
        }
        return {
            "ui": {"text": [_pretty(diagnostics)]},
            "result": (final_erp, str(cg02_manifest), _pretty(diagnostics)),
        }


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10PanoramaResultPublisher": ConceptGhostP10PanoramaResultPublisher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10PanoramaResultPublisher": "P10 · CG-02 · Publish Tangible 360 Panorama Results",
}
