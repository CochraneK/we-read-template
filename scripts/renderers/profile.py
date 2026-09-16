#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render evidence-based WeRead reading profile JSON to standalone HTML."""
from __future__ import annotations

from pathlib import Path
from html import escape
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DATA / "analysis" / "reading_profile.json"
DEFAULT_OUTPUT = DATA / "analysis" / "reading_profile.html"


def clamp(value, low=0.0, high=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return max(low, min(high, value))


def evidence_text(item):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item)
    return str(item.get("text") or item.get("title") or item.get("label") or item.get("summary") or item.get("source") or "")


def normalize(payload):
    facts = []
    for fact in payload.get("facts") or []:
        if not isinstance(fact, dict) or not str(fact.get("label") or "").strip():
            continue
        facts.append({
            "label": str(fact.get("label") or "").strip(),
            "value": str(fact.get("value") if fact.get("value") is not None else "—"),
            "detail": str(fact.get("detail") or "").strip(),
            "source": str(fact.get("source") or "").strip(),
        })

    interpretations = []
    for item in payload.get("interpretations") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not label or not summary:
            continue
        interpretations.append({
            "label": label,
            "summary": summary,
            "confidence": clamp(item.get("confidence")),
            "evidence": [evidence_text(x).strip() for x in (item.get("evidence") or []) if evidence_text(x).strip()],
            "counterEvidence": [evidence_text(x).strip() for x in (item.get("counterEvidence") or []) if evidence_text(x).strip()],
        })
    return facts, interpretations


def render_html(payload):
    headline = str(payload.get("headline") or "阅读画像").strip()
    summary = str(payload.get("summary") or "").strip()
    facts, interpretations = normalize(payload)
    if not facts and not interpretations:
        raise ValueError("reading profile needs at least one fact or interpretation")

    fact_html = "".join(
        f'''<article class="fact"><div class="fact-value">{escape(fact["value"])}</div><div class="fact-label">{escape(fact["label"])}</div>{f'<p>{escape(fact["detail"])}</p>' if fact["detail"] else ''}{f'<small>{escape(fact["source"])}</small>' if fact["source"] else ''}</article>'''
        for fact in facts
    )

    cards = []
    for item in interpretations:
        confidence = round(item["confidence"] * 100)
        evidence_html = "".join(f"<li>{escape(x)}</li>" for x in item["evidence"][:8]) or "<li class=muted>暂无证据条目</li>"
        counter_html = "".join(f"<li>{escape(x)}</li>" for x in item["counterEvidence"][:6])
        counter_section = f'<div class="counter"><h4>反证 / 限制</h4><ul>{counter_html}</ul></div>' if counter_html else ""
        cards.append(f'''<article class="interpretation"><header><h3>{escape(item["label"])}</h3><span>{confidence}%</span></header><div class="meter"><i style="width:{confidence}%"></i></div><p>{escape(item["summary"])}</p><h4>证据</h4><ul>{evidence_html}</ul>{counter_section}</article>''')
    interpretations_html = "".join(cards)

    coverage = payload.get("coverage") or {}
    coverage_text = " · ".join(f"{escape(str(k))}: {escape(str(v))}" for k, v in coverage.items())
    themes = payload.get("themes") or []
    theme_html = "".join(
        f'<span>{escape(str(t.get("label") if isinstance(t, dict) else t))}</span>'
        for t in themes[:16]
        if str(t.get("label") if isinstance(t, dict) else t).strip()
    )

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微信读书 · 阅读画像</title><style>
:root{{--bg:#F7F3EC;--panel:#FFFCF7;--text:#2B2724;--muted:#7A7066;--border:#E6DECF;--accent:#C2724B;--soft:#F0E8DC}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif}}main{{width:min(1080px,calc(100% - 28px));margin:auto;padding:42px 0 68px}}.eyebrow{{font-size:12px;color:var(--accent);font-weight:800;letter-spacing:.12em}}h1{{font-size:clamp(30px,5vw,52px);letter-spacing:-.04em;margin:8px 0}}.lead{{color:var(--muted);line-height:1.75;max-width:780px}}.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:28px 0}}.fact{{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:17px}}.fact-value{{font-size:22px;font-weight:800}}.fact-label{{font-size:12px;color:var(--muted);margin-top:4px}}.fact p{{font-size:12px;line-height:1.55;margin:10px 0 0}}.fact small{{display:block;color:var(--muted);margin-top:7px}}.themes{{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 22px}}.themes span{{background:var(--soft);border-radius:999px;padding:7px 10px;font-size:12px}}h2{{font-size:18px;margin:28px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.interpretation{{background:var(--panel);border:1px solid var(--border);border-radius:22px;padding:20px}}.interpretation header{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.interpretation h3{{margin:0;font-size:18px}}.interpretation header span{{color:var(--accent);font-weight:800}}.meter{{height:5px;background:var(--soft);border-radius:99px;overflow:hidden;margin:11px 0 14px}}.meter i{{display:block;height:100%;background:var(--accent)}}.interpretation p,.interpretation li{{line-height:1.65}}.interpretation p{{color:#514A44}}.interpretation h4{{font-size:11px;color:var(--muted);letter-spacing:.08em;margin:18px 0 6px}}.interpretation ul{{margin:0;padding-left:20px}}.counter{{border-top:1px solid var(--border);margin-top:16px;padding-top:2px}}.counter li{{color:var(--muted)}}.meta{{font-size:11px;color:var(--muted);margin-top:18px;line-height:1.6}}.warning{{border-left:3px solid var(--accent);background:var(--soft);padding:12px 14px;margin-top:20px;border-radius:0 14px 14px 0;font-size:12px;line-height:1.65}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}main{{width:min(100% - 18px,1080px);padding-top:28px}}}}</style></head><body><main><div class="eyebrow">WEREAD INTELLIGENCE · EVIDENCE-BASED PROFILE</div><h1>{escape(headline)}</h1>{f'<p class="lead">{escape(summary)}</p>' if summary else ''}<section class="facts">{fact_html}</section>{f'<div class="themes">{theme_html}</div>' if theme_html else ''}<h2>解释型洞察</h2><section class="grid">{interpretations_html}</section><div class="warning">“画像”是基于当前数据的解释，不是心理诊断、人格定型或敏感属性推断。事实卡与解释卡必须分开阅读。</div>{f'<div class="meta">数据覆盖：{coverage_text}</div>' if coverage_text else ''}</main></body></html>'''


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead reading profile JSON.")
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
    print(f"reading-profile: {args.output}")


if __name__ == "__main__":
    main()
