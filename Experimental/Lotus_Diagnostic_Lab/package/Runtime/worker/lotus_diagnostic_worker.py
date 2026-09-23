from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def now_id() -> str:
    return time.strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:10]


def ensure_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert('RGB')


def save_placeholder(path: Path, title: str, subtitle: str = ''):
    img = Image.new('RGB', (900, 500), (28, 28, 28))
    d = ImageDraw.Draw(img)
    d.text((35, 45), title, fill=(235,235,235))
    if subtitle:
        d.multiline_text((35, 100), subtitle, fill=(180,180,180), spacing=8)
    img.save(path)


def normalize01(arr: np.ndarray, lo_p=1.0, hi_p=99.0):
    a = np.asarray(arr, dtype=np.float32)
    finite = np.isfinite(a)
    if not finite.any():
        return np.zeros_like(a, dtype=np.float32), 0.0, 1.0
    vals = a[finite]
    lo = float(np.percentile(vals, lo_p))
    hi = float(np.percentile(vals, hi_p))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        lo, hi = float(vals.min()), float(vals.max())
    if hi <= lo:
        hi = lo + 1e-6
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~finite] = 0
    return out, lo, hi


def save_gray01(arr01: np.ndarray, path: Path):
    Image.fromarray(np.clip(arr01 * 255.0, 0, 255).astype(np.uint8), mode='L').convert('RGB').save(path)


def save_heatmap(arr01: np.ndarray, path: Path):
    u8 = np.clip(arr01 * 255.0, 0, 255).astype(np.uint8)
    heat = cv2.applyColorMap(u8, cv2.COLORMAP_TURBO)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    Image.fromarray(heat).save(path)


def save_bands(arr01: np.ndarray, path: Path, bands=12):
    q = np.floor(np.clip(arr01, 0, 0.999999) * bands) / max(1, bands - 1)
    save_heatmap(q, path)


def save_edges(arr01: np.ndarray, path: Path):
    f = arr01.astype(np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mag01, _, _ = normalize01(mag, 2, 99)
    save_gray01(mag01, path)


def save_contours(arr01: np.ndarray, base_rgb: Image.Image, path: Path, levels=12):
    base = np.array(base_rgb.resize((arr01.shape[1], arr01.shape[0]), Image.Resampling.BILINEAR), dtype=np.uint8)
    q = np.floor(np.clip(arr01, 0, 0.999999) * levels).astype(np.uint8)
    edge = cv2.Canny((q * max(1, 255 // max(levels,1))).astype(np.uint8), 20, 60)
    out = base.copy()
    out[edge > 0] = np.array([255, 70, 20], dtype=np.uint8)
    Image.fromarray(out).save(path)


def pointcloud_from_relative_depth(depth01: np.ndarray, rgb: np.ndarray, fov_deg: float, stride: int = 5):
    h, w = depth01.shape
    z = 0.25 + 3.75 * depth01
    f = 0.5 * w / math.tan(math.radians(fov_deg) * 0.5)
    ys, xs = np.mgrid[0:h:stride, 0:w:stride]
    zs = z[0:h:stride, 0:w:stride]
    X = (xs - (w - 1) * 0.5) * zs / f
    Y = -((ys - (h - 1) * 0.5) * zs / f)
    pts = np.stack([X, Y, zs], axis=-1).reshape(-1, 3)
    cols = rgb[0:h:stride, 0:w:stride].reshape(-1, 3)
    finite = np.isfinite(pts).all(axis=1)
    return pts[finite].astype(np.float32), cols[finite].astype(np.uint8)


def write_ply(path: Path, pts: np.ndarray, cols: np.ndarray):
    with path.open('w', encoding='ascii', newline='\n') as f:
        f.write('ply\nformat ascii 1.0\n')
        f.write(f'element vertex {len(pts)}\n')
        f.write('property float x\nproperty float y\nproperty float z\n')
        f.write('property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
        for p, c in zip(pts, cols):
            f.write(f'{p[0]:.7f} {p[1]:.7f} {p[2]:.7f} {int(c[0])} {int(c[1])} {int(c[2])}\n')


def render_pointcloud_views(pts: np.ndarray, cols: np.ndarray, out_path: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if len(pts) > 30000:
        idx = np.linspace(0, len(pts)-1, 30000).astype(int)
        pts, cols = pts[idx], cols[idx]
    c = cols.astype(np.float32) / 255.0
    fig = plt.figure(figsize=(12, 10), dpi=120)
    views = [
        ('FRONT · relative', 20, -90),
        ('SIDE · relative', 15, 0),
        ('TOP · relative', 90, -90),
        ('3D · relative', 25, -60),
    ]
    for i, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection='3d')
        ax.scatter(pts[:,0], pts[:,2], pts[:,1], c=c, s=0.35, linewidths=0)
        ax.set_title(title)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
    fig.suptitle('Lotus relative point-cloud preview · assumed FOV · NOT METRIC', fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def make_mosaic(paths, labels, out_path: Path):
    ims = []
    for p in paths:
        im = ensure_rgb(Path(p))
        im.thumbnail((520, 360), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (540, 410), 'black')
        canvas.paste(im, ((540-im.width)//2, 35))
        ims.append(canvas)
    cols = 3
    rows = math.ceil(len(ims)/cols)
    out = Image.new('RGB', (cols*540, rows*410), (18,18,18))
    d = ImageDraw.Draw(out)
    for i, (im, label) in enumerate(zip(ims, labels)):
        x=(i%cols)*540; y=(i//cols)*410
        out.paste(im,(x,y))
        d.text((x+12,y+10),label,fill=(240,240,240))
    out.save(out_path)


def _tail_text(path: Path, max_lines: int = 120, max_chars: int = 16000) -> str:
    try:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()[-max_lines:]
        text = "\n".join(lines)
        return text[-max_chars:]
    except Exception as e:
        return f"<unable to read log tail: {e!r}>"


def run_infer(python_exe: Path, source_root: Path, model_path: Path, input_dir: Path, output_dir: Path,
              task: str, disparity: bool, processing_res: int, log_path: Path):
    runtime_root = python_exe.parent.parent
    adapter = runtime_root/'Worker'/'lotus_infer_adapter.py'
    if not adapter.is_file():
        raise RuntimeError(f'Missing isolated Lotus inference adapter: {adapter}')
    cmd = [str(python_exe), str(adapter),
           '--source-root', str(source_root), '--model-path', str(model_path),
           '--output-dir', str(output_dir), '--input-dir', str(input_dir),
           '--task', task, '--processing-res', str(processing_res),
           '--memory-mode', 'auto']
    if disparity:
        cmd.append('--disparity')
    env = os.environ.copy()
    env['PYTHONPATH'] = str(source_root)
    env['PYTHONNOUSERSITE'] = '1'
    with log_path.open('w', encoding='utf-8', errors='replace') as log:
        cp = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(source_root))
    if cp.returncode != 0:
        tail = _tail_text(log_path)
        raise RuntimeError(
            f'Lotus {task} inference failed with code {cp.returncode}.\n'
            f'Log: {log_path}\n--- inference log tail ---\n{tail}\n--- end log tail ---'
        )


def find_single(directory: Path, pattern: str) -> Path:
    hits = list(directory.rglob(pattern))
    if len(hits) != 1:
        raise RuntimeError(f'Expected exactly one {pattern} below {directory}, found {len(hits)}')
    return hits[0]


def self_test(runtime_root: Path):
    cfg_path = runtime_root/'Manifests'/'runtime_config.json'
    if not cfg_path.is_file():
        raise RuntimeError(f'Missing {cfg_path}')
    cfg=json.loads(cfg_path.read_text(encoding='utf-8'))
    for key in ('depth','normal'):
        p=Path(cfg['models'][key]['snapshot_path'])
        if not p.exists(): raise RuntimeError(f'Missing model snapshot: {p}')
    src=Path(cfg['source_root'])
    for name in ('infer.py','pipeline.py'):
        if not (src/name).is_file(): raise RuntimeError(f'Missing Lotus source: {src/name}')
    adapter=runtime_root/'Worker'/'lotus_infer_adapter.py'
    if not adapter.is_file(): raise RuntimeError(f'Missing isolated inference adapter: {adapter}')
    import numpy, cv2, PIL, matplotlib, torch, diffusers, transformers, safetensors
    cuda={'available':bool(torch.cuda.is_available()), 'torch_cuda':torch.version.cuda}
    if torch.cuda.is_available():
        cuda.update({'device':torch.cuda.get_device_name(0),'total_vram':int(torch.cuda.get_device_properties(0).total_memory)})
    print(json.dumps({'status':'PASS','runtime_root':str(runtime_root),'numpy':numpy.__version__,'cv2':cv2.__version__,'pillow':PIL.__version__,'matplotlib':matplotlib.__version__,'torch':torch.__version__,'diffusers':diffusers.__version__,'transformers':transformers.__version__,'cuda':cuda}, indent=2))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--runtime-root', required=True)
    ap.add_argument('--input')
    ap.add_argument('--processing-res', type=int, default=768)
    ap.add_argument('--save-raw', action='store_true')
    ap.add_argument('--preview-3d', action='store_true')
    ap.add_argument('--extended', action='store_true')
    ap.add_argument('--assumed-fov', type=float, default=60.0)
    ap.add_argument('--self-test', action='store_true')
    args=ap.parse_args()
    root=Path(args.runtime_root).resolve()
    if args.self_test:
        self_test(root); return
    if not args.input:
        ap.error('--input is required unless --self-test is used')
    input_path=Path(args.input).resolve()
    cfg=json.loads((root/'Manifests'/'runtime_config.json').read_text(encoding='utf-8'))
    source_root=Path(cfg['source_root'])
    python_exe=root/'Python'/'python.exe'
    run_id=now_id(); run=root/'Outputs'/run_id
    inp=run/'input'; native=run/'native'; diag=run/'diagnostics'; raw=run/'raw'; logs=run/'logs'
    for d in (inp,native,diag,raw,logs): d.mkdir(parents=True, exist_ok=True)
    src_ext=input_path.suffix.lower() if input_path.suffix.lower() in ('.png','.jpg','.jpeg') else '.png'
    local_input=inp/('source'+src_ext)
    ensure_rgb(input_path).save(local_input)
    manifest={
      'schema':'ConceptGhost.LotusDiagnostic.RunManifest.v1', 'run_id':run_id, 'status':'RUNNING',
      'purpose':'DIAGNOSTIC_ONLY', 'authority':'NONE_OFFICIAL_GEOMETRY', 'geometry_impact':'NONE',
      'input':{'path':str(local_input),'sha256':sha256_file(local_input)},
      'models':cfg['models'], 'processing_res':args.processing_res,
      'toggles':{'save_raw_outputs':args.save_raw,'enable_3d_preview':args.preview_3d,'enable_extended_diagnostics':args.extended},
      'pointcloud':{'metric':False,'source':'inverse normalized disparity','assumed_fov_degrees':args.assumed_fov},
      'outputs':{}, 'warnings':['Lotus disparity is relative/non-metric. Inverse disparity is a visualization proxy, not metric depth.']
    }
    man_path=run/'manifest.json'
    try:
        depth_out=native/'depth'; normal_out=native/'normal'
        run_infer(python_exe,source_root,Path(cfg['models']['depth']['snapshot_path']),inp,depth_out,'depth',True,args.processing_res,logs/'depth_inference.log')
        run_infer(python_exe,source_root,Path(cfg['models']['normal']['snapshot_path']),inp,normal_out,'normal',False,args.processing_res,logs/'normal_inference.log')
        depth_npy=find_single(depth_out/'depth','*.npy')
        normal_npy=find_single(normal_out/'normal','*.npy')
        depth_vis=find_single(depth_out/'depth_vis','*.png')
        normal_vis=find_single(normal_out/'normal_vis','*.png')
        disparity=np.load(depth_npy).astype(np.float32)
        if disparity.ndim==3: disparity=disparity.mean(axis=-1)
        normal=np.load(normal_npy).astype(np.float32)
        src=ensure_rgb(local_input).resize((disparity.shape[1],disparity.shape[0]), Image.Resampling.BILINEAR)
        src_np=np.array(src,dtype=np.uint8)
        disp01,lo,hi=normalize01(disparity)
        rel_depth=1.0/(0.05+0.95*disp01)
        rel01,_,_=normalize01(rel_depth)
        paths={}
        paths['original']=diag/'00_original.png'; src.save(paths['original'])
        paths['native_disparity_preview']=diag/'01_lotus_native_disparity_preview.png'; shutil.copy2(depth_vis,paths['native_disparity_preview'])
        paths['disparity_grayscale']=diag/'02_lotus_disparity_grayscale.png'; save_gray01(disp01,paths['disparity_grayscale'])
        paths['disparity_heatmap']=diag/'03_lotus_disparity_heatmap.png'; save_heatmap(disp01,paths['disparity_heatmap'])
        paths['relative_depth_proxy']=diag/'04_lotus_inverse_disparity_relative_depth.png'; save_gray01(rel01,paths['relative_depth_proxy'])
        paths['normal_native']=diag/'08_lotus_normal_native.png'; shutil.copy2(normal_vis,paths['normal_native'])
        if args.extended:
            paths['depth_bands']=diag/'05_lotus_relative_depth_bands.png'; save_bands(rel01,paths['depth_bands'])
            paths['depth_contours']=diag/'06_lotus_relative_depth_contours.png'; save_contours(rel01,src,paths['depth_contours'])
            paths['depth_edges']=diag/'07_lotus_disparity_edges.png'; save_edges(disp01,paths['depth_edges'])
        else:
            for k,fn,title in [
                ('depth_bands','05_lotus_relative_depth_bands.png','Extended diagnostics disabled'),
                ('depth_contours','06_lotus_relative_depth_contours.png','Extended diagnostics disabled'),
                ('depth_edges','07_lotus_disparity_edges.png','Extended diagnostics disabled')]:
                paths[k]=diag/fn; save_placeholder(paths[k],title,'Enable Lotus Extended Diagnostics in the ComfyUI node.')
        pc_ply=raw/'lotus_relative_pointcloud.ply'
        paths['pointcloud_preview']=diag/'09_lotus_relative_pointcloud_preview.png'
        if args.preview_3d:
            pts,cols=pointcloud_from_relative_depth(rel01,src_np,args.assumed_fov)
            write_ply(pc_ply,pts,cols)
            render_pointcloud_views(pts,cols,paths['pointcloud_preview'])
        else:
            save_placeholder(paths['pointcloud_preview'],'3D preview disabled','Enable Lotus 3D Preview. Any generated point cloud is relative/non-metric.')
        stats_vals=disparity[np.isfinite(disparity)]
        stats={'count':int(stats_vals.size),'min':float(stats_vals.min()),'max':float(stats_vals.max()),'mean':float(stats_vals.mean()),'std':float(stats_vals.std()),
               'percentiles':{str(p):float(np.percentile(stats_vals,p)) for p in [1,5,25,50,75,95,99]},
               'normal_shape':list(normal.shape),'disparity_shape':list(disparity.shape),'normalization_clip':{'p1':lo,'p99':hi}}
        stats_path=run/'stats.json'; stats_path.write_text(json.dumps(stats,indent=2),encoding='utf-8')
        paths['comparison_mosaic']=diag/'10_lotus_comparison_mosaic.png'
        order=['original','disparity_grayscale','disparity_heatmap','relative_depth_proxy','depth_bands','depth_contours','depth_edges','normal_native','pointcloud_preview']
        labels=['Original','Lotus disparity · grayscale','Lotus disparity · heatmap','Inverse disparity · relative-depth proxy','Relative-depth bands','Relative-depth contours','Disparity edges','Lotus native normals','Relative point-cloud preview']
        make_mosaic([paths[k] for k in order],labels,paths['comparison_mosaic'])
        if args.save_raw:
            shutil.copy2(depth_npy, raw/'lotus_disparity_native.npy')
            shutil.copy2(normal_npy, raw/'lotus_normal_native.npy')
        shutil.rmtree(native, ignore_errors=True)
        manifest['outputs']={k:{'path':str(v),'sha256':sha256_file(v)} for k,v in paths.items()}
        manifest['outputs']['stats']={'path':str(stats_path),'sha256':sha256_file(stats_path)}
        if args.save_raw:
            for p in [raw/'lotus_disparity_native.npy',raw/'lotus_normal_native.npy']:
                manifest['outputs'][p.stem]={'path':str(p),'sha256':sha256_file(p)}
        if args.preview_3d and pc_ply.exists():
            manifest['outputs']['relative_pointcloud_ply']={'path':str(pc_ply),'sha256':sha256_file(pc_ply),'metric':False}
        manifest['status']='PASS'; manifest['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        man_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(json.dumps({'status':'PASS','run_dir':str(run),'manifest':str(man_path),'outputs':{k:str(v) for k,v in paths.items()}},ensure_ascii=False))
    except Exception as e:
        manifest['status']='FAIL'; manifest['error']=repr(e); manifest['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        man_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(json.dumps({'status':'FAIL','run_dir':str(run),'manifest':str(man_path),'error':repr(e)}),file=sys.stderr)
        raise

if __name__=='__main__':
    main()
