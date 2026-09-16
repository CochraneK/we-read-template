#!/usr/bin/env python3
"""Small zero-dependency CLI for the WeRead Intelligence starter template."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
REQUIRED_DATA = [
    "weread_shelf.json",
    "weread_notes_export.json",
    "weread_readdata.json",
    "weread_progress.json",
    "weread_bookinfo.json",
]


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = os.path.expanduser(value)


def data_dir() -> Path:
    raw = os.environ.get("WEREAD_DATA_DIR", "~/.local/share/we-read")
    return Path(raw).expanduser().resolve()


def run_script(path: str, *args: str) -> None:
    env = os.environ.copy()
    env["WEREAD_DATA_DIR"] = str(data_dir())
    subprocess.run([sys.executable, str(ROOT / path), *args], cwd=ROOT, env=env, check=True)


def cmd_setup(_: argparse.Namespace) -> int:
    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print(f"created {ENV_FILE}")
    else:
        print(f"kept existing {ENV_FILE}")
    data_dir().mkdir(parents=True, exist_ok=True)
    print(f"data directory: {data_dir()}")
    print("next: edit .env, set WEREAD_API_KEY, then run: python scripts/weread.py doctor")
    return 0


def doctor_payload() -> dict:
    d = data_dir()
    key = os.environ.get("WEREAD_API_KEY", "").strip()
    files = {name: (d / name).exists() for name in REQUIRED_DATA}
    return {
        "python": {
            "version": ".".join(map(str, sys.version_info[:3])),
            "supported": sys.version_info >= (3, 11),
        },
        "env_file": ENV_FILE.exists(),
        "api_key": {
            "present": bool(key),
            "looks_valid": bool(key) and key.startswith("wrk-"),
        },
        "data_dir": {
            "path": str(d),
            "exists": d.exists(),
            "writable": d.exists() and os.access(d, os.W_OK),
        },
        "data_files": files,
        "ready_to_build": all(files.values()),
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    payload = doctor_payload()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("WeRead Intelligence doctor")
        print(f"[{'OK' if payload['python']['supported'] else 'FAIL'}] Python {payload['python']['version']} (requires >= 3.11)")
        print(f"[{'OK' if payload['env_file'] else 'WARN'}] .env {'found' if payload['env_file'] else 'missing; run setup'}")
        key = payload["api_key"]
        print(f"[{'OK' if key['looks_valid'] else 'WARN'}] WEREAD_API_KEY {'looks valid' if key['looks_valid'] else 'missing or unexpected format'}")
        dd = payload["data_dir"]
        print(f"[{'OK' if dd['writable'] else 'FAIL'}] data dir {dd['path']}")
        for name, ok in payload["data_files"].items():
            print(f"[{'OK' if ok else 'MISS'}] {name}")
        print("READY" if payload["ready_to_build"] else "NOT YET: run sync to fetch your account data")
    if not payload["python"]["supported"] or not payload["data_dir"]["writable"]:
        return 1
    if args.require_key and not payload["api_key"]["looks_valid"]:
        return 2
    return 0


def require_key() -> None:
    key = os.environ.get("WEREAD_API_KEY", "").strip()
    if not key:
        raise SystemExit("ERROR: WEREAD_API_KEY is missing. Run setup and edit .env.")


def cmd_sync(_: argparse.Namespace) -> int:
    require_key()
    # export_notes.py can reuse an existing notebooks list for interrupted runs.
    # A normal user-facing sync should refresh that list so newly-noted books appear.
    notebooks_cache = data_dir() / "weread_notebooks.json"
    if notebooks_cache.exists():
        notebooks_cache.unlink()
    for script in ("scripts/fetch_shelf.py", "scripts/export_notes.py", "scripts/fetch_enrich.py"):
        run_script(script)
    return 0


def ensure_data() -> None:
    missing = [name for name in REQUIRED_DATA if not (data_dir() / name).exists()]
    if missing:
        raise SystemExit("ERROR: missing data files: " + ", ".join(missing) + ". Run sync first.")


def cmd_build_public(_: argparse.Namespace) -> int:
    ensure_data()
    run_script("scripts/pages_runtime.py")
    run_script("scripts/pages_public_quotes.py")
    run_script("scripts/pages_polish_site.py")
    run_script("scripts/validate_pages_output.py", "--js-out", str(ROOT / ".tmp-pages-inline.js"))
    print(f"public archive: {ROOT / 'site' / 'index.html'}")
    return 0


def cmd_build_private(args: argparse.Namespace) -> int:
    ensure_data()
    extra = []
    if args.include_private:
        extra.append("--include-private")
    if args.with_text:
        extra.append("--with-text")
    run_script("scripts/build_private_reading_lab.py", *extra)
    print(f"private lab: {data_dir() / 'analysis' / 'private_lab' / 'index.html'}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    cmd_sync(args)
    cmd_build_public(args)
    cmd_build_private(args)
    return 0


def cmd_sample(_: argparse.Namespace) -> int:
    sample = ROOT / "examples" / "sample-data"
    os.environ["WEREAD_DATA_DIR"] = str(sample)
    cmd_build_public(argparse.Namespace())
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="weread", description="Build your own WeRead Intelligence archive")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="create local .env and data directory").set_defaults(func=cmd_setup)
    d = sub.add_parser("doctor", help="check local configuration and data readiness")
    d.add_argument("--json", action="store_true")
    d.add_argument("--require-key", action="store_true")
    d.set_defaults(func=cmd_doctor)
    sub.add_parser("sync", help="fetch shelf, notes, reading stats and enrichment").set_defaults(func=cmd_sync)
    sub.add_parser("build-public", help="generate the public reading archive").set_defaults(func=cmd_build_public)
    bp = sub.add_parser("build-private", help="generate the local Private Reading Lab")
    bp.add_argument("--include-private", action="store_true")
    bp.add_argument("--with-text", action="store_true")
    bp.set_defaults(func=cmd_build_private)
    a = sub.add_parser("all", help="sync and build both surfaces")
    a.add_argument("--include-private", action="store_true")
    a.add_argument("--with-text", action="store_true")
    a.set_defaults(func=cmd_all)
    sub.add_parser("sample", help="build the synthetic starter archive").set_defaults(func=cmd_sample)
    return p


def main() -> int:
    load_dotenv()
    args = parser().parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
