#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the final local-only Private Reading Lab artifact.

Unlike the public Page validator, raw evidence is expected here. The validator
instead enforces local-only markers, critical UX contracts, no browser network
APIs, and JavaScript syntax when Node is available.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import re
import shutil
import subprocess
import tempfile

REQUIRED = (
    'name="robots" content="noindex,nofollow,noarchive"',
    'Private / Raw Evidence',
    'id="deep"',
    'id="search"',
    'id="recall"',
    'id="recall-history"',
    'id="actions"',
    'id="books"',
    'wereadPrivateRecallHistoryV1',
    'data-recall=',
)
FORBIDDEN_NETWORK = (
    'fetch(',
    'XMLHttpRequest',
    'new WebSocket',
    'EventSource(',
)


def inline_scripts(page: str) -> list[str]:
    return re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', page, flags=re.S | re.I)


def validate_text(page: str) -> dict:
    missing = [marker for marker in REQUIRED if marker not in page]
    network = [marker for marker in FORBIDDEN_NETWORK if marker in page]
    external_scripts = re.findall(r'<script[^>]+src\s*=', page, flags=re.I)
    if missing:
        raise ValueError('missing Private Lab contracts: ' + ', '.join(missing))
    if network:
        raise ValueError('browser network API found in Private Lab: ' + ', '.join(network))
    if external_scripts:
        raise ValueError('external <script src> is not allowed in Private Lab')
    scripts = inline_scripts(page)
    if not scripts:
        raise ValueError('no inline JavaScript found')
    return {"inlineScripts": len(scripts), "inlineJsBytes": sum(len(x.encode('utf-8')) for x in scripts)}


def node_check(page: str) -> str:
    node = shutil.which('node')
    if not node:
        return 'skipped:no-node'
    scripts = inline_scripts(page)
    with tempfile.TemporaryDirectory() as td:
        combined = Path(td) / 'private-lab-inline.js'
        combined.write_text('\n'.join(scripts), encoding='utf-8')
        result = subprocess.run([node, '--check', str(combined)], capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError('node --check failed:\n' + result.stderr.strip())
    return 'passed'


def validate(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f'missing Private Lab HTML: {path}')
    page = path.read_text(encoding='utf-8')
    info = validate_text(page)
    info['nodeCheck'] = node_check(page)
    info['bytes'] = path.stat().st_size
    return info


def main():
    p = argparse.ArgumentParser(description='Validate final local-only Private Reading Lab HTML.')
    p.add_argument('--html', type=Path, required=True)
    a = p.parse_args()
    try:
        info = validate(a.html)
    except ValueError as exc:
        raise SystemExit(f'ERROR: {exc}')
    print(
        f"private-lab-validation: passed | html={a.html} bytes={info['bytes']} "
        f"scripts={info['inlineScripts']} js_bytes={info['inlineJsBytes']} node={info['nodeCheck']}"
    )


if __name__ == '__main__':
    main()
