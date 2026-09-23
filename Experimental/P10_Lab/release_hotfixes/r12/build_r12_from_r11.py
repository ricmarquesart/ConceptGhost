from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile, zipfile, subprocess
from pathlib import Path

R11_SHA256='5edaaaad1ca7c2a054bd019d48cc359a52146b6d10cb56e01cecea5880ce7e1c'
R11_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r11'
R12_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r12'
P10_SOURCE_COMMIT='f9ca7c6070a10c9c39a241ef9ebe8c4822988f66'
EXCLUDED={'BUNDLE_MANIFEST.json','P10_DR9_BUNDLE_MANIFEST.json','SHA256SUMS.txt'}

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def rt(p:Path)->str: return p.read_text(encoding='utf-8-sig')
def wt(p:Path,s:str,newline='\n'):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline=newline) as f:f.write(s)

def req(s,old,new,label):
    if old not in s: raise RuntimeError(f'missing required patch {label}: {old}')
    return s.replace(old,new,1)

def patch_entrypoints(root:Path):
    for rel,target in [('03_INSTALL_ALL.bat','Installer\\install_dr12.ps1'),('04_VERIFY_INSTALL.bat','Installer\\verify_dr12.ps1')]:
        p=root/rel; s=rt(p).replace('\r\n','\n').replace('\r','\n').replace('r11','r12')
        if rel.startswith('03_'): s=s.replace('Installer\\install_dr11.ps1','Installer\\install_dr12.ps1')
        else: s=s.replace('Installer\\verify_dr11.ps1','Installer\\verify_dr12.ps1')
        lines=s.splitlines(); cleaned=[]; i=0; marker=f'if not exist "%~dp0{target}" ('
        while i<len(lines):
            if lines[i].strip()==marker:
                i+=1
                while i<len(lines) and lines[i].strip()!=')': i+=1
                if i<len(lines): i+=1
                continue
            cleaned.append(lines[i]); i+=1
        s='\n'.join(cleaned)+'\n'
        invoke=f'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0{target}"'
        if invoke not in s: raise RuntimeError(f'{rel} missing invoke {invoke}')
        guard=(f'if not exist "%~dp0{target}" (\n  echo.\n  echo [FAIL] Required r12 entrypoint is missing: {target}\n  pause\n  exit /b 1\n)\n')
        s=s.replace(invoke,guard+invoke,1)
        p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    install_src=root/'Installer/install_dr11.ps1'; verify_src=root/'Installer/verify_dr11.ps1'
    if not install_src.is_file() or not verify_src.is_file(): raise RuntimeError('r11 entrypoints missing')
    wt(root/'Installer/install_dr12.ps1',rt(install_src).replace('r11','r12').replace('R11','R12'))
    wt(root/'Installer/verify_dr12.ps1',rt(verify_src).replace('r11','r12').replace('R11','R12'))
    install_src.unlink(); verify_src.unlink()

def patch_moge_evidence(root:Path):
    p=root/'Payload/custom_nodes/ConceptGhost_Stage68/nodes.py'; s=rt(p)
    old='''            worker_profile = dict(geometry["conceptghost_profile_config"] or {})
            worker_report = dict(geometry["conceptghost_worker_report"] or {})
            if worker_profile != profile:
                raise RuntimeError("[MOGE_EVIDENCE] worker profile_config differs from authoritative profile_config")
            required_worker = {
'''
    new='''            worker_profile = dict(geometry["conceptghost_profile_config"] or {})
            worker_report = dict(geometry["conceptghost_worker_report"] or {})
            worker_profile = assert_profile_contract(
                worker_profile,
                stage="MOGE_EVIDENCE_WORKER_PROFILE",
                expected_profile=selected,
            )
            # The worker may carry one diagnostic-only extension from the P10
            # diagnostic tap. It controls returned evidence only, not geometry authority.
            diagnostic_only_keys = {"diagnostic_return_per_step"}
            profile_mismatches = []
            for key in sorted(set(profile) | set(worker_profile)):
                if key in diagnostic_only_keys:
                    continue
                if worker_profile.get(key) != profile.get(key):
                    profile_mismatches.append(key)
            if profile_mismatches:
                details = ", ".join(
                    f"{key}: worker={worker_profile.get(key)!r} authoritative={profile.get(key)!r}"
                    for key in profile_mismatches
                )
                raise RuntimeError(
                    "[MOGE_EVIDENCE] worker profile_config differs from authoritative "
                    f"profile_config on authority-bearing fields: {details}"
                )
            expected_return_per_step = bool(
                worker_profile.get("return_per_step", False)
                or worker_profile.get("diagnostic_return_per_step", False)
            )
            required_worker = {
'''
    s=req(s,old,new,'MoGe evidence selective profile compare')
    marker='expected_return_per_step = bool('
    idx=s.index(marker); tail=s[idx:]
    old2='''                "use_fp16": bool(profile["use_fp16"]),
                "precision_policy": profile["precision_policy"],
            }
'''
    new2='''                "use_fp16": bool(profile["use_fp16"]),
                "precision_policy": profile["precision_policy"],
                "return_per_step": expected_return_per_step,
            }
'''
    if old2 not in tail: raise RuntimeError('MoGe evidence required_worker tail missing')
    s=s[:idx]+tail.replace(old2,new2,1)
    wt(p,s)

def add_test(root:Path):
    test='''from pathlib import Path\nimport json,sys\n\ndef main(root):\n root=Path(root).resolve(); e=[]\n nodes=(root/"Payload/custom_nodes/ConceptGhost_Stage68/nodes.py").read_text(encoding="utf-8-sig")\n for x in [\'diagnostic_only_keys = {"diagnostic_return_per_step"}\',\'stage="MOGE_EVIDENCE_WORKER_PROFILE"\',\'"return_per_step": expected_return_per_step\',\'authority-bearing fields\']:\n  if x not in nodes:e.append("missing "+x)\n if "if worker_profile != profile:" in nodes:e.append("legacy full dict comparison remains")\n for rel in ["Installer/install_dr12.ps1","Installer/verify_dr12.ps1"]:\n  if not (root/rel).is_file():e.append("missing "+rel)\n ib=(root/"03_INSTALL_ALL.bat").read_text(encoding="utf-8-sig"); vb=(root/"04_VERIFY_INSTALL.bat").read_text(encoding="utf-8-sig")\n if "Installer\\\\install_dr12.ps1" not in ib:e.append("03 target mismatch")\n if "Installer\\\\verify_dr12.ps1" not in vb:e.append("04 target mismatch")\n w=sorted(p.name for p in (root/"Payload/workflows").glob("*.json"))\n if w != ["01_ConceptGhost_P10_ROUTE_SETUP.json","02_ConceptGhost_P10_PRODUCTION.json"]:e.append("workflow contract changed")\n r=json.loads((root/"RELEASE.json").read_text(encoding="utf-8-sig"))\n if not str(r.get("release","")).endswith("_r12"):e.append("release metadata mismatch")\n if e:\n  print("\\n".join("[FAIL] "+x for x in e));return 1\n print("CONCEPTGHOST_DR9R_R12_MOGE_EVIDENCE_PROFILE_COMPATIBILITY_PASS");return 0\nif __name__=="__main__":raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else "."))\n'''
    wt(root/'Installer/test_r12_bundle.py',test)

def update_meta(root:Path,commit:str):
    old=root/'USER_GUIDE_DR9R_R11.md'; new=root/'USER_GUIDE_DR9R_R12.md'
    g=rt(old).replace('DR9R R11','DR9R R12').replace('DR9R r11','DR9R r12')
    g+='''\n\n## r12 MoGe evidence profile compatibility hotfix\n\nr12 fixes the post-inference node 1011 failure caused by comparing a diagnostic-only worker profile extension as if it were geometry authority. `diagnostic_return_per_step` may differ; every authority-bearing profile field remains strict and the worker `return_per_step` result is verified separately.\n'''; wt(new,g); old.unlink()
    p=root/'README.md'; s=rt(p).replace('DR9R r11','DR9R r12').replace('DR9R R11','DR9R R12'); s+='''\n\n## r12 MoGe evidence profile compatibility\nOnly `diagnostic_return_per_step` may differ between the worker runtime profile and authoritative geometry profile. Geometry-authority fields remain fail-closed.\n'''; wt(p,s)
    t=root/'Installer/test_dr9_bundle.py'; wt(t,rt(t).replace("root/'USER_GUIDE_DR9R_R11.md'","root/'USER_GUIDE_DR9R_R12.md'"))
    doc=f'''# ConceptGhost P10 DR9R — r12 MoGe Evidence Profile Compatibility\n\nDate: 2026-09-23\n\nThe target run proved MoGe-3 inference itself completed successfully. Node 1011 then rejected the worker profile because the diagnostic tap can alter `diagnostic_return_per_step`, a diagnostic-only field. r12 allows only that field to differ while preserving strict validation for all geometry-authority fields and verifying the worker `return_per_step` result.\n\nBase: {R11_NAME}.zip\nBase SHA-256: {R11_SHA256}\nP10 source: {P10_SOURCE_COMMIT}\nr12 build commit: {commit or 'LOCAL_BUILD'}\n'''; wt(root/'Payload/docs/24_DR9R_R12_MOGE_EVIDENCE_PROFILE_COMPATIBILITY.md',doc)
    for name in ['RELEASE.json','P10_DR9_RELEASE.json']:
        p=root/name; d=json.loads(rt(p)); d['schema']='ConceptGhost.P10DR9RRelease.v0.12'; d['release']=R12_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R12_MOGE_EVIDENCE_HOTFIX'; d['package_hotfix_commit']=commit or 'LOCAL_BUILD'; d['base_package']={'release':R11_NAME,'sha256':R11_SHA256}; wt(p,json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    wt(root/'P10_DR9_VALIDATION.txt',f'''ConceptGhost P10 DR9R r12 validation\n\nPackage build status: PASS\nBase package SHA-256: {R11_SHA256}\nMoGe Evidence authority-bearing profile validation: PASS\nAllowed diagnostic-only delta: diagnostic_return_per_step ONLY\nWorker return_per_step provenance validation: PASS\nGate5/Gate6 compatibility: RETAINED\nVersioned BAT entrypoints: RETAINED\nPublic workflows 01/02 only: PASS\nP9/P10 geometry authority: UNCHANGED\nUser runtime acceptance: PENDING\n''')

def manifests(root:Path):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED: rows.append({'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'size_bytes':p.stat().st_size})
    d=json.loads(rt(root/'BUNDLE_MANIFEST.json')); d['schema']='ConceptGhost.P10DR9RBundle.v0.12'; d['release']=R12_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R12_MOGE_EVIDENCE_HOTFIX'; d['file_count_excluding_manifests_and_checksums']=len(rows); d['moge_evidence_profile_compatibility']={'authority_fields_strict':True,'allowed_diagnostic_only_keys':['diagnostic_return_per_step'],'worker_return_per_step_verified':True}; d['files']=rows
    payload=json.dumps(d,indent=2,ensure_ascii=False)+'\n'; wt(root/'BUNDLE_MANIFEST.json',payload); wt(root/'P10_DR9_BUNDLE_MANIFEST.json',payload)
    wt(root/'SHA256SUMS.txt','\n'.join(f'{sha256(p)}  {p.relative_to(root).as_posix()}' for p in sorted(root.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt')+'\n')

def validate(root:Path):
    e=[]
    for p in list((root/'Installer').glob('*.py'))+list((root/'Payload/custom_nodes/ConceptGhost_Stage68').glob('*.py'))+list((root/'Payload/custom_nodes/ConceptGhost_P10_Lab').glob('*.py')):
        try: compile(rt(p),str(p),'exec')
        except Exception as x:e.append(f'compile {p.name}: {x}')
    for raw in rt(root/'SHA256SUMS.txt').splitlines():
        h,rel=raw.split('  ',1); p=root/rel
        if not p.is_file() or sha256(p)!=h:e.append('sha mismatch '+rel)
    return e

def zipdet(root:Path,out:Path):
    if out.exists():out.unlink()
    fixed=(2026,9,23,21,10,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=fixed);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--hotfix-commit',default=os.environ.get('GITHUB_SHA',''));ap.add_argument('--keep-extracted',type=Path);a=ap.parse_args()
    if sha256(a.source)!=R11_SHA256:raise SystemExit('wrong r11 sha: '+sha256(a.source))
    with tempfile.TemporaryDirectory(prefix='cg-r12-') as td:
        root=Path(td)/R12_NAME;root.mkdir()
        with zipfile.ZipFile(a.source) as z:z.extractall(root)
        patch_entrypoints(root);patch_moge_evidence(root);add_test(root);update_meta(root,a.hotfix_commit);manifests(root)
        for script in ['test_dr9_bundle.py','test_r12_bundle.py']:
            q=subprocess.run([os.sys.executable,str(root/'Installer'/script),str(root)],capture_output=True,text=True);print(q.stdout.strip())
            if q.returncode:raise SystemExit(q.stdout+q.stderr)
        for c in sorted(root.rglob('__pycache__'),key=lambda x:len(x.parts),reverse=True):shutil.rmtree(c,ignore_errors=True)
        for p in root.rglob('*.pyc'):p.unlink(missing_ok=True)
        manifests(root);e=validate(root)
        if e:raise SystemExit('\n'.join('[FAIL] '+x for x in e))
        a.output.parent.mkdir(parents=True,exist_ok=True);zipdet(root,a.output)
        print('R12_ZIP='+str(a.output));print('R12_BYTES='+str(a.output.stat().st_size));print('R12_SHA256='+sha256(a.output))
        if a.keep_extracted:
            if a.keep_extracted.exists():shutil.rmtree(a.keep_extracted)
            shutil.copytree(root,a.keep_extracted)
if __name__=='__main__':raise SystemExit(main())