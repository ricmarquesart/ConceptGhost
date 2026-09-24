from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .visual_evidence_contract import (
    VISUAL_EVIDENCE_RULES,
    validate_visual_evidence_manifest,
)


_SCHEMA = "ConceptGhost.P10Gate7Closeout.v0.1"
_REQUIRED_VISUAL_GATES = ("G7.1", "G7.2", "G7.2C", "G7.3", "G7.4", "G7.5")


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _same_identity(payloads: list[tuple[str, dict[str, Any]]]) -> dict[str, str]:
    identity: dict[str, str] = {}
    aliases = {
        "scene_contract_id": ("scene_contract_id",),
        "p9_run_id": ("p9_run_id", "run_id"),
        "p10_attempt_id": ("p10_attempt_id",),
    }
    for canonical, keys in aliases.items():
        values = []
        for label, payload in payloads:
            value = None
            for key in keys:
                if payload.get(key) not in (None, ""):
                    value = str(payload.get(key))
                    break
            if value is not None:
                values.append((label, value))
        unique = {value for _, value in values}
        if len(unique) > 1:
            raise ContractError(
                f"Gate 7 closeout identity mismatch for {canonical}: {values}"
            )
        identity[canonical] = next(iter(unique), "")
    return identity


def audit_gate7_source_contract() -> dict[str, Any]:
    """Audit source-level Gate 7 completeness without claiming runtime acceptance."""

    required_rules = set(_REQUIRED_VISUAL_GATES) | {"G7.6"}
    missing_rules = sorted(required_rules.difference(VISUAL_EVIDENCE_RULES))
    if missing_rules:
        raise ContractError(f"Gate 7 source closeout is missing visual rules: {missing_rules}")

    # Imports prove the source stages are present and importable in the package.
    from . import gate7_registration  # noqa: F401
    from . import gate7_provenance  # noqa: F401
    from . import geometry_confidence  # noqa: F401
    from . import free_space_evidence  # noqa: F401
    from . import free_space_constraints  # noqa: F401
    from . import free_space_confidence  # noqa: F401
    from . import protected_fusion  # noqa: F401
    from . import gate7_visual_review  # noqa: F401
    from . import visual_comparisons  # noqa: F401

    return {
        "schema": "ConceptGhost.P10Gate7SourceCloseout.v0.1",
        "status": "PASS",
        "gate": 7,
        "source_subgates": {
            "G7.1": "IMPLEMENTED",
            "G7.2": "IMPLEMENTED",
            "G7.2C": "IMPLEMENTED",
            "G7.3": "IMPLEMENTED",
            "G7.4": "IMPLEMENTED",
            "G7.5": "IMPLEMENTED",
            "G7.6": "IMPLEMENTED",
        },
        "visual_evidence_contract": {
            "required_for_every_gate": True,
            "preview_required": True,
            "comparison_required": True,
            "terminal_branch_required": True,
            "same_camera_replay_supported": True,
            "confidence_blue_high_red_low_supported": True,
        },
        "source_contract_complete": True,
        "preview_package_ready_for_build": True,
        "preview_package_published": False,
        "runtime_gate7_accepted": False,
        "ready_for_gate8": False,
        "promotion_blockers": [
            "DR9R_R15_RUNTIME_UX_ACCEPTANCE_PENDING",
            "GATE7_PREVIEW_PACKAGE_NOT_YET_PUBLISHED",
            "GATE7_ARTIST_VISUAL_REVIEW_PENDING",
        ],
    }


def write_gate7_source_closeout(output_root: str | Path) -> dict[str, Any]:
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    result = audit_gate7_source_contract()
    path = output_root / "gate7_source_closeout.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(path)
    return result


def _open_visual_frame(path: Path, Image):
    try:
        with Image.open(path) as opened:
            opened.seek(0)
            return opened.convert("RGB").copy()
    except Exception:
        return None


def _contact_sheet(
    evidence: dict[str, dict[str, Any]],
    output_root: Path,
    *,
    Image,
    ImageDraw,
):
    tiles = []
    for gate in _REQUIRED_VISUAL_GATES:
        manifest = evidence[gate]
        candidates = [
            *(manifest.get("preview_artifacts") or []),
            *(manifest.get("comparison_artifacts") or []),
        ]
        frame = None
        source_path = None
        for item in candidates:
            source = Path(item)
            frame = _open_visual_frame(source, Image)
            if frame is not None:
                source_path = source
                break
        if frame is not None:
            tiles.append((gate, frame, source_path))

    if not tiles:
        raise ContractError("Gate 7 runtime closeout found no renderable visual-evidence artifacts")

    tile_w, tile_h = 420, 250
    columns = 2
    rows = (len(tiles) + columns - 1) // columns
    image = Image.new("RGB", (columns * tile_w + 36, rows * tile_h + 70), (15, 15, 18))
    draw = ImageDraw.Draw(image)
    draw.text((14, 12), "ConceptGhost · Gate 7 Visual Evidence Index", fill=(245,245,248))
    for index, (gate, frame, source) in enumerate(tiles):
        col, row = index % columns, index // columns
        x0 = 12 + col * tile_w
        y0 = 48 + row * tile_h
        frame.thumbnail((tile_w - 24, tile_h - 48))
        px = x0 + (tile_w - frame.width) // 2
        py = y0 + 24
        image.paste(frame, (px, py))
        draw.rectangle((x0, y0, x0 + tile_w - 8, y0 + tile_h - 8), outline=(78,78,86))
        draw.text((x0 + 8, y0 + 6), gate, fill=(240,240,244))
        draw.text((x0 + 8, y0 + tile_h - 27), source.name[:54], fill=(150,150,158))
    path = output_root / "gate7_visual_evidence_index.png"
    image.save(path)
    return path


def _input_output_summary(
    evidence: dict[str, dict[str, Any]],
    visual_review: dict[str, Any],
    output_root: Path,
    *,
    Image,
    ImageDraw,
):
    left = None
    left_source = None
    # Prefer the G7.4 BEFORE/AFTER artifact because it directly answers whether
    # protected fusion changed the problem region under identical views/cameras.
    for gate in ("G7.4", "G7.3", "G7.2C"):
        manifest = evidence.get(gate) or {}
        for item in manifest.get("comparison_artifacts") or []:
            frame = _open_visual_frame(Path(item), Image)
            if frame is not None:
                left = frame
                left_source = Path(item)
                break
        if left is not None:
            break

    right_path = Path(str(visual_review.get("preview_png_path") or ""))
    right = _open_visual_frame(right_path, Image) if right_path.is_file() else None
    if left is None or right is None:
        raise ContractError(
            "Gate 7 closeout comparison requires a renderable earlier comparison and G7.5 review"
        )

    panel_w, panel_h = 720, 440
    image = Image.new("RGB", (panel_w * 2 + 28, panel_h + 70), (15,15,18))
    draw = ImageDraw.Draw(image)
    draw.text((14, 12), "Gate 7 INPUT / OUTPUT Visual Summary", fill=(245,245,248))
    for frame, x0, title in (
        (left, 10, "EARLIER / BEFORE-AFTER EVIDENCE"),
        (right, panel_w + 18, "G7.5 PROTECTED RESULT REVIEW"),
    ):
        frame.thumbnail((panel_w - 20, panel_h - 46))
        px = x0 + (panel_w - frame.width) // 2
        py = 54 + (panel_h - 46 - frame.height) // 2
        image.paste(frame, (px, py))
        draw.rectangle((x0, 44, x0 + panel_w - 2, 44 + panel_h), outline=(80,80,88))
        draw.text((x0 + 8, 50), title, fill=(235,235,240))
    path = output_root / "gate7_input_output_summary.png"
    image.save(path)
    return path, left_source, right_path


def build_gate7_runtime_closeout(
    registration_manifest_path: str | Path,
    provenance_manifest_path: str | Path,
    confidence_manifest_path: str | Path,
    free_space_constraints_manifest_path: str | Path,
    protected_fusion_manifest_path: str | Path,
    visual_review_manifest_path: str | Path,
    visual_evidence_manifest_paths: list[str | Path],
    output_root: str | Path,
    *,
    dr9r_runtime_accepted: bool = False,
    artist_visual_review_approved: bool = False,
) -> dict[str, Any]:
    """Validate the complete runtime Gate 7 chain and render G7.6 evidence.

    The function can close the source/runtime evidence chain while still
    refusing Gate 8 promotion until both explicit human/runtime approvals exist.
    """

    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise ContractError("Gate 7 closeout visual index requires Pillow") from error

    registration = _read_json(registration_manifest_path, "G7.1 registration")
    provenance = _read_json(provenance_manifest_path, "G7.2 provenance")
    confidence = _read_json(confidence_manifest_path, "G7.2C confidence")
    free_space = _read_json(free_space_constraints_manifest_path, "G7.3 free-space constraints")
    fusion = _read_json(protected_fusion_manifest_path, "G7.4 protected fusion")
    review = _read_json(visual_review_manifest_path, "G7.5 visual review")

    expected_schemas = (
        (registration, "ConceptGhost.P10Gate7Registration.v0.1", "G7.1"),
        (provenance, "ConceptGhost.P10Gate7Provenance.v0.1", "G7.2"),
        (confidence, "ConceptGhost.P10Gate7GeometryConfidence.v0.1", "G7.2C"),
        (free_space, "ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1", "G7.3"),
        (fusion, "ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1", "G7.4"),
        (review, "ConceptGhost.P10Gate7VisualReview.v0.1", "G7.5"),
    )
    for payload, schema, label in expected_schemas:
        if payload.get("schema") != schema or payload.get("status") != "PASS":
            raise ContractError(f"{label} closeout schema/status mismatch")

    identity = _same_identity([
        ("G7.1", registration),
        ("G7.2", provenance),
        ("G7.2C", confidence),
        ("G7.3", free_space),
        ("G7.4", fusion),
        ("G7.5", review),
    ])
    if not all(identity.values()):
        raise ContractError("Gate 7 closeout requires complete scene/P9/attempt identity")

    if registration.get("registration_policy") != "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION":
        raise ContractError("Gate 7 closeout requires identity registration authority")
    if float(registration.get("scale", 0.0)) != 1.0 or registration.get("sim3_refit_allowed") is not False:
        raise ContractError("Gate 7 closeout forbids scale change or Sim(3)")
    if registration.get("p9_authority_changed") is not False:
        raise ContractError("Gate 7 closeout detected changed P9 authority")
    if provenance.get("official_geometry_changed") is not False:
        raise ContractError("G7.2 unexpectedly changed official geometry")
    if confidence.get("geometry_confidence_refine") is not False:
        raise ContractError("Gate 7 closeout requires confidence refinement OFF")
    if confidence.get("official_geometry_changed") is not False:
        raise ContractError("G7.2C unexpectedly changed official geometry")
    if free_space.get("official_geometry_changed") is not False:
        raise ContractError("G7.3 unexpectedly changed official geometry")
    if fusion.get("candidate_is_official_geometry") is not False:
        raise ContractError("Gate 7.4 candidate was incorrectly marked official")
    if fusion.get("official_geometry_changed") is not False:
        raise ContractError("G7.4 unexpectedly changed official geometry")
    p9_policy = fusion.get("p9_policy") if isinstance(fusion.get("p9_policy"), dict) else {}
    if p9_policy.get("all_p9_faces_copied_unchanged") is not True:
        raise ContractError("Gate 7 closeout requires all P9 faces copied unchanged")
    if int(p9_policy.get("p9_faces_removed", -1)) != 0 or int(p9_policy.get("p9_vertices_moved", -1)) != 0:
        raise ContractError("Gate 7 closeout detected P9 geometry mutation")
    if review.get("candidate_is_official_geometry") is not False or review.get("official_geometry_changed") is not False:
        raise ContractError("G7.5 review must remain non-promoting")

    evidence_by_gate: dict[str, dict[str, Any]] = {}
    for item in visual_evidence_manifest_paths:
        value = validate_visual_evidence_manifest(item)
        gate = str(value.get("gate_id") or "").upper()
        if gate in evidence_by_gate:
            raise ContractError(f"Duplicate visual evidence manifest for {gate}")
        evidence_by_gate[gate] = value
    missing_visual = [gate for gate in _REQUIRED_VISUAL_GATES if gate not in evidence_by_gate]
    if missing_visual:
        raise ContractError(f"Gate 7 closeout is missing visual evidence for {missing_visual}")

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = _contact_sheet(
        evidence_by_gate,
        output_root,
        Image=Image,
        ImageDraw=ImageDraw,
    )
    summary_path, summary_before, summary_after = _input_output_summary(
        evidence_by_gate,
        review,
        output_root,
        Image=Image,
        ImageDraw=ImageDraw,
    )

    blockers = []
    if not dr9r_runtime_accepted:
        blockers.append("DR9R_R15_RUNTIME_UX_ACCEPTANCE_PENDING")
    if not artist_visual_review_approved:
        blockers.append("GATE7_ARTIST_VISUAL_REVIEW_PENDING")
    accepted = not blockers

    result = {
        "schema": _SCHEMA,
        "status": "PASS",
        "gate": 7,
        "subgate": "7.6",
        **identity,
        "source_contract_complete": True,
        "runtime_evidence_chain_complete": True,
        "visual_evidence_complete": True,
        "visual_evidence_gates": list(_REQUIRED_VISUAL_GATES),
        "visual_evidence_index_png_path": str(index_path),
        "input_output_summary_png_path": str(summary_path),
        "input_output_summary_before_source": str(summary_before),
        "input_output_summary_after_source": str(summary_after),
        "immutability": {
            "p9_authority_changed": False,
            "p9_faces_removed": 0,
            "p9_vertices_moved": 0,
            "sim3_refit": False,
            "scale_changed": False,
        },
        "promotion": {
            "dr9r_runtime_accepted": bool(dr9r_runtime_accepted),
            "artist_visual_review_approved": bool(artist_visual_review_approved),
            "gate7_accepted": accepted,
            "ready_for_gate8": accepted,
            "blockers": blockers,
        },
        "official_geometry_changed_by_closeout": False,
        "g7_6_visual_branch_terminal": True,
    }
    manifest_path = output_root / "gate7_closeout_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["manifest_path"] = str(manifest_path)
    return result
