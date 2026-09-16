#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn one book's user-owned WeRead notes into a local evidence-backed Skill.

The generated Skill is intentionally conservative: it does not pretend to
contain the whole book. It exposes only the user's exported highlights and
reviews as evidence and requires answers to distinguish quote-like highlights
from the user's own reviews/thoughts.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_OUTPUT_ROOT = DATA / "generated-skills"


def slugify(value: str) -> str:
    value = str(value or "book").lower().strip()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value).strip("-")
    return value[:48] or "book"


def choose_book(context: dict, book_id: str | None = None, title: str | None = None) -> dict:
    books = [b for b in (context.get("books") or []) if isinstance(b, dict)]
    if book_id:
        for book in books:
            if str(book.get("bookId") or "") == str(book_id):
                return book
        raise ValueError(f"bookId not found: {book_id}")
    if title:
        wanted = title.strip().lower()
        exact = [b for b in books if str(b.get("title") or "").strip().lower() == wanted]
        if len(exact) == 1:
            return exact[0]
        partial = [b for b in books if wanted in str(b.get("title") or "").lower()]
        if len(partial) == 1:
            return partial[0]
        if not exact and not partial:
            raise ValueError(f"title not found: {title}")
        raise ValueError("title is ambiguous; use --book-id")
    raise ValueError("pass --book-id or --title")


def evidence_items(book: dict, max_items: int = 120) -> list[dict]:
    items = []
    for mark in book.get("marks") or []:
        if isinstance(mark, dict) and str(mark.get("text") or "").strip():
            items.append({
                "kind": "highlight",
                "chapter": str(mark.get("chapter") or ""),
                "text": str(mark.get("text") or "").strip(),
                "createTime": int(mark.get("createTime") or 0),
            })
    for review in book.get("reviews") or []:
        if isinstance(review, dict) and str(review.get("text") or "").strip():
            items.append({
                "kind": "user_review",
                "chapter": str(review.get("chapter") or ""),
                "text": str(review.get("text") or "").strip(),
                "createTime": int(review.get("createTime") or 0),
            })
    # User-authored thoughts are usually more valuable for a personal skill.
    items.sort(key=lambda x: (x["kind"] != "user_review", -x["createTime"]))
    return items[:max(1, max_items)]


def render_evidence(book: dict, items: list[dict]) -> str:
    lines = [
        f"# 《{book.get('title') or '未命名'}》个人阅读证据",
        "",
        "> 本文件只包含用户自己在微信读书中导出的划线和想法，不代表完整书籍内容。",
        "",
    ]
    for index, item in enumerate(items, 1):
        label = "我的想法" if item["kind"] == "user_review" else "我的划线"
        chapter = item.get("chapter") or "未标章节"
        lines.extend([
            f"## {index}. {label} · {chapter}",
            "",
            item["text"],
            "",
        ])
    return "\n".join(lines)


def render_skill(book: dict, skill_name: str, description: str | None = None) -> str:
    title = str(book.get("title") or "未命名书籍")
    author = str(book.get("author") or "")
    description = description or f"基于用户在《{title}》中的个人划线与想法进行证据检索和知识复用。当用户明确希望调用这本书的个人阅读笔记、框架或回顾时使用。"
    return f'''---
name: {skill_name}
description: {description}
---

# 《{title}》个人阅读 Skill

作者：{author or '未知'}

## 数据边界

这个 Skill **不是整本书的替代品**。它只基于 `references/evidence.md` 中用户自己导出的划线与想法工作。

- `我的划线`：来自用户保存的原文片段，回答时应表述为“你划下的内容”。
- `我的想法`：用户自己写的点评/想法，回答时应表述为“你当时写下的想法”。
- 不得把划线误说成用户本人观点。
- 不得补写 evidence 中不存在的作者观点、章节内容或案例。

## 工作流

1. 先阅读 `references/evidence.md`，定位与当前问题最相关的证据。
2. 优先使用用户自己的想法；划线用于补充其来源语境。
3. 如果多个证据相互冲突，明确指出冲突，而不是强行统一。
4. 输出时区分：
   - **证据**：笔记里实际存在的内容；
   - **解释**：基于这些证据做出的推论；
   - **应用**：如何把它用于当前问题。
5. evidence 不足时直接说不足，不从“对这本书的一般常识”偷偷补全。

## 推荐输出结构

```text
这本书在你的笔记里，与当前问题最相关的是：

1. 证据
2. 你当时的理解
3. 可以怎么用
4. 哪些地方证据还不够
```

## 隐私

此 Skill 默认是个人本地产物。除非用户明确要求，不要发布 `references/evidence.md` 的原始内容。
'''


def generate(context: dict, output_root: Path, book_id=None, title=None, name=None, max_items=120):
    book = choose_book(context, book_id=book_id, title=title)
    slug = slugify(name or book.get("title") or book.get("bookId") or "book")
    skill_name = f"weread-book-{slug}"
    output = output_root / skill_name
    refs = output / "references"
    items = evidence_items(book, max_items=max_items)
    output.mkdir(parents=True, exist_ok=True)
    refs.mkdir(parents=True, exist_ok=True)
    (output / "SKILL.md").write_text(render_skill(book, skill_name), encoding="utf-8")
    (refs / "evidence.md").write_text(render_evidence(book, items), encoding="utf-8")
    manifest = {
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or ""),
        "skill": skill_name,
        "evidenceItems": len(items),
        "source": "visualization_context.json",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, manifest


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a local evidence-backed Skill from one WeRead book.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--book-id")
    group.add_argument("--title")
    parser.add_argument("--name", help="Optional safe suffix used for the generated skill name.")
    parser.add_argument("--max-items", type=int, default=120)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    output, manifest = generate(
        context, args.output_root.expanduser().resolve(), book_id=args.book_id,
        title=args.title, name=args.name, max_items=args.max_items,
    )
    print(json.dumps({"output": str(output), **manifest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
