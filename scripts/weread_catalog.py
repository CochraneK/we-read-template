#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small official WeRead Agent Gateway client for catalog verification.

The client follows Tencent/WeChatReading skill 1.0.4 search semantics: explicit
scope=10 for ebook lookup and no assumption that response group scope equals the
request scope.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

URL = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.4"


def api_key() -> str:
    return os.environ.get("WEREAD_API_KEY", "").strip()


def call(body: dict, *, key: str | None = None, retries: int = 3, timeout: int = 30) -> dict:
    token = (key if key is not None else api_key()).strip()
    if not token:
        raise RuntimeError("WEREAD_API_KEY is required for live catalog verification")
    payload = dict(body)
    payload.setdefault("skill_version", SKILL_VERSION)
    last = None
    for attempt in range(max(1, retries)):
        try:
            req = urllib.request.Request(
                URL,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("upgrade_info"):
                info = data.get("upgrade_info")
                message = info.get("message") if isinstance(info, dict) else info
                raise RuntimeError(f"WeRead Skill upgrade required: {message}")
            if data.get("errcode", 0) != 0:
                raise RuntimeError(f"gateway errcode={data.get('errcode')}: {data.get('errmsg','unknown error')}")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < max(1, retries):
                time.sleep(1.0 + attempt * 0.5)
    raise RuntimeError(f"WeRead gateway request failed: {last}")


def flatten_search_response(data: dict) -> list[dict]:
    """Flatten all response groups that contain books; do not filter by group scope."""
    rows = []
    for group in data.get("results") or []:
        if not isinstance(group, dict):
            continue
        for row in group.get("books") or []:
            if not isinstance(row, dict):
                continue
            info = row.get("bookInfo") or {}
            if not isinstance(info, dict):
                continue
            book_id = str(info.get("bookId") or "")
            title = str(info.get("title") or "").strip()
            if not book_id and not title:
                continue
            rows.append({
                "bookId": book_id,
                "title": title,
                "author": str(info.get("author") or "").strip(),
                "publisher": str(info.get("publisher") or "").strip(),
                "category": str(info.get("category") or "").strip(),
                "intro": str(info.get("intro") or "").strip(),
                "deepLink": str(info.get("deepLink") or "").strip(),
                "cover": str(info.get("cover") or "").strip(),
                "soldout": int(info.get("soldout") or 0),
                "payType": info.get("payType"),
                "price": info.get("price"),
                "readingCount": int(row.get("readingCount") or 0),
                "rating": int(row.get("newRating") or 0),
                "ratingCount": int(row.get("newRatingCount") or 0),
                "ratingLabel": str((row.get("newRatingDetail") or {}).get("title") or ""),
                "searchIdx": int(row.get("searchIdx") or 0),
                "responseGroup": str(group.get("title") or ""),
                "responseScope": group.get("scope"),
            })
    return rows


def search_books(keyword: str, *, count: int | None = None, max_idx: int = 0, key: str | None = None) -> dict:
    keyword = str(keyword or "").strip()
    if not keyword:
        raise ValueError("keyword is required")
    body = {"api_name": "/store/search", "skill_version": SKILL_VERSION, "keyword": keyword, "scope": 10, "maxIdx": int(max_idx)}
    if count is not None:
        body["count"] = max(1, min(int(count), 50))
    raw = call(body, key=key)
    return {
        "keyword": keyword,
        "scope": 10,
        "hasMore": int(raw.get("hasMore") or 0),
        "sid": raw.get("sid"),
        "items": flatten_search_response(raw),
    }


def book_info(book_id: str, *, key: str | None = None) -> dict:
    book_id = str(book_id or "").strip()
    if not book_id:
        raise ValueError("book_id is required")
    return call({"api_name": "/book/info", "skill_version": SKILL_VERSION, "bookId": book_id}, key=key)
