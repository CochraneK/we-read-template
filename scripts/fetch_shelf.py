#!/usr/bin/env python3
"""Fetch the authenticated user's WeRead shelf into the local data directory."""
from __future__ import annotations

from pathlib import Path
import json
import os
import time
import urllib.error
import urllib.request

URL = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.4"
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
OUT = DATA / "weread_shelf.json"


def api_key() -> str:
    key = os.environ.get("WEREAD_API_KEY", "").strip()
    if not key:
        raise SystemExit("ERROR: WEREAD_API_KEY is not set. Copy .env.example to .env and add your key.")
    return key


def call(tries: int = 3) -> dict:
    payload = {"api_name": "/shelf/sync", "skill_version": SKILL_VERSION}
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key()}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.load(response)
            if data.get("upgrade_info"):
                info = data["upgrade_info"]
                message = info.get("message") if isinstance(info, dict) else info
                raise RuntimeError(f"WeRead skill upgrade required: {message}")
            if data.get("errcode", 0) != 0:
                raise RuntimeError(f"gateway errcode={data.get('errcode')}: {data.get('errmsg', 'unknown error')}")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < tries:
                time.sleep(1 + attempt)
    raise SystemExit(f"ERROR: shelf fetch failed: {last}")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = call()
    books = payload.get("books") or []
    albums = payload.get("albums") or []
    mp = payload.get("mp")
    payload.setdefault("books", books)
    payload.setdefault("albums", albums)
    payload.setdefault("archive", payload.get("archive") or [])
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    total = len(books) + len(albums) + (1 if mp else 0)
    private = sum(1 for b in books if int(b.get("secret") or 0) == 1)
    private += sum(1 for a in albums if int(((a.get("albumInfoExtra") or {}).get("secret")) or 0) == 1)
    private += 1 if mp else 0
    print(f"shelf: {OUT} | visible_entries={total} books={len(books)} albums={len(albums)} private={private}")


if __name__ == "__main__":
    main()
