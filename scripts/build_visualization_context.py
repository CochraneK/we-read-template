#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a normalized, privacy-aware context for WeRead visualization skills.

This is the bridge between raw exported WeRead JSON and AI/renderer layers.
It performs deterministic joins only; it does not infer personality or topics.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_OUTPUT = DATA / "analysis" / "visualization_context.json"


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def build_context(data_dir: Path, include_private: bool = False) -> dict:
    shelf = read_json(data_dir / "weread_shelf.json", {})
    notes = read_json(data_dir / "weread_notes_export.json", [])
    progress = read_json(data_dir / "weread_progress.json", {})
    info = read_json(data_dir / "weread_bookinfo.json", {})
    readdata = read_json(data_dir / "weread_readdata.json", {})

    shelf_books = {}
    for item in shelf.get("books", []) if isinstance(shelf, dict) else []:
        bid = str(item.get("bookId") or "")
        if bid:
            shelf_books[bid] = item

    notes_by_id = {
        str(item.get("bookId")): item
        for item in notes
        if isinstance(item, dict) and item.get("bookId")
    }

    ids = sorted(
        set(shelf_books)
        | set(notes_by_id)
        | {str(k) for k in progress.keys()}
        | {str(k) for k in info.keys()}
    )

    books = []
    excluded_private = 0
    for bid in ids:
        shelf_item = shelf_books.get(bid, {})
        note_item = notes_by_id.get(bid, {})
        prog = progress.get(bid, {}) or {}
        meta = info.get(bid, {}) or {}

        secret = as_int(shelf_item.get("secret"), 0) == 1
        if secret and not include_private:
            excluded_private += 1
            continue

        title = (
            shelf_item.get("title")
            or (shelf_item.get("book") or {}).get("title")
            or note_item.get("title")
            or ""
        )
        author = (
            shelf_item.get("author")
            or (shelf_item.get("book") or {}).get("author")
            or note_item.get("author")
            or ""
        )
        category = shelf_item.get("category") or meta.get("category") or note_item.get("category") or ""

        marks = [
            {
                "type": "mark",
                "chapter": mark.get("chapter", ""),
                "text": mark.get("text", ""),
                "createTime": as_int(mark.get("createTime")),
            }
            for mark in note_item.get("marks", [])
            if isinstance(mark, dict)
        ]
        reviews = [
            {
                "type": "review",
                "chapter": review.get("chapter", ""),
                "abstract": review.get("abstract", ""),
                "text": review.get("content", ""),
                "createTime": as_int(review.get("createTime")),
            }
            for review in note_item.get("reviews", [])
            if isinstance(review, dict)
        ]

        books.append(
            {
                "bookId": bid,
                "title": title,
                "author": author,
                "category": category,
                "secret": secret,
                "privacyKnown": bid in shelf_books,
                "inShelf": bid in shelf_books,
                "inNotebook": bid in notes_by_id,
                "shelfReadUpdateTime": as_int(shelf_item.get("readUpdateTime")),
                "progress": prog.get("progress"),
                "recordReadingTime": as_int(prog.get("recordReadingTime")),
                "finishTime": as_int(prog.get("finishTime")),
                "updateTime": as_int(prog.get("updateTime")),
                "isStartReading": prog.get("isStartReading"),
                "publisher": meta.get("publisher"),
                "publishTime": meta.get("publishTime"),
                "wordCount": meta.get("wordCount"),
                "noteCount": len(marks) + len(reviews),
                "markCount": len(marks),
                "reviewCount": len(reviews),
                "marks": marks,
                "reviews": reviews,
            }
        )

    annual = []
    for year, period in sorted((readdata.get("annually") or {}).items()):
        if not isinstance(period, dict):
            continue
        annual.append(
            {
                "year": str(year),
                "totalReadTime": as_int(period.get("totalReadTime")),
                "readDays": as_int(period.get("readDays")),
                "preferCategory": period.get("preferCategory") or [],
                "readLongest": period.get("readLongest") or [],
            }
        )

    overall = readdata.get("overall") or {}
    coverage = {
        "shelfBooks": len(shelf_books),
        "notebookBooks": len(notes_by_id),
        "contextBooks": len(books),
        "excludedPrivateBooks": excluded_private,
        "booksWithProgress": sum(1 for b in books if b["progress"] is not None),
        "booksWithNotes": sum(1 for b in books if b["noteCount"] > 0),
        "marks": sum(b["markCount"] for b in books),
        "reviews": sum(b["reviewCount"] for b in books),
        "annualPeriods": len(annual),
    }

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "includePrivate": include_private,
            "defaultPolicy": "explicit secret books excluded unless --include-private is set",
        },
        "coverage": coverage,
        "reading": {
            "overall": {
                "totalReadTime": as_int(overall.get("totalReadTime")),
                "readDays": as_int(overall.get("readDays")),
                "preferCategory": overall.get("preferCategory") or [],
                "preferAuthor": overall.get("preferAuthor") or [],
                "preferPublisher": overall.get("preferPublisher") or [],
            },
            "annual": annual,
        },
        "books": books,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build normalized WeRead visualization context.")
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include books explicitly marked secret. Off by default.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    context = build_context(args.data_dir.expanduser().resolve(), args.include_private)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    c = context["coverage"]
    print(
        f"context: {args.output} | books={c['contextBooks']} notes={c['booksWithNotes']} "
        f"marks={c['marks']} reviews={c['reviews']} excluded_private={c['excludedPrivateBooks']}"
    )


if __name__ == "__main__":
    main()
