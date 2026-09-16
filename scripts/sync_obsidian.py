#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incrementally sync privacy-filtered WeRead context into an Obsidian vault.

Safety properties:
- consumes visualization_context.json, so the default private-book exclusion applies;
- only manages files it created (identified by explicit markers);
- preserves USER_EDIT_ZONE byte-for-byte across syncs;
- never deletes orphaned notes automatically;
- refuses to overwrite unmanaged files unless --adopt-unmanaged is explicit.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"

SYNC_START = "<!-- WEREAD_SYNC_START -->"
SYNC_END = "<!-- WEREAD_SYNC_END -->"
USER_START = "<!-- USER_EDIT_ZONE_START -->"
USER_END = "<!-- USER_EDIT_ZONE_END -->"

INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_filename(value: str, fallback: str = "untitled") -> str:
    value = INVALID_FILENAME.sub("_", str(value or "")).strip().strip(".")
    value = re.sub(r"\s+", " ", value)
    value = value[:100].rstrip(" .")
    return value or fallback


def yaml_string(value) -> str:
    return json.dumps(str(value or ""), ensure_ascii=False)


def extract_user_zone(text: str):
    start = text.find(USER_START)
    end = text.find(USER_END)
    if start < 0 or end < 0 or end < start:
        return None
    start += len(USER_START)
    inner = text[start:end]
    if inner.startswith("\n"):
        inner = inner[1:]
    if inner.endswith("\n"):
        inner = inner[:-1]
    return inner


def is_managed(text: str) -> bool:
    return SYNC_START in text and SYNC_END in text and USER_START in text and USER_END in text


def note_lines(book: dict) -> list[str]:
    entries = []
    for mark in book.get("marks") or []:
        if isinstance(mark, dict) and str(mark.get("text") or "").strip():
            entries.append((int(mark.get("createTime") or 0), "划线", mark))
    for review in book.get("reviews") or []:
        if isinstance(review, dict) and str(review.get("text") or "").strip():
            entries.append((int(review.get("createTime") or 0), "想法", review))
    entries.sort(key=lambda x: (x[0], x[1]))

    lines = []
    for timestamp, kind, item in entries:
        chapter = str(item.get("chapter") or "未标章节").strip()
        text = str(item.get("text") or "").strip().replace("\r\n", "\n")
        when = ""
        if timestamp:
            try:
                when = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
            except (ValueError, OSError, OverflowError):
                when = ""
        suffix = f" · {when}" if when else ""
        lines.extend([
            f"### {kind} · {chapter}{suffix}",
            "",
            text,
            "",
        ])
    return lines


def render_book(book: dict, user_text: str = "") -> str:
    title = str(book.get("title") or "未命名书籍").strip()
    author = str(book.get("author") or "").strip()
    category = str(book.get("category") or "").strip()
    book_id = str(book.get("bookId") or "").strip()
    progress = book.get("progress")
    progress_text = "" if progress is None else str(progress)

    generated = [
        "---",
        f"title: {yaml_string(title)}",
        f"author: {yaml_string(author)}",
        f"category: {yaml_string(category)}",
        f"weread_book_id: {yaml_string(book_id)}",
        f"progress: {yaml_string(progress_text)}",
        "source: we-read",
        "---",
        "",
        SYNC_START,
        f"# {title}",
        "",
    ]
    if author:
        generated.append(f"**作者**：{author}")
    if category:
        generated.append(f"**分类**：{category}")
    if progress is not None:
        generated.append(f"**阅读进度**：{progress}%")
    generated.extend([
        "",
        f"**划线 / 想法**：{int(book.get('markCount') or 0)} / {int(book.get('reviewCount') or 0)}",
        "",
        "## 微信读书同步内容",
        "",
    ])
    notes = note_lines(book)
    generated.extend(notes if notes else ["暂无划线或想法。", ""])
    generated.extend([
        SYNC_END,
        "",
        "## 我的补充",
        "",
        USER_START,
        user_text,
        USER_END,
        "",
    ])
    return "\n".join(generated)


def target_filename(book: dict) -> str:
    title = sanitize_filename(book.get("title") or "未命名书籍")
    bid = sanitize_filename(str(book.get("bookId") or "book"))[:12]
    return f"{title} [{bid}].md"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_context(context: dict, vault: Path, folder: str = "WeRead", dry_run: bool = False,
                 adopt_unmanaged: bool = False) -> dict:
    root = vault.expanduser().resolve() / folder
    books = [b for b in (context.get("books") or []) if isinstance(b, dict) and b.get("bookId")]
    stats = {"created": 0, "updated": 0, "unchanged": 0, "skippedUnmanaged": 0, "wouldWrite": 0}
    manifest_books = {}

    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)

    for book in sorted(books, key=lambda b: (str(b.get("title") or ""), str(b.get("bookId") or ""))):
        filename = target_filename(book)
        target = root / filename
        user_text = ""
        existed = target.exists()
        existing = target.read_text(encoding="utf-8") if existed else ""

        if existed:
            if is_managed(existing):
                user_text = extract_user_zone(existing) or ""
            elif not adopt_unmanaged:
                stats["skippedUnmanaged"] += 1
                continue
            else:
                # Explicit adoption preserves the entire previous file as user-authored material.
                user_text = existing

        rendered = render_book(book, user_text=user_text)
        digest = content_hash(rendered)
        manifest_books[str(book.get("bookId"))] = {"file": filename, "sha256": digest}

        if existed and existing == rendered:
            stats["unchanged"] += 1
            continue
        if dry_run:
            stats["wouldWrite"] += 1
            continue
        target.write_text(rendered, encoding="utf-8")
        stats["updated" if existed else "created"] += 1

    manifest = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceContextGeneratedAt": context.get("generatedAt"),
        "privacy": context.get("privacy") or {},
        "books": manifest_books,
    }
    if not dry_run:
        (root / ".weread-sync.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {"folder": str(root), "books": len(books), **stats}


def parse_args():
    parser = argparse.ArgumentParser(description="Safely sync WeRead notes into an Obsidian vault.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--vault", type=Path, default=os.environ.get("OBSIDIAN_VAULT"))
    parser.add_argument("--folder", default="WeRead")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--adopt-unmanaged", action="store_true",
        help="Explicitly adopt an existing unmanaged file while preserving its full content in USER_EDIT_ZONE.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.vault:
        raise SystemExit("ERROR: pass --vault /path/to/vault or set OBSIDIAN_VAULT")
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing context: {args.context}")
    result = sync_context(
        load_json(args.context), Path(args.vault), args.folder,
        dry_run=args.dry_run, adopt_unmanaged=args.adopt_unmanaged,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
