#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render evidence-based blindspot/counter-reading JSON to standalone HTML."""
from __future__ import annotations

from pathlib import Path
from html import escape
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DATA / "analysis" / "blindspot.json"
DEFAULT_OUTPUT = DATA / "analysis" / "blindspot.html"


def clamp(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, min(1.0, value))


def evidence_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text") or value.get("label") or value.get("summary") or value.get("title") or "")
    return str(value)


def render_html(payload: dict) -> str:
    blindspots = [x for x in (payload.get("blindspots") or []) if isinstance(x, dict)]
    if not blindspots:
        raise ValueError("blindspot report needs at least one blindspot item")

    cards = []
    for item in blindspots:
        label = str(item.get("label") or "可能的盲点").strip()
        summary = str(item.get("summary") or "").strip()
        confidence = round(clamp(item.get("confidence")) * 100)
        evidence = [evidence_text(x).strip() for x in (item.get("evidence") or []) if evidence_text(x).strip()]
        counter = [evidence_text(x).strip() for x in (item.get("counterEvidence") or []) if evidence_text(x).strip()]
        directions = [str(x).strip() for x in (item.get("counterReadingDirections") or []) if str(x).strip()]
        questions = [str(x).strip() for x in (item.get("questions") or []) if str(x).strip()]
        evidence_html = "".join(f"<li>{escape(x)}</li>" for x in evidence[:8]) or "<li class=muted>暂无证据条目</li>"
        counter_html = "".join(f"<li>{escape(x)}</li>" for x in counter[:6])
        directions_html = "".join(f"<li>{escape(x)}</li>" for x in directions[:6])
        questions_html = "".join(f"<li>{escape(x)}</li>" for x in questions[:6])
        cards.append(
            '<article class="card">'
            f'<header><h2>{escape(label)}</h2><span>{confidence}%</span></header>'
            f'<div class="meter"><i style="width:{confidence}%"></i></div>'
            f'<p>{escape(summary)}</p>'
            '<h3>证据</h3><ul>' + evidence_html + '</ul>'
            + (('<h3>反证 / 限制</h3><ul class="soft">' + counter_html + '</ul>') if counter_html else '')
            + (('<h3>反向阅读方向</h3><ul>' + directions_html + '</ul>') if directions_html else '')
            + (('<h3>值得追问</h3><ul>' + questions_html + '</ul>') if questions_html else '')
            + '</article>'
        )

    global_questions = "".join(
        f"<li>{escape(str(x))}</li>" for x in (payload.get("questions") or []) if str(x).strip()
    )
    summary = str(payload.get("summary") or "").strip()
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微信读书 · Blindspot</title><style>
:root{{--bg:#F5F1EA;--panel:#FFFCF7;--text:#2B2724;--muted:#786F67;--line:#E4DACD;--accent:#A75C3C;--soft:#EFE6DB}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif}}main{{width:min(1080px,calc(100% - 28px));margin:auto;padding:48px 0 72px}}.eyebrow{{font-size:12px;font-weight:800;letter-spacing:.14em;color:var(--accent)}}h1{{font-size:clamp(34px,6vw,60px);letter-spacing:-.05em;margin:9px 0}}.lead{{max-width:820px;color:var(--muted);line-height:1.8}}.notice{{background:var(--soft);border-left:3px solid var(--accent);padding:13px 15px;border-radius:0 14px 14px 0;line-height:1.65;font-size:12px;margin:18px 0 28px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:20px}}.card header{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.card h2{{font-size:19px;margin:0}}.card header span{{font-weight:850;color:var(--accent)}}.meter{{height:5px;background:var(--soft);overflow:hidden;border-radius:99px;margin:11px 0 16px}}.meter i{{height:100%;display:block;background:var(--accent)}}.card p,.card li{{line-height:1.68}}.card h3{{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:18px 0 6px}}.card ul{{margin:0;padding-left:20px}}.soft li,.muted{{color:var(--muted)}}.questions{{margin-top:20px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main><div class="eyebrow">WEREAD INTELLIGENCE · BLINDSPOT / COUNTER READING</div><h1>给自己的阅读找反例</h1>{f'<p class="lead">{escape(summary)}</p>' if summary else ''}<div class="notice">这里的“盲点”不是人格缺陷或心理诊断，只是当前阅读数据里值得核对的集中度、投入落差或缺失视角。反向阅读的目标是挑战论点，不是给读者贴标签。</div><section class="grid">{''.join(cards)}</section>{f'<section class="questions"><h2>全局追问</h2><ul>{global_questions}</ul></section>' if global_questions else ''}</main></body></html>'''


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead blindspot analysis JSON.")
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
    print(f"blindspot: {args.output}")


if __name__ == "__main__":
    main()
