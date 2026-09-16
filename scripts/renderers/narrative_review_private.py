#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json


def render(draft: dict) -> str:
    title = html.escape(str(draft.get("title") or "阅读复盘"))
    spec = draft.get("platformSpec") or {}
    sections = []
    for sec in draft.get("sections") or []:
        body = "".join(f"<p>{html.escape(str(p))}</p>" for p in sec.get("paragraphs") or [])
        bullets = sec.get("bullets") or []
        if bullets:
            body += "<ul>" + "".join(f"<li>{html.escape(str(x))}</li>" for x in bullets) + "</ul>"
        sections.append(f"<section><h2>{html.escape(str(sec.get('heading') or ''))}</h2>{body}</section>")
    prompts = "".join(f"<li>{html.escape(str(x))}</li>" for x in draft.get("editingPrompts") or [])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>{title}</title><style>
:root{{--bg:#f4efe6;--paper:#fffaf3;--ink:#28241f;--muted:#756d64;--line:#ded3c5;--accent:#a95039}}@media(prefers-color-scheme:dark){{:root{{--bg:#171513;--paper:#221f1c;--ink:#f4eee7;--muted:#aaa096;--line:#3e3832;--accent:#df6b50;color-scheme:dark}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC",sans-serif;line-height:1.8}}main{{max-width:860px;margin:auto;padding:46px 24px 80px}}h1,h2{{font-family:"Songti SC","Noto Serif CJK SC",serif}}h1{{font-size:38px;line-height:1.3;margin:0 0 10px}}h2{{font-size:23px;margin-top:34px}}.meta{{color:var(--muted);font-size:13px}}.notice{{border:1px dashed var(--line);border-radius:14px;padding:14px 16px;margin:22px 0;background:var(--paper)}}section{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:22px;margin:16px 0}}li{{margin:5px 0}}.prompt{{border-left:4px solid var(--accent)}}button{{border:1px solid var(--line);border-radius:999px;background:var(--paper);color:var(--ink);padding:8px 12px;cursor:pointer}}@media print{{button{{display:none}}body{{background:#fff}}section{{break-inside:avoid;box-shadow:none}}}}
</style></head><body><main><button onclick="window.print()">打印 / 保存 PDF</button><h1>{title}</h1><div class="meta">平台：{html.escape(str(spec.get('label') or draft.get('platform') or ''))} · 建议篇幅 {html.escape(str(spec.get('length') or ''))}</div><div class="notice"><strong>证据边界：</strong>这是一版事实约束草稿。数字与书目来自阅读数据；兴趣转向、弃读原因和“改变了我”之类的因果意义不会自动编造。</div>{''.join(sections)}<section class="prompt"><h2>发布前编辑检查</h2><ul>{prompts}</ul></section></main></body></html>'''


def main():
    p=argparse.ArgumentParser(description="Render private reading review HTML")
    p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    draft=json.loads(a.input.read_text(encoding="utf-8"));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(draft),encoding="utf-8");print(f"narrative-review-report: {a.output}")

if __name__=="__main__":main()
