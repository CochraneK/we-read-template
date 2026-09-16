#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render WeRead Cognitive Shift JSON into a standalone interactive timeline.

Input:  data/analysis/cognitive_shift.json
Output: data/analysis/cognitive_shift.html
No third-party dependencies.
"""
from __future__ import annotations

from pathlib import Path
from html import escape
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DATA / "analysis" / "cognitive_shift.json"
DEFAULT_OUTPUT = DATA / "analysis" / "cognitive_shift.html"
STAGE_COLORS = ["#C2724B", "#D9A441", "#7E9B8E", "#9B7B6B", "#6F8A84", "#A8774E"]


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize(payload):
    clean = []
    for index, stage in enumerate(payload.get("stages") or []):
        if not isinstance(stage, dict):
            continue
        label = str(stage.get("label") or "").strip()
        if not label:
            continue
        books = []
        for item in stage.get("books") or []:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("label") or "").strip()
                if title:
                    books.append({
                        "title": title,
                        "author": str(item.get("author") or "").strip(),
                        "bookId": str(item.get("bookId") or "").strip(),
                    })
            elif str(item).strip():
                books.append({"title": str(item).strip(), "author": "", "bookId": ""})
        evidence = []
        for item in stage.get("evidence") or []:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("quote") or item.get("summary") or item.get("title") or "").strip()
                if text:
                    evidence.append({
                        "text": text,
                        "source": str(item.get("source") or item.get("bookTitle") or "").strip(),
                        "kind": str(item.get("kind") or "").strip(),
                    })
            elif str(item).strip():
                evidence.append({"text": str(item).strip(), "source": "", "kind": ""})
        clean.append({
            "id": str(stage.get("id") or f"stage-{index + 1}"),
            "label": label,
            "start": str(stage.get("start") or "").strip(),
            "end": str(stage.get("end") or "").strip(),
            "themes": [str(x).strip() for x in (stage.get("themes") or []) if str(x).strip()],
            "books": books,
            "evidence": evidence,
            "transition": str(stage.get("transition") or "").strip(),
            "summary": str(stage.get("summary") or "").strip(),
            "confidence": max(0.0, min(1.0, safe_float(stage.get("confidence"), 0.0))),
        })
    return clean


def period_label(stage):
    start, end = stage["start"], stage["end"]
    if start and end and start != end:
        return f"{start} → {end}"
    return start or end or "时间未标注"


def build_stage_cards(stages):
    cards = []
    for i, stage in enumerate(stages):
        active = " active" if i == 0 else ""
        themes_html = "".join(f'<span class="theme-chip">{escape(theme)}</span>' for theme in stage["themes"]) or '<span class="empty">未标注主题</span>'
        book_rows = []
        for book in stage["books"][:10]:
            author = f' <span>· {escape(book["author"])}</span>' if book["author"] else ""
            book_rows.append(f'<li><strong>{escape(book["title"])}</strong>{author}</li>')
        books_html = "".join(book_rows) or '<li class="empty">暂无代表书籍</li>'
        evidence_rows = []
        for item in stage["evidence"][:8]:
            source = f'<small>{escape(item["source"])}</small>' if item["source"] else ""
            evidence_rows.append(f'<li><blockquote>{escape(item["text"])}</blockquote>{source}</li>')
        evidence_html = "".join(evidence_rows) or '<li class="empty">暂无证据摘录</li>'
        confidence = round(stage["confidence"] * 100)
        transition_html = f'<div class="transition"><span>下一阶段转向</span><p>{escape(stage["transition"])}</p></div>' if stage["transition"] else ""
        summary_html = f'<p class="stage-summary">{escape(stage["summary"])}</p>' if stage["summary"] else ""
        cards.append(f'''<article class="stage{active}" data-index="{i}">
<header><div><div class="period">{escape(period_label(stage))}</div><h2>{escape(stage["label"])}</h2></div><div class="confidence"><span>{confidence}%</span><small>置信度</small></div></header>
{summary_html}
<section><h3>主导主题</h3><div class="theme-row">{themes_html}</div></section>
<div class="two-col"><section><h3>代表书籍</h3><ul>{books_html}</ul></section><section><h3>证据</h3><ul class="evidence">{evidence_html}</ul></section></div>
{transition_html}
</article>''')
    return "".join(cards)


def build_rail(stages):
    items = []
    for i, stage in enumerate(stages):
        color = STAGE_COLORS[i % len(STAGE_COLORS)]
        active = " active" if i == 0 else ""
        items.append(f'''<button type="button" class="rail-item{active}" data-index="{i}"><span class="rail-dot" style="background:{color}"></span><span class="rail-copy"><strong>{escape(stage["label"])}</strong><small>{escape(period_label(stage))}</small></span></button>''')
    return "".join(items)


def render_html(payload):
    stages = normalize(payload)
    if not stages:
        raise ValueError("No valid cognitive-shift stages found")
    coverage = payload.get("coverage") or {}
    coverage_html = "".join(
        f'<div><strong>{escape(str(coverage[key]))}</strong><span>{label}</span></div>'
        for key, label in [("books", "参与书籍"), ("notebookBooks", "有笔记书"), ("evidenceCount", "证据"), ("years", "覆盖年份")]
        if key in coverage
    )
    insights = [str(x) for x in (payload.get("insights") or []) if str(x).strip()]
    insights_html = "".join(f'<li>{escape(x)}</li>' for x in insights[:8])
    insights_section = f'<section class="insights"><h2>整体洞察</h2><ul>{insights_html}</ul></section>' if insights_html else ""
    data_json = json.dumps({"stages": stages}, ensure_ascii=False).replace("</", "<\\/")
    rail_html = build_rail(stages)
    cards_html = build_stage_cards(stages)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微信读书 · 认知变迁</title>
<style>
:root{{--bg:#F7F3EC;--panel:#FFFCF7;--text:#2B2724;--muted:#7A7066;--border:#E6DECF;--accent:#C2724B;--soft:#F0E8DC}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"SF Pro Display","Inter","PingFang SC","Microsoft YaHei",sans-serif}}main{{width:min(1180px,calc(100% - 28px));margin:0 auto;padding:40px 0 64px}}.eyebrow{{color:var(--accent);font-size:12px;font-weight:750;letter-spacing:.13em;text-transform:uppercase}}h1{{margin:7px 0;font-size:clamp(30px,5vw,50px);letter-spacing:-.04em}}.lead{{margin:0;max-width:800px;color:var(--muted);line-height:1.7}}.coverage{{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0 18px}}.coverage div{{min-width:110px;background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:13px 15px}}.coverage strong,.coverage span{{display:block}}.coverage strong{{font-size:19px}}.coverage span{{color:var(--muted);font-size:11px}}.layout{{display:grid;grid-template-columns:260px minmax(0,1fr);gap:16px;align-items:start}}.rail{{position:sticky;top:12px;background:var(--panel);border:1px solid var(--border);border-radius:22px;padding:12px}}.rail-item{{width:100%;display:grid;grid-template-columns:18px 1fr;gap:8px;align-items:start;border:0;background:transparent;text-align:left;padding:13px 8px;cursor:pointer;color:var(--text);border-radius:14px;font:inherit;position:relative}}.rail-item:not(:last-child)::after{{content:"";position:absolute;left:16px;top:34px;bottom:-13px;width:1px;background:var(--border)}}.rail-item.active{{background:var(--soft)}}.rail-dot{{width:12px;height:12px;border-radius:50%;margin-top:4px;z-index:1;box-shadow:0 0 0 3px var(--panel)}}.rail-copy strong,.rail-copy small{{display:block}}.rail-copy small{{color:var(--muted);margin-top:3px;font-size:11px}}.stage{{display:none;background:var(--panel);border:1px solid var(--border);border-radius:24px;padding:clamp(18px,4vw,32px)}}.stage.active{{display:block}}.stage header{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}}.period{{color:var(--accent);font-size:12px;font-weight:700}}.stage h2{{margin:5px 0 0;font-size:clamp(24px,4vw,36px)}}.stage h3{{font-size:12px;letter-spacing:.08em;color:var(--muted);margin:24px 0 10px}}.stage-summary{{color:#514A44;line-height:1.75;max-width:780px}}.confidence{{min-width:76px;padding:10px;border-radius:16px;background:var(--soft);text-align:center}}.confidence span,.confidence small{{display:block}}.confidence span{{font-size:20px;font-weight:760}}.confidence small{{color:var(--muted);font-size:10px;margin-top:2px}}.theme-row{{display:flex;flex-wrap:wrap;gap:7px}}.theme-chip{{border:1px solid var(--border);border-radius:999px;padding:7px 10px;background:#fff;font-size:13px}}.two-col{{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:24px}}ul{{margin:0;padding-left:20px}}li{{margin:9px 0;line-height:1.55}}.evidence blockquote{{margin:0;color:#49413B}}.evidence small{{display:block;color:var(--muted);margin-top:3px}}.transition{{margin-top:26px;border-left:3px solid var(--accent);background:var(--soft);padding:14px 16px;border-radius:0 14px 14px 0}}.transition span{{color:var(--accent);font-size:11px;font-weight:750}}.transition p{{margin:5px 0 0;line-height:1.65}}.insights{{margin-top:18px;background:var(--panel);border:1px solid var(--border);border-radius:20px;padding:18px 22px}}.insights h2{{margin:0 0 10px;font-size:17px}}.empty{{color:var(--muted)}}.meta{{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.6}}@media(max-width:820px){{main{{width:min(100% - 18px,1180px);padding-top:26px}}.layout{{grid-template-columns:1fr}}.rail{{position:static;display:flex;overflow-x:auto}}.rail-item{{min-width:190px}}.rail-item::after{{display:none}}.two-col{{grid-template-columns:1fr;gap:0}}}}
</style></head><body><main><div class="eyebrow">WeRead Intelligence · longitudinal evidence</div><h1>认知变迁</h1><p class="lead">把长期阅读拆成有证据支撑的阶段，观察主题重心如何迁移。阶段与“转向”属于解释层，不等同于心理诊断或人格定论。</p><div class="coverage">{coverage_html}</div><div class="layout"><nav class="rail" aria-label="阅读阶段">{rail_html}</nav><div>{cards_html}</div></div>{insights_section}<p class="meta">每个阶段应保留代表书籍、划线/想法和置信度；证据不足时应降低置信度，而不是补造一个完整故事。</p></main><script id="timeline-data" type="application/json">{data_json}</script><script>(()=>{{const buttons=[...document.querySelectorAll('.rail-item')],stages=[...document.querySelectorAll('.stage')];function select(index){{buttons.forEach((b,i)=>b.classList.toggle('active',i===index));stages.forEach((s,i)=>s.classList.toggle('active',i===index))}}buttons.forEach((button,index)=>button.addEventListener('click',()=>select(index)))}})();</script></body></html>'''


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead cognitive-shift JSON.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"ERROR: missing {args.input}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(payload), encoding="utf-8")
    print(f"cognitive-shift: {args.output} | stages={len(normalize(payload))}")


if __name__ == "__main__":
    main()
