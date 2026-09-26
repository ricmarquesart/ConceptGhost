from __future__ import annotations

import json
import shutil
from pathlib import Path

from .contracts import ContractError
from .result_output_contract import stage_root, update_stage_status
from .result_output_nodes import _image_to_pil, _make_contact_sheet, _save_image


_CATEGORY = "ConceptGhost/P10 Author Integration"
_EXPECTED_AUTHOR_ROUTES = 5


def _pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _safe_name(value: str) -> str:
    text = str(value or "").strip() or "route"
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in text)


def _frame_batch(image):
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("Author result gates require NumPy") from error
    array = image.detach().cpu().numpy() if hasattr(image, "detach") else np.asarray(image)
    if array.ndim == 3:
        array = array[None, ...]
    if array.ndim != 4:
        raise ContractError(f"Expected IMAGE batch [N,H,W,C], got shape {getattr(array, 'shape', None)}")
    return array


def _save_batch(folder: Path, image, prefix: str) -> list[str]:
    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Author result gates require NumPy and Pillow") from error
    folder.mkdir(parents=True, exist_ok=True)
    array = _frame_batch(image)
    paths: list[str] = []
    for index, frame in enumerate(array):
        rgb = frame
        if rgb.shape[-1] > 3:
            rgb = rgb[..., :3]
        if rgb.shape[-1] == 1:
            rgb = np.repeat(rgb, 3, axis=-1)
        data = (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        path = folder / f"{prefix}_{index:04d}.png"
        Image.fromarray(data, mode="RGB").save(path, format="PNG")
        paths.append(str(path))
    return paths


def _save_gif(path: Path, image, *, max_frames: int = 81, duration_ms: int = 80) -> str:
    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Author result gates require NumPy and Pillow") from error
    array = _frame_batch(image)
    count = min(int(array.shape[0]), int(max_frames))
    frames = []
    for frame in array[:count]:
        rgb = frame[..., :3]
        data = (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        frames.append(Image.fromarray(data, mode="RGB"))
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    return str(path)


def _validate_attempt(attempt_root: str, attempt_id: str, scene_contract_id: str) -> tuple[Path, dict]:
    attempt = Path(attempt_root).expanduser().resolve()
    attempt_id = str(attempt_id or "").strip()
    if not attempt.is_dir() or attempt.name != attempt_id:
        raise ContractError("Author result gate attempt identity/path mismatch")
    manifest_path = attempt / "attempt_manifest.json"
    if not manifest_path.is_file():
        raise ContractError("Author result gate requires attempt_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("scene_contract_id") or "") != str(scene_contract_id or "").strip():
        raise ContractError("Author result gate scene_contract_id mismatch")
    return attempt, manifest


class ConceptGhostP10AuthorWanResultGate:
    """Persist every WAN route before HiResComposite is allowed to consume it."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "route_index": ("INT", {"default": 0, "min": 0, "max": 4, "step": 1}),
                "route_name": ("STRING", {"forceInput": True}),
                "control_video": ("IMAGE",),
                "control_mask": ("IMAGE",),
                "wan_frames": ("IMAGE",),
                "rail_json": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("wan_frames", "rail_json", "route_name", "diagnostics_json")
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        scene_contract_id: str,
        route_index: int,
        route_name: str,
        control_video,
        control_mask,
        wan_frames,
        rail_json: str,
    ):
        attempt, attempt_manifest = _validate_attempt(
            p10_attempt_root, p10_attempt_id, scene_contract_id
        )
        index = int(route_index)
        safe = _safe_name(route_name)
        rail = Path(rail_json).expanduser().resolve()
        if not rail.is_file():
            raise ContractError(f"CG-06 rail JSON is missing: {rail}")

        stage = stage_root(attempt, "CG_06")
        outputs, previews, manifests, logs = (
            stage / "OUTPUTS",
            stage / "PREVIEWS",
            stage / "MANIFESTS",
            stage / "LOGS",
        )
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        route_root = outputs / f"{index + 1:02d}_{safe}"
        frame_paths = _save_batch(route_root / "wan_frames", wan_frames, "wan")
        _save_image(route_root / "control_first_frame.png", control_video)
        _save_image(route_root / "control_mask_first_frame.png", control_mask)
        rail_copy = route_root / "rail.json"
        shutil.copy2(rail, rail_copy)

        gif_path = _save_gif(previews / f"{index + 1:02d}_{safe}_wan.gif", wan_frames)
        contact = _make_contact_sheet(
            previews / f"{index + 1:02d}_{safe}_control_vs_wan.png",
            [
                ("CONTROL FIRST FRAME", route_root / "control_first_frame.png"),
                ("WAN FIRST FRAME", Path(frame_paths[0])),
                ("WAN LAST FRAME", Path(frame_paths[-1])),
            ],
        )

        route_manifest = {
            "schema": "ConceptGhost.CG06AuthorWanRoute.v0.1",
            "stage": "CG_06",
            "status": "PASS",
            "route_index": index,
            "route_name": route_name,
            "frame_count": len(frame_paths),
            "wan_frames_dir": str(route_root / "wan_frames"),
            "rail_json": str(rail_copy),
            "preview_gif": gif_path,
            "control_vs_wan_preview": contact,
        }
        route_manifest_path = manifests / f"{index + 1:02d}_{safe}.json"
        route_manifest_path.write_text(_pretty(route_manifest) + "\n", encoding="utf-8")
        (logs / f"{index + 1:02d}_{safe}.log").write_text(
            f"CG-06 WAN route evidence written during execution.\nframes={len(frame_paths)}\n",
            encoding="utf-8",
        )

        present = sorted(manifests.glob("[0-9][0-9]_*.json"))
        complete = len(present) >= _EXPECTED_AUTHOR_ROUTES
        aggregate_path = manifests / "cg06_wan_routes_index.json"
        aggregate_path.write_text(
            _pretty({
                "schema": "ConceptGhost.CG06AuthorWanIndex.v0.1",
                "status": "PASS" if complete else "PARTIAL",
                "expected_routes": _EXPECTED_AUTHOR_ROUTES,
                "published_routes": len(present),
                "route_manifests": [str(path) for path in present],
                "all_wan_routes_physically_published": complete,
            }) + "\n",
            encoding="utf-8",
        )

        status = update_stage_status(
            attempt,
            p10_attempt_id=str(p10_attempt_id),
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=str(scene_contract_id),
            stage_code="CG_06",
            runtime_status="PASS",
            functional_status="PASS" if complete else "PENDING",
            artist_quality_status="PENDING",
            notes=[
                f"Published WAN route {index + 1}: {route_name}.",
                f"{len(present)}/{_EXPECTED_AUTHOR_ROUTES} WAN route manifests physically present.",
            ],
        )

        diagnostics = {
            "status": "PASS" if complete else "PARTIAL",
            "stage": "CG_06",
            "route_index": index,
            "route_name": route_name,
            "wan_frames_dir": str(route_root / "wan_frames"),
            "preview_gif": gif_path,
            "aggregate_manifest": str(aggregate_path),
            "stage_status_path": status["status_path"],
        }
        return wan_frames, str(rail_copy), str(route_name), _pretty(diagnostics)


class ConceptGhostP10AuthorHiResResultGate:
    """Persist tangible source-preserving HiRes evidence before SphereSfM."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "p10_attempt_root": ("STRING", {"forceInput": True}),
                "p10_attempt_id": ("STRING", {"forceInput": True}),
                "scene_contract_id": ("STRING", {"forceInput": True}),
                "route_index": ("INT", {"default": 0, "min": 0, "max": 4, "step": 1}),
                "route_name": ("STRING", {"forceInput": True}),
                "proxy_frames": ("IMAGE",),
                "gate_masks": ("IMAGE",),
                "hires_dir": ("STRING", {"forceInput": True}),
                "proxy_dir": ("STRING", {"forceInput": True}),
                "hires_manifest": ("STRING", {"forceInput": True}),
                "report": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("proxy_frames", "hires_manifest", "route_name", "diagnostics_json")
    FUNCTION = "publish"
    CATEGORY = _CATEGORY
    OUTPUT_NODE = False

    def publish(
        self,
        p10_attempt_root: str,
        p10_attempt_id: str,
        scene_contract_id: str,
        route_index: int,
        route_name: str,
        proxy_frames,
        gate_masks,
        hires_dir: str,
        proxy_dir: str,
        hires_manifest: str,
        report: str,
    ):
        attempt, attempt_manifest = _validate_attempt(
            p10_attempt_root, p10_attempt_id, scene_contract_id
        )
        index = int(route_index)
        safe = _safe_name(route_name)
        hires_manifest_source = Path(hires_manifest).expanduser().resolve()
        if not hires_manifest_source.is_file():
            raise ContractError(f"CG-07 HiRes manifest is missing: {hires_manifest_source}")

        stage = stage_root(attempt, "CG_07")
        outputs, previews, manifests, logs = (
            stage / "OUTPUTS",
            stage / "PREVIEWS",
            stage / "MANIFESTS",
            stage / "LOGS",
        )
        for folder in (outputs, previews, manifests, logs):
            folder.mkdir(parents=True, exist_ok=True)

        route_root = outputs / f"{index + 1:02d}_{safe}"
        proxy_paths = _save_batch(route_root / "proxy_frames", proxy_frames, "proxy")
        mask_paths = _save_batch(route_root / "gate_masks", gate_masks, "gate")
        manifest_copy = route_root / "author_hires_manifest.json"
        shutil.copy2(hires_manifest_source, manifest_copy)
        (route_root / "author_hires_dir.txt").write_text(str(hires_dir) + "\n", encoding="utf-8")
        (route_root / "author_proxy_dir.txt").write_text(str(proxy_dir) + "\n", encoding="utf-8")
        (route_root / "author_report.txt").write_text(str(report or "") + "\n", encoding="utf-8")

        preview_path = previews / f"{index + 1:02d}_{safe}_proxy.gif"
        _save_gif(preview_path, proxy_frames)
        contact = _make_contact_sheet(
            previews / f"{index + 1:02d}_{safe}_hires_evidence.png",
            [
                ("PROXY FIRST", Path(proxy_paths[0])),
                ("PROXY LAST", Path(proxy_paths[-1])),
                ("GATE MASK FIRST", Path(mask_paths[0])),
            ],
        )

        route_manifest = {
            "schema": "ConceptGhost.CG07AuthorHiResRoute.v0.1",
            "stage": "CG_07",
            "status": "PASS",
            "route_index": index,
            "route_name": route_name,
            "proxy_frame_count": len(proxy_paths),
            "gate_mask_count": len(mask_paths),
            "author_hires_dir": str(hires_dir),
            "author_proxy_dir": str(proxy_dir),
            "author_hires_manifest_source": str(hires_manifest_source),
            "published_hires_manifest": str(manifest_copy),
            "proxy_preview_gif": str(preview_path),
            "evidence_contact_sheet": contact,
        }
        route_manifest_path = manifests / f"{index + 1:02d}_{safe}.json"
        route_manifest_path.write_text(_pretty(route_manifest) + "\n", encoding="utf-8")
        (logs / f"{index + 1:02d}_{safe}.log").write_text(
            f"CG-07 HiRes route evidence written during execution.\nproxy_frames={len(proxy_paths)}\n",
            encoding="utf-8",
        )

        present = sorted(manifests.glob("[0-9][0-9]_*.json"))
        complete = len(present) >= _EXPECTED_AUTHOR_ROUTES
        aggregate_path = manifests / "cg07_hires_routes_index.json"
        aggregate_path.write_text(
            _pretty({
                "schema": "ConceptGhost.CG07AuthorHiResIndex.v0.1",
                "status": "PASS" if complete else "PARTIAL",
                "expected_routes": _EXPECTED_AUTHOR_ROUTES,
                "published_routes": len(present),
                "route_manifests": [str(path) for path in present],
                "all_hires_routes_physically_published": complete,
            }) + "\n",
            encoding="utf-8",
        )

        status = update_stage_status(
            attempt,
            p10_attempt_id=str(p10_attempt_id),
            p9_run_id=str(attempt_manifest.get("parent_p9_run_id") or ""),
            scene_contract_id=str(scene_contract_id),
            stage_code="CG_07",
            runtime_status="PASS",
            functional_status="PASS" if complete else "PENDING",
            artist_quality_status="PENDING",
            notes=[
                f"Published HiRes/proxy route {index + 1}: {route_name}.",
                f"{len(present)}/{_EXPECTED_AUTHOR_ROUTES} HiRes route manifests physically present.",
            ],
        )

        diagnostics = {
            "status": "PASS" if complete else "PARTIAL",
            "stage": "CG_07",
            "route_index": index,
            "route_name": route_name,
            "proxy_frames_dir": str(route_root / "proxy_frames"),
            "author_hires_dir": str(hires_dir),
            "aggregate_manifest": str(aggregate_path),
            "stage_status_path": status["status_path"],
        }
        return proxy_frames, str(manifest_copy), str(route_name), _pretty(diagnostics)


NODE_CLASS_MAPPINGS = {
    "ConceptGhostP10AuthorWanResultGate": ConceptGhostP10AuthorWanResultGate,
    "ConceptGhostP10AuthorHiResResultGate": ConceptGhostP10AuthorHiResResultGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptGhostP10AuthorWanResultGate": "P10 · CG-06 · Publish WAN Frames Before HiRes",
    "ConceptGhostP10AuthorHiResResultGate": "P10 · CG-07 · Publish HiRes/Proxy Evidence Before SphereSfM",
}
