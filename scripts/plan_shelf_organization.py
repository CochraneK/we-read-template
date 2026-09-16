#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create an auditable local shelf/booklist organization plan.

This script NEVER writes to WeRead. It converts the normalized context into a
reviewable grouping plan. Any remote shelf mutation must be a separate,
explicitly confirmed workflow using a currently supported API contract.
"""
from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_JSON = DATA / "analysis" / "shelf_plan.json"
DEFAULT_MD = DATA / "analysis" / "shelf_plan.md"


def safe_progress(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def category_root(value: str) -> str:
    value = str(value or "未分类").strip() or "未分类"
    parts = re.split(r"[-—/·>|]", value, maxsplit=1)
    return (parts[0].strip() or "未分类")[:24]


def status_for(book: dict) -> str:
    progress = safe_progress(book.get("progress"))
    note_count = int(book.get("noteCount") or 0)
    review_count = int(book.get("reviewCount") or 0)
    if review_count > 0 or note_count >= 10:
        return "深读"
    if progress is not None and progress >= 100:
        return "已读"
    if progress is not None and progress > 0:
        return "在读"
    return "待读"


def group_for(book: dict, strategy: str) -> str:
    status = status_for(book)
    category = category_root(book.get("category"))
    if strategy == "status":
        return status
    if strategy == "category":
        return category
    return f"{status} · {category}"


def build_plan(context: dict, strategy: str = "hybrid") -> dict:
    if strategy not in {"status", "category", "hybrid"}:
        raise ValueError("strategy must be status, category, or hybrid")
    groups = defaultdict(list)
    books = [b for b in (context.get("books") or []) if isinstance(b, dict) and b.get("bookId")]
    for book in books:
        group = group_for(book, strategy)
        groups[group].append({
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
            "category": str(book.get("category") or ""),
            "progress": book.get("progress"),
            "noteCount": int(book.get("noteCount") or 0),
            "reason": f"status={status_for(book)}; category={category_root(book.get('category'))}",
        })

    output_groups = []
    for name in sorted(groups):
        items = sorted(groups[name], key=lambda x: (-x["noteCount"], x["title"], x["bookId"]))
        output_groups.append({"name": name, "count": len(items), "books": items})
    return {
        "version": "1",
        "strategy": strategy,
        "mode": "plan-only",
        "remoteMutationPerformed": False,
        "privacy": context.get("privacy") or {},
        "coverage": context.get("coverage") or {},
        "groups": output_groups,
        "warnings": [
            "This is a local plan only; no WeRead shelf/archive was modified.",
            "Review group names and book assignments before any future remote write.",
            "A book's shelf presence indicates interest/acquisition, not completed reading.",
        ],
    }


def render_markdown(plan: dict) -> str:
    lines = [
        "# 微信读书书架整理计划",
        "",
        f"策略：`{plan.get('strategy')}` · 模式：**plan-only**",
        "",
        "> 此文件只是本地预览，没有修改微信读书远端书架。",
        "",
    ]
    for group in plan.get("groups") or []:
        lines.extend([f"## {group['name']} · {group['count']} 本", ""])
        for book in group.get("books") or []:
            progress = "?" if book.get("progress") is None else str(book.get("progress")) + "%"
            author = f" · {book['author']}" if book.get("author") else ""
            lines.append(f"- **{book.get('title') or '未命名'}**{author} · 进度 {progress} · 笔记 {book.get('noteCount', 0)}")
        lines.append("")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Plan WeRead shelf organization without remote mutation.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--strategy", choices=["status", "category", "hybrid"], default="hybrid")
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    plan = build_plan(context, args.strategy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown.write_text(render_markdown(plan), encoding="utf-8")
    print(json.dumps({"groups": len(plan["groups"]), "books": sum(g["count"] for g in plan["groups"]), "remoteMutationPerformed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
