#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a local/private evidence-bounded Advisor shortlist."""
from pathlib import Path
import argparse, html, json

def e(x): return html.escape(str(x or ""))

def render(d):
    cards=[]
    for x in d.get("shortlist") or []:
        reasons=''.join(f'<li>{e(r)}</li>' for r in x.get('evidenceBoundedReasons') or [])
        link=f'<a href="{e(x.get("deepLink"))}">打开微信读书</a>' if x.get('deepLink') else ''
        cards.append(f'<article><h3>{e(x.get("title"))}</h3><p class="meta">{e(x.get("author"))} · {e(x.get("category"))} · 评分 {x.get("rating") or "—"}</p><ul>{reasons}</ul>{link}</article>')
    evidence=d.get('readingEvidence') or {}
    read=''.join(f'<li>{e(x.get("title"))} · {x.get("noteCount",0)} 条笔记 · {e(x.get("depthBand"))}</li>' for x in evidence.get('matchedBooks') or [])
    axes=' / '.join((d.get('remainingGate') or {}).get('requiredAxes') or [])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Advisor · {e(d.get('topic'))}</title><style>:root{{--bg:#f2eee6;--paper:#fffdf8;--ink:#28241f;--muted:#756d63;--line:#ded5c8;--accent:#a9573f}}@media(prefers-color-scheme:dark){{:root{{--bg:#171614;--paper:#22201d;--ink:#f0e9df;--muted:#aaa096;--line:#403b35;--accent:#e07a5f;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif;line-height:1.6}}main{{max-width:980px;margin:auto;padding:34px 22px}}a{{color:var(--accent)}}.notice,article,section{{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}}.notice{{border-style:dashed}}.meta,.muted{{color:var(--muted);font-size:12px}}h1{{font-family:"Songti SC",serif}}h3{{margin:0}}ul{{padding-left:20px}}</style></head><body><main><p><a href="index.html">← Private Reading Lab</a></p><h1>Advisor · {e(d.get('topic'))}</h1><div class="notice"><strong>已完成：实时目录核验 + 已读排除 + 候选排序。</strong><p class="muted">还不能把它们叫“最终推荐”。剩余语义 gate：{e(axes)}。目录可用 ≠ 概念上真正补缺。</p></div><section><h2>你在这个主题上的既有证据</h2><ul>{read or '<li>当前 metadata 没有匹配到深读证据。</li>'}</ul></section><section><h2>实时验证候选</h2>{''.join(cards) or '<p class="muted">没有可用候选。</p>'}</section></main></body></html>'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=json.loads(a.input.read_text(encoding='utf-8'));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(d),encoding='utf-8')
if __name__=='__main__': main()
