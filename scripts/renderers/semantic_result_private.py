#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json

LABELS={"school_or_viewpoint":"观点/学派","era_or_paradigm":"时代/范式","abstraction_level":"抽象层级","adjacent_discipline":"相邻学科"}

def e(x): return html.escape(str(x or ""))

def render(data: dict) -> str:
    cards=[]
    for x in data.get("promoted") or []:
        axes=''.join(f'<li><strong>{e(LABELS.get(k,k))}</strong>：{e((v or {}).get("value"))}<br><span>{e((v or {}).get("evidence"))} · confidence {e((v or {}).get("confidence"))}</span></li>' for k,v in (x.get('semanticAnnotation') or {}).items())
        fit=x.get('conceptualFit') or {}
        stage=f'<p><b>阶段：</b>{e(x.get("stage"))} · {e(x.get("stageEvidence"))}</p>' if data.get('mode')=='path' else ''
        link=f'<a href="{e(x.get("deepLink"))}">打开微信读书</a>' if x.get('deepLink') else ''
        cards.append(f'<article><h2>{e(x.get("title"))}</h2><p class="meta">{e(x.get("author"))} · {e(x.get("category"))}</p>{stage}<ul>{axes}</ul><p><b>为什么补缺：</b>{e(fit.get("value"))}</p><p class="muted">{e(fit.get("evidence"))} · confidence {e(fit.get("confidence"))}</p>{link}</article>')
    rejected=''.join(f'<li>{e(x.get("title"))}：{e(", ".join(x.get("semanticGateProblems") or []))}</li>' for x in data.get('rejected') or [])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Semantic Result</title><style>:root{{--bg:#f4efe7;--paper:#fffaf3;--ink:#28241f;--muted:#756d64;--line:#ddd2c4;--accent:#a6523d}}@media(prefers-color-scheme:dark){{:root{{--bg:#171513;--paper:#231f1c;--ink:#f2ece5;--muted:#aaa096;--line:#403832;--accent:#df7053;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif;line-height:1.7}}main{{max-width:980px;margin:auto;padding:34px 22px}}article,.notice{{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:17px;margin:12px 0}}.notice{{border-style:dashed}}.meta,.muted,li span{{color:var(--muted);font-size:12px}}a{{color:var(--accent)}}</style></head><body><main><p><a href="index.html">← Private Reading Lab</a></p><h1>{'Advisor 最终语义推荐' if data.get('mode')=='advisor' else 'Reading Path 语义审阅结果'}</h1><div class="notice">只有通过完整语义证据 gate 的候选会出现在这里；目录可用、评分高或标题相似都不能替代概念适配证据。</div>{''.join(cards) or '<p>暂无候选通过 gate。</p>'}<h2>未通过</h2><ul>{rejected or '<li>无</li>'}</ul></main></body></html>'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=json.loads(a.input.read_text(encoding='utf-8'));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(data),encoding='utf-8')
if __name__=='__main__':main()
