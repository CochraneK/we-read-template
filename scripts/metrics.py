#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared deterministic metrics for WeRead analyses.

This module contains no plotting and performs no file I/O. It is intended to
replace duplicated calculations embedded in legacy `analysis.py` over time.
The real-data GitHub Pages builder also imports these shared metrics, so Page
rebuilds keep the same deterministic category/engagement definitions.
"""
from __future__ import annotations

from collections import Counter


def _book_id(item):
    return str(item.get("bookId") or (item.get("book") or {}).get("bookId") or "")


def _category(item):
    return str(item.get("category") or (item.get("book") or {}).get("category") or "未知")


def _note_count(item):
    if "marks" in item or "reviews" in item:
        return len(item.get("marks") or []) + len(item.get("reviews") or [])
    return int(item.get("noteCount") or 0) + int(item.get("reviewCount") or 0)


def category_participation(shelf_books, notebook_books):
    """Return unique-book category counts and note density.

    Rules:
    - each bookId counts at most once in `book_count`;
    - shelf metadata wins for overlapping books;
    - notebook-only books are retained;
    - note counts come from notebook records only;
    - records without bookId get synthetic per-source ids so they do not collapse.
    """
    shelf_by_id = {}
    for index, item in enumerate(shelf_books or []):
        bid = _book_id(item) or f"__shelf_missing_{index}"
        shelf_by_id[bid] = item

    notes_by_id = {}
    for index, item in enumerate(notebook_books or []):
        bid = _book_id(item) or f"__notes_missing_{index}"
        notes_by_id[bid] = item

    book_count = Counter()
    note_count = Counter()
    all_ids = set(shelf_by_id) | set(notes_by_id)

    for bid in all_ids:
        shelf_item = shelf_by_id.get(bid)
        note_item = notes_by_id.get(bid)
        metadata = shelf_item or note_item or {}
        category = _category(metadata)
        book_count[category] += 1
        if note_item:
            note_count[category] += _note_count(note_item)

    rows = []
    for category in sorted(book_count, key=lambda key: (-book_count[key], key)):
        books = book_count[category]
        notes = note_count[category]
        rows.append({
            "category": category,
            "bookCount": books,
            "noteCount": notes,
            "notesPerBook": round(notes / books, 2) if books else 0.0,
        })

    return {
        "bookCount": dict(book_count),
        "noteCount": dict(note_count),
        "rows": rows,
        "uniqueBooks": len(all_ids),
    }


def engagement_summary(shelf_books, notebook_books):
    """Small fact block useful for dashboards and reading-profile generation."""
    shelf_ids = {_book_id(item) for item in (shelf_books or []) if _book_id(item)}
    note_ids = {_book_id(item) for item in (notebook_books or []) if _book_id(item)}
    overlap = shelf_ids & note_ids
    return {
        "shelfBooks": len(shelf_ids),
        "notebookBooks": len(note_ids),
        "shelfAndNotes": len(overlap),
        "notesOnlyBooks": len(note_ids - shelf_ids),
        "shelfOnlyBooks": len(shelf_ids - note_ids),
    }
