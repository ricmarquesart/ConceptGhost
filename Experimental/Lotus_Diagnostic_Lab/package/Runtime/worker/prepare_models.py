import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

import requests
from huggingface_hub import HfApi, hf_hub_url

CHUNK = 8 * 1024 * 1024
USER_AGENT = "ConceptGhost-LotusDiagnostic/1.0 direct-no-symlink"


def _safe_repo_dir(repo_id: str) -> str:
    return "models--" + repo_id.replace("/", "--")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _metadata_for_repo(api: HfApi, repo_id: str):
    info = api.model_info(repo_id=repo_id, revision="main", files_metadata=True, token=False)
    commit = info.sha
    files = []
    for s in info.siblings or []:
        name = getattr(s, "rfilename", None)
        if not name:
            continue
        size = getattr(s, "size", None)
        lfs = getattr(s, "lfs", None)
        blob_id = getattr(s, "blob_id", None)
        sha256 = None
        if lfs:
            sha256 = getattr(lfs, "sha256", None)
            if sha256 is None and isinstance(lfs, dict):
                sha256 = lfs.get("sha256")
        files.append({"name": name, "size": int(size) if size is not None else None, "sha256": sha256, "blob_id": blob_id})
    return commit, files


def _reuse_legacy_blob(legacy_repo_cache: Path, meta: dict, dest: Path) -> bool:
    candidates = []
    if meta.get("sha256"):
        candidates.append(legacy_repo_cache / "blobs" / meta["sha256"])
    if meta.get("blob_id"):
        candidates.append(legacy_repo_cache / "blobs" / meta["blob_id"])
    expected = meta.get("size")
    for src in candidates:
        if src.is_file() and (expected is None or src.stat().st_size == expected):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[reuse] {meta['name']} <- {src.name}", flush=True)
            return True
    for src in candidates:
        inc = Path(str(src) + ".incomplete")
        if inc.is_file() and inc.stat().st_size > 0 and (expected is None or inc.stat().st_size < expected):
            part = Path(str(dest) + ".part")
            if not part.exists() or inc.stat().st_size > part.stat().st_size:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(inc, part)
                print(f"[resume-seed] {meta['name']} <- {inc.name} ({inc.stat().st_size} bytes)", flush=True)
                return False
    return False


def _download_direct(repo_id: str, revision: str, meta: dict, dest: Path, session: requests.Session):
    expected = meta.get("size")
    if dest.is_file() and (expected is None or dest.stat().st_size == expected):
        print(f"[ready] {meta['name']} ({dest.stat().st_size} bytes)", flush=True)
        return
    if dest.exists():
        dest.unlink()

    part = Path(str(dest) + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    start = part.stat().st_size if part.is_file() else 0
    if expected is not None and start > expected:
        part.unlink()
        start = 0

    url = hf_hub_url(repo_id=repo_id, filename=meta["name"], revision=revision)
    headers = {"User-Agent": USER_AGENT}
    mode = "wb"
    if start > 0:
        headers["Range"] = f"bytes={start}-"
        mode = "ab"
        print(f"[resume] {meta['name']} from {start} / {expected or '?'} bytes", flush=True)
    else:
        print(f"[download] {meta['name']} ({expected or '?'} bytes)", flush=True)

    with session.get(url, headers=headers, stream=True, allow_redirects=True, timeout=(30, 300)) as r:
        if start > 0 and r.status_code == 416 and expected is not None and start == expected:
            part.replace(dest)
            return
        r.raise_for_status()
        if start > 0 and r.status_code != 206:
            mode = "wb"
            start = 0
        written = start
        last_report = time.time()
        with part.open(mode) as f:
            for chunk in r.iter_content(chunk_size=CHUNK):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if time.time() - last_report >= 5:
                    if expected:
                        pct = min(100.0, written * 100.0 / expected)
                        print(f"  {pct:5.1f}%  {written}/{expected} bytes", flush=True)
                    else:
                        print(f"  {written} bytes", flush=True)
                    last_report = time.time()

    final_size = part.stat().st_size
    if expected is not None and final_size != expected:
        raise RuntimeError(f"Incomplete direct download for {repo_id}/{meta['name']}: {final_size} != {expected}")
    part.replace(dest)
    if meta.get("sha256"):
        actual = _sha256(dest)
        if actual.lower() != meta["sha256"].lower():
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"SHA256 mismatch for {repo_id}/{meta['name']}: {actual} != {meta['sha256']}")
    print(f"[done] {meta['name']} ({dest.stat().st_size} bytes)", flush=True)


def materialize_repo(root: Path, key: str, repo_id: str, api: HfApi, session: requests.Session):
    revision, files = _metadata_for_repo(api, repo_id)
    dest_root = root / "Models" / key
    legacy = root / "Models" / "hf_cache" / _safe_repo_dir(repo_id)
    dest_root.mkdir(parents=True, exist_ok=True)

    reused = 0
    total_bytes = 0
    for meta in files:
        dest = dest_root / Path(meta["name"])
        if meta.get("size"):
            total_bytes += meta["size"]
        if dest.is_file() and (meta.get("size") is None or dest.stat().st_size == meta["size"]):
            print(f"[ready] {meta['name']} ({dest.stat().st_size} bytes)", flush=True)
            continue
        if _reuse_legacy_blob(legacy, meta, dest):
            reused += 1
            continue
        _download_direct(repo_id, revision, meta, dest, session)

    required = [
        dest_root / "model_index.json",
        dest_root / "unet" / "config.json",
        dest_root / "unet" / "diffusion_pytorch_model.safetensors",
        dest_root / "vae" / "config.json",
        dest_root / "vae" / "diffusion_pytorch_model.safetensors",
        dest_root / "text_encoder" / "config.json",
        dest_root / "text_encoder" / "model.safetensors",
        dest_root / "tokenizer" / "tokenizer_config.json",
        dest_root / "scheduler" / "scheduler_config.json",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError(f"Model materialization incomplete for {repo_id}; missing: {missing}")

    return {
        "repo_id": repo_id,
        "revision": revision,
        "snapshot_path": str(dest_root.resolve()),
        "download_mode": "DIRECT_HTTP_NO_SYMLINKS",
        "file_count": len(files),
        "declared_total_bytes": total_bytes,
        "legacy_cache_files_reused": reused,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runtime-root", required=True)
    args = p.parse_args()
    root = Path(args.runtime_root).resolve()
    (root / "Models").mkdir(parents=True, exist_ok=True)

    api = HfApi(token=False)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    models = {
        "depth": "jingheya/lotus-depth-d-v2-0-disparity",
        "normal": "jingheya/lotus-normal-d-v1-1",
    }
    resolved = {}
    for key, repo_id in models.items():
        print(f"=== Materializing {key}: {repo_id} ===", flush=True)
        resolved[key] = materialize_repo(root, key, repo_id, api, session)

    legacy_cache = root / "Models" / "hf_cache"
    if legacy_cache.exists():
        shutil.rmtree(legacy_cache, ignore_errors=True)
        print(f"[cleanup] removed obsolete owned HF cache: {legacy_cache}", flush=True)

    cfg = {
        "schema": "ConceptGhost.LotusDiagnostic.RuntimeConfig.v2",
        "runtime_root": str(root),
        "source_root": str((root / "Source" / "Lotus").resolve()),
        "models": resolved,
        "outputs_root": str((root / "Outputs").resolve()),
        "symlink_policy": "FORBIDDEN",
    }
    out = root / "Manifests" / "runtime_config.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
