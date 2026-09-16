#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and query a local WeRead search index from visualization_context.json.

The index inherits the context's privacy policy. It never calls WeRead APIs.
SQLite FTS5 is used when available, with a LIKE fallback for short/CJK queries.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_DB = DATA / "analysis" / "weread_search.sqlite"


def read_context(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"missing context: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def iter_documents(context):
    for book in context.get("books") or []:
        if not isinstance(book, dict):
            continue
        bid = str(book.get("bookId") or "")
        title = str(book.get("title") or "")
        author = str(book.get("author") or "")
        category = str(book.get("category") or "")
        yield {
            "book_id": bid,
            "title": title,
            "author": author,
            "category": category,
            "kind": "book",
            "chapter": "",
            "text": " ".join(x for x in [title, author, category] if x),
            "created_at": 0,
        }
        for mark in book.get("marks") or []:
            if not isinstance(mark, dict):
                continue
            text = str(mark.get("text") or "").strip()
            if not text:
                continue
            yield {
                "book_id": bid,
                "title": title,
                "author": author,
                "category": category,
                "kind": "mark",
                "chapter": str(mark.get("chapter") or ""),
                "text": text,
                "created_at": int(mark.get("createTime") or 0),
            }
        for review in book.get("reviews") or []:
            if not isinstance(review, dict):
                continue
            text = str(review.get("text") or "").strip()
            abstract = str(review.get("abstract") or "").strip()
            combined = "\n".join(x for x in [abstract, text] if x)
            if not combined:
                continue
            yield {
                "book_id": bid,
                "title": title,
                "author": author,
                "category": category,
                "kind": "review",
                "chapter": str(review.get("chapter") or ""),
                "text": combined,
                "created_at": int(review.get("createTime") or 0),
            }


def _create_fts(conn):
    conn.execute("DROP TABLE IF EXISTS docs_fts")
    for tokenizer in ("trigram", "unicode61"):
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE docs_fts USING fts5("
                "title, author, category, chapter, text, "
                "content='docs', content_rowid='id', tokenize='{}')".format(tokenizer)
            )
            return tokenizer
        except sqlite3.OperationalError:
            conn.execute("DROP TABLE IF EXISTS docs_fts")
    return None


def build_index(context, db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS docs")
        conn.execute(
            "CREATE TABLE docs("
            "id INTEGER PRIMARY KEY, book_id TEXT, title TEXT, author TEXT, category TEXT, "
            "kind TEXT, chapter TEXT, text TEXT, created_at INTEGER)"
        )
        docs = list(iter_documents(context))
        conn.executemany(
            "INSERT INTO docs(book_id,title,author,category,kind,chapter,text,created_at) "
            "VALUES(:book_id,:title,:author,:category,:kind,:chapter,:text,:created_at)",
            docs,
        )
        tokenizer = _create_fts(conn)
        if tokenizer:
            conn.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_book_id ON docs(book_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kind ON docs(kind)")
        conn.commit()
        return {"documents": len(docs), "tokenizer": tokenizer or "LIKE-only"}
    finally:
        conn.close()


def _where_filters(kind=None, book_id=None, alias="d"):
    clauses = []
    params = []
    if kind:
        clauses.append(f"{alias}.kind = ?")
        params.append(kind)
    if book_id:
        clauses.append(f"{alias}.book_id = ?")
        params.append(str(book_id))
    return clauses, params


def search_index(db_path: Path, query: str, limit=20, kind=None, book_id=None):
    query = str(query or "").strip()
    if not query:
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = []
        seen = set()
        has_fts = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='docs_fts'"
        ).fetchone()
        if has_fts:
            clauses, params = _where_filters(kind, book_id, "d")
            where = " AND " + " AND ".join(clauses) if clauses else ""
            try:
                sql = (
                    "SELECT d.*, bm25(docs_fts) AS score FROM docs_fts "
                    "JOIN docs d ON d.id = docs_fts.rowid WHERE docs_fts MATCH ?"
                    + where
                    + " ORDER BY score LIMIT ?"
                )
                for row in conn.execute(sql, [query] + params + [int(limit)]):
                    rows.append(dict(row))
                    seen.add(row["id"])
            except sqlite3.OperationalError:
                pass

        clauses, params = _where_filters(kind, book_id, "d")
        like = "%" + query + "%"
        text_clause = "(d.title LIKE ? OR d.author LIKE ? OR d.category LIKE ? OR d.chapter LIKE ? OR d.text LIKE ?)"
        clauses.insert(0, text_clause)
        like_params = [like, like, like, like, like]
        sql = "SELECT d.*, NULL AS score FROM docs d WHERE " + " AND ".join(clauses) + " ORDER BY d.created_at DESC, d.id DESC LIMIT ?"
        for row in conn.execute(sql, like_params + params + [int(limit) * 2]):
            if row["id"] in seen:
                continue
            rows.append(dict(row))
            seen.add(row["id"])
            if len(rows) >= limit:
                break
        return rows[:limit]
    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Build/query local WeRead full-text index.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--query", help="Search after ensuring the index exists")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--kind", choices=["book", "mark", "review"])
    parser.add_argument("--book-id")
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.rebuild or not args.db.exists():
        context = read_context(args.context)
        meta = build_index(context, args.db)
        print(f"search-index: {args.db} | documents={meta['documents']} tokenizer={meta['tokenizer']}")
    if args.query:
        results = search_index(args.db, args.query, args.limit, args.kind, args.book_id)
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
