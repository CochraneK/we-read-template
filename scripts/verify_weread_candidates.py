#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify candidate books against the current official WeRead catalog.

Modes:
- discovery: `--query TOPIC` searches the official ebook catalog (scope=10);
- candidate file: `--candidates file.json` searches each supplied title and tries
  to resolve an exact title/author match.

The script never invents availability: live verification requires WEREAD_API_KEY.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import weread_catalog


def norm(value: str) -> str:
    return re.sub(r"[\s·•:：,，。.!！?？《》<>\-—_()（）\[\]【】]+", "", str(value or "").lower())


def local_books(context: dict) -> tuple[dict[str, dict], list[dict]]:
    by_id = {}
    rows = []
    for book in context.get("books") or []:
        if not isinstance(book, dict):
            continue
        row = {
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
            "noteCount": int(book.get("noteCount") or 0),
            "progress": book.get("progress"),
            "inShelf": bool(book.get("inShelf")),
        }
        if row["bookId"]:
            by_id[row["bookId"]] = row
        rows.append(row)
    return by_id, rows


def local_match(item: dict, by_id: dict[str, dict], rows: list[dict]) -> dict | None:
    bid = str(item.get("bookId") or "")
    if bid and bid in by_id:
        return by_id[bid]
    title, author = norm(item.get("title")), norm(item.get("author"))
    exact = [r for r in rows if title and norm(r["title"]) == title and (not author or norm(r["author"]) == author)]
    return exact[0] if len(exact) == 1 else None


def annotate(item: dict, by_id: dict[str, dict], rows: list[dict], *, query: str = "", requested: dict | None = None) -> dict:
    local = local_match(item, by_id, rows)
    available = bool(item.get("bookId")) and int(item.get("soldout") or 0) != 1
    status = "available" if available else "soldout" if int(item.get("soldout") or 0) == 1 else "unresolved"
    read = bool(local and (int(local.get("noteCount") or 0) >= 3 or (local.get("progress") is not None and float(local.get("progress") or 0) >= 80)))
    return {
        **item,
        "query": query,
        "requested": requested or None,
        "verifiedAgainstCatalog": True,
        "verifiedAvailable": available,
        "verificationStatus": status,
        "local": local,
        "alreadyRead": read,
        "shelvedUnengaged": bool(local and local.get("inShelf") and int(local.get("noteCount") or 0) == 0),
        "recommendationEligible": bool(available and not read),
    }


def best_match(requested: dict, found: list[dict]) -> dict | None:
    title = norm(requested.get("title"))
    author = norm(requested.get("author"))
    if not title:
        return None
    exact = [x for x in found if norm(x.get("title")) == title and (not author or norm(x.get("author")) == author)]
    if exact:
        return exact[0]
    title_only = [x for x in found if norm(x.get("title")) == title]
    if len(title_only) == 1:
        return title_only[0]
    partial = [x for x in found if title in norm(x.get("title")) or norm(x.get("title")) in title]
    return partial[0] if len(partial) == 1 else None


def load_candidates(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("candidates") or raw.get("items") or []
    if not isinstance(raw, list):
        raise ValueError("candidate file must contain a list or candidates/items list")
    out = []
    for row in raw:
        if isinstance(row, str):
            row = {"title": row}
        if isinstance(row, dict) and str(row.get("title") or "").strip():
            out.append(dict(row))
    return out


def verify_discovery(context: dict, query: str, *, count: int = 15) -> dict:
    by_id, local = local_books(context)
    search = weread_catalog.search_books(query, count=count)
    items = [annotate(x, by_id, local, query=query) for x in search["items"]]
    items.sort(key=lambda x: (
        0 if x["recommendationEligible"] else 1,
        0 if x["verifiedAvailable"] else 1,
        -int(x.get("rating") or 0),
        -int(x.get("ratingCount") or 0),
        int(x.get("searchIdx") or 0),
    ))
    return {
        "mode": "discovery",
        "query": query,
        "scope": 10,
        "searchIsPaginatedFragment": True,
        "hasMore": search.get("hasMore", 0),
        "items": items,
    }


def verify_candidates(context: dict, requested: list[dict], *, count_per_title: int = 10) -> dict:
    by_id, local = local_books(context)
    rows = []
    for req in requested:
        title = str(req.get("title") or "").strip()
        search = weread_catalog.search_books(title, count=count_per_title)
        match = best_match(req, search["items"])
        if match:
            row = annotate(match, by_id, local, query=title, requested=req)
        else:
            row = {
                "title": title,
                "author": str(req.get("author") or ""),
                "stage": req.get("stage"),
                "requested": req,
                "query": title,
                "verifiedAgainstCatalog": True,
                "verifiedAvailable": False,
                "verificationStatus": "not_found_exact",
                "alreadyRead": False,
                "recommendationEligible": False,
            }
        if req.get("stage") is not None:
            row["stage"] = req.get("stage")
        rows.append(row)
    return {"mode": "candidate-file", "items": rows}


def parse_args():
    parser = argparse.ArgumentParser(description="Verify reading candidates against the official WeRead ebook catalog.")
    parser.add_argument("--context", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", default="")
    group.add_argument("--candidates", type=Path)
    parser.add_argument("--count", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    context = json.loads(args.context.read_text(encoding="utf-8"))
    if args.query:
        result = verify_discovery(context, args.query.strip(), count=max(1, min(args.count, 50)))
    else:
        result = verify_candidates(context, load_candidates(args.candidates), count_per_title=max(1, min(args.count, 30)))
    result.update({
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "skillVersion": weread_catalog.SKILL_VERSION,
        "catalogContract": {
            "api": "/store/search",
            "requestScope": 10,
            "availabilitySource": "official live WeRead Agent Gateway",
            "mustNotClaimCompleteness": True,
        },
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    eligible = sum(1 for x in result["items"] if x.get("recommendationEligible"))
    print(f"weread-candidates: {args.output} | mode={result['mode']} returned={len(result['items'])} eligible={eligible}")


if __name__ == "__main__":
    main()
