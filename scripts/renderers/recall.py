#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render recall_queue.json into standalone self-test cards."""
from __future__ import annotations

from pathlib import Path
from html import escape
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DATA / "analysis" / "recall_queue.json"
DEFAULT_OUTPUT = DATA / "analysis" / "reading_recall.html"


def render_html(payload):
    items = [x for x in (payload.get("items") or []) if isinstance(x, dict)]
    if not items:
        raise ValueError("recall queue is empty")
    cards = []
    for item in items:
        kind = "想法" if item.get("kind") == "review" else "划线"
        source = "《{}》{}".format(
            escape(str(item.get("title") or "未知书籍")),
            (" · " + escape(str(item.get("chapter") or ""))) if item.get("chapter") else "",
        )
        cards.append(
            '<article class="card"><div class="meta"><span>{}</span><span>{} 天前</span></div>'
            '<h2>{}</h2><p class="prompt">{}</p><details><summary>查看原始证据</summary>'
            '<blockquote>{}</blockquote><div class="source">{}</div></details></article>'.format(
                kind,
                int(item.get("ageDays") or 0),
                source,
                escape(str(item.get("prompt") or "回忆这段内容。")),
                escape(str(item.get("text") or "")),
                source,
            )
        )
    coverage = payload.get("coverage") or {}
    subtitle = "{} 条回顾证据 · {} 本书".format(
        int(coverage.get("selected") or len(items)), int(coverage.get("books") or 0)
    )
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微信读书 · Recall</title><style>
:root{{--bg:#F5F1EA;--panel:#FFFDF9;--text:#2B2724;--muted:#776E66;--line:#E3D9CC;--accent:#B86643;--soft:#EFE5D8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif}}main{{width:min(900px,calc(100% - 24px));margin:auto;padding:44px 0 70px}}.eyebrow{{font-size:12px;font-weight:800;color:var(--accent);letter-spacing:.14em}}h1{{font-size:clamp(34px,6vw,58px);margin:8px 0;letter-spacing:-.04em}}.lead{{color:var(--muted);line-height:1.7;margin-bottom:28px}}.cards{{display:grid;gap:13px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 4px 14px rgba(43,39,36,.04)}}.meta{{display:flex;justify-content:space-between;color:var(--muted);font-size:11px}}.card h2{{font-size:16px;margin:12px 0 8px}}.prompt{{font-size:19px;line-height:1.65;margin:10px 0 18px}}details{{border-top:1px solid var(--line);padding-top:12px}}summary{{cursor:pointer;color:var(--accent);font-weight:700;font-size:12px}}blockquote{{margin:14px 0 8px;padding:14px 16px;background:var(--soft);border-radius:14px;line-height:1.7}}.source{{color:var(--muted);font-size:11px}}.notice{{margin-top:24px;color:var(--muted);font-size:12px;line-height:1.6}}@media print{{details{{display:block}}details summary{{display:none}}details:not([open])>*:not(summary){{display:block}}body{{background:white}}}}</style></head><body><main><div class="eyebrow">WEREAD INTELLIGENCE · RECALL</div><h1>阅读回顾卡</h1><p class="lead">{subtitle}。先回答，再展开原始证据；这里展示的是你过去留下的材料，不是模型生成的“正确答案”。</p><section class="cards">{cards}</section><p class="notice">队列默认按“更久未回顾”优先，并限制每本书的卡片数量，避免单本书淹没整个回顾队列。私密范围继承 visualization_context.json。</p></main></body></html>'''.format(
        subtitle=escape(subtitle), cards="".join(cards)
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead recall cards.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"ERROR: missing {args.input}; run scripts/build_recall_queue.py first")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(payload), encoding="utf-8")
    print(f"reading-recall: {args.output}")


if __name__ == "__main__":
    main()
