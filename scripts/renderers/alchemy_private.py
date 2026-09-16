#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render local-only Alchemy synthesis scaffold."""
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json


def esc(v):
    return html.escape(str(v or ""))


def evidence_cards(rows, kind):
    if not rows:
        return '<p class="muted">暂无证据。</p>'
    return ''.join(
        f'<article class="evidence {kind}"><small>{esc(r.get("title"))} · {esc(r.get("chapter"))}</small><p>{esc(r.get("text"))}</p></article>'
        for r in rows
    )


def render(data: dict) -> str:
    selector = data.get("selector") or {}
    title = selector.get("title") or selector.get("topic") or "Alchemy"
    if not data.get("ready"):
        body = '<section class="panel"><h2>需要先缩小范围</h2><p>当前跨主题证据量超过 scope gate。先回到 Alchemy Context 选择更窄的子主题，再生成综合。</p></section>'
    else:
        blocks=[]
        for c in data.get("clusters") or []:
            blocks.append(f'''<section class="cluster"><div class="cluster-head"><div><span>议题候选</span><h2>{esc(c.get("label"))}</h2></div><small>{c.get("evidenceCount",0)} 条 · 来源 {c.get("sourceCount",0)} · 我的想法 {c.get("userThoughtCount",0)}</small></div><p class="question">{esc(c.get("question"))}</p><div class="cols"><div><h3>来源文本</h3>{evidence_cards(c.get("representativeSourceText") or [],"source")}</div><div><h3>我的想法</h3>{evidence_cards(c.get("representativeUserThought") or [],"thought")}</div></div><div class="books">涉及：{esc(' / '.join(c.get("books") or []))}</div></section>''')
        body=''.join(blocks)
    questions=''.join(f'<li>{esc(q)}</li>' for q in data.get('questions') or [])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Alchemy · {esc(title)}</title><style>
:root{{--bg:#f2eee6;--paper:#fffdf8;--paper2:#f8f3ea;--ink:#28241f;--muted:#756d63;--line:#ded5c8;--accent:#a9573f;--green:#71866e}}@media(prefers-color-scheme:dark){{:root{{--bg:#171614;--paper:#22201d;--paper2:#2a2723;--ink:#f0e9df;--muted:#aaa096;--line:#403b35;--accent:#e07a5f;--green:#94ad8f;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif;line-height:1.65}}main{{max-width:1120px;margin:auto;padding:34px 22px 60px}}a{{color:var(--accent)}}h1{{font-family:"Songti SC",serif;font-size:36px;margin:4px 0}}.muted{{color:var(--muted)}}.notice,.panel,.cluster{{border:1px solid var(--line);background:var(--paper);border-radius:18px;padding:18px;margin:14px 0}}.notice{{border-style:dashed}}.cluster-head{{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}}.cluster-head span{{font-size:10px;color:var(--accent);letter-spacing:.12em}}.cluster h2{{margin:3px 0;font-size:23px}}.cluster h3{{font-size:13px}}.cols{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.evidence{{padding:11px;border-radius:12px;background:var(--paper2);border:1px solid var(--line);margin:8px 0}}.evidence small{{color:var(--muted)}}.evidence p{{white-space:pre-wrap;margin:5px 0 0}}.thought{{border-left:4px solid var(--accent)}}.source{{border-left:4px solid var(--green)}}.question{{font-weight:650}}.books{{font-size:11px;color:var(--muted);margin-top:8px}}@media(max-width:760px){{.cols{{grid-template-columns:1fr}}}}
</style></head><body><main><p><a href="index.html">← Private Reading Lab</a></p><div class="notice"><strong>Private Alchemy</strong><br><span class="muted">这是私人证据综合页。议题名来自词法聚类，只是进一步思考的候选，不是模型理解后的确定结论。</span></div><h1>{esc(title)}</h1><p class="muted">来源文本与“我的想法”始终分栏显示，避免把作者原文误当成你的观点。</p>{body}<section class="panel"><h2>下一轮问题</h2><ul>{questions}</ul></section></main></body></html>'''


def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();data=json.loads(a.input.read_text(encoding="utf-8"));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(data),encoding="utf-8");print(f"alchemy-private: {a.output} | clusters={len(data.get('clusters') or [])}")

if __name__=="__main__": main()
