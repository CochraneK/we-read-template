#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble WeRead deterministic facts and optional AI analyses into one HTML report."""
from __future__ import annotations

from pathlib import Path
from html import escape
from collections import Counter
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
ANALYSIS = DATA / "analysis"

DEFAULT_CONTEXT = ANALYSIS / "visualization_context.json"
DEFAULT_NARRATIVE = ANALYSIS / "reading_report.json"
DEFAULT_MAP = ANALYSIS / "reading_map.json"
DEFAULT_SHIFT = ANALYSIS / "cognitive_shift.json"
DEFAULT_GRAPH = ANALYSIS / "knowledge_graph.json"
DEFAULT_PROFILE = ANALYSIS / "reading_profile.json"
DEFAULT_OUTPUT = ANALYSIS / "reading_report.html"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value, low=0.0, high=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return max(low, min(high, value))


def format_duration(seconds):
    try:
        seconds = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        seconds = 0
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分"


def evidence_text(item):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item)
    return str(
        item.get("text")
        or item.get("title")
        or item.get("label")
        or item.get("summary")
        or item.get("source")
        or ""
    )


def period_from_context(context):
    annual = ((context.get("reading") or {}).get("annual") or [])
    years = [str(x.get("year")) for x in annual if isinstance(x, dict) and x.get("year")]
    if not years:
        return "全部可用数据"
    return years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"


def deterministic_stats(context):
    coverage = context.get("coverage") or {}
    overall = ((context.get("reading") or {}).get("overall") or {})
    return [
        ("总阅读时长", format_duration(overall.get("totalReadTime"))),
        ("有效阅读天", f"{int(overall.get('readDays') or 0)} 天"),
        ("纳入书籍", f"{int(coverage.get('contextBooks') or 0)} 本"),
        ("有笔记书", f"{int(coverage.get('booksWithNotes') or 0)} 本"),
        ("划线", f"{int(coverage.get('marks') or 0)} 条"),
        ("想法", f"{int(coverage.get('reviews') or 0)} 条"),
    ]


def top_themes(reading_map, limit=8):
    nodes = [n for n in ((reading_map or {}).get("nodes") or []) if isinstance(n, dict)]
    nodes.sort(
        key=lambda n: (float(n.get("weight") or 0), float(n.get("confidence") or 0)),
        reverse=True,
    )
    out = []
    for node in nodes[:limit]:
        label = str(node.get("label") or "").strip()
        if not label:
            continue
        out.append(
            {
                "label": label,
                "summary": str(node.get("summary") or "").strip(),
                "tier": str(node.get("tier") or ""),
                "confidence": clamp(node.get("confidence")),
                "evidenceCount": len(node.get("evidence") or []),
            }
        )
    return out


def stages(cognitive_shift, limit=8):
    out = []
    for item in ((cognitive_shift or {}).get("stages") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "label": str(item.get("label") or "阶段").strip(),
                "period": f"{item.get('start') or '?'} → {item.get('end') or '?'}",
                "summary": str(item.get("summary") or item.get("transition") or "").strip(),
                "themes": [str(x) for x in (item.get("themes") or [])[:6]],
                "confidence": clamp(item.get("confidence")),
            }
        )
    return out


def graph_summary(graph):
    nodes = [n for n in ((graph or {}).get("nodes") or []) if isinstance(n, dict)]
    edges = [e for e in ((graph or {}).get("edges") or []) if isinstance(e, dict)]
    types = Counter(str(n.get("type") or "unknown") for n in nodes)
    focus = [n for n in nodes if n.get("type") in {"theme", "concept"}]
    focus.sort(key=lambda n: float(n.get("weight") or 0), reverse=True)
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "types": types,
        "focus": [str(n.get("label") or "") for n in focus[:10] if n.get("label")],
    }


def profile_summary(profile):
    items = []
    for item in ((profile or {}).get("interpretations") or [])[:6]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not label or not summary:
            continue
        evidence = []
        for raw in (item.get("evidence") or [])[:3]:
            text = evidence_text(raw).strip()
            if text:
                evidence.append(text)
        items.append(
            {
                "label": label,
                "summary": summary,
                "confidence": clamp(item.get("confidence")),
                "evidence": evidence,
            }
        )
    return items


def build_model(context, narrative=None, reading_map=None, cognitive_shift=None, graph=None, profile=None):
    narrative = narrative or {}
    profile = profile or {}
    return {
        "title": str(narrative.get("title") or "我的微信读书阅读报告"),
        "subtitle": str(narrative.get("subtitle") or "从阅读行为到主题、认知与知识网络"),
        "period": str(narrative.get("period") or period_from_context(context)),
        "summary": str(
            narrative.get("summary")
            or profile.get("summary")
            or "本报告把确定性阅读事实与解释型分析分开呈现；所有解释应回到书籍、划线、想法和时间证据核对。"
        ),
        "stats": deterministic_stats(context),
        "highlights": list(narrative.get("highlights") or [])[:8],
        "takeaways": list(narrative.get("takeaways") or [])[:6],
        "nextActions": list(narrative.get("nextActions") or [])[:6],
        "themes": top_themes(reading_map),
        "stages": stages(cognitive_shift),
        "graph": graph_summary(graph),
        "profile": profile_summary(profile),
        "privacy": context.get("privacy") or {},
        "coverage": context.get("coverage") or {},
    }


def render_highlights(items):
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        detail = ""
        if item.get("detail"):
            detail = "<p>" + escape(str(item.get("detail") or "")) + "</p>"
        parts.append(
            '<article class="mini"><b>{}</b><span>{}</span>{}</article>'.format(
                escape(str(item.get("value", "—"))),
                escape(str(item.get("label", ""))),
                detail,
            )
        )
    return "".join(parts)


def render_themes(items):
    if not items:
        return '<p class="muted">尚未生成 Reading Map。</p>'
    parts = []
    for item in items:
        parts.append(
            '<article class="theme"><header><h3>{}</h3><span>{}%</span></header>'
            '<p>{}</p><small>{} · 证据 {} 条</small></article>'.format(
                escape(item["label"]),
                round(item["confidence"] * 100),
                escape(item["summary"] or "跨书主题"),
                escape(item["tier"] or "theme"),
                item["evidenceCount"],
            )
        )
    return "".join(parts)


def render_stages(items):
    if not items:
        return '<p class="muted">尚未生成 Cognitive Shift。</p>'
    parts = []
    for item in items:
        chips = "".join("<span>{}</span>".format(escape(t)) for t in item["themes"])
        parts.append(
            '<article class="stage"><div class="dot"></div><small>{}</small><h3>{}</h3>'
            '<p>{}</p><div class="chips">{}</div><em>置信度 {}%</em></article>'.format(
                escape(item["period"]),
                escape(item["label"]),
                escape(item["summary"]),
                chips,
                round(item["confidence"] * 100),
            )
        )
    return "".join(parts)


def render_profile(items):
    if not items:
        return '<p class="muted">尚未生成 Reading Profile。</p>'
    parts = []
    for item in items:
        evidence = ""
        if item["evidence"]:
            evidence = "<ul>" + "".join(
                "<li>{}</li>".format(escape(text)) for text in item["evidence"]
            ) + "</ul>"
        parts.append(
            '<article class="insight"><header><h3>{}</h3><span>{}%</span></header>'
            '<p>{}</p>{}</article>'.format(
                escape(item["label"]),
                round(item["confidence"] * 100),
                escape(item["summary"]),
                evidence,
            )
        )
    return "".join(parts)


def render_takeaways(items):
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        confidence = ""
        if item.get("confidence") is not None:
            confidence = "<span>{}%</span>".format(round(clamp(item.get("confidence")) * 100))
        parts.append(
            '<article class="insight"><header><h3>{}</h3>{}</header><p>{}</p></article>'.format(
                escape(str(item.get("title") or "洞察")),
                confidence,
                escape(str(item.get("summary") or "")),
            )
        )
    return "".join(parts)


def render_actions(items):
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        reason = ""
        if item.get("reason"):
            reason = "<span>{}</span>".format(escape(str(item.get("reason") or "")))
        parts.append(
            "<li><b>{}</b>{}</li>".format(escape(str(item.get("title") or "")), reason)
        )
    return "".join(parts)


def render_html(model, asset_links=None):
    asset_links = asset_links or {}
    stats_html = "".join(
        '<article class="stat"><b>{}</b><span>{}</span></article>'.format(
            escape(value), escape(label)
        )
        for label, value in model["stats"]
    )
    highlights_html = render_highlights(model["highlights"])
    themes_html = render_themes(model["themes"])
    stages_html = render_stages(model["stages"])
    profile_html = render_profile(model["profile"])
    takeaway_html = render_takeaways(model["takeaways"])
    actions_html = render_actions(model["nextActions"])

    graph = model["graph"]
    type_text = " · ".join(
        "{} {}".format(escape(k), v) for k, v in sorted(graph["types"].items())
    )
    focus_html = "".join("<span>{}</span>".format(escape(x)) for x in graph["focus"])
    links_html = "".join(
        '<a href="{}">{} ↗</a>'.format(escape(href), escape(label))
        for label, href in asset_links.items()
    )

    excluded = int(model["coverage"].get("excludedPrivateBooks") or 0)
    if excluded:
        privacy_note = f"默认隐私策略已排除 {excluded} 本明确标记为私密的书。"
    else:
        privacy_note = "当前上下文按默认隐私策略构建，未发现被排除的明确私密书。"

    highlights_section = '<div class="highlights">{}</div>'.format(highlights_html) if highlights_html else ""
    takeaways_section = ""
    if takeaway_html:
        takeaways_section = (
            '<section><div class="section-head"><h2>关键结论</h2>'
            '<p>来自 reading_report.json 的编辑层</p></div><div class="grid">{}</div></section>'
        ).format(takeaway_html)
    actions_section = ""
    if actions_html:
        actions_section = (
            '<section><div class="section-head"><h2>下一步</h2>'
            '<p>行动建议不是事实指标</p></div><ol class="actions">{}</ol></section>'
        ).format(actions_html)
    links_section = '<div class="links">{}</div>'.format(links_html) if links_html else ""

    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
:root{{--bg:#F4F0E9;--panel:#FFFDF9;--text:#282421;--muted:#776E66;--line:#E3D9CC;--accent:#B86643;--soft:#EFE5D8}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif}}main{{width:min(1160px,calc(100% - 28px));margin:auto;padding:52px 0 80px}}.hero{{padding:26px 0 18px;border-bottom:1px solid var(--line)}}.eyebrow{{font-size:12px;font-weight:800;letter-spacing:.14em;color:var(--accent)}}h1{{font-size:clamp(36px,6vw,68px);line-height:1.02;letter-spacing:-.055em;margin:10px 0 12px}}.subtitle{{font-size:18px;color:var(--muted)}}.summary{{max-width:850px;font-size:16px;line-height:1.8}}.period{{display:inline-block;margin-top:10px;padding:7px 10px;background:var(--soft);border-radius:999px;font-size:12px}}.stats,.highlights{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin:20px 0}}.stat,.mini,.theme,.insight,.graphbox{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px}}.stat b,.mini b{{display:block;font-size:20px}}.stat span,.mini span{{display:block;font-size:11px;color:var(--muted);margin-top:5px}}.mini p{{font-size:12px;line-height:1.55;color:var(--muted)}}section{{padding:28px 0;border-bottom:1px solid var(--line)}}.section-head{{display:flex;justify-content:space-between;gap:14px;align-items:end;margin-bottom:14px}}h2{{font-size:24px;margin:0}}.section-head p{{margin:0;color:var(--muted);font-size:12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.theme header,.insight header{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.theme h3,.insight h3,.stage h3{{margin:0;font-size:17px}}.theme header span,.insight header span{{color:var(--accent);font-weight:800}}.theme p,.insight p,.stage p{{line-height:1.65;color:#514A44}}.theme small,.stage small,.stage em{{font-size:11px;color:var(--muted);font-style:normal}}.timeline{{position:relative;padding-left:22px}}.timeline:before{{content:"";position:absolute;left:6px;top:4px;bottom:4px;width:1px;background:var(--line)}}.stage{{position:relative;padding:4px 0 24px 14px}}.dot{{position:absolute;width:11px;height:11px;border-radius:50%;background:var(--accent);left:-21px;top:7px;box-shadow:0 0 0 5px var(--bg)}}.chips{{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}}.chips span,.focus span{{background:var(--soft);border-radius:999px;padding:6px 9px;font-size:11px}}.graphnum{{font-size:34px;font-weight:850}}.focus{{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}}.links{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}.links a{{color:var(--text);text-decoration:none;background:var(--panel);border:1px solid var(--line);padding:9px 12px;border-radius:999px;font-size:12px}}.actions{{margin:0;padding-left:0;list-style:none;display:grid;gap:8px}}.actions li{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}}.actions span{{display:block;color:var(--muted);font-size:12px;margin-top:4px}}.muted{{color:var(--muted)}}.notice{{margin-top:24px;border-left:3px solid var(--accent);background:var(--soft);padding:14px 16px;border-radius:0 14px 14px 0;font-size:12px;line-height:1.65}}@media(max-width:900px){{.stats,.highlights{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:680px){{main{{width:min(100% - 18px,1160px);padding-top:28px}}.stats,.highlights,.grid{{grid-template-columns:1fr 1fr}}.section-head{{align-items:start;flex-direction:column}}}}@media print{{body{{background:white}}main{{width:100%;padding:0}}.links{{display:none}}.stat,.mini,.theme,.insight,.graphbox{{break-inside:avoid}}}}</style></head><body><main><header class="hero"><div class="eyebrow">WEREAD INTELLIGENCE · UNIFIED REPORT</div><h1>{title}</h1><div class="subtitle">{subtitle}</div><div class="period">{period}</div><p class="summary">{summary}</p></header><div class="stats">{stats}</div>{highlights}<section><div class="section-head"><h2>阅读版图</h2><p>跨书主题，而不是书架分类的简单复刻</p></div><div class="grid">{themes}</div></section><section><div class="section-head"><h2>认知变迁</h2><p>阶段由主题结构变化决定，不机械按年份切割</p></div><div class="timeline">{stages}</div></section><section><div class="section-head"><h2>知识网络</h2><p>Book → Theme → Concept → Quote / Review</p></div><div class="graphbox"><div class="graphnum">{nodes} 节点 · {edges} 关系</div><p class="muted">{types}</p><div class="focus">{focus}</div></div></section><section><div class="section-head"><h2>阅读画像</h2><p>解释型结论必须带置信度和证据</p></div><div class="grid">{profile}</div></section>{takeaways}{actions}{links}<div class="notice">{privacy} 报告中的数值来自确定性数据层；主题、认知变化和画像属于解释层，不应被当作人格诊断或敏感属性推断。</div></main></body></html>'''.format(
        title=escape(model["title"]),
        subtitle=escape(model["subtitle"]),
        period=escape(model["period"]),
        summary=escape(model["summary"]),
        stats=stats_html,
        highlights=highlights_section,
        themes=themes_html,
        stages=stages_html,
        nodes=graph["nodes"],
        edges=graph["edges"],
        types=type_text or "尚未生成 Knowledge Graph。",
        focus=focus_html,
        profile=profile_html,
        takeaways=takeaways_section,
        actions=actions_section,
        links=links_section,
        privacy=escape(privacy_note),
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Render one-page unified WeRead report.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--narrative", type=Path, default=DEFAULT_NARRATIVE)
    parser.add_argument("--reading-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--cognitive-shift", type=Path, default=DEFAULT_SHIFT)
    parser.add_argument("--knowledge-graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(
            f"ERROR: missing {args.context}; run scripts/build_visualization_context.py first"
        )
    context = load_json(args.context, {})
    narrative = load_json(args.narrative, {})
    reading_map = load_json(args.reading_map, {})
    shift = load_json(args.cognitive_shift, {})
    graph = load_json(args.knowledge_graph, {})
    profile = load_json(args.profile, {})
    model = build_model(context, narrative, reading_map, shift, graph, profile)

    candidates = {
        "阅读热力图": args.output.parent / "reading_heatmap.html",
        "阅读版图": args.output.parent / "reading_map.html",
        "认知变迁": args.output.parent / "cognitive_shift.html",
        "知识图谱": args.output.parent / "knowledge_graph.html",
        "阅读画像": args.output.parent / "reading_profile.html",
    }
    links = {label: path.name for label, path in candidates.items() if path.exists()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(model, links), encoding="utf-8")
    print(f"reading-report: {args.output}")


if __name__ == "__main__":
    main()
