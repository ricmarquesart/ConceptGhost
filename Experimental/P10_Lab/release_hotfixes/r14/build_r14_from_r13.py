from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, tempfile, zipfile, re
from pathlib import Path

R13_SHA256='98361c6857d629f8780db601316f946626b7cd890f8b649abff0b5bf002e68cd'
R13_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r13'
R14_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r14'
P10_SOURCE_COMMIT='59724195a94a5614c5d7b853aa15589779ab9641'
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

def patch_entrypoints(root:Path):
    # BAT user entrypoints.
    for rel,target,oldtarget in [
        ('03_INSTALL_ALL.bat','Installer\\install_dr14.ps1','Installer\\install_dr13.ps1'),
        ('04_VERIFY_INSTALL.bat','Installer\\verify_dr14.ps1','Installer\\verify_dr13.ps1'),
    ]:
        p=root/rel
        s=rt(p).replace('\r\n','\n').replace('\r','\n')
        s=s.replace('r13','r14').replace('R13','R14').replace(oldtarget,target)
        # Remove any inherited guard for the new target, then insert one canonical guard.
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
        guard=(f'if not exist "%~dp0{target}" (\n  echo.\n  echo [FAIL] Required r14 entrypoint is missing: {target}\n  pause\n  exit /b 1\n)\n')
        s=s.replace(invoke,guard+invoke,1)
        p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))

    install_src=root/'Installer/install_dr13.ps1'
    verify_src=root/'Installer/verify_dr13.ps1'
    if not install_src.is_file() or not verify_src.is_file(): raise RuntimeError('r13 entrypoints missing')
    install=rt(install_src).replace('r13','r14').replace('R13','R14')
    install=install.replace('f9ca7c6070a10c9c39a241ef9ebe8c4822988f66',P10_SOURCE_COMMIT)
    wt(root/'Installer/install_dr14.ps1',install)
    verify=rt(verify_src).replace('r13','r14').replace('R13','R14')
    wt(root/'Installer/verify_dr14.ps1',verify)


def patch_runtime_verifier(root:Path):
    p=root/'Installer/verify_p10_dr9.py'
    s=rt(p)
    old="SOURCE_COMMIT='f9ca7c6070a10c9c39a241ef9ebe8c4822988f66'"
    if old not in s:
        # If base has already changed, require exact expected target instead of silently guessing.
        m=re.search(r"^SOURCE_COMMIT='([0-9a-f]{40})'",s,re.M)
        if not m: raise RuntimeError('verify_p10_dr9.py SOURCE_COMMIT declaration missing')
        if m.group(1)!=P10_SOURCE_COMMIT: raise RuntimeError(f'unexpected verifier source commit before patch: {m.group(1)}')
    else:
        s=s.replace(old,f"SOURCE_COMMIT='{P10_SOURCE_COMMIT}'",1)
    s=s.replace("'schema':'ConceptGhost.P10DR9RRuntimeVerify.v0.11'","'schema':'ConceptGhost.P10DR9RRuntimeVerify.v0.14'",1)
    s=s.replace("CONCEPTGHOST_P10_DR9R_R11_NESTED_INSTALLER_RUNTIME_VERIFY_PASS","CONCEPTGHOST_P10_DR9R_R14_RUNTIME_VERIFY_PASS")
    wt(p,s)


def add_test(root:Path):
    test=f'''from pathlib import Path\nimport json,re,sys\nEXPECTED={P10_SOURCE_COMMIT!r}\n\ndef main(root):\n root=Path(root).resolve();e=[]\n manifest=json.loads((root/'P10_DR9_CODE_MANIFEST.json').read_text(encoding='utf-8-sig'))\n release=json.loads((root/'RELEASE.json').read_text(encoding='utf-8-sig'))\n verifier=(root/'Installer/verify_p10_dr9.py').read_text(encoding='utf-8-sig')\n install=(root/'Installer/install_dr14.ps1').read_text(encoding='utf-8-sig')\n m=re.search(r\"^SOURCE_COMMIT='([0-9a-f]{{40}})'\",verifier,re.M)\n if manifest.get('source_commit')!=EXPECTED:e.append('code manifest source commit mismatch')\n if release.get('source_commit')!=EXPECTED:e.append('release source commit mismatch')\n if not m or m.group(1)!=EXPECTED:e.append('runtime verifier source commit mismatch')\n if EXPECTED not in install:e.append('install marker source commit mismatch')\n if 'f9ca7c6070a10c9c39a241ef9ebe8c4822988f66' in install:e.append('stale f9ca source remains in current r14 installer')\n for rel in ['Installer/install_dr14.ps1','Installer/verify_dr14.ps1']:\n  if not (root/rel).is_file():e.append('missing '+rel)\n ib=(root/'03_INSTALL_ALL.bat').read_text(encoding='utf-8-sig'); vb=(root/'04_VERIFY_INSTALL.bat').read_text(encoding='utf-8-sig')\n if 'Installer\\\\install_dr14.ps1' not in ib:e.append('03 target mismatch')\n if 'Installer\\\\verify_dr14.ps1' not in vb:e.append('04 target mismatch')\n if e:\n  print('\\n'.join('[FAIL] '+x for x in e));return 1\n print('CONCEPTGHOST_DR9R_R14_SOURCE_COMMIT_CONSISTENCY_PASS');return 0\nif __name__=='__main__':raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else '.'))\n'''
    wt(root/'Installer/test_r14_bundle.py',test)


def update_meta(root:Path,commit:str):
    old=root/'USER_GUIDE_DR9R_R13.md'; new=root/'USER_GUIDE_DR9R_R14.md'
    g=rt(old).replace('DR9R R13','DR9R R14').replace('DR9R r13','DR9R r14')
    g+='''\n\n## r14 source-commit consistency hotfix\n\nr13 installed Gate5/Gate6 successfully but its final DR9R verifier still hard-coded the pre-route-editor source commit. r14 makes the code manifest, release metadata, current installer marker and runtime verifier agree on the same P10 source commit. This is packaging/provenance consistency only; no geometry behavior is changed.\n'''
    wt(new,g); old.unlink()
    p=root/'README.md'; s=rt(p).replace('DR9R r13','DR9R r14').replace('DR9R R13','DR9R R14'); s+='''\n\n## r14 source-commit consistency\nThe final DR9R runtime verifier now validates the same P10 source commit recorded by the code manifest and release metadata. The r13 route-editor JavaScript repair is retained.\n'''; wt(p,s)
    t=root/'Installer/test_dr9_bundle.py'; wt(t,rt(t).replace("root/'USER_GUIDE_DR9R_R13.md'","root/'USER_GUIDE_DR9R_R14.md'"))
    doc=f'''# ConceptGhost P10 DR9R — r14 Source Commit Consistency Hotfix\n\nDate: 2026-09-23\n\nTarget r13 install passed base v1.53, Gate5 WAN, Gate6 code/COLMAP and reconstruction verification, then failed at final DR9R verification with `unexpected DR9R source commit`. The r13 package correctly changed `P10_DR9_CODE_MANIFEST.json` to the route-editor fix commit, but `verify_p10_dr9.py` and current install marker still referenced the older source commit.\n\nr14 aligns all current release/runtime provenance checks to `{P10_SOURCE_COMMIT}` and adds a regression test that fails if manifest, release, installer or runtime verifier diverge again.\n\nNo P9/P10 geometry-authority behavior changed.\n\nBase: {R13_NAME}.zip\nBase SHA-256: {R13_SHA256}\nr14 package commit: {commit or 'LOCAL_BUILD'}\n'''
    wt(root/'Payload/docs/26_DR9R_R14_SOURCE_COMMIT_CONSISTENCY.md',doc)
    for name in ['RELEASE.json','P10_DR9_RELEASE.json']:
        p=root/name; d=json.loads(rt(p)); d['schema']='ConceptGhost.P10DR9RRelease.v0.14'; d['release']=R14_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R14_SOURCE_COMMIT_HOTFIX'; d['source_commit']=P10_SOURCE_COMMIT; d['package_hotfix_commit']=commit or 'LOCAL_BUILD'; d['base_package']={'release':R13_NAME,'sha256':R13_SHA256}; wt(p,json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    wt(root/'P10_DR9_VALIDATION.txt',f'''ConceptGhost P10 DR9R r14 validation\n\nPackage build status: PASS\nBase package SHA-256: {R13_SHA256}\nP10 source commit: {P10_SOURCE_COMMIT}\nCode manifest / release / installer / runtime verifier source-commit consistency: PASS\nRoute editor frontend repair: RETAINED\nMoGe Evidence compatibility: RETAINED\nGate5/Gate6 compatibility: RETAINED\nVersioned BAT entrypoints: RETAINED\nPublic workflows 01/02 only: PASS\nP9/P10 geometry authority: UNCHANGED\nUser runtime acceptance: PENDING\n''')


def manifests(root:Path):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED:
            rows.append({'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'size_bytes':p.stat().st_size})
    d=json.loads(rt(root/'BUNDLE_MANIFEST.json')); d['schema']='ConceptGhost.P10DR9RBundle.v0.14'; d['release']=R14_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R14_SOURCE_COMMIT_HOTFIX'; d['source_commit']=P10_SOURCE_COMMIT; d['file_count_excluding_manifests_and_checksums']=len(rows); d['source_commit_consistency']={'code_manifest':P10_SOURCE_COMMIT,'release':P10_SOURCE_COMMIT,'runtime_verifier':P10_SOURCE_COMMIT,'current_installer':P10_SOURCE_COMMIT}; d['files']=rows
    payload=json.dumps(d,indent=2,ensure_ascii=False)+'\n'; wt(root/'BUNDLE_MANIFEST.json',payload); wt(root/'P10_DR9_BUNDLE_MANIFEST.json',payload)
    wt(root/'SHA256SUMS.txt','\n'.join(f'{sha256(p)}  {p.relative_to(root).as_posix()}' for p in sorted(root.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt')+'\n')


def validate(root:Path):
    e=[]
    for p in list((root/'Installer').glob('*.py'))+list((root/'Payload/custom_nodes/ConceptGhost_P10_Lab').glob('*.py')):
        try: compile(rt(p),str(p),'exec')
        except Exception as x:e.append(f'compile {p.name}: {x}')
    for raw in rt(root/'SHA256SUMS.txt').splitlines():
        h,rel=raw.split('  ',1); p=root/rel
        if not p.is_file() or sha256(p)!=h:e.append('sha mismatch '+rel)
    return e


def zipdet(root:Path,out:Path):
    if out.exists():out.unlink()
    fixed=(2026,9,23,23,35,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=fixed);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--hotfix-commit',default=os.environ.get('GITHUB_SHA','')); ap.add_argument('--keep-extracted',type=Path); a=ap.parse_args()
    if sha256(a.source)!=R13_SHA256: raise SystemExit('wrong r13 sha: '+sha256(a.source))
    with tempfile.TemporaryDirectory(prefix='cg-r14-') as td:
        root=Path(td)/R14_NAME; root.mkdir()
        with zipfile.ZipFile(a.source) as z:z.extractall(root)
        patch_entrypoints(root); patch_runtime_verifier(root); add_test(root); update_meta(root,a.hotfix_commit); manifests(root)
        for script in ['test_dr9_bundle.py','test_r14_bundle.py']:
            q=subprocess.run([os.sys.executable,str(root/'Installer'/script),str(root)],capture_output=True,text=True); print(q.stdout.strip())
            if q.returncode: raise SystemExit(q.stdout+q.stderr)
        for c in sorted(root.rglob('__pycache__'),key=lambda x:len(x.parts),reverse=True): shutil.rmtree(c,ignore_errors=True)
        for p in root.rglob('*.pyc'): p.unlink(missing_ok=True)
        manifests(root); e=validate(root)
        if e: raise SystemExit('\n'.join('[FAIL] '+x for x in e))
        a.output.parent.mkdir(parents=True,exist_ok=True); zipdet(root,a.output)
        print('R14_ZIP='+str(a.output)); print('R14_BYTES='+str(a.output.stat().st_size)); print('R14_SHA256='+sha256(a.output))
        if a.keep_extracted:
            if a.keep_extracted.exists(): shutil.rmtree(a.keep_extracted)
            shutil.copytree(root,a.keep_extracted)
    return 0

if __name__=='__main__': raise SystemExit(main())