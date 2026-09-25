from __future__ import annotations

import json
from pathlib import Path


def _image_file_to_tensor(path: Path):
    try:
        import numpy as np
        import torch
        from PIL import Image
    except ImportError as error:
        raise RuntimeError(
            "Gate 6 visual preview requires NumPy, Pillow and Torch from ComfyUI"
        ) from error
    with Image.open(path) as opened:
        arr=np.asarray(opened.convert("RGB"),dtype=np.float32)/255.0
    return torch.from_numpy(arr).unsqueeze(0)


def _render_mesh_preview_png(mesh_path: Path, png_path: Path):
    """Legacy/fallback mesh-only preview with one metric scale per panel."""

    try:
        import numpy as np
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError(
            "Gate 6 visual preview requires NumPy and Pillow from ComfyUI"
        ) from error

    from .prefusion_mesh import _read_mesh, _vertex

    _header, vertices, sampled_faces, _invalid = _read_mesh(mesh_path, 9000)
    if not sampled_faces:
        raise RuntimeError("Pre-fusion mesh has no sampled faces for preview")

    points=np.asarray(
        [_vertex(vertices,index) for face in sampled_faces for index in face],
        dtype=np.float64,
    )
    lo=np.min(points,axis=0)
    hi=np.max(points,axis=0)
    span=np.maximum(hi-lo,1.0e-9)
    lo=lo-span*0.04
    hi=hi+span*0.04

    panel=420
    gap=16
    top=72
    pad=28
    usable=panel-2*pad
    width=panel*3+gap*4
    height=panel+top+gap
    image=Image.new("RGB",(width,height),(13,13,13))
    draw=ImageDraw.Draw(image)
    draw.text(
        (14,14),
        "ConceptGhost Gate 6.6 - pre-fusion mesh-only fallback preview",
        fill=(245,245,245),
    )
    draw.text(
        (14,36),
        "Metric-isotropic panels; preferred preview is the P9/P10 overlay.",
        fill=(165,165,165),
    )

    specs=((0,2,"TOP XZ"),(0,1,"FRONT XY"),(2,1,"SIDE ZY"))
    for panel_index,(a,b,label) in enumerate(specs):
        x0=gap+panel_index*(panel+gap)
        y0=top
        draw.rectangle(
            (x0,y0,x0+panel,y0+panel),
            outline=(90,90,90),
            fill=(22,22,22),
        )
        draw.text((x0+10,y0+8),label,fill=(235,235,235))

        span_a=max(float(hi[a]-lo[a]),1.0e-9)
        span_b=max(float(hi[b]-lo[b]),1.0e-9)
        ppm=min(usable/span_a,usable/span_b)
        display_a=usable/ppm
        display_b=usable/ppm
        center_a=float((lo[a]+hi[a])*0.5)
        center_b=float((lo[b]+hi[b])*0.5)
        alo,ahi=center_a-display_a*0.5,center_a+display_a*0.5
        blo,bhi=center_b-display_b*0.5,center_b+display_b*0.5
        draw.text((x0+10,y0+25),f"{ppm:.2f} px/m",fill=(145,145,145))

        def project(p):
            px=x0+pad+(p[a]-alo)/(ahi-alo)*usable
            py=y0+panel-pad-(p[b]-blo)/(bhi-blo)*usable
            return (px,py)

        for face in sampled_faces:
            pts=[project(_vertex(vertices,index)) for index in face]
            draw.line(
                [pts[0],pts[1],pts[2],pts[0]],
                fill=(155,203,255),
                width=1,
            )

    png_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(png_path)
    return _image_file_to_tensor(png_path)


class ConceptGhostP10ReconstructionRuntime:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "wan_manifest_path":("STRING",{"forceInput":True}),
                "camera_manifest_path":("STRING",{"forceInput":True}),
                "resume_existing":("BOOLEAN",{"default":True}),
                "colmap_executable":("STRING",{"default":""}),
            }
        }

    RETURN_TYPES=("IMAGE","STRING","STRING","STRING","STRING")
    RETURN_NAMES=(
        "mesh_preview",
        "pre_fusion_mesh",
        "gate6_output_root",
        "runtime_manifest_path",
        "diagnostics_json",
    )
    FUNCTION="reconstruct"
    CATEGORY="ConceptGhost/P10 Refined"
    OUTPUT_NODE=True

    def reconstruct(
        self,
        wan_manifest_path,
        camera_manifest_path,
        resume_existing,
        colmap_executable,
    ):
        import folder_paths
        from .reconstruction_runtime import run_reconstruction_pipeline

        wan_path=Path(wan_manifest_path)
        try:
            wan=json.loads(wan_path.read_text(encoding="utf-8"))
        except Exception as error:
            raise RuntimeError(f"Cannot read WAN manifest: {wan_path}: {error}") from error
        run_id=str(wan.get("run_id") or "").strip()
        if not run_id:
            raise RuntimeError("WAN manifest is missing run_id")

        attempt_root_value=str(wan.get("p10_attempt_root") or "").strip()
        if attempt_root_value:
            comfy_output=Path(folder_paths.get_output_directory()).resolve()
            attempt_root=Path(attempt_root_value).resolve()
            try:
                attempt_root.relative_to(comfy_output)
            except ValueError as error:
                raise RuntimeError("WAN manifest p10_attempt_root is outside ComfyUI output") from error
            output_root=attempt_root/"gate6"
        else:
            output_root=(
                Path(folder_paths.get_output_directory())
                /"conceptghost"/"p10_gate6"/run_id
            )
        diagnostics=run_reconstruction_pipeline(
            wan_manifest_path,
            camera_manifest_path,
            output_root,
            colmap_executable=colmap_executable or None,
            resume=bool(resume_existing),
        )
        mesh_path=Path(
            str(
                diagnostics.get("gate6_raw_p10_geometry_path")
                or diagnostics["pre_fusion_mesh_path"]
            )
        )
        overlay_value=str(diagnostics.get("metric_overlay_preview_png_path") or "").strip()
        overlay_path=Path(overlay_value) if overlay_value else None
        if overlay_path is not None and overlay_path.is_file():
            preview=_image_file_to_tensor(overlay_path)
            diagnostics["mesh_preview_png_path"]=str(overlay_path.resolve())
            diagnostics["mesh_preview_kind"]="METRIC_P9_P10_RECONSTRUCTION_OVERLAY"
        else:
            png_path=mesh_path.parent/"pre_fusion_mesh_preview.png"
            preview=_render_mesh_preview_png(mesh_path,png_path)
            diagnostics["mesh_preview_png_path"]=str(png_path.resolve())
            diagnostics["mesh_preview_kind"]="METRIC_ISOTROPIC_MESH_ONLY_FALLBACK"
        rendered=json.dumps(diagnostics,indent=2,sort_keys=True)
        return {
            "ui":{"text":[rendered]},
            "result":(
                preview,
                str(mesh_path),
                str(output_root),
                str(diagnostics["runtime_manifest_path"]),
                rendered,
            ),
        }
