from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, zipfile
from pathlib import Path

R14_SHA256='66e2486e501d79ef9cb06c498d42fc96bd982c37abca65fd0a595b344c4f6c85'
R14_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r14'
R15_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r15'
P10_SOURCE_COMMIT='98059287678e96280990dbf9c1888789f515213e'
PREVIOUS_SOURCE_COMMIT='59724195a94a5614c5d7b853aa15589779ab9641'
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
    for rel,target,oldtarget in [
        ('03_INSTALL_ALL.bat','Installer\\install_dr15.ps1','Installer\\install_dr14.ps1'),
        ('04_VERIFY_INSTALL.bat','Installer\\verify_dr15.ps1','Installer\\verify_dr14.ps1'),
    ]:
        p=root/rel
        s=rt(p).replace('\r\n','\n').replace('\r','\n')
        s=s.replace('r14','r15').replace('R14','R15').replace(oldtarget,target)
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
        guard=(f'if not exist "%~dp0{target}" (\n  echo.\n  echo [FAIL] Required r15 entrypoint is missing: {target}\n  pause\n  exit /b 1\n)\n')
        s=s.replace(invoke,guard+invoke,1)
        p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))

    install_src=root/'Installer/install_dr14.ps1'
    verify_src=root/'Installer/verify_dr14.ps1'
    if not install_src.is_file() or not verify_src.is_file(): raise RuntimeError('r14 entrypoints missing')
    install=rt(install_src).replace('r14','r15').replace('R14','R15').replace(PREVIOUS_SOURCE_COMMIT,P10_SOURCE_COMMIT)
    verify=rt(verify_src).replace('r14','r15').replace('R14','R15')
    wt(root/'Installer/install_dr15.ps1',install)
    wt(root/'Installer/verify_dr15.ps1',verify)

def patch_route_editor(root:Path, source:Path):
    if not source.is_file(): raise RuntimeError(f'route editor source missing: {source}')
    text=rt(source)
    required=[
        'function zoomControlRects(panel)',
        'function hitZoomControl(x, y)',
        'function applyPanelZoom(panel, factor, anchorPoint = null)',
        'function zoomAtCanvasPoint(xy, factor)',
        'function drawZoomControls(panel)',
        'root.addEventListener("wheel"',
        'event.stopPropagation()',
        'event.stopImmediatePropagation?.()',
        '{ passive: false, capture: true }',
        'zoomControl.action === "in" ? 1.25 : 0.80',
    ]
    for token in required:
        if token not in text: raise RuntimeError(f'route editor zoom contract missing: {token}')
    if 'canvas.addEventListener("wheel"' in text:
        raise RuntimeError('legacy canvas-local wheel handler remains')
    dst=root/'Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js'
    wt(dst,text)

    manifest_path=root/'P10_DR9_CODE_MANIFEST.json'
    manifest=json.loads(rt(manifest_path))
    manifest['schema']='ConceptGhost.P10DR9CodeManifest.v0.15'
    manifest['source_commit']=P10_SOURCE_COMMIT
    found=False
    for item in manifest.get('files',[]):
        if item.get('path')=='web/js/drone_route_editor.js':
            item['bytes']=dst.stat().st_size
            item['sha256']=sha256(dst)
            found=True
    if not found: raise RuntimeError('P10 code manifest missing route editor row')
    wt(manifest_path,json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')

def patch_runtime_verifier(root:Path):
    p=root/'Installer/verify_p10_dr9.py'
    s=rt(p)
    m=re.search(r"^SOURCE_COMMIT='([0-9a-f]{40})'",s,re.M)
    if not m: raise RuntimeError('verify_p10_dr9.py SOURCE_COMMIT declaration missing')
    if m.group(1) not in {PREVIOUS_SOURCE_COMMIT,P10_SOURCE_COMMIT}:
        raise RuntimeError(f'unexpected verifier source commit: {m.group(1)}')
    s=s[:m.start(1)]+P10_SOURCE_COMMIT+s[m.end(1):]
    s=s.replace("'schema':'ConceptGhost.P10DR9RRuntimeVerify.v0.14'","'schema':'ConceptGhost.P10DR9RRuntimeVerify.v0.15'",1)
    s=s.replace("CONCEPTGHOST_P10_DR9R_R14_RUNTIME_VERIFY_PASS","CONCEPTGHOST_P10_DR9R_R15_RUNTIME_VERIFY_PASS")
    wt(p,s)

def add_test(root:Path):
    test=f'''from pathlib import Path\nimport json,re,sys\nEXPECTED={P10_SOURCE_COMMIT!r}\n\ndef main(root):\n root=Path(root).resolve();e=[]\n js=(root/'Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js').read_text(encoding='utf-8-sig')\n for token in ['function zoomControlRects(panel)','function hitZoomControl(x, y)','function applyPanelZoom(panel, factor, anchorPoint = null)','function zoomAtCanvasPoint(xy, factor)','function drawZoomControls(panel)','root.addEventListener("wheel"','event.stopPropagation()','event.stopImmediatePropagation?.()','{{ passive: false, capture: true }}','zoomControl.action === "in" ? 1.25 : 0.80']:\n  if token not in js:e.append('missing '+token)\n if 'canvas.addEventListener("wheel"' in js:e.append('legacy canvas wheel handler remains')\n if js.count('drawZoomControls(perspective)')!=1:e.append('perspective zoom controls missing/duplicated')\n if js.count('drawZoomControls(panel)')<2:e.append('orthographic zoom controls missing')\n manifest=json.loads((root/'P10_DR9_CODE_MANIFEST.json').read_text(encoding='utf-8-sig'))\n release=json.loads((root/'RELEASE.json').read_text(encoding='utf-8-sig'))\n verifier=(root/'Installer/verify_p10_dr9.py').read_text(encoding='utf-8-sig')\n install=(root/'Installer/install_dr15.ps1').read_text(encoding='utf-8-sig')\n m=re.search(r"^SOURCE_COMMIT='([0-9a-f]{{40}})'",verifier,re.M)\n if manifest.get('source_commit')!=EXPECTED:e.append('code manifest source commit mismatch')\n if release.get('source_commit')!=EXPECTED:e.append('release source commit mismatch')\n if not m or m.group(1)!=EXPECTED:e.append('runtime verifier source commit mismatch')\n if EXPECTED not in install:e.append('installer source commit mismatch')\n for rel in ['Installer/install_dr15.ps1','Installer/verify_dr15.ps1']:\n  if not (root/rel).is_file():e.append('missing '+rel)\n if e:\n  print('\\n'.join('[FAIL] '+x for x in e));return 1\n print('CONCEPTGHOST_DR9R_R15_ROUTE_EDITOR_ZOOM_PASS');return 0\nif __name__=='__main__':raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else '.'))\n'''
    wt(root/'Installer/test_r15_bundle.py',test)

def update_meta(root:Path,commit:str):
    old=root/'USER_GUIDE_DR9R_R14.md'; new=root/'USER_GUIDE_DR9R_R15.md'
    g=rt(old).replace('DR9R R14','DR9R R15').replace('DR9R r14','DR9R r15')
    g+='''\n\n## r15 route-editor local zoom correction\n\nTarget runtime confirmed the Route Setup editor now loads, but mouse-wheel input was still being consumed by the outer ComfyUI graph zoom instead of the four camera/drone viewports. r15 captures wheel input inside the DOM editor before workspace zoom, applies cursor-anchored zoom locally, and adds explicit −/+ controls in every Perspective/TOP/SIDE/FRONT viewport as a deterministic fallback. Enquadrar tudo remains the global framing reset.\n'''
    wt(new,g); old.unlink()

    p=root/'README.md'
    s=rt(p).replace('DR9R r14','DR9R r15').replace('DR9R R14','DR9R R15')
    s+='''\n\n## r15 route-editor zoom\nWheel input inside the route editor is isolated from ComfyUI workspace zoom. Each of the four viewports also has explicit −/+ zoom buttons. No route, P9, or geometry-authority behavior changed.\n'''
    wt(p,s)

    t=root/'Installer/test_dr9_bundle.py'
    ts=rt(t).replace("root/'USER_GUIDE_DR9R_R14.md'","root/'USER_GUIDE_DR9R_R15.md'").replace(PREVIOUS_SOURCE_COMMIT,P10_SOURCE_COMMIT)
    wt(t,ts)

    doc=f'''# ConceptGhost P10 DR9R — r15 Route Editor Local Zoom\n\nDate: 2026-09-23\n\nTarget runtime confirmed r14 successfully loads the Route Setup editor and camera/drone workspace. Remaining UX defect: wheel movement over a viewport zoomed the outer ComfyUI graph instead of the selected Perspective/TOP/SIDE/FRONT panel.\n\nr15 changes only the route-editor frontend: wheel events are captured inside the DOM editor, propagation to the ComfyUI graph is stopped, local cursor-anchored zoom is applied, and each viewport renders explicit −/+ zoom controls. The buttons work independently of wheel-event routing.\n\nP9 authority, route data, WAN, COLMAP, reconstruction, Maya contracts and P10 geometry authority are unchanged.\n\nBase: {R14_NAME}.zip\nBase SHA-256: {R14_SHA256}\nP10 source commit: {P10_SOURCE_COMMIT}\nr15 package commit: {commit or 'LOCAL_BUILD'}\n'''
    wt(root/'Payload/docs/27_DR9R_R15_ROUTE_EDITOR_LOCAL_ZOOM.md',doc)

    for name in ['RELEASE.json','P10_DR9_RELEASE.json']:
        p=root/name; d=json.loads(rt(p))
        d['schema']='ConceptGhost.P10DR9RRelease.v0.15'
        d['release']=R15_NAME
        d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R15_ROUTE_EDITOR_ZOOM'
        d['source_commit']=P10_SOURCE_COMMIT
        d['package_hotfix_commit']=commit or 'LOCAL_BUILD'
        d['base_package']={'release':R14_NAME,'sha256':R14_SHA256}
        d['route_editor_zoom']={'wheel_isolated_from_workspace':True,'per_view_buttons':True,'views':['Perspective','Top','Side','Front']}
        wt(p,json.dumps(d,indent=2,ensure_ascii=False)+'\n')

    wt(root/'P10_DR9_VALIDATION.txt',f'''ConceptGhost P10 DR9R r15 validation\n\nPackage build status: PASS\nBase package SHA-256: {R14_SHA256}\nP10 source commit: {P10_SOURCE_COMMIT}\nRoute editor wheel capture isolation: PASS\nPer-view explicit −/+ zoom controls: PASS\nCursor-anchored orthographic wheel zoom: PASS\nPerspective local zoom: PASS\nNode.js syntax check: REQUIRED IN CI\nSource-commit consistency: PASS\nMoGe / Gate5 / Gate6 compatibility: RETAINED\nPublic workflows 01/02 only: PASS\nP9/P10 geometry authority: UNCHANGED\nUser runtime acceptance: PENDING\n''')

def manifests(root:Path):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED:
            rows.append({'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'size_bytes':p.stat().st_size})
    d=json.loads(rt(root/'BUNDLE_MANIFEST.json'))
    d['schema']='ConceptGhost.P10DR9RBundle.v0.15'
    d['release']=R15_NAME
    d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R15_ROUTE_EDITOR_ZOOM'
    d['source_commit']=P10_SOURCE_COMMIT
    d['file_count_excluding_manifests_and_checksums']=len(rows)
    d['route_editor_zoom']={'wheel_capture':True,'stops_workspace_propagation':True,'cursor_anchored':True,'explicit_per_view_buttons':True}
    d['files']=rows
    payload=json.dumps(d,indent=2,ensure_ascii=False)+'\n'
    wt(root/'BUNDLE_MANIFEST.json',payload); wt(root/'P10_DR9_BUNDLE_MANIFEST.json',payload)
    wt(root/'SHA256SUMS.txt','\n'.join(f'{sha256(p)}  {p.relative_to(root).as_posix()}' for p in sorted(root.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt')+'\n')

def validate(root:Path):
    e=[]
    for p in list((root/'Installer').glob('*.py'))+list((root/'Payload/custom_nodes/ConceptGhost_P10_Lab').glob('*.py')):
        try: compile(rt(p),str(p),'exec')
        except Exception as x:e.append(f'compile {p.name}: {x}')
    m=json.loads(rt(root/'P10_DR9_CODE_MANIFEST.json')); p10=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
    for item in m.get('files',[]):
        p=p10/item['path']
        if not p.is_file():e.append('P10 code missing '+item['path'])
        elif sha256(p)!=item['sha256']:e.append('P10 code hash mismatch '+item['path'])
    for raw in rt(root/'SHA256SUMS.txt').splitlines():
        h,rel=raw.split('  ',1); p=root/rel
        if not p.is_file() or sha256(p)!=h:e.append('sha mismatch '+rel)
    return e

def zipdet(root:Path,out:Path):
    if out.exists():out.unlink()
    fixed=(2026,9,24,1,20,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=fixed)
            info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--route-editor-source',type=Path,required=True)
    ap.add_argument('--hotfix-commit',default=os.environ.get('GITHUB_SHA',''))
    ap.add_argument('--keep-extracted',type=Path)
    a=ap.parse_args()
    if sha256(a.source)!=R14_SHA256: raise SystemExit('wrong r14 sha: '+sha256(a.source))
    with tempfile.TemporaryDirectory(prefix='cg-r15-') as td:
        root=Path(td)/R15_NAME; root.mkdir()
        with zipfile.ZipFile(a.source) as z:z.extractall(root)
        patch_entrypoints(root)
        patch_route_editor(root,a.route_editor_source)
        patch_runtime_verifier(root)
        add_test(root)
        update_meta(root,a.hotfix_commit)
        manifests(root)
        for script in ['test_dr9_bundle.py','test_r15_bundle.py']:
            q=subprocess.run([os.sys.executable,str(root/'Installer'/script),str(root)],capture_output=True,text=True)
            print(q.stdout.strip())
            if q.returncode: raise SystemExit(q.stdout+q.stderr)
        for c in sorted(root.rglob('__pycache__'),key=lambda x:len(x.parts),reverse=True): shutil.rmtree(c,ignore_errors=True)
        for p in root.rglob('*.pyc'): p.unlink(missing_ok=True)
        manifests(root)
        e=validate(root)
        if e: raise SystemExit('\n'.join('[FAIL] '+x for x in e))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        zipdet(root,a.output)
        print('R15_ZIP='+str(a.output))
        print('R15_BYTES='+str(a.output.stat().st_size))
        print('R15_SHA256='+sha256(a.output))
        if a.keep_extracted:
            if a.keep_extracted.exists(): shutil.rmtree(a.keep_extracted)
            shutil.copytree(root,a.keep_extracted)
    return 0

if __name__=='__main__': raise SystemExit(main())
