#!/usr/bin/env python3
"""Read-only verification for ConceptGhost's pinned upstream reference mirrors."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_text(path: Path, *args: str) -> tuple[int, str]:
    cp = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return cp.returncode, (cp.stdout or cp.stderr).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source(item: dict[str, Any]) -> dict[str, Any]:
    path = Path(item["drive_path"])
    result: dict[str, Any] = {
        "id": item["id"],
        "name": item["name"],
        "kind": item["kind"],
        "path": str(path),
        "expected_commit": item["commit"],
        "expected_url": item["url"],
        "status": "MISSING",
    }

    if item["kind"] == "git":
        if not (path / ".git").is_dir():
            return result
        code, head = git_text(path, "rev-parse", "HEAD")
        if code != 0:
            result.update(status="ERROR", detail=head)
            return result
        code, remote = git_text(path, "remote", "get-url", "origin")
        if code != 0:
            result.update(status="ERROR", actual_commit=head, detail=remote)
            return result
        result["actual_commit"] = head
        result["actual_url"] = remote
        commit_ok = head.lower() == item["commit"].lower()
        url_ok = remote.rstrip("/").removesuffix(".git").lower() == item["url"].rstrip("/").removesuffix(".git").lower()
        result["commit_ok"] = commit_ok
        result["url_ok"] = url_ok
        result["status"] = "OK" if commit_ok and url_ok else "MISMATCH"
        return result

    if item["kind"] == "file":
        if not path.is_file():
            return result
        result["size_bytes"] = path.stat().st_size
        result["sha256"] = sha256_file(path)
        result["status"] = "OK"
        return result

    result.update(status="ERROR", detail=f"Unsupported kind: {item['kind']}")
    return result


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ConceptGhost Reference Verification",
        "=" * 78,
        f"Generated: {report['generated_at']}",
        f"Source lock: {report['source_lock']}",
        "",
    ]
    for row in report["results"]:
        suffix = ""
        if row["kind"] == "git" and row.get("actual_commit"):
            suffix = f"  expected={row['expected_commit'][:12]} actual={row['actual_commit'][:12]}"
        lines.append(f"[{row['status']:<8}] {row['name']}{suffix}")
        lines.append(f"           {row['path']}")
    lines.extend(
        [
            "",
            "SUMMARY",
            "-" * 78,
            f"OK: {report['summary']['ok']}",
            f"Missing: {report['summary']['missing']}",
            f"Mismatch: {report['summary']['mismatch']}",
            f"Error: {report['summary']['error']}",
            f"Overall: {report['summary']['overall']}",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify pinned ConceptGhost reference mirrors without modifying them")
    parser.add_argument("--lock", required=True)
    parser.add_argument("--report-txt", required=True)
    parser.add_argument("--report-json", required=True)
    args = parser.parse_args(argv)

    lock_path = Path(args.lock)
    lock = read_json(lock_path)
    results = [verify_source(item) for item in lock["sources"]]
    summary = {
        "ok": sum(r["status"] == "OK" for r in results),
        "missing": sum(r["status"] == "MISSING" for r in results),
        "mismatch": sum(r["status"] == "MISMATCH" for r in results),
        "error": sum(r["status"] == "ERROR" for r in results),
    }
    summary["overall"] = "PASS" if summary["missing"] == summary["mismatch"] == summary["error"] == 0 else "FAIL"
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "source_lock": str(lock_path),
        "results": results,
        "summary": summary,
    }

    txt_path = Path(args.report_txt)
    json_path = Path(args.report_json)
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(render_text(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(render_text(report), end="")
    return 0 if summary["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
