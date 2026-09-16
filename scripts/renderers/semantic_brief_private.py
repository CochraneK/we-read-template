#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render an offline editor for candidate semantic annotations.

The page makes no network calls. Users can fill semantic evidence and export the
completed JSON for `apply_candidate_semantics.py`.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json

AXES=("school_or_viewpoint","era_or_paradigm","abstraction_level","adjacent_discipline")
LABELS={"school_or_viewpoint":"观点/学派","era_or_paradigm":"时代/范式","abstraction_level":"抽象层级","adjacent_discipline":"相邻学科"}


def esc(x): return html.escape(str(x or ""))


def render(data: dict) -> str:
    rows=[]
    mode=data.get("mode")
    for i,item in enumerate(data.get("items") or []):
        axes=''.join(f'''<div class="axis"><label>{LABELS[a]}<input data-axis="{a}" data-field="value" value="{esc((item.get('semanticAnnotation') or {}).get(a,{}).get('value'))}"></label><label>证据<textarea data-axis="{a}" data-field="evidence">{esc((item.get('semanticAnnotation') or {}).get(a,{}).get('evidence'))}</textarea></label><label>置信度 0–1<input type="number" min="0" max="1" step="0.05" data-axis="{a}" data-field="confidence" value="{esc((item.get('semanticAnnotation') or {}).get(a,{}).get('confidence') or 0)}"></label></div>''' for a in AXES)
        stage=''
        if mode=='path':
            stage='''<div class="stage"><label>阶段<select data-stage><option value="">未判断</option><option value="intro">intro 入门</option><option value="framework">framework 框架</option><option value="frontier">frontier 前沿</option></select></label><label>阶段证据<textarea data-stage-evidence></textarea></label></div>'''
        rows.append(f'''<article class="candidate" data-index="{i}"><h2>{esc(item.get('title'))}</h2><p class="meta">{esc(item.get('author'))} · {esc(item.get('category'))} · {esc(item.get('publisher'))}</p><div class="intro">{esc(item.get('intro')) or '暂无官方简介'}</div>{axes}<div class="fit"><label>为什么能补当前知识缺口<input data-fit="value"></label><label>证据<textarea data-fit="evidence"></textarea></label><label>置信度 0–1<input type="number" min="0" max="1" step="0.05" data-fit="confidence" value="0"></label></div>{stage}</article>''')
    payload=json.dumps(data,ensure_ascii=False).replace('</','<\/')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>Semantic Review · {esc(data.get('topic'))}</title><style>:root{{--bg:#f4efe7;--paper:#fffaf3;--ink:#28241f;--muted:#756d64;--line:#ddd2c4;--accent:#a6523d}}@media(prefers-color-scheme:dark){{:root{{--bg:#171513;--paper:#231f1c;--ink:#f2ece5;--muted:#aaa096;--line:#403832;--accent:#df7053;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif}}main{{max-width:1100px;margin:auto;padding:34px 22px}}.notice,.candidate{{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px;margin:14px 0}}.notice{{border-style:dashed}}.meta,.intro{{color:var(--muted);font-size:12px;line-height:1.6}}.axis,.fit,.stage{{display:grid;grid-template-columns:1fr 2fr 120px;gap:8px;margin-top:10px}}.stage{{grid-template-columns:1fr 2fr}}label{{font-size:11px;color:var(--muted)}}input,textarea,select{{display:block;width:100%;margin-top:4px;border:1px solid var(--line);border-radius:9px;padding:8px;background:var(--bg);color:var(--ink);font:inherit}}textarea{{min-height:70px;resize:vertical}}button{{border:1px solid var(--line);border-radius:999px;padding:9px 13px;background:var(--paper);color:var(--ink);cursor:pointer}}@media(max-width:760px){{.axis,.fit,.stage{{grid-template-columns:1fr}}}}</style></head><body><main><h1>Semantic Review · {esc(data.get('topic'))}</h1><div class="notice">这不是自动推荐器。请依据官方简介/类别/出版社与已有阅读证据填写；不知道就留空。只有证据和置信度达到 gate 的候选才会被后续脚本提升为最终推荐。</div><button id="export">导出已填写 JSON</button>{''.join(rows)}</main><script>const data={payload};document.querySelectorAll('.candidate').forEach(card=>{{const i=+card.dataset.index,item=data.items[i];card.querySelectorAll('[data-axis]').forEach(el=>el.addEventListener('input',()=>{{const a=el.dataset.axis,f=el.dataset.field;item.semanticAnnotation[a][f]=f==='confidence'?+el.value:el.value}}));card.querySelectorAll('[data-fit]').forEach(el=>el.addEventListener('input',()=>{{const f=el.dataset.fit;item.conceptualFit[f]=f==='confidence'?+el.value:el.value}}));const stage=card.querySelector('[data-stage]'),se=card.querySelector('[data-stage-evidence]');if(stage)stage.addEventListener('change',()=>item.stage=stage.value);if(se)se.addEventListener('input',()=>item.stageEvidence=se.value)}});document.getElementById('export').onclick=()=>{{const blob=new Blob([JSON.stringify(data,null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`weread-semantic-${{data.mode||'review'}}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}};</script></body></html>'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=json.loads(a.input.read_text(encoding='utf-8'));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(data),encoding='utf-8');print(f"semantic-editor: {a.output} | mode={data.get('mode')} candidates={len(data.get('items') or [])}")
if __name__=='__main__':main()
