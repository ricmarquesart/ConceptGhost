from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

R3="ConceptGhost_v1.54_P10_GATE7_PREVIEW_r3_ROUTE_UX_COLMAP_FIX"
R4="ConceptGhost_v1.54_P10_GATE7_PREVIEW_r4_AUDIT_COVERAGE_FIX"
BASE="cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd"
EXCLUDED={"BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json","SHA256SUMS.txt"}

def h(p):
 d=hashlib.sha256()
 with Path(p).open("rb") as s:
  for b in iter(lambda:s.read(1024*1024),b""): d.update(b)
 return d.hexdigest()

def rt(p): return Path(p).read_text(encoding="utf-8-sig")
def wt(p,s,nl="\n"):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("w",encoding="utf-8",newline=nl) as f:f.write(s)

def replace_tree(root,a,b):
 for p in sorted(Path(root).rglob("*")):
  if not p.is_file() or p.suffix.lower() not in {".py",".ps1",".md",".json",".txt"}: continue
  try:s=rt(p)
  except UnicodeDecodeError: continue
  if a in s: wt(p,s.replace(a,b))

def patch_entrypoints(root):
 root=Path(root)
 oi=root/"Installer/install_gate7_preview_r3_route_ux_colmap_fix.ps1"
 ov=root/"Installer/verify_gate7_preview_r3_route_ux_colmap_fix.ps1"
 if not oi.is_file() or not ov.is_file(): raise RuntimeError("r3 entrypoints missing")
 ins=rt(oi).replace("Gate 7 Preview r3 + Route UX + COLMAP Fix","Gate 7 Preview r4 + Audit + 70% COLMAP Coverage").replace(R3,R4).replace("before_gate7_preview_r3_route_ux_colmap_fix","before_gate7_preview_r4_audit_coverage_fix")
 ver=rt(ov).replace("Gate 7 Preview r3 + Route UX + COLMAP Fix","Gate 7 Preview r4 + Audit + 70% COLMAP Coverage").replace(R3,R4).replace("P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_READY_VERIFY.json","P10_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX_READY_VERIFY.json")
 wt(root/"Installer/install_gate7_preview_r4_audit_coverage_fix.ps1",ins); wt(root/"Installer/verify_gate7_preview_r4_audit_coverage_fix.ps1",ver)
 oi.unlink(); ov.unlink()
 ibat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 Preview r4
echo     Auto Audit + 70%% COLMAP Coverage + Route UX
echo ============================================================
echo RUN_AUDIT_BUNDLE is automatic on Gate 7 success or failure.
echo Canonical path: concept_scene\\P10_AUDITS
echo Gate 8 remains blocked.
echo ============================================================
if not exist "%~dp0Installer\\install_gate7_preview_r4_audit_coverage_fix.ps1" (
  echo [FAIL] Required r4 installer entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\install_gate7_preview_r4_audit_coverage_fix.ps1"
if errorlevel 1 (
  echo [FAIL] Gate 7 Preview r4 installation did not complete.
  pause
  exit /b 1
)
echo [PASS] Gate 7 Preview r4 installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
 vbat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 Preview r4
echo ============================================================
if not exist "%~dp0Installer\\verify_gate7_preview_r4_audit_coverage_fix.ps1" (
  echo [FAIL] Required r4 verifier entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\verify_gate7_preview_r4_audit_coverage_fix.ps1"
if errorlevel 1 (
  echo [FAIL] Gate 7 Preview r4 verification failed.
  pause
  exit /b 1
)
echo [PASS] Gate 7 Preview r4 installation verification completed.
pause
"""
 (root/"03_INSTALL_ALL.bat").write_bytes(ibat.replace("\n","\r\n").encode("utf-8"))
 (root/"04_VERIFY_INSTALL.bat").write_bytes(vbat.replace("\n","\r\n").encode("utf-8"))

def patch_workflow(root):
 p=Path(root)/"Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json"
 w=json.loads(rt(p)); by={int(n["id"]):n for n in w.get("nodes",[])}
 a=by.get(2420)
 if not a or a.get("type")!="ConceptGhostP10RunAuditBundle": raise RuntimeError("audit node 2420 missing")
 a["title"]="RUN AUDIT BUNDLE - AUTO-SAVED concept_scene/P10_AUDITS - TERMINAL REFRESH"
 e=w.setdefault("extra",{}).setdefault("conceptghost",{})
 e.update({
  "gate7_preview_release":"GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX",
  "run_audit_bundle_auto_on_gate7_success_or_failure":True,
  "run_audit_project_storage":"concept_scene/P10_AUDITS/<P9_RUN>/<P10_ATTEMPT>",
  "colmap_registered_intersection_policy":"70_PERCENT_FRAME_AND_MISSION_COVERAGE",
 })
 n=by.get(2412)
 if n and n.get("widgets_values"):
  n["widgets_values"][0]=str(n["widgets_values"][0])+"\\n\\nr4: RUN_AUDIT_BUNDLE is automatic on Gate 7 success or failure. Canonical path: concept_scene/P10_AUDITS/<P9_RUN>/<P10_ATTEMPT>. Gate 7 uses registered geometric intersection and requires 70% frame coverage and 70% qualifying mission coverage."
 wt(p,json.dumps(w,indent=2,ensure_ascii=False)+"\n")

def patch_contracts(root,source_commit,package_commit):
 root=Path(root)
 p=root/"Installer/verify_p10_dr9.py"; wt(p,rt(p).replace("CONCEPTGHOST_P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_RUNTIME_VERIFY_PASS","CONCEPTGHOST_P10_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX_RUNTIME_VERIFY_PASS"))
 p=root/"Installer/test_gate7_preview_bundle.py"; s=rt(p).replace("GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_RUNTIME_VERIFY_PASS","GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX_RUNTIME_VERIFY_PASS").replace("Installer/install_gate7_preview_r3_route_ux_colmap_fix.ps1","Installer/install_gate7_preview_r4_audit_coverage_fix.ps1").replace("Installer/verify_gate7_preview_r3_route_ux_colmap_fix.ps1","Installer/verify_gate7_preview_r4_audit_coverage_fix.ps1"); wt(p,s)
 p=root/"Installer/test_dr9_bundle.py"; wt(p,rt(p).replace("USER_GUIDE_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX.md","USER_GUIDE_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX.md"))
 og=root/"USER_GUIDE_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX.md"
 guide=rt(og).replace("Gate 7 Preview r3 + Route UX + COLMAP Fix","Gate 7 Preview r4 + Audit + 70% COLMAP Coverage")
 guide+="""\n## r4 automatic audit\nNo separate action is required. Gate 7 creates RUN_AUDIT_BUNDLE.zip on success and creates a PARTIAL_FAILURE audit before surfacing a Gate 7 exception.\nCanonical project path: G:\\My Drive\\ConceptGhost\\Outputs\\ConceptGhost\\concept_scene\\P10_AUDITS\\<P9_RUN>\\<P10_ATTEMPT>.\nLatest pointers live directly under concept_scene\\P10_AUDITS. The accepted P9 run is not modified. The terminal audit node rebuilds the same bundle with visual evidence after success.\n\n## r4 COLMAP coverage\nGate 7.3 uses only the intersection of registered views with geometric depth and consistency evidence. It requires usable frame coverage >=70%, qualifying mission coverage >=70%, and >=70% usable frames inside each qualifying mission. At least two independent missions must qualify. Missing authored views remain UNKNOWN and are never interpreted as FREE space.\n"""
 ng=root/"USER_GUIDE_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX.md"; wt(ng,guide); og.unlink()
 wt(root/"Payload/docs/37_GATE7_R4_AUDIT_AND_COLMAP_COVERAGE.md",f"""# Gate 7 Preview r4 - Audit + COLMAP Coverage\n\nSource commit: {source_commit}\nPackage commit: {package_commit or 'LOCAL_BUILD'}\n\nAudit is automatic on Gate 7 success or failure and is stored under concept_scene/P10_AUDITS/<P9_RUN>/<P10_ATTEMPT>. The accepted P9 run stays unmodified.\n\nCOLMAP Gate 7.3 policy: registered + geometric-evidence intersection; frame >=0.70; qualifying missions >=0.70; per qualifying mission frames >=0.70; minimum two qualifying independent missions. Missing views remain UNKNOWN. Gate 8 remains blocked.\n""")
 cm=root/"P10_DR9_CODE_MANIFEST.json"; d=json.loads(rt(cm)); d.update({"schema":"ConceptGhost.P10Gate7PreviewAuditCoverageCodeManifest.v0.4","release":R4,"source_commit":source_commit}); wt(cm,json.dumps(d,indent=2,ensure_ascii=False)+"\n")
 for name in ("RELEASE.json","P10_DR9_RELEASE.json"):
  p=root/name; d=json.loads(rt(p)); d.update({"schema":"ConceptGhost.P10Gate7PreviewAuditCoverageRelease.v0.4","release":R4,"source_commit":source_commit,"package_hotfix_commit":package_commit or "LOCAL_BUILD"})
  d["run_audit_bundle_r4"]={"automatic_on_gate7_success":True,"automatic_on_gate7_failure":True,"terminal_node_rebuilds_with_visual_pack":True,"project_storage":"concept_scene/P10_AUDITS/<P9_RUN>/<P10_ATTEMPT>","p9_run_mutated":False}
  d["colmap_coverage_r4"]={"selection":"REGISTERED_GEOMETRIC_INTERSECTION","min_frame_coverage_ratio":0.70,"min_mission_coverage_ratio":0.70,"min_per_mission_frame_ratio":0.70,"min_qualifying_missions":2,"missing_views_state":"UNKNOWN_NEVER_FREE"}
  wt(p,json.dumps(d,indent=2,ensure_ascii=False)+"\n")
 ov=root/"P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_VALIDATION.txt"
 if ov.exists(): ov.unlink()
 wt(root/"P10_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX_VALIDATION.txt",f"""ConceptGhost P10 Gate 7 Preview r4 Audit + Coverage validation\n\nBase r15 SHA-256: {BASE}\nSource commit: {source_commit}\nRegistered geometric intersection: ENABLED\nMinimum usable frame coverage: 70%\nMinimum qualifying mission coverage: 70%\nMinimum per qualifying mission frame ratio: 70%\nMissing views treated as UNKNOWN: YES\nAuto audit on Gate 7 success: YES\nAuto partial audit on Gate 7 failure: YES\nCanonical audit storage: concept_scene/P10_AUDITS/<P9_RUN>/<P10_ATTEMPT>\nAccepted P9 run mutated: NO\nGate 8 node present: NO\nUser runtime acceptance: PENDING\n""")
 test="""from pathlib import Path\nimport json,sys\n\ndef main(root):\n root=Path(root).resolve(); errors=[]; n=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'\n free=(n/'free_space_evidence.py').read_text(encoding='utf-8'); runtime=(n/'gate7_runtime.py').read_text(encoding='utf-8'); audit=(n/'run_audit_bundle.py').read_text(encoding='utf-8')\n for t in ('min_frame_coverage_ratio: float = 0.70','min_mission_coverage_ratio: float = 0.70','min_per_mission_frame_ratio: float = 0.70','USE_REGISTERED_GEOMETRIC_INTERSECTION_REQUIRE_70_PERCENT','UNKNOWN_NEVER_FREE'):\n  if t not in free: errors.append('free-space missing '+t)\n for t in ('build_partial_run_audit_bundle','Automatic RUN_AUDIT_BUNDLE','min_frame_coverage_ratio=0.70'):\n  if t not in runtime: errors.append('runtime missing '+t)\n for t in ('default_project_audit_root','P10_AUDITS','LATEST_AUDIT_INDEX.json','PARTIAL_FAILURE','reconstruction_runtime_manifest_included'):\n  if t not in audit: errors.append('audit missing '+t)\n w=json.loads((root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json').read_text(encoding='utf-8-sig')); by={int(x['id']):x for x in w.get('nodes',[])}\n if 'P10_AUDITS' not in str(by.get(2420,{}).get('title')): errors.append('workflow audit path title missing')\n if any('Gate8' in str(x.get('type')) or 'Gate 8' in str(x.get('type')) for x in w.get('nodes',[])): errors.append('Gate 8 leaked')\n if errors:\n  print('\\\\n'.join('[FAIL] '+x for x in errors)); return 1\n print('CONCEPTGHOST_GATE7_PREVIEW_R4_AUDIT_COVERAGE_FIX_PASS'); return 0\n\nif __name__=='__main__': raise SystemExit(main(sys.argv[1]))\n"""
 wt(root/"Installer/test_gate7_r4_audit_coverage_fix.py",test)

def rebuild(root,source_commit):
 root=Path(root); rows=[]
 for p in sorted(root.rglob("*")):
  rel=p.relative_to(root).as_posix()
  if p.is_file() and rel not in EXCLUDED: rows.append({"path":rel,"sha256":h(p),"size_bytes":p.stat().st_size})
 for name in ("BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json"):
  p=root/name; d=json.loads(rt(p)); d.update({"schema":"ConceptGhost.P10Gate7PreviewAuditCoverageBundle.v0.4","release":R4,"source_commit":source_commit,"file_count_excluding_manifests_and_checksums":len(rows),"r4":{"automatic_audit_success_failure":True,"registered_geometric_intersection":True,"frame_coverage_threshold":0.70,"mission_coverage_threshold":0.70,"gate8_present":False},"files":rows}); wt(p,json.dumps(d,indent=2,ensure_ascii=False)+"\n")
 lines=[f"{h(p)}  {p.relative_to(root).as_posix()}" for p in sorted(root.rglob("*")) if p.is_file() and p.name!="SHA256SUMS.txt"]; wt(root/"SHA256SUMS.txt","\n".join(lines)+"\n")

def validate(root,source_commit):
 root=Path(root); e=[]; cm=json.loads(rt(root/"P10_DR9_CODE_MANIFEST.json")); n=root/"Payload/custom_nodes/ConceptGhost_P10_Lab"
 if cm.get("source_commit")!=source_commit:e.append("code manifest source mismatch")
 for x in cm.get("files",[]):
  p=n/x["path"]
  if not p.is_file() or h(p)!=x["sha256"]:e.append("P10 code mismatch "+x["path"])
 for p in list(n.glob("*.py"))+list((root/"Installer").glob("*.py")):
  try:compile(rt(p),str(p),"exec")
  except Exception as z:e.append(f"compile {p.name}: {z}")
 for raw in rt(root/"SHA256SUMS.txt").splitlines():
  d,rel=raw.split("  ",1);p=root/rel
  if not p.is_file() or h(p)!=d:e.append("sha mismatch "+rel)
 if len(list((root/"Payload/workflows").glob("*.json")))!=2:e.append("not exactly two workflows")
 return e

def zipdet(root,out):
 root=Path(root);out=Path(out)
 if out.exists():out.unlink()
 with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(root.rglob("*")):
   if not p.is_file():continue
   i=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=(2026,9,24,18,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o644<<16;z.writestr(i,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def main():
 a=argparse.ArgumentParser();a.add_argument("--source",type=Path,required=True);a.add_argument("--output",type=Path,required=True);a.add_argument("--p10-source-root",type=Path,required=True);a.add_argument("--source-commit",default=os.environ.get("GITHUB_SHA",""));a.add_argument("--package-commit",default=os.environ.get("GITHUB_SHA",""));a.add_argument("--keep-extracted",type=Path);x=a.parse_args()
 if h(x.source)!=BASE:raise SystemExit("wrong frozen r15 base SHA")
 if not re.fullmatch(r"[0-9a-f]{40}",x.source_commit or ""):raise SystemExit("source commit must be 40-char SHA")
 b=Path(__file__).resolve().parents[1]/"gate7_preview_r3_route_ux_colmap_fix"/"build_gate7_preview_r3_from_r15.py"
 with tempfile.TemporaryDirectory(prefix="cg-r4-") as td:
  t=Path(td);r3=t/(R3+".zip");root=t/R4
  q=subprocess.run([sys.executable,str(b),"--source",str(x.source),"--output",str(r3),"--p10-source-root",str(x.p10_source_root),"--source-commit",x.source_commit,"--package-commit",x.package_commit,"--keep-extracted",str(root)],capture_output=True,text=True);print(q.stdout)
  if q.returncode:raise SystemExit(q.stdout+q.stderr)
  patch_entrypoints(root);replace_tree(root,R3,R4);patch_workflow(root);patch_contracts(root,x.source_commit,x.package_commit)
  for s in ("test_dr9_bundle.py","test_gate7_preview_bundle.py","test_run_audit_bundle_package.py","test_gate7_r3_route_ux_colmap_fix.py","test_gate7_r4_audit_coverage_fix.py"):
   q=subprocess.run([sys.executable,str(root/"Installer"/s),str(root)],capture_output=True,text=True);print(q.stdout.strip())
   if q.returncode:raise SystemExit(q.stdout+q.stderr)
  for p in sorted(root.rglob("__pycache__"),key=lambda p:len(p.parts),reverse=True):shutil.rmtree(p,ignore_errors=True)
  rebuild(root,x.source_commit);err=validate(root,x.source_commit)
  if err:raise SystemExit("\n".join("[FAIL] "+z for z in err))
  x.output.parent.mkdir(parents=True,exist_ok=True);zipdet(root,x.output);print("R4_ZIP="+str(x.output));print("R4_BYTES="+str(x.output.stat().st_size));print("R4_SHA256="+h(x.output))
  if x.keep_extracted:
   if x.keep_extracted.exists():shutil.rmtree(x.keep_extracted)
   shutil.copytree(root,x.keep_extracted)
 return 0
if __name__=="__main__":raise SystemExit(main())
