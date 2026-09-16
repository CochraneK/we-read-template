#!/usr/bin/env python3
"""Check or apply sanitized code drift from the canonical we-read upstream."""
from __future__ import annotations

from pathlib import Path
import argparse
import filecmp
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "template-manifest.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def files_under(root: Path, names: list[str]) -> dict[str, Path]:
    out = {}
    for name in names:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                out[path.relative_to(root).as_posix()] = path
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cfg = load_manifest()
    owned = set(cfg.get("template_owned") or [])
    excluded = set(cfg.get("sync_exclude") or [])
    roots = list(cfg.get("sync_roots") or [])
    with tempfile.TemporaryDirectory(prefix="we-read-upstream-") as tmp:
        upstream = Path(tmp) / "upstream"
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", cfg.get("branch", "main"), cfg["upstream"], str(upstream)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        source = files_under(upstream, roots)
        target = files_under(ROOT, roots)
        drift = []
        for rel, src in sorted(source.items()):
            if rel in owned or rel in excluded:
                continue
            dst = ROOT / rel
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                drift.append(rel)
                if args.apply:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        for rel in sorted(set(target) - set(source)):
            if rel in owned or rel in excluded:
                continue
            drift.append(rel + " (removed upstream)")
            if args.apply:
                (ROOT / rel).unlink()

    if drift:
        print("upstream drift:")
        for rel in drift:
            print(" -", rel)
        if args.check:
            print("Run: python scripts/sync_from_upstream.py --apply")
            return 1
        print(f"applied {len(drift)} upstream changes")
    else:
        print("upstream: in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
