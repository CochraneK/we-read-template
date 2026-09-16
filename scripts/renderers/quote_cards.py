#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a local-only quote card gallery from build_quote_lib.py output.

The gallery is intentionally designed for personal review/printing. It can contain
raw saved highlight text, so it must never be copied into the public Pages site.
Each card links back to the matching book inside the Private Reading Lab.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
import argparse
import html
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DATA / "analysis" / "private_lab" / "quotes" / "金句库.json"
DEFAULT_OUTPUT = DATA / "analysis" / "private_lab" / "quote_cards.html"


def selected_quotes(payload: dict, include_all: bool = False) -> list[dict]:
    rows = [q for q in (payload.get("quotes") or []) if isinstance(q, dict)]
    if include_all:
        return rows
    return [q for q in rows if q.get("selected")]


def card_html(quote_row: dict, index: int) -> str:
    text = html.escape(str(quote_row.get("text") or ""))
    title = html.escape(str(quote_row.get("title") or "未知书名"))
    author = html.escape(str(quote_row.get("author") or "未知作者"))
    chapter = html.escape(str(quote_row.get("chapter") or ""))
    theme = html.escape(str(quote_row.get("theme") or "其他"))
    tier = html.escape(str(quote_row.get("tier") or "—"))
    score = int(quote_row.get("score") or 0)
    raw_book_id = str(quote_row.get("bookId") or "")
    book_id = html.escape(raw_book_id, quote=True)
    search = html.escape(" ".join([text, title, author, chapter, theme]).lower(), quote=True)
    deep_link = f"weread://reading?bId={quote(raw_book_id, safe='')}" if raw_book_id else ""
    lab_link = f"index.html?book={quote(raw_book_id, safe='')}#book-workbench" if raw_book_id else "index.html"
    actions = '<div class="actions">'
    if deep_link:
        actions += f'<a class="book-link" href="{deep_link}">打开微信读书</a>'
    actions += f'<a class="lab-link" href="{lab_link}">进入这本书的 Workbench</a></div>'
    return f'''<article class="quote-card" tabindex="0" data-book-id="{book_id}" data-search="{search}" data-theme-label="{theme}" aria-label="第 {index} 张划线卡片，点击翻转">
  <div class="quote-card-inner">
    <section class="face front">
      <div class="eyebrow">{theme} · {tier} · {score}</div>
      <blockquote>{text}</blockquote>
      <footer><span>{author}</span><strong>《{title}》</strong></footer>
    </section>
    <section class="face back">
      <div class="back-title">《{title}》</div>
      <dl>
        <dt>作者</dt><dd>{author}</dd>
        <dt>章节</dt><dd>{chapter or '—'}</dd>
        <dt>主题</dt><dd>{theme}</dd>
        <dt>金句度</dt><dd>{score}</dd>
      </dl>
      {actions}
      <p class="private-note">个人划线证据 · 不代表本人观点 · 仅本地使用</p>
    </section>
  </div>
</article>'''


def render(payload: dict, *, include_all: bool = False) -> str:
    rows = selected_quotes(payload, include_all=include_all)
    cards = "\n".join(card_html(q, i) for i, q in enumerate(rows, 1))
    warning = html.escape(str((payload.get("meta") or {}).get("copyright_warning") or "公开传播前请人工核验版权。"))
    return f'''<!doctype html>
<html lang="zh-CN" data-card-theme="a">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>WeRead Private Quote Cards</title>
<style>
:root{{--bg:#f3eee5;--paper:#fffaf1;--ink:#2b2724;--muted:#7b7065;--line:#dfd4c5;--accent:#b85d3f;--shadow:0 16px 40px rgba(53,43,33,.10)}}
html[data-card-theme="b"]{{--bg:#ece7dc;--paper:#f9f5eb;--ink:#241f1a;--muted:#766b60;--line:#cfc5b7;--accent:#674739;--shadow:0 16px 40px rgba(35,29,24,.08)}}
html[data-card-theme="c"]{{--bg:#181715;--paper:#24211e;--ink:#f4eee5;--muted:#aaa096;--line:#403a34;--accent:#d46248;--shadow:none;color-scheme:dark}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Inter","PingFang SC","Noto Sans SC",sans-serif;line-height:1.6}}.wrap{{max-width:1280px;margin:auto;padding:28px}}h1{{font-family:"Songti SC","Noto Serif CJK SC",serif;margin:0 0 6px;font-size:30px}}.sub{{color:var(--muted);font-size:13px;max-width:850px}}.toolbar{{position:sticky;top:0;z-index:10;display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:12px 0 16px;background:color-mix(in srgb,var(--bg) 94%,transparent);backdrop-filter:blur(10px)}}button,input,.home-link{{font:inherit}}button,.home-link{{border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:8px 12px;cursor:pointer;text-decoration:none}}button[aria-pressed="true"]{{border-color:var(--accent);color:var(--accent)}}input{{flex:1;min-width:220px;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:9px 14px}}.count{{color:var(--muted);font-size:12px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}.quote-card{{min-height:300px;perspective:1200px;outline:none}}.quote-card-inner{{position:relative;width:100%;height:100%;min-height:300px;transition:transform .45s ease;transform-style:preserve-3d}}.quote-card.flipped .quote-card-inner{{transform:rotateY(180deg)}}.face{{position:absolute;inset:0;backface-visibility:hidden;background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:var(--shadow);display:flex;flex-direction:column}}.front blockquote{{margin:auto 0;font-family:"Songti SC","Noto Serif CJK SC",serif;font-size:22px;line-height:1.75;letter-spacing:.02em}}.front footer{{display:flex;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:13px}}.front footer strong{{color:var(--accent);font-weight:600}}.eyebrow{{color:var(--accent);font-size:11px;letter-spacing:.12em;text-transform:uppercase}}.back{{transform:rotateY(180deg)}}.back-title{{font-family:"Songti SC","Noto Serif CJK SC",serif;font-size:22px;margin-bottom:14px}}dl{{display:grid;grid-template-columns:64px 1fr;gap:8px 12px;margin:0}}dt{{color:var(--muted)}}dd{{margin:0}}.actions{{margin-top:auto;display:flex;gap:7px;flex-wrap:wrap}}.book-link,.lab-link{{color:var(--accent);text-decoration:none;font-weight:600;border:1px solid var(--line);border-radius:999px;padding:7px 9px;font-size:11px}}.private-note{{font-size:11px;color:var(--muted);margin:12px 0 0}}.hidden{{display:none}}.notice{{margin:16px 0 22px;padding:12px 14px;border:1px dashed var(--line);border-radius:12px;color:var(--muted);font-size:12px}}
@media (prefers-reduced-motion:reduce){{.quote-card-inner{{transition:none}}}}
@media print{{.toolbar,.notice{{display:none!important}}body{{background:#fff}}.wrap{{max-width:none;padding:0}}.grid{{grid-template-columns:repeat(2,1fr);gap:8mm}}.quote-card,.quote-card-inner{{min-height:120mm;break-inside:avoid}}.face{{box-shadow:none}}.quote-card.flipped .quote-card-inner{{transform:none}}.back{{display:none}}}}
</style>
</head>
<body><main class="wrap">
<h1>我的微信读书 · 划线卡片</h1>
<p class="sub">从个人划线中筛选、去重并按启发式“金句度”排序。划线是保存的原文，不自动代表你的观点；自己的想法应以 review 为证据。每张卡片都可进入对应书籍的 Private Lab Workbench。</p>
<div class="notice">本页含原始划线正文，属于私有阅读材料，不进入公开 GitHub Pages。{warning}</div>
<div class="toolbar">
  <a class="home-link" href="index.html">← Private Lab</a>
  <button type="button" data-set-theme="a" aria-pressed="true">A 暖米色</button>
  <button type="button" data-set-theme="b" aria-pressed="false">B 墨色</button>
  <button type="button" data-set-theme="c" aria-pressed="false">C 暗夜</button>
  <input id="q" type="search" placeholder="搜索原文 / 书名 / 作者 / 章节 / 主题">
  <span class="count" id="count">{len(rows)} 张</span>
</div>
<section class="grid" id="grid">{cards}</section>
</main>
<script>
(()=>{{
 const root=document.documentElement,cards=[...document.querySelectorAll('.quote-card')],input=document.getElementById('q'),count=document.getElementById('count');
 function setTheme(v){{root.dataset.cardTheme=v;document.querySelectorAll('[data-set-theme]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.setTheme===v)));localStorage.setItem('wereadPrivateQuoteThemeV1',v)}}
 const saved=localStorage.getItem('wereadPrivateQuoteThemeV1');if(['a','b','c'].includes(saved))setTheme(saved);
 document.querySelectorAll('[data-set-theme]').forEach(b=>b.addEventListener('click',()=>setTheme(b.dataset.setTheme)));
 function flip(card){{card.classList.toggle('flipped')}}
 cards.forEach(card=>{{card.addEventListener('click',e=>{{if(e.target.closest('a'))return;flip(card)}});card.addEventListener('keydown',e=>{{if(e.key==='Enter'||e.key===' '){{e.preventDefault();flip(card)}}}})}});
 function filter(){{const q=(input.value||'').trim().toLowerCase();let visible=0;cards.forEach(card=>{{const show=!q||card.dataset.search.includes(q);card.classList.toggle('hidden',!show);if(show)visible++}});count.textContent=`${{visible}} / ${{cards.length}} 张`}}
 input.addEventListener('input',filter);
}})();
</script></body></html>'''


def parse_args():
    parser = argparse.ArgumentParser(description="Render local-only WeRead quote cards.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--all", action="store_true", help="Render all candidates, not only selected quotes.")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"ERROR: missing {args.input}; run build_quote_lib.py first")
    payload_data = json.loads(args.input.read_text(encoding="utf-8"))
    page = render(payload_data, include_all=args.all)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(f"quote-cards: {args.output} | cards={len(selected_quotes(payload_data, args.all))} private=true")


if __name__ == "__main__":
    main()
