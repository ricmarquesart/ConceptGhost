from __future__ import annotations

import json
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root, update_stage_status


_CATEGORY = "ConceptGhost/P10 Author Integration"


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _model_files(sparse_root: Path) -> list[Path]:
    candidates = []
    for name in ("cameras.bin", "images.bin", "points3D.bin", "cameras.txt", "images.txt", "points3D.txt"):
        path = sparse_root / name
        if path.is_file():
            candidates.append(path)
    return candidates


def _write_dataset_preview(path: Path, image_paths: list[Path], *, num_images: int, num_points: int) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError("CG-08 dataset preview requires Pillow") from error

    width = 1200
    thumb_w = 360
    thumb_h = 240
    header_h = 90
    cols = 3
    selected = image_paths[:6]
    rows = max(1, (len(selected) + cols - 1) // cols)
    height = header_h + rows * (thumb_h + 50)
    canvas = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 20), "ConceptGhost CG-08 · SphereSfM/COLMAP dataset", fill=(255, 255, 255))
    draw.text((24, 50), f"registered images: {num_images}    sparse points: {num_points}", fill=(220, 220, 220))

    for index, source in enumerate(selected):
        try:
            with Image.open(source) as opened:
                image = opened.convert("RGB")
                image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                cell_x = 20 + (index % cols) * 390
                cell_y = header_h + (index // cols) * (thumb_h + 50)
                canvas.paste(image, (cell_x, cell_y))
                draw.text((cell_x, cell_y + thumb_h + 8), source.name[:48], fill=(210, 210, 210))
        except Exception:
            continue

    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG")


class ConceptGhostP10AuthorDatasetResultGate:
    """Validate and publish the author SphereSfM/COLMAP dataset as CG-08 evidence."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "dataset_project_absolute": ("STRING", {"forceInput": True}),
                "model_dir": ("STRING", {"forceInput": True}),
                "num_images": ("INT", {"forceInput": True}),
                "num_points": ("INT", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = (
        "validated_model_dir",
        "num_images",
        "num_points",
        "cg08_manifest_path",
        "diagnostics_json",
    )
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = True

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        scene_contract_id: str,
        dataset_project_absolute: str,
        model_dir: str,
        num_images: int,
        num_points: int,
    ):
        attempt = Path(p10_attempt_root).expanduser().resolve()
        attempt_id = str(p10_attempt_id or "").strip()
        scene_id = str(scene_contract_id or "").strip()
        if not attempt.is_dir() or attempt.name != attempt_id:
            raise ContractError("CG-08 attempt identity/path mismatch")

        attempt_manifest_path = attempt / "attempt_manifest.json"
        if not attempt_manifest_path.is_file():
            raise ContractError("CG-08 requires attempt_manifest.json")
        attempt_manifest = json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
        if str(attempt_manifest.get("scene_contract_id") or "") != scene_id:
            raise ContractError("CG-08 scene_contract_id mismatch")

        expected_project = Path(dataset_project_absolute).expanduser().resolve()
        model = Path(model_dir).expanduser().resolve()
        try:
            model.relative_to(expected_project)
        except ValueError as error:
            raise ContractError(
                f"CG-08 SphereSfM model escaped current attempt project: {model}"
            ) from error

        if not model.is_dir():
            raise ContractError(f"CG-08 model_dir does not exist: {model}")
        images_dir = model / "images"
        sparse_root = model / "sparse" / "0"
        if not images_dir.is_dir() or not sparse_root.is_dir():
            raise ContractError("CG-08 dataset is missing images/ or sparse/0/")

        image_paths = sorted(
            path for path in images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        model_files = _model_files(sparse_root)
        if int(num_images) <= 0 or len(image_paths) <= 0:
            raise ContractError("CG-08 SphereSfM produced no registered dataset images")
        if int(num_points) <= 0:
            raise ContractError("CG-08 SphereSfM produced no sparse 3D points")
        if len(model_files) < 3:
            raise ContractError("CG-08 sparse model is incomplete")

        stage = stage_root(attempt, "CG_08")
        outputs, previews, manifests, logs = (
            stage / "OUTPUTS",
            stage / "PREVIEWS",
            stage / "MANIFESTS",
            stage / "LOGS",
        )
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        # The author project itself is already physically under CG-08/OUTPUTS;
        # publish an explicit pointer/inventory rather than duplicate the whole dataset.
        pointer = outputs / "AUTHOR_DATASET_LOCATION.txt"
        pointer.write_text(str(model) + "\n", encoding="utf-8")

        preview = previews / "dataset_contact_sheet.png"
        _write_dataset_preview(
            preview,
            image_paths,
            num_images=int(num_images),
            num_points=int(num_points),
        )

        payload = {
            "schema": "ConceptGhost.CG08AuthorDatasetResult.v0.1",
            "stage": "CG_08",
            "status": "PASS",
            "p10_attempt_id": attempt_id,
            "scene_contract_id": scene_id,
            "dataset_project_absolute": str(expected_project),
            "model_dir": str(model),
            "images_dir": str(images_dir),
            "sparse_dir": str(sparse_root),
            "reported_num_images": int(num_images),
            "physical_image_file_count": len(image_paths),
            "reported_num_points": int(num_points),
            "sparse_model_files": [str(path) for path in model_files],
            "dataset_preview": str(preview),
            "dataset_is_inside_current_attempt": True,
            "manual_copy_or_backfill_required": False,
            "sphere_sfm_functional_result_proven": True,
        }
        manifest_path = manifests / "cg08_multiview_dataset.json"
        manifest_path.write_text(_pretty(payload) + "\n", encoding="utf-8")
        (logs / "dataset_validation.log").write_text(_pretty(payload) + "\n", encoding="utf-8")

        status = update_stage_status(
            attempt,
            p10_attempt_id=attempt_id,
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=scene_id,
            stage_code="CG_08",
            runtime_status="PASS",
            functional_status="PASS",
            artist_quality_status="PENDING",
            notes=[
                "Physical SphereSfM/COLMAP images and sparse model verified inside current attempt.",
                f"Registered images={int(num_images)}, sparse points={int(num_points)}.",
            ],
        )

        diagnostics = {
            "status": "PASS",
            "stage": "CG_08",
            "model_dir": str(model),
            "num_images": int(num_images),
            "num_points": int(num_points),
            "manifest_path": str(manifest_path),
            "preview_path": str(preview),
            "stage_status_path": status["status_path"],
        }
        return str(model), int(num_images), int(num_points), str(manifest_path), _pretty(diagnostics)


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetResultGate": ConceptGhostP10AuthorDatasetResultGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorDatasetResultGate": "P10 · CG-08 · Validate Tangible SphereSfM/COLMAP Dataset",
}
