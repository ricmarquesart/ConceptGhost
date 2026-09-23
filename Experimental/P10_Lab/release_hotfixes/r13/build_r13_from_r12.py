from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, tempfile, zipfile
from pathlib import Path

R12_SHA256='334f926dc8ecb86172ed1839201abd1e7d3994d64b5386c72cd2dc215e529bdb'
R12_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r12'
R13_NAME='ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r13'
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
    for rel,target in [('03_INSTALL_ALL.bat','Installer\\install_dr13.ps1'),('04_VERIFY_INSTALL.bat','Installer\\verify_dr13.ps1')]:
        p=root/rel
        s=rt(p).replace('\r\n','\n').replace('\r','\n').replace('r12','r13').replace('R12','R13')
        if rel.startswith('03_'): s=s.replace('Installer\\install_dr12.ps1','Installer\\install_dr13.ps1')
        else: s=s.replace('Installer\\verify_dr12.ps1','Installer\\verify_dr13.ps1')
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
        guard=(f'if not exist "%~dp0{target}" (\n  echo.\n  echo [FAIL] Required r13 entrypoint is missing: {target}\n  pause\n  exit /b 1\n)\n')
        s=s.replace(invoke,guard+invoke,1)
        p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    install_src=root/'Installer/install_dr12.ps1'; verify_src=root/'Installer/verify_dr12.ps1'
    if not install_src.is_file() or not verify_src.is_file(): raise RuntimeError('r12 entrypoints missing')
    wt(root/'Installer/install_dr13.ps1',rt(install_src).replace('r12','r13').replace('R12','R13'))
    wt(root/'Installer/verify_dr13.ps1',rt(verify_src).replace('r12','r13').replace('R12','R13'))
    install_src.unlink(); verify_src.unlink()

def patch_route_editor(root:Path, source:Path):
    if not source.is_file(): raise RuntimeError(f'route editor source missing: {source}')
    text=rt(source)
    forbidden=(
        'function pushHistory()    };',
        'function perspectivePanel() {    function perspectivePanel() {',
        'function eventCoordinates(event) {    function eventCoordinates(event) {',
        'droneSelect.addEventListener("change", () => {    droneSelect.addEventListener("change", () => {',
    )
    for bad in forbidden:
        if bad in text: raise RuntimeError(f'route editor source still corrupt: {bad}')
    required={
        'function pushHistory() {':1,
        'function perspectivePanel() {':1,
        'function eventCoordinates(event) {':1,
        'droneSelect.addEventListener("change", () => {':1,
        'node.addDOMWidget("cg_drone_route_editor"':1,
        'chainCallback(node, "onExecuted"':1,
    }
    for token,count in required.items():
        actual=text.count(token)
        if actual!=count: raise RuntimeError(f'route editor contract {token!r}: expected {count}, got {actual}')
    dst=root/'Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js'
    wt(dst,text)

    manifest_path=root/'P10_DR9_CODE_MANIFEST.json'
    manifest=json.loads(rt(manifest_path))
    manifest['schema']='ConceptGhost.P10DR9CodeManifest.v0.13'
    manifest['source_commit']=P10_SOURCE_COMMIT
    found=False
    for item in manifest.get('files',[]):
        if item.get('path')=='web/js/drone_route_editor.js':
            item['bytes']=dst.stat().st_size
            item['sha256']=sha256(dst)
            found=True
    if not found: raise RuntimeError('P10 code manifest missing route editor entry')
    wt(manifest_path,json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')

def add_test(root:Path):
    test='''from pathlib import Path\nimport json,sys\n\ndef main(root):\n root=Path(root).resolve();e=[]\n js=(root/"Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js").read_text(encoding="utf-8-sig")\n checks={\n  "function pushHistory() {":1,\n  "function perspectivePanel() {":1,\n  "function eventCoordinates(event) {":1,\n  'droneSelect.addEventListener("change", () => {':1,\n  'node.addDOMWidget("cg_drone_route_editor"':1,\n  'chainCallback(node, "onExecuted"':1,\n }\n for token,count in checks.items():\n  if js.count(token)!=count:e.append(f"{token}: expected {count}, got {js.count(token)}")\n for bad in ["function pushHistory()    };","function perspectivePanel() {    function perspectivePanel() {","function eventCoordinates(event) {    function eventCoordinates(event) {",'droneSelect.addEventListener("change", () => {    droneSelect.addEventListener("change", () => {']:\n  if bad in js:e.append("corrupt JS token remains: "+bad)\n m=json.loads((root/"P10_DR9_CODE_MANIFEST.json").read_text(encoding="utf-8-sig"))\n if m.get("source_commit")!="59724195a94a5614c5d7b853aa15589779ab9641":e.append("P10 source commit mismatch")\n row=next((x for x in m.get("files",[]) if x.get("path")=="web/js/drone_route_editor.js"),None)\n if not row:e.append("route editor manifest row missing")\n for rel in ["Installer/install_dr13.ps1","Installer/verify_dr13.ps1"]:\n  if not (root/rel).is_file():e.append("missing "+rel)\n r=json.loads((root/"RELEASE.json").read_text(encoding="utf-8-sig"))\n if not str(r.get("release","")).endswith("_r13"):e.append("release metadata mismatch")\n if e:\n  print("\\n".join("[FAIL] "+x for x in e));return 1\n print("CONCEPTGHOST_DR9R_R13_ROUTE_EDITOR_FRONTEND_PASS");return 0\nif __name__=="__main__":raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else "."))\n'''
    wt(root/'Installer/test_r13_bundle.py',test)

def update_meta(root:Path,commit:str):
    old=root/'USER_GUIDE_DR9R_R12.md'; new=root/'USER_GUIDE_DR9R_R13.md'
    g=rt(old).replace('DR9R R12','DR9R R13').replace('DR9R r12','DR9R r13')
    g+='''\n\n## r13 route editor frontend hotfix\n\nThe Route Setup backend completed successfully, but the browser-side drone route editor did not load because its JavaScript contained malformed duplicated declarations. r13 repairs the frontend syntax and adds source/package regressions plus Node.js syntax validation in CI. The intended toolbar (+ Drone, camera aim/orientation controls, Resetar rota, Enquadrar tudo) and Perspective/TOP/SIDE/FRONT workspace are restored.\n'''
    wt(new,g); old.unlink()
    p=root/'README.md'; s=rt(p).replace('DR9R r12','DR9R r13').replace('DR9R R12','DR9R R13'); s+='''\n\n## r13 drone-route editor frontend repair\nRun #1 backend output was valid, but malformed JavaScript prevented the DOM route editor from mounting. r13 restores the interactive map/camera toolbar without changing P9/P10 geometry authority.\n'''; wt(p,s)
    t=root/'Installer/test_dr9_bundle.py'; wt(t,rt(t).replace("root/'USER_GUIDE_DR9R_R12.md'","root/'USER_GUIDE_DR9R_R13.md'").replace('f9ca7c6070a10c9c39a241ef9ebe8c4822988f66',P10_SOURCE_COMMIT))
    doc=f'''# ConceptGhost P10 DR9R — r13 Route Editor Frontend Repair\n\nDate: 2026-09-23\n\nTarget-machine evidence: Workflow 01 Run #1 completed successfully, but the Step-2 Route Authoring node displayed a blank grey editor area and no drone/camera controls. The backend had returned route-editor metadata; the browser extension failed to parse because `drone_route_editor.js` contained malformed duplicated declarations.\n\nr13 repairs those syntax defects, validates the JavaScript with `node --check` in CI, and preserves the full interactive editor contract: + Drone / remove, PATH / 360, camera aim modes, target editing, yaw/pitch, Resetar rota, Enquadrar tudo, Perspective/TOP/SIDE/FRONT pan/zoom/orbit.\n\nNo P9 or P10 geometry-authority policy changes.\n\nBase: {R12_NAME}.zip\nBase SHA-256: {R12_SHA256}\nP10 source commit: {P10_SOURCE_COMMIT}\nr13 package commit: {commit or 'LOCAL_BUILD'}\n'''
    wt(root/'Payload/docs/25_DR9R_R13_ROUTE_EDITOR_FRONTEND_REPAIR.md',doc)
    for name in ['RELEASE.json','P10_DR9_RELEASE.json']:
        p=root/name; d=json.loads(rt(p)); d['schema']='ConceptGhost.P10DR9RRelease.v0.13'; d['release']=R13_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R13_ROUTE_EDITOR_HOTFIX'; d['source_commit']=P10_SOURCE_COMMIT; d['package_hotfix_commit']=commit or 'LOCAL_BUILD'; d['base_package']={'release':R12_NAME,'sha256':R12_SHA256}; wt(p,json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    wt(root/'P10_DR9_VALIDATION.txt',f'''ConceptGhost P10 DR9R r13 validation\n\nPackage build status: PASS\nBase package SHA-256: {R12_SHA256}\nP10 source commit: {P10_SOURCE_COMMIT}\nRoute editor malformed/duplicate JavaScript declarations: REMOVED\nRoute editor DOM widget contract: PASS\nNode.js syntax check: REQUIRED IN CI\nMoGe Evidence r12 compatibility: RETAINED\nGate5/Gate6 compatibility: RETAINED\nVersioned BAT entrypoints: RETAINED\nPublic workflows 01/02 only: PASS\nP9/P10 geometry authority: UNCHANGED\nUser runtime acceptance: PENDING\n''')

def manifests(root:Path):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED: rows.append({'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'size_bytes':p.stat().st_size})
    d=json.loads(rt(root/'BUNDLE_MANIFEST.json')); d['schema']='ConceptGhost.P10DR9RBundle.v0.13'; d['release']=R13_NAME; d['status']='READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R13_ROUTE_EDITOR_HOTFIX'; d['source_commit']=P10_SOURCE_COMMIT; d['file_count_excluding_manifests_and_checksums']=len(rows); d['route_editor_frontend']={'javascript_syntax_repaired':True,'dom_widget_expected':True,'controls_expected':['+ Drone','PATH','360','Aim','Editar alvo','Yaw','Pitch','Resetar rota','Enquadrar tudo']}; d['files']=rows
    payload=json.dumps(d,indent=2,ensure_ascii=False)+'\n'; wt(root/'BUNDLE_MANIFEST.json',payload); wt(root/'P10_DR9_BUNDLE_MANIFEST.json',payload)
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
    fixed=(2026,9,23,23,20,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=fixed);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--route-editor-source',type=Path,required=True); ap.add_argument('--hotfix-commit',default=os.environ.get('GITHUB_SHA','')); ap.add_argument('--keep-extracted',type=Path); a=ap.parse_args()
    if sha256(a.source)!=R12_SHA256: raise SystemExit('wrong r12 sha: '+sha256(a.source))
    with tempfile.TemporaryDirectory(prefix='cg-r13-') as td:
        root=Path(td)/R13_NAME; root.mkdir()
        with zipfile.ZipFile(a.source) as z:z.extractall(root)
        patch_entrypoints(root); patch_route_editor(root,a.route_editor_source); add_test(root); update_meta(root,a.hotfix_commit); manifests(root)
        for script in ['test_dr9_bundle.py','test_r13_bundle.py']:
            q=subprocess.run([os.sys.executable,str(root/'Installer'/script),str(root)],capture_output=True,text=True); print(q.stdout.strip())
            if q.returncode: raise SystemExit(q.stdout+q.stderr)
        for c in sorted(root.rglob('__pycache__'),key=lambda x:len(x.parts),reverse=True): shutil.rmtree(c,ignore_errors=True)
        for p in root.rglob('*.pyc'): p.unlink(missing_ok=True)
        manifests(root); e=validate(root)
        if e: raise SystemExit('\n'.join('[FAIL] '+x for x in e))
        a.output.parent.mkdir(parents=True,exist_ok=True); zipdet(root,a.output)
        print('R13_ZIP='+str(a.output)); print('R13_BYTES='+str(a.output.stat().st_size)); print('R13_SHA256='+sha256(a.output))
        if a.keep_extracted:
            if a.keep_extracted.exists(): shutil.rmtree(a.keep_extracted)
            shutil.copytree(root,a.keep_extracted)
    return 0

if __name__=='__main__': raise SystemExit(main())
