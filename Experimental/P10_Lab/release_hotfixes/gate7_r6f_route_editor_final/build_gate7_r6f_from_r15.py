from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

R5="ConceptGhost_v1.54_P10_GATE7_PREVIEW_r5_GEOMETRIC_EVIDENCE_AUDIT_FIX"
R6F="ConceptGhost_v1.54_P10_GATE7_R6F_ROUTE_EDITOR_FINAL"
BASE="cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd"
EXCLUDED={"BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json","SHA256SUMS.txt"}


def h(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def rt(path):
    return Path(path).read_text(encoding="utf-8-sig")


def wt(path,text,newline="\n"):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline=newline) as stream:
        stream.write(text)


def replace_tree(root,old,new):
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py",".ps1",".md",".json",".txt",".bat"}:
            continue
        try:
            text=rt(path)
        except UnicodeDecodeError:
            continue
        if old in text:
            wt(path,text.replace(old,new),"\r\n" if path.suffix.lower()==".bat" else "\n")


def patch_entrypoints(root):
    root=Path(root)
    old_install=root/"Installer/install_gate7_preview_r5_geometric_evidence_audit_fix.ps1"
    old_verify=root/"Installer/verify_gate7_preview_r5_geometric_evidence_audit_fix.ps1"
    if not old_install.is_file() or not old_verify.is_file():
        raise RuntimeError("r5 installer/verifier entrypoints missing")
    install=rt(old_install)
    verify=rt(old_verify)
    replacements=(
        ("Gate 7 Preview r5 + Geometric Evidence + Run-Local Audit","Gate 7 R6F + Route Editor Final"),
        (R5,R6F),
        ("before_gate7_preview_r5_geometric_evidence_audit_fix","before_gate7_r6f_route_editor_final"),
        ("P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_READY_VERIFY.json","P10_GATE7_R6F_ROUTE_EDITOR_FINAL_READY_VERIFY.json"),
        ("CONCEPTGHOST_P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS","CONCEPTGHOST_P10_GATE7_R6F_ROUTE_EDITOR_FINAL_RUNTIME_VERIFY_PASS"),
    )
    for old,new in replacements:
        install=install.replace(old,new)
        verify=verify.replace(old,new)
    wt(root/"Installer/install_gate7_r6f_route_editor_final.ps1",install)
    wt(root/"Installer/verify_gate7_r6f_route_editor_final.ps1",verify)
    old_install.unlink()
    old_verify.unlink()

    install_bat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 R6F
echo     Route Editor Final + Geometric Evidence + Run-Local Audit
echo ============================================================
echo This is the first R6 target-PC validation package.
echo R6A-R6E were source/CI-only checkpoints.
echo Gate 8 remains blocked until this R6F runtime is accepted.
echo ============================================================
if not exist "%~dp0Installer\\install_gate7_r6f_route_editor_final.ps1" (
  echo [FAIL] Required R6F installer entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\install_gate7_r6f_route_editor_final.ps1"
if errorlevel 1 (
  echo [FAIL] R6F installation did not complete.
  pause
  exit /b 1
)
echo [PASS] R6F installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
    verify_bat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 R6F
echo ============================================================
if not exist "%~dp0Installer\\verify_gate7_r6f_route_editor_final.ps1" (
  echo [FAIL] Required R6F verifier entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\verify_gate7_r6f_route_editor_final.ps1"
if errorlevel 1 (
  echo [FAIL] R6F installation verification failed.
  pause
  exit /b 1
)
echo [PASS] R6F installation verification completed.
pause
"""
    (root/"03_INSTALL_ALL.bat").write_bytes(install_bat.replace("\n","\r\n").encode("utf-8"))
    (root/"04_VERIFY_INSTALL.bat").write_bytes(verify_bat.replace("\n","\r\n").encode("utf-8"))


def patch_route_workflow(root):
    root=Path(root)
    path=root/"Payload/workflows/01_ConceptGhost_P10_ROUTE_SETUP.json"
    workflow=json.loads(rt(path))
    nodes=workflow.get("nodes",[])
    by={int(node["id"]):node for node in nodes}
    route=by.get(2099)
    commit=by.get(2110)
    if not route or route.get("type")!="ConceptGhostP10DroneRouteAuthoring":
        raise RuntimeError("Route Authoring node 2099 missing")
    if not commit or commit.get("type")!="ConceptGhostP10RouteCommit":
        raise RuntimeError("Route Commit node 2110 missing")

    route["title"]="01 · STEP 2 · R6 EDIT DRONES · POINT/MESH LOD + LIVE CAMERA AIM"
    route["size"]=[1180,1490]
    commit["pos"]=[12100,9600]

    instruction=by.get(2097)
    if instruction and instruction.get("widgets_values"):
        instruction["widgets_values"][0]=(
            "WORKFLOW 01 — R6F ROUTE SETUP\n\n"
            "RUN #1: resolva/carregue P9. Edite os drones no Route Editor.\n\n"
            "R6 EDITOR: Points Low/Medium/High ou Mesh Surface/Wireframe; ajuste Point Size; "
            "selecione P1/P2/P3 para Live Selected Camera View; use Aim deste ponto para orientação individual; "
            "SPIN_360 usa Yaw Start + Pitch; use o gimbal X/Right, Y/Up, Z/Forward para mover o pivot da Perspective.\n\n"
            "SELECTED CAMERA NODE: mission_index/waypoint_index são seletores manuais para a checagem dedicada de maior confiança.\n\n"
            "RUN #2: depois de editar, clique Run novamente para COMMITAR a rota. "
            "Abra Workflow 02 apenas quando production_ready=true."
        )

    preview_id=2111
    image_id=2112
    if any(node.get("type")=="ConceptGhostP10SelectedDroneCameraPreview" for node in nodes):
        raise RuntimeError("Selected camera preview node already exists unexpectedly")
    link_run=197
    link_route=198
    link_image=199
    preview_node={
        "id":preview_id,
        "type":"ConceptGhostP10SelectedDroneCameraPreview",
        "pos":[10900,11250],
        "size":[570,420],
        "flags":{},
        "order":2013,
        "mode":0,
        "inputs":[
            {"name":"run_dir","type":"STRING","link":link_run},
            {"name":"route_plan_json","type":"STRING","link":link_route},
            {"name":"mission_index","type":"INT","widget":{"name":"mission_index"},"link":None},
            {"name":"waypoint_index","type":"INT","widget":{"name":"waypoint_index"},"link":None},
            {"name":"preview_mode","type":"COMBO","widget":{"name":"preview_mode"},"link":None},
            {"name":"preview_width","type":"INT","widget":{"name":"preview_width"},"link":None},
        ],
        "outputs":[
            {"name":"selected_camera_preview","type":"IMAGE","links":[link_image],"slot_index":0},
            {"name":"diagnostics_json","type":"STRING","links":None,"slot_index":1},
        ],
        "properties":{"Node name for S&R":"ConceptGhostP10SelectedDroneCameraPreview"},
        "widgets_values":[0,0,"POINTS_HIGH",720],
        "title":"P10 · SELECTED DRONE CAMERA PREVIEW · MANUAL HIGH-CONFIDENCE CHECK",
    }
    preview_image={
        "id":image_id,
        "type":"PreviewImage",
        "pos":[11520,11250],
        "size":[900,650],
        "flags":{},
        "order":2014,
        "mode":0,
        "inputs":[{"name":"images","type":"IMAGE","link":link_image}],
        "outputs":[],
        "properties":{"Node name for S&R":"PreviewImage"},
        "widgets_values":[],
        "title":"P10 · SELECTED CAMERA · PREVIEW IMAGE",
    }
    nodes.extend([preview_node,preview_image])
    workflow.setdefault("links",[]).extend([
        [link_run,1015,0,preview_id,0,"STRING"],
        [link_route,2099,1,preview_id,1,"STRING"],
        [link_image,preview_id,0,image_id,0,"IMAGE"],
    ])
    workflow["last_node_id"]=max(int(workflow.get("last_node_id") or 0),image_id)
    workflow["last_link_id"]=max(int(workflow.get("last_link_id") or 0),link_image)
    extra=workflow.setdefault("extra",{}).setdefault("conceptghost",{})
    extra.update({
        "r6f_route_editor_final":True,
        "route_schema":"ConceptGhost.P10DroneRoutePlan.v0.3",
        "portable_route_preset_schema":"ConceptGhost.P10DroneRoutePreset.v0.2",
        "point_lods":["POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH"],
        "mesh_modes":["MESH_SURFACE","MESH_WIREFRAME"],
        "selected_camera_live_preview":True,
        "selected_camera_refresh_node":True,
        "per_waypoint_camera_aim":True,
        "spin_pitch_yaw":True,
        "perspective_pivot_gimbal":True,
        "route_export":["JSON","CSV","TXT"],
    })
    wt(path,json.dumps(workflow,indent=2,ensure_ascii=False)+"\n")


def patch_production_workflow(root):
    path=Path(root)/"Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json"
    workflow=json.loads(rt(path))
    extra=workflow.setdefault("extra",{}).setdefault("conceptghost",{})
    extra["gate7_preview_release"]="GATE7_R6F_ROUTE_EDITOR_FINAL"
    extra["r6f_route_schema"]="ConceptGhost.P10DroneRoutePlan.v0.3"
    extra["r6f_user_validation_required"]=True
    wt(path,json.dumps(workflow,indent=2,ensure_ascii=False)+"\n")


def patch_contracts(root,source_commit,package_commit):
    root=Path(root)
    p=root/"Installer/verify_p10_dr9.py"
    wt(p,rt(p).replace(
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS",
        "CONCEPTGHOST_P10_GATE7_R6F_ROUTE_EDITOR_FINAL_RUNTIME_VERIFY_PASS",
    ))

    p=root/"Installer/test_gate7_preview_bundle.py"
    text=rt(p).replace(
        "GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS",
        "GATE7_R6F_ROUTE_EDITOR_FINAL_RUNTIME_VERIFY_PASS",
    ).replace(
        "Installer/install_gate7_preview_r5_geometric_evidence_audit_fix.ps1",
        "Installer/install_gate7_r6f_route_editor_final.ps1",
    ).replace(
        "Installer/verify_gate7_preview_r5_geometric_evidence_audit_fix.ps1",
        "Installer/verify_gate7_r6f_route_editor_final.ps1",
    )
    wt(p,text)

    p=root/"Installer/test_dr9_bundle.py"
    wt(p,rt(p).replace(
        "USER_GUIDE_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX.md",
        "USER_GUIDE_GATE7_R6F_ROUTE_EDITOR_FINAL.md",
    ))

    old_guide=root/"USER_GUIDE_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX.md"
    if not old_guide.is_file():
        raise RuntimeError("r5 user guide missing")
    guide=rt(old_guide).replace(
        "Gate 7 Preview r5 + Geometric Evidence + Run-Local Audit",
        "Gate 7 R6F + Route Editor Final",
    )
    guide += """
## R6F Route Editor final validation
R6A-R6E were developed and CI-validated without target-PC acceptance. R6F is the first runtime validation package.

Route Editor includes Points Low/Medium/High, Mesh Surface/Wireframe, Point Size, live Selected Camera View, selected-camera frustum, explicit per-waypoint camera aim, SPIN_360 pitch/yaw-start controls, Perspective RUF pivot/gimbal, conventional horizontal orbit direction, and JSON + CSV/TXT route export.

The dedicated node P10 · Selected Drone Camera Preview is present in Workflow 01 for a higher-confidence manual check. Its mission_index and waypoint_index widgets select the control camera to inspect.

Route authority schema is v0.3. Legacy v0.1/v0.2 route bindings remain readable. Portable preset schema is v0.2 and v0.1 remains import-compatible.

Gate 8 remains blocked until this R6F target-PC run is accepted.
"""
    wt(root/"USER_GUIDE_GATE7_R6F_ROUTE_EDITOR_FINAL.md",guide)
    old_guide.unlink()

    wt(root/"Payload/docs/40_R6F_ROUTE_EDITOR_FINAL.md",f"""# ConceptGhost P10 Gate 7 R6F — Route Editor Final

Source commit: {source_commit}
Package commit: {package_commit or 'LOCAL_BUILD'}

## Included R6 gates
- R6A Point/Mesh display LOD and Point Size.
- R6B Live Selected Camera View + frustum + dedicated selected-camera preview node.
- R6C Per-waypoint aim interpolation + SPIN_360 pitch/yaw start.
- R6D Perspective pivot/gimbal + conventional horizontal orbit.
- R6E portable preset v0.2 + authority JSON and readable CSV/TXT export.
- R6F aggregate package/regression gate.

P9 remains immutable. Gate 8 remains blocked until user runtime acceptance.
""")

    code_manifest=root/"P10_DR9_CODE_MANIFEST.json"
    data=json.loads(rt(code_manifest))
    data.update({
        "schema":"ConceptGhost.P10Gate7R6FCodeManifest.v0.1",
        "release":R6F,
        "source_commit":source_commit,
    })
    wt(code_manifest,json.dumps(data,indent=2,ensure_ascii=False)+"\n")

    for name in ("RELEASE.json","P10_DR9_RELEASE.json"):
        p=root/name
        data=json.loads(rt(p))
        data.update({
            "schema":"ConceptGhost.P10Gate7R6FRelease.v0.1",
            "release":R6F,
            "source_commit":source_commit,
            "package_hotfix_commit":package_commit or "LOCAL_BUILD",
        })
        data["r6f"]={
            "r6a_point_mesh_lod":True,
            "r6b_selected_camera_preview":True,
            "r6c_per_waypoint_camera_pose":True,
            "r6c_spin_pitch_yaw":True,
            "r6d_pivot_gimbal":True,
            "r6d_conventional_orbit":True,
            "r6e_route_schema":"ConceptGhost.P10DroneRoutePlan.v0.3",
            "r6e_portable_preset_schema":"ConceptGhost.P10DroneRoutePreset.v0.2",
            "r6e_readable_exports":["CSV","TXT"],
            "user_runtime_acceptance":"PENDING",
            "gate8_present":False,
        }
        wt(p,json.dumps(data,indent=2,ensure_ascii=False)+"\n")

    old_validation=root/"P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_VALIDATION.txt"
    if old_validation.exists():
        old_validation.unlink()
    wt(root/"P10_GATE7_R6F_ROUTE_EDITOR_FINAL_VALIDATION.txt",f"""ConceptGhost P10 Gate 7 R6F Route Editor Final

Base r15 SHA-256: {BASE}
Source commit: {source_commit}
R6A point/mesh LOD: PASS SOURCE/CI
R6B selected camera live + node: PASS SOURCE/CI
R6C per-waypoint aim + 360 pitch/yaw: PASS SOURCE/CI
R6D pivot/gimbal + orbit correction: PASS SOURCE/CI
R6E JSON + CSV/TXT route export: PASS SOURCE/CI
Gate 7 geometric consistency evidence fix: INCLUDED
Run-local automatic audit fix: INCLUDED
Accepted P9 run mutated: NO
Gate 8 node present: NO
User runtime acceptance: PENDING — THIS R6F PACKAGE IS THE VALIDATION POINT
""")

    test="""from pathlib import Path
import json,sys

def main(root):
 root=Path(root).resolve(); errors=[]; n=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
 required={
  'drone_route_preview.py':('P10RoutePreviewGeometry.v0.2','POINTS_HIGH','DISPLAY_ONLY_P9_PRIMARYMESH_LOD'),
  'route_authoring_node.py':('selected_camera_live_preview','perspective_pivot_gimbal','camera_preview_contract'),
  'selected_camera_preview.py':('ConceptGhostP10SelectedDroneCameraPreview','preview_authority','P9_ACCEPTED_PRIMARYMESH'),
  'drone_route_plan.py':('P10DroneRoutePlan.v0.3','look_direction','spin_pitch_deg','spin_yaw_start_deg','_legacy_v02_route_hash'),
 }
 for name,tokens in required.items():
  p=n/name
  if not p.is_file(): errors.append('missing source '+name); continue
  source=p.read_text(encoding='utf-8')
  for token in tokens:
   if token not in source: errors.append(name+' missing '+token)
 js=(n/'web/js/drone_route_editor.js').read_text(encoding='utf-8')
 for token in ('Points Low','Mesh Surface','Selected Camera View','Aim deste ponto','Reset Pivot','Pivot to Selected Camera','state.orbitYaw -= dx * 0.008','P10DroneRoutePreset.v0.2','readableRouteExports'):
  if token not in js: errors.append('frontend missing '+token)
 w=json.loads((root/'Payload/workflows/01_ConceptGhost_P10_ROUTE_SETUP.json').read_text(encoding='utf-8-sig')); by={int(x['id']):x for x in w.get('nodes',[])}
 if by.get(2111,{}).get('type')!='ConceptGhostP10SelectedDroneCameraPreview': errors.append('workflow selected-camera node missing')
 if by.get(2112,{}).get('type')!='PreviewImage': errors.append('workflow selected-camera PreviewImage missing')
 links={int(x[0]):x for x in w.get('links',[])}
 for lid in (197,198,199):
  if lid not in links: errors.append('workflow link missing '+str(lid))
 if any('Gate8' in str(x.get('type')) or 'Gate 8' in str(x.get('title')) for x in w.get('nodes',[])): errors.append('Gate 8 leaked into Route Setup')
 p=json.loads((root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json').read_text(encoding='utf-8-sig'))
 if any('Gate8' in str(x.get('type')) or 'Gate 8' in str(x.get('title')) for x in p.get('nodes',[])): errors.append('Gate 8 leaked into Production')
 if errors:
  print('\\n'.join('[FAIL] '+x for x in errors)); return 1
 print('CONCEPTGHOST_GATE7_R6F_ROUTE_EDITOR_FINAL_PASS'); return 0

if __name__=='__main__': raise SystemExit(main(sys.argv[1]))
"""
    wt(root/"Installer/test_gate7_r6f_route_editor_final.py",test)


def rebuild(root,source_commit):
    root=Path(root)
    rows=[]
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root).as_posix()
        if path.is_file() and rel not in EXCLUDED:
            rows.append({"path":rel,"sha256":h(path),"size_bytes":path.stat().st_size})
    for name in ("BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json"):
        path=root/name
        data=json.loads(rt(path))
        data.update({
            "schema":"ConceptGhost.P10Gate7R6FBundle.v0.1",
            "release":R6F,
            "source_commit":source_commit,
            "file_count_excluding_manifests_and_checksums":len(rows),
            "r6f":{
                "route_editor_final":True,
                "point_mesh_lod":True,
                "selected_camera_preview":True,
                "per_waypoint_camera_pose":True,
                "spin_pitch_yaw":True,
                "pivot_gimbal":True,
                "route_export_json_csv_txt":True,
                "gate7_geometric_evidence_fix":True,
                "run_local_audit_fix":True,
                "gate8_present":False,
                "user_runtime_acceptance":"PENDING",
            },
            "files":rows,
        })
        wt(path,json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    lines=[
        f"{h(path)}  {path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name!="SHA256SUMS.txt"
    ]
    wt(root/"SHA256SUMS.txt","\n".join(lines)+"\n")


def validate(root,source_commit):
    root=Path(root)
    errors=[]
    cm=json.loads(rt(root/"P10_DR9_CODE_MANIFEST.json"))
    node_root=root/"Payload/custom_nodes/ConceptGhost_P10_Lab"
    if cm.get("source_commit")!=source_commit:
        errors.append("code manifest source mismatch")
    for item in cm.get("files",[]):
        path=node_root/item["path"]
        if not path.is_file() or h(path)!=item["sha256"]:
            errors.append("P10 code mismatch "+item["path"])
    for path in list(node_root.glob("*.py"))+list((root/"Installer").glob("*.py")):
        try:
            compile(rt(path),str(path),"exec")
        except Exception as error:
            errors.append(f"compile {path.name}: {error}")
    for raw in rt(root/"SHA256SUMS.txt").splitlines():
        digest,rel=raw.split("  ",1)
        path=root/rel
        if not path.is_file() or h(path)!=digest:
            errors.append("sha mismatch "+rel)
    if len(list((root/"Payload/workflows").glob("*.json")))!=2:
        errors.append("not exactly two workflows")
    return errors


def zipdet(root,out):
    root=Path(root)
    out=Path(out)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            info=zipfile.ZipInfo(path.relative_to(root).as_posix(),date_time=(2026,9,24,20,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--p10-source-root",type=Path,required=True)
    parser.add_argument("--source-commit",default=os.environ.get("GITHUB_SHA",""))
    parser.add_argument("--package-commit",default=os.environ.get("GITHUB_SHA",""))
    parser.add_argument("--keep-extracted",type=Path)
    args=parser.parse_args()

    if h(args.source)!=BASE:
        raise SystemExit("wrong frozen r15 base SHA")
    if not re.fullmatch(r"[0-9a-f]{40}",args.source_commit or ""):
        raise SystemExit("source commit must be 40-char SHA")

    r5_builder=Path(__file__).resolve().parents[1]/"gate7_preview_r5_geometric_evidence_audit_fix"/"build_gate7_preview_r5_from_r15.py"
    with tempfile.TemporaryDirectory(prefix="cg-r6f-") as temp:
        temp=Path(temp)
        r5_zip=temp/(R5+".zip")
        root=temp/R6F
        result=subprocess.run([
            sys.executable,str(r5_builder),
            "--source",str(args.source),
            "--output",str(r5_zip),
            "--p10-source-root",str(args.p10_source_root),
            "--source-commit",args.source_commit,
            "--package-commit",args.package_commit,
            "--keep-extracted",str(root),
        ],capture_output=True,text=True)
        print(result.stdout)
        if result.returncode:
            raise SystemExit(result.stdout+result.stderr)

        patch_entrypoints(root)
        replace_tree(root,R5,R6F)
        patch_route_workflow(root)
        patch_production_workflow(root)
        patch_contracts(root,args.source_commit,args.package_commit)

        tests=(
            "test_dr9_bundle.py",
            "test_gate7_preview_bundle.py",
            "test_run_audit_bundle_package.py",
            "test_gate7_r3_route_ux_colmap_fix.py",
            "test_gate7_r5_geometric_evidence_audit_fix.py",
            "test_gate7_r6f_route_editor_final.py",
        )
        for name in tests:
            result=subprocess.run([sys.executable,str(root/"Installer"/name),str(root)],capture_output=True,text=True)
            print(result.stdout.strip())
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)

        js=root/"Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js"
        if shutil.which("node"):
            result=subprocess.run(["node","--check",str(js)],capture_output=True,text=True)
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)

        for cache in sorted(root.rglob("__pycache__"),key=lambda item:len(item.parts),reverse=True):
            shutil.rmtree(cache,ignore_errors=True)
        rebuild(root,args.source_commit)
        errors=validate(root,args.source_commit)
        if errors:
            raise SystemExit("\n".join("[FAIL] "+item for item in errors))

        args.output.parent.mkdir(parents=True,exist_ok=True)
        zipdet(root,args.output)
        print("R6F_ZIP="+str(args.output))
        print("R6F_BYTES="+str(args.output.stat().st_size))
        print("R6F_SHA256="+h(args.output))
        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root,args.keep_extracted)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
