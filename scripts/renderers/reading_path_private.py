#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render private Reading Path discovery pools or finalized verified plans."""
from pathlib import Path
import argparse, html, json

def e(x): return html.escape(str(x or ""))

def card(x):
    link=f'<a href="{e(x.get("deepLink"))}">打开微信读书</a>' if x.get('deepLink') else ''
    status='已读，路径中跳过' if x.get('alreadyRead') or x.get('planStatus')=='skip_already_read' else '候选'
    return f'<article class="book"><h3>{e(x.get("title"))}</h3><p>{e(x.get("author"))} · {e(x.get("category"))}</p><small>{status} · 评分 {x.get("rating") or "—"} · {e(x.get("wordCount") or "字数未知")}</small>{link}</article>'

def render_discovery(d):
    groups=[]
    for stage in ('intro','framework','frontier'):
        rows=[x for x in d.get('items') or [] if stage in (x.get('stageProposals') or [x.get('stageProposed')])]
        groups.append(f'<section><h2>{stage}</h2><p class="muted">查询阶段只是发现启发，不等于语义确认。</p><div class="grid">{"".join(card(x) for x in rows[:12]) or "<p>暂无候选</p>"}</div></section>')
    return ''.join(groups)

def render_plan(d):
    blocks=[]
    for stage in d.get('stages') or []:
        chosen=''.join(card(x) for x in stage.get('selected') or [])
        skips=''.join(card(x) for x in stage.get('alreadyReadKeptAsContext') or [])
        blocks.append(f'<section><h2>{e(stage.get("label"))}</h2><p>{e(stage.get("purpose"))}</p><div class="grid">{chosen or "<p>候选不足</p>"}</div><p class="checkpoint"><strong>Feynman：</strong>{e(stage.get("feynmanCheckpoint"))}</p>{("<details><summary>已读上下文</summary><div class=\"grid\">"+skips+"</div></details>") if skips else ""}</section>')
    minimum=''.join(card(x) for x in d.get('minimumVersion') or [])
    t=d.get('timeEstimate') or {}
    return f'<div class="notice"><strong>ready={d.get("ready")}</strong> · 缺口 {e(d.get("deficits"))} · 已知字数书 {t.get("booksWithWordCount",0)}/{t.get("booksSelected",0)} · 已知部分约 {t.get("estimatedHoursKnownBooks",0)}h</div>{"".join(blocks)}<section><h2>最小版本</h2><div class="grid">{minimum}</div></section>'

def render(d):
    discovery='searches' in d and 'stages' not in d
    body=render_discovery(d) if discovery else render_plan(d)
    title=f'Reading Path · {e(d.get("topic"))}'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>{title}</title><style>:root{{--bg:#f2eee6;--paper:#fffdf8;--ink:#28241f;--muted:#756d63;--line:#ded5c8;--accent:#a9573f}}@media(prefers-color-scheme:dark){{:root{{--bg:#171614;--paper:#22201d;--ink:#f0e9df;--muted:#aaa096;--line:#403b35;--accent:#e07a5f;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif;line-height:1.6}}main{{max-width:1050px;margin:auto;padding:34px 22px}}a{{color:var(--accent);display:block;margin-top:8px}}h1{{font-family:"Songti SC",serif}}section,.notice{{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}}.notice{{border-style:dashed}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.book{{border:1px solid var(--line);border-radius:12px;padding:12px}}.book h3{{margin:0}}.book p,.book small,.muted{{color:var(--muted)}}.checkpoint{{border-top:1px dashed var(--line);padding-top:10px}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main><p><a href="index.html">← Private Reading Lab</a></p><h1>{title}</h1>{body}</main></body></html>'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=json.loads(a.input.read_text(encoding='utf-8'));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(d),encoding='utf-8')
if __name__=='__main__': main()
