from __future__ import annotations

import json
from pathlib import Path


def _render_mesh_preview_png(mesh_path: Path, png_path: Path):
    try:
        import numpy as np
        import torch
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError("Gate 6 visual preview requires NumPy, Pillow and Torch from ComfyUI") from error

    from .prefusion_mesh import _read_mesh, _vertex

    _header, vertices, sampled_faces, _invalid = _read_mesh(mesh_path, 9000)
    if not sampled_faces:
        raise RuntimeError("Pre-fusion mesh has no sampled faces for preview")

    points=[_vertex(vertices,i) for face in sampled_faces for i in face]
    bounds=[]
    for axis in range(3):
        values=[p[axis] for p in points]
        lo=min(values); hi=max(values)
        if abs(hi-lo)<1e-9:
            lo-=0.5; hi+=0.5
        bounds.append((lo,hi))

    panel=420
    gap=16
    top=52
    width=panel*3+gap*4
    height=panel+top+gap
    image=Image.new("RGB",(width,height),(13,13,13))
    draw=ImageDraw.Draw(image)
    draw.text((14,14),"ConceptGhost Gate 6.6 - pre-fusion reconstruction preview",fill=(245,245,245))

    specs=((0,2,"TOP XZ"),(0,1,"FRONT XY"),(2,1,"SIDE ZY"))
    for panel_index,(a,b,label) in enumerate(specs):
        x0=gap+panel_index*(panel+gap)
        y0=top
        draw.rectangle((x0,y0,x0+panel,y0+panel),outline=(90,90,90),fill=(22,22,22))
        draw.text((x0+10,y0+8),label,fill=(235,235,235))
        pad=28
        usable=panel-2*pad
        alo,ahi=bounds[a]
        blo,bhi=bounds[b]
        def project(p):
            px=x0+pad+(p[a]-alo)/(ahi-alo)*usable
            py=y0+panel-pad-(p[b]-blo)/(bhi-blo)*usable
            return (px,py)
        for face in sampled_faces:
            pts=[project(_vertex(vertices,index)) for index in face]
            draw.line([pts[0],pts[1],pts[2],pts[0]],fill=(155,203,255),width=1)

    png_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(png_path)

    arr=np.asarray(image,dtype=np.float32)/255.0
    tensor=torch.from_numpy(arr).unsqueeze(0)
    return tensor


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
        mesh_path=Path(diagnostics["pre_fusion_mesh_path"])
        png_path=mesh_path.parent/"pre_fusion_mesh_preview.png"
        preview=_render_mesh_preview_png(mesh_path,png_path)
        diagnostics["mesh_preview_png_path"]=str(png_path.resolve())
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
