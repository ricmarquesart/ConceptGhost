from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .free_space_constraints import FreeSpaceState
from .gate7_closeout import build_gate7_runtime_closeout
from .gate7_provenance import Gate7ProvenanceClass
from .gate7_visual_review import _read_candidate_ascii
from .visual_comparisons import (
    render_confidence_before_after,
    render_drone_mesh_before_after_replay,
)
from .visual_evidence_contract import build_visual_evidence_manifest


_SCHEMA = "ConceptGhost.P10Gate7VisualEvidencePack.v0.1"


_PROVENANCE_COLORS = {
    int(Gate7ProvenanceClass.P9_SOURCE_PROTECTED): (65, 125, 255),
    int(Gate7ProvenanceClass.P9_RETAINED): (120, 160, 210),
    int(Gate7ProvenanceClass.P10_MULTIVIEW_SUPPORTED): (75, 215, 120),
    int(Gate7ProvenanceClass.P10_GENERATED_ONLY): (235, 175, 70),
    int(Gate7ProvenanceClass.UNKNOWN): (145, 145, 150),
    int(Gate7ProvenanceClass.CONFLICT): (225, 70, 220),
}


def _runtime():
    try:
        import numpy as np
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise ContractError("Gate 7 visual evidence pack requires NumPy and Pillow") from error
    return np, Image, ImageDraw


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def _axis_pair(points, np):
    spans = np.ptp(points, axis=0)
    pairs = ((0,1,"X/Y"),(0,2,"X/Z"),(2,1,"Z/Y"))
    return max(pairs, key=lambda pair: float(spans[pair[0]] * spans[pair[1]]))


def _bounds_for(point_sets, np):
    valid = [np.asarray(points, dtype=np.float64) for points in point_sets if len(points)]
    if not valid:
        raise ContractError("Visual evidence requires non-empty point sets")
    combined = np.concatenate(valid, axis=0)
    lo = np.min(combined, axis=0)
    hi = np.max(combined, axis=0)
    center = (lo + hi) * 0.5
    span = np.maximum(hi - lo, 1e-7)
    return combined, center, span


def _projector(point_sets, rect, np):
    combined, center, span = _bounds_for(point_sets, np)
    ax, ay, label = _axis_pair(combined, np)
    x0,y0,w,h = rect
    margin = 32
    usable_w = max(1,w-2*margin)
    usable_h = max(1,h-2*margin)
    scale = min(usable_w/float(span[ax]), usable_h/float(span[ay]))
    def project(point):
        x = x0 + w*0.5 + (float(point[ax])-float(center[ax]))*scale
        y = y0 + h*0.5 - (float(point[ay])-float(center[ay]))*scale
        return x,y
    return project,label


def _sample(values, max_count, np):
    count=len(values)
    if count<=max_count:
        return np.arange(count,dtype=np.int64)
    stride=max(1,math.ceil(count/max_count))
    return np.arange(0,count,stride,dtype=np.int64)[:max_count]


def _draw_points(draw, points, colors, project, np, *, max_points=30000, radius=1):
    idx=_sample(points,max_points,np)
    for i in idx:
        x,y=project(points[int(i)])
        color=colors[int(i)] if hasattr(colors,"__len__") and len(colors)==len(points) else colors
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=tuple(int(v) for v in color))


def _save_pair(
    left_points,
    left_colors,
    right_points,
    right_colors,
    output_path: Path,
    *,
    left_title: str,
    right_title: str,
    header: str,
    np,
    Image,
    ImageDraw,
    panel_size=560,
):
    width=panel_size*2+36
    height=panel_size+76
    image=Image.new("RGB",(width,height),(16,16,19))
    draw=ImageDraw.Draw(image)
    draw.text((14,12),header,fill=(245,245,248))
    rects=[(10,46,panel_size,panel_size),(26+panel_size,46,panel_size,panel_size)]
    project,label=_projector([left_points,right_points],rects[0],np)
    # Both panels must use the exact same center/scale; derive a second projector
    # with the same combined bounds but shifted panel coordinates.
    combined,center,span=_bounds_for([left_points,right_points],np)
    ax,ay,_=_axis_pair(combined,np)
    margin=32
    scale=min((panel_size-2*margin)/float(span[ax]),(panel_size-2*margin)/float(span[ay]))
    def make_project(rect):
        x0,y0,w,h=rect
        def p(point):
            return (
                x0+w*0.5+(float(point[ax])-float(center[ax]))*scale,
                y0+h*0.5-(float(point[ay])-float(center[ay]))*scale,
            )
        return p
    for rect,title,pts,colors in (
        (rects[0],left_title,left_points,left_colors),
        (rects[1],right_title,right_points,right_colors),
    ):
        x0,y0,w,h=rect
        draw.rectangle((x0,y0,x0+w,y0+h),fill=(22,22,25),outline=(80,80,88))
        draw.text((x0+9,y0+8),title,fill=(235,235,240))
        _draw_points(draw,pts,colors,make_project(rect),np)
        draw.text((x0+9,y0+h-19),f"same metric projection {label}",fill=(150,150,158))
    output_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(output_path)
    return output_path


def _save_overlay(
    point_sets,
    colors,
    output_path: Path,
    *,
    title: str,
    labels: list[tuple[str, tuple[int,int,int]]] | None,
    np,
    Image,
    ImageDraw,
    panel_size=720,
):
    image=Image.new("RGB",(panel_size,panel_size+68),(16,16,19))
    draw=ImageDraw.Draw(image)
    draw.text((14,12),title,fill=(245,245,248))
    rect=(10,44,panel_size-20,panel_size-20)
    draw.rectangle((10,44,panel_size-10,panel_size+24),fill=(22,22,25),outline=(80,80,88))
    project,label=_projector(point_sets,rect,np)
    for pts,cols in zip(point_sets,colors):
        _draw_points(draw,pts,cols,project,np)
    draw.text((18,panel_size+6),f"metric-isotropic {label}",fill=(150,150,158))
    if labels:
        x=18
        y=28
        for name,color in labels:
            draw.rectangle((x,y,x+8,y+8),fill=color)
            draw.text((x+12,y-2),name,fill=(225,225,230))
            x += max(80,18+len(name)*7)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(output_path)
    return output_path


def _confidence_colors(scores):
    result=[]
    for score in scores:
        value=max(0.0,min(1.0,float(score)))
        result.append((
            int(round(235*(1-value)+35*value)),
            int(round(55+75*(1-abs(value-0.5)*2))),
            int(round(45*(1-value)+240*value)),
        ))
    return result


def build_gate7_visual_evidence_pack(
    gate7_runtime_manifest_path: str | Path,
    output_root: str | Path,
    *,
    dr9r_runtime_accepted: bool = False,
    artist_visual_review_approved: bool = False,
) -> dict[str, Any]:
    """Generate terminal per-gate visual branches and G7.6 review evidence."""

    np,Image,ImageDraw=_runtime()
    runtime_path=Path(gate7_runtime_manifest_path).resolve()
    runtime=_read_json(runtime_path,"Gate 7 runtime manifest")
    if runtime.get("schema")!="ConceptGhost.P10Gate7Runtime.v0.1" or runtime.get("status")!="PASS":
        raise ContractError("Visual pack requires Gate 7 runtime schema/status PASS")
    if runtime.get("ready_for_visual_evidence_pack") is not True:
        raise ContractError("Gate 7 runtime did not promote to visual evidence pack")
    artifacts=runtime.get("artifacts")
    if not isinstance(artifacts,dict):
        raise ContractError("Gate 7 runtime manifest is missing artifacts")

    registration=_read_json(artifacts["registration_manifest_path"],"G7.1 registration")
    provenance=_read_json(artifacts["provenance_manifest_path"],"G7.2 provenance")
    confidence=_read_json(artifacts["confidence_manifest_path"],"G7.2C confidence")
    constraints=_read_json(artifacts["free_space_constraints_manifest_path"],"G7.3 constraints")
    overlay=_read_json(artifacts["confidence_free_space_overlay_manifest_path"],"G7.3 confidence overlay")
    fusion=_read_json(artifacts["protected_fusion_manifest_path"],"G7.4 fusion")
    review=_read_json(artifacts["visual_review_manifest_path"],"G7.5 review")

    root=Path(output_root).resolve()
    root.mkdir(parents=True,exist_ok=True)

    prov_npz=Path(str(provenance.get("evidence_npz_path") or "")).resolve()
    with np.load(prov_npz,allow_pickle=False) as payload:
        p9_points=np.asarray(payload["p9_points"],dtype=np.float64)
        p9_labels=np.asarray(payload["p9_labels"],dtype=np.uint8)
        p10_points=np.asarray(payload["p10_points"],dtype=np.float64)
        p10_labels=np.asarray(payload["p10_labels"],dtype=np.uint8)

    neutral_p9=[(120,160,210)]*len(p9_points)
    neutral_p10=[(110,205,125)]*len(p10_points)
    prov_p9=[_PROVENANCE_COLORS.get(int(v),(145,145,150)) for v in p9_labels]
    prov_p10=[_PROVENANCE_COLORS.get(int(v),(145,145,150)) for v in p10_labels]

    # G7.1 registration: same metric projection makes displacement obvious.
    g71=root/"g7_1"
    reg_preview=_save_overlay(
        [p9_points,p10_points],
        [neutral_p9,neutral_p10],
        g71/"registration_overlay.png",
        title="G7.1 · P9 / REGISTERED P10 OVERLAY",
        labels=[("P9",(120,160,210)),("P10",(110,205,125))],
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    reg_compare=_save_pair(
        p9_points,neutral_p9,p10_points,neutral_p10,
        g71/"registration_reference_result.png",
        left_title="REFERENCE · P9",right_title="RESULT · REGISTERED P10",
        header="G7.1 Registration Comparison",
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    g71_manifest=build_visual_evidence_manifest(
        "G7.1",g71/"manifest",
        preview_artifacts=[reg_preview],
        comparison_artifacts=[reg_compare],
        diagnostics_artifacts=[Path(artifacts["registration_manifest_path"])],
        metadata={"same_coordinate_space":True,"registration_policy":registration.get("registration_policy")},
    )

    # G7.2 provenance.
    g72=root/"g7_2"
    prov_preview=_save_overlay(
        [p9_points,p10_points],
        [prov_p9,prov_p10],
        g72/"provenance_overlay.png",
        title="G7.2 · GEOMETRY PROVENANCE",
        labels=[
            ("P9 PROTECTED",_PROVENANCE_COLORS[1]),
            ("P9 RETAINED",_PROVENANCE_COLORS[2]),
            ("P10 MULTIVIEW",_PROVENANCE_COLORS[3]),
            ("GENERATED",_PROVENANCE_COLORS[4]),
            ("CONFLICT",_PROVENANCE_COLORS[6]),
        ],
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    prov_compare=_save_pair(
        p10_points,[(150,150,155)]*len(p10_points),
        p10_points,prov_p10,
        g72/"provenance_raw_vs_classified.png",
        left_title="BEFORE · RAW P10",right_title="AFTER · PROVENANCE CLASSES",
        header="G7.2 Provenance Classification Comparison",
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    g72_manifest=build_visual_evidence_manifest(
        "G7.2",g72/"manifest",
        preview_artifacts=[prov_preview],
        comparison_artifacts=[prov_compare],
        diagnostics_artifacts=[Path(artifacts["provenance_manifest_path"])],
        metadata={"official_geometry_changed":False},
    )

    # G7.2C confidence + G7.3D comparison.
    conf_npz=Path(str(confidence.get("evidence_npz_path") or "")).resolve()
    with np.load(conf_npz,allow_pickle=False) as payload:
        conf_points=np.asarray(payload["p10_points"],dtype=np.float64)
        conf_scores=np.asarray(payload["p10_confidence"],dtype=np.float64)
    g72c=root/"g7_2c"
    conf_preview=_save_overlay(
        [conf_points],[_confidence_colors(conf_scores)],
        g72c/"confidence_blue_high_red_low.png",
        title="G7.2C · CONFIDENCE · BLUE HIGH / RED LOW",
        labels=[("LOW",(235,55,45)),("HIGH",(35,55,240))],
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    conf_compare_result=render_confidence_before_after(
        artifacts["confidence_manifest_path"],
        artifacts["confidence_free_space_overlay_manifest_path"],
        g72c/"comparison",
        panel_size=480,
    )
    g72c_manifest=build_visual_evidence_manifest(
        "G7.2C",g72c/"manifest",
        preview_artifacts=[conf_preview],
        comparison_artifacts=[Path(conf_compare_result["comparison_png_path"])],
        diagnostics_artifacts=[
            Path(artifacts["confidence_manifest_path"]),
            Path(artifacts["confidence_free_space_overlay_manifest_path"]),
        ],
        metadata={"high_confidence_color":"BLUE","low_confidence_color":"RED"},
    )

    # G7.3 free-space.
    constraints_npz=Path(str(constraints.get("constraints_npz_path") or "")).resolve()
    with np.load(constraints_npz,allow_pickle=False) as payload:
        free_points=np.asarray(payload["voxel_centers"],dtype=np.float64)
        states=np.asarray(payload["state"],dtype=np.uint8)
        free_votes=np.asarray(payload["free_effective_votes"],dtype=np.float64)
        occupied_votes=np.asarray(payload["occupied_effective_votes"],dtype=np.float64)
    state_color={
        int(FreeSpaceState.UNKNOWN):(110,110,115),
        int(FreeSpaceState.OCCUPIED):(230,230,230),
        int(FreeSpaceState.CONFIRMED_FREE):(40,220,210),
        int(FreeSpaceState.CONFLICT):(225,70,220),
    }
    classified_colors=[state_color[int(v)] for v in states]
    ratio=free_votes/np.maximum(free_votes+occupied_votes,1.0)
    raw_colors=_confidence_colors(ratio)
    g73=root/"g7_3"
    free_preview=_save_overlay(
        [free_points],[classified_colors],
        g73/"free_space_states.png",
        title="G7.3 · FREE-SPACE STATES",
        labels=[
            ("OCCUPIED",state_color[int(FreeSpaceState.OCCUPIED)]),
            ("CONFIRMED_FREE",state_color[int(FreeSpaceState.CONFIRMED_FREE)]),
            ("UNKNOWN",state_color[int(FreeSpaceState.UNKNOWN)]),
            ("CONFLICT",state_color[int(FreeSpaceState.CONFLICT)]),
        ],
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    free_compare=_save_pair(
        free_points,raw_colors,free_points,classified_colors,
        g73/"free_space_raw_vs_classified.png",
        left_title="BEFORE · RAW FREE/OCCUPIED VOTE RATIO",
        right_title="AFTER · NO-FILL CLASSIFICATION",
        header="G7.3 Free-Space Evidence Comparison",
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    g73_manifest=build_visual_evidence_manifest(
        "G7.3",g73/"manifest",
        preview_artifacts=[free_preview],
        comparison_artifacts=[free_compare],
        diagnostics_artifacts=[Path(artifacts["free_space_constraints_manifest_path"])],
        metadata={"confirmed_free":"NO_FILL_NO_BRIDGE","unknown":"NO_AUTOMATIC_ACTION"},
    )

    # G7.4 protected fusion candidate.
    candidate_path=Path(str(fusion.get("candidate_ply_path") or "")).resolve()
    (
        candidate_vertices,_candidate_faces,vertex_layer,vertex_provenance,
        _vertex_confidence,_face_layer,_face_provenance,
    )=_read_candidate_ascii(candidate_path,np)
    candidate_colors=[]
    for layer,prov in zip(vertex_layer,vertex_provenance):
        if int(layer)==1:
            candidate_colors.append(_PROVENANCE_COLORS.get(int(prov),(120,160,210)))
        else:
            candidate_colors.append((75,215,120))
    g74=root/"g7_4"
    fusion_preview=_save_overlay(
        [candidate_vertices],[candidate_colors],
        g74/"protected_fusion_candidate.png",
        title="G7.4 · PROTECTED FUSION CANDIDATE · P9 + ACCEPTED P10",
        labels=[("P9",(120,160,210)),("P10 ACCEPTED",(75,215,120))],
        np=np,Image=Image,ImageDraw=ImageDraw,
    )
    dataset_manifest_path=Path(str(registration.get("dataset_manifest_path") or "")).resolve()
    replay=render_drone_mesh_before_after_replay(
        dataset_manifest_path,
        registration["pre_fusion_mesh_path"],
        fusion["candidate_ply_path"],
        g74/"drone_replay",
        before_label="BEFORE · PRE-FUSION",
        after_label="AFTER · PROTECTED FUSION",
    )
    g74_manifest=build_visual_evidence_manifest(
        "G7.4",g74/"manifest",
        preview_artifacts=[fusion_preview],
        comparison_artifacts=[Path(replay["comparison_gif_path"])],
        diagnostics_artifacts=[Path(artifacts["protected_fusion_manifest_path"])],
        metadata={
            "same_camera_replay":True,
            "before_mesh":registration["pre_fusion_mesh_path"],
            "after_mesh":fusion["candidate_ply_path"],
        },
    )

    # G7.5 consolidated human-review comparison.
    g75=root/"g7_5"
    review_png=Path(str(review.get("preview_png_path") or "")).resolve()
    if not review_png.is_file():
        raise ContractError("G7.5 review PNG is missing")
    previews=[reg_preview,prov_preview,conf_preview,free_preview,fusion_preview]
    thumbs=[]
    for path in previews:
        with Image.open(path) as opened:
            img=opened.convert("RGB")
            img.thumbnail((300,190))
            thumbs.append(img.copy())
    sheet=Image.new("RGB",(950,470),(15,15,18))
    draw=ImageDraw.Draw(sheet)
    draw.text((12,10),"G7.5 · EVIDENCE SUMMARY BEFORE ARTIST REVIEW",fill=(245,245,248))
    for idx,img in enumerate(thumbs):
        col=idx%3;row=idx//3
        x=10+col*310;y=38+row*210
        sheet.paste(img,(x,y))
        draw.rectangle((x,y,x+300,y+190),outline=(75,75,82))
        draw.text((x+6,y+172),["G7.1","G7.2","G7.2C","G7.3","G7.4"][idx],fill=(230,230,235))
    evidence_summary=g75/"gate7_evidence_summary.png"
    g75.mkdir(parents=True,exist_ok=True)
    sheet.save(evidence_summary)
    g75_manifest=build_visual_evidence_manifest(
        "G7.5",g75/"manifest",
        preview_artifacts=[review_png],
        comparison_artifacts=[evidence_summary],
        diagnostics_artifacts=[Path(artifacts["visual_review_manifest_path"])],
        metadata={"artist_review_status":"PENDING"},
    )

    evidence_manifests=[
        g71_manifest["manifest_path"],g72_manifest["manifest_path"],
        g72c_manifest["manifest_path"],g73_manifest["manifest_path"],
        g74_manifest["manifest_path"],g75_manifest["manifest_path"],
    ]
    closeout=build_gate7_runtime_closeout(
        artifacts["registration_manifest_path"],
        artifacts["provenance_manifest_path"],
        artifacts["confidence_manifest_path"],
        artifacts["free_space_constraints_manifest_path"],
        artifacts["protected_fusion_manifest_path"],
        artifacts["visual_review_manifest_path"],
        evidence_manifests,
        root/"g7_6",
        dr9r_runtime_accepted=bool(dr9r_runtime_accepted),
        artist_visual_review_approved=bool(artist_visual_review_approved),
    )
    g76_manifest=build_visual_evidence_manifest(
        "G7.6",root/"g7_6"/"visual_manifest",
        preview_artifacts=[Path(closeout["visual_evidence_index_png_path"])],
        comparison_artifacts=[Path(closeout["input_output_summary_png_path"])],
        diagnostics_artifacts=[Path(closeout["manifest_path"])],
        metadata={"gate7_accepted":closeout["promotion"]["gate7_accepted"]},
    )

    result={
        "schema":_SCHEMA,
        "status":"PASS",
        "scene_contract_id":runtime.get("scene_contract_id"),
        "p9_run_id":runtime.get("p9_run_id"),
        "p10_attempt_id":runtime.get("p10_attempt_id"),
        "gate7_runtime_manifest_path":str(runtime_path),
        "visual_root":str(root),
        "visual_evidence_manifests":{
            "G7.1":g71_manifest["manifest_path"],
            "G7.2":g72_manifest["manifest_path"],
            "G7.2C":g72c_manifest["manifest_path"],
            "G7.3":g73_manifest["manifest_path"],
            "G7.4":g74_manifest["manifest_path"],
            "G7.5":g75_manifest["manifest_path"],
            "G7.6":g76_manifest["manifest_path"],
        },
        "key_outputs":{
            "confidence_preview_png":str(conf_preview),
            "confidence_before_after_png":conf_compare_result["comparison_png_path"],
            "drone_replay_before_gif":replay["before_gif_path"],
            "drone_replay_after_gif":replay["after_gif_path"],
            "drone_replay_comparison_gif":replay["comparison_gif_path"],
            "gate7_review_png":str(review_png),
            "gate7_visual_evidence_index_png":closeout["visual_evidence_index_png_path"],
            "gate7_input_output_summary_png":closeout["input_output_summary_png_path"],
        },
        "promotion":closeout["promotion"],
        "terminal_visual_branch":True,
        "feeds_geometry_pipeline":False,
        "official_geometry_changed":False,
        "p9_authority_changed":False,
    }
    manifest=root/"gate7_visual_evidence_pack.json"
    manifest.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    result["manifest_path"]=str(manifest)
    return result
