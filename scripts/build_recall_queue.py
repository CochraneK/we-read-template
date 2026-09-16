#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a deterministic recall queue from privacy-filtered WeRead context."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "recall_queue.json"
DAY = 86400


def read_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"missing context: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def prompt_for(kind):
    if kind == "review":
        return "不看原文：你当时为什么会写下这个想法？现在还认同吗？"
    return "不看原文：你能用自己的话解释这段内容，并举一个自己的例子吗？"


def stable_evidence_id(book_id: str, kind: str, created_at: int, chapter: str, text: str) -> str:
    """Stable id survives queue re-ordering/rebuilds for browser-local review history."""
    raw = "\0".join([
        str(book_id or ""),
        str(kind or ""),
        str(int(created_at or 0)),
        str(chapter or "").strip(),
        str(text or "").strip(),
    ]).encode("utf-8")
    return "ev-" + hashlib.sha256(raw).hexdigest()[:20]


def collect_candidates(context, now_ts=None, min_age_days=30):
    now_ts = int(now_ts if now_ts is not None else time.time())
    out = []
    for book in context.get("books") or []:
        if not isinstance(book, dict):
            continue
        base = {
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
        }
        for source_key, kind in (("reviews", "review"), ("marks", "mark")):
            for item in book.get(source_key) or []:
                if not isinstance(item, dict):
                    continue
                created = int(item.get("createTime") or 0)
                text = str(item.get("text") or "").strip()
                chapter = str(item.get("chapter") or "")
                if not created or not text or created > now_ts:
                    continue
                age_days = max(0, (now_ts - created) // DAY)
                if age_days < min_age_days:
                    continue
                out.append(
                    {
                        **base,
                        "kind": kind,
                        "chapter": chapter,
                        "text": text,
                        "createdAt": created,
                        "ageDays": int(age_days),
                        "prompt": prompt_for(kind),
                        "evidenceId": stable_evidence_id(base["bookId"], kind, created, chapter, text),
                    }
                )
    out.sort(
        key=lambda x: (
            -x["ageDays"],
            0 if x["kind"] == "review" else 1,
            x["title"],
            x["chapter"],
        )
    )
    return out


def build_queue(context, limit=20, min_age_days=30, max_per_book=2, now_ts=None):
    candidates = collect_candidates(context, now_ts, min_age_days)
    per_book = {}
    selected = []
    for item in candidates:
        bid = item["bookId"] or item["title"]
        used = per_book.get(bid, 0)
        if used >= max_per_book:
            continue
        selected.append(item)
        per_book[bid] = used + 1
        if len(selected) >= limit:
            break

    generated_ts = int(now_ts if now_ts is not None else time.time())
    for index, item in enumerate(selected, 1):
        # Sequential id remains convenient for display; evidenceId is the stable
        # identity used by local spaced-repetition history.
        item["id"] = f"recall-{index:03d}"

    return {
        "version": "2",
        "generatedAt": datetime.fromtimestamp(generated_ts, timezone.utc).isoformat(),
        "policy": {
            "minAgeDays": int(min_age_days),
            "maxPerBook": int(max_per_book),
            "limit": int(limit),
            "ordering": "oldest evidence first; reviews win ties; per-book diversity cap",
            "stableIdentity": "evidenceId=sha256(bookId, kind, createdAt, chapter, text) prefix",
        },
        "coverage": {
            "candidateEvidence": len(candidates),
            "selected": len(selected),
            "books": len({x["bookId"] or x["title"] for x in selected}),
            "contextIncludePrivate": bool((context.get("privacy") or {}).get("includePrivate")),
        },
        "items": selected,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build deterministic WeRead recall queue.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-age-days", type=int, default=30)
    parser.add_argument("--max-per-book", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    context = read_json(args.context)
    queue = build_queue(
        context,
        limit=max(1, args.limit),
        min_age_days=max(0, args.min_age_days),
        max_per_book=max(1, args.max_per_book),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    c = queue["coverage"]
    print(f"recall-queue: {args.output} | selected={c['selected']} books={c['books']} candidates={c['candidateEvidence']}")


if __name__ == "__main__":
    main()
