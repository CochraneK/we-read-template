#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the local-only Private Text Mining Lab."""
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
LAB = DATA / "analysis" / "private_lab"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return default


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def pills(rows, key="term", count_key="documents", limit=24):
    items = []
    for row in (rows or [])[:limit]:
        items.append(
            f'<span class="pill"><b>{esc(row.get(key))}</b>'
            f'<small>{esc(row.get(count_key) if row.get(count_key) is not None else row.get("score"))}</small></span>'
        )
    return "".join(items) or '<p class="empty">暂无足够证据。</p>'


def render(lite: dict, semantic: dict | None = None) -> str:
    semantic = semantic or {}
    coverage = lite.get("coverage") or {}
    source = (lite.get("corpora") or {}).get("source") or {}
    self_corpus = (lite.get("corpora") or {}).get("self") or {}
    communities = ((lite.get("cooccurrence") or {}).get("communities") or [])[:12]
    bursts = ((lite.get("temporal") or {}).get("bursts") or [])[:16]
    resurgence = ((lite.get("temporal") or {}).get("resurgence") or [])[:16]
    novelty = lite.get("novelty") or {}
    lags = ((lite.get("exposureExpression") or {}).get("items") or [])[:20]
    rhetoric = (lite.get("rhetoricalLanguage") or {}).get("signals") or []
    semantic_clusters = semantic.get("clusters") or []
    semantic_pairs = semantic.get("crossBookSimilarity") or []
    semantic_drift = semantic.get("yearlyDrift") or []
    semantic_align = semantic.get("sourceSelfAlignment") or []

    community_html = "".join(
        f'<article class="card"><div class="eyebrow">Lexical topic candidate</div>'
        f'<h3>{esc(row.get("label"))}</h3><p>{esc(" · ".join(row.get("terms") or []))}</p>'
        f'<small>{row.get("size",0)} lexical units · support {row.get("documentSupport",0)}</small></article>'
        for row in communities
    ) or '<p class="empty">共现不足，暂未形成稳定 lexical community。</p>'

    burst_html = "".join(
        f'<div class="row"><b>{esc(row.get("term"))}</b><span>{esc(row.get("peakYear"))}</span>'
        f'<span>{round(float(row.get("peakShare") or 0)*100,1)}%</span><span>z={esc(row.get("z"))}</span></div>'
        for row in bursts
    ) or '<p class="empty">暂无明显 burst。</p>'

    resurgence_html = "".join(
        f'<div class="row"><b>{esc(row.get("term"))}</b><span>{esc(row.get("firstYear"))} → {esc(row.get("resurgenceYear"))}</span>'
        f'<span>gap {esc(row.get("gapYears"))}y</span><span>{round(float(row.get("resurgenceShare") or 0)*100,1)}%</span></div>'
        for row in resurgence
    ) or '<p class="empty">暂无明显 resurgence。</p>'

    novelty_html = "".join(
        f'<article class="evidence"><div><b>{esc(row.get("title"))}</b><span>{esc(row.get("date"))}</span>'
        f'<span>{esc(row.get("role"))}</span><span>novelty {esc(row.get("novelty"))}</span></div>'
        f'<p>{esc(row.get("snippet"))}</p></article>'
        for row in (novelty.get("mostNovel") or [])[:12]
    ) or '<p class="empty">暂无带时间戳的证据。</p>'

    lag_html = "".join(
        f'<div class="row"><b>{esc(row.get("term"))}</b><span>{esc(row.get("lagDays"))} days</span>'
        f'<span>source {esc(row.get("sourceDocuments"))}</span><span>self {esc(row.get("selfDocuments"))}</span></div>'
        for row in lags
    ) or '<p class="empty">暂无满足门槛的 source→self lexical overlap。</p>'

    rhetoric_html = "".join(
        f'<div class="bar"><div><b>{esc(row.get("signal"))}</b><span>{row.get("documents",0)} docs · {round(float(row.get("share") or 0)*100,1)}%</span></div>'
        f'<i style="width:{max(1,round(float(row.get("share") or 0)*100,1))}%"></i></div>'
        for row in rhetoric
    )

    semantic_block = (
        f'''<section class="panel" id="semantic">
        <div class="head"><div><div class="eyebrow">Optional semantic layer</div><h2>Semantic Mining</h2>
        <p>本地 embedding；similarity / cluster / drift 都是候选关系，不代表赞同、因果或真实心理变化。</p></div>
        <span class="status">model · {esc(semantic.get("model"))}</span></div>
        <div class="cards">{''.join(
            f'<article class="card"><div class="eyebrow">Embedding cluster</div><h3>{esc(x.get("label"))}</h3>'
            f'<p>{esc(" · ".join(x.get("terms") or []))}</p><small>{x.get("documents",0)} docs</small></article>'
            for x in semantic_clusters[:12]
        ) or '<p class="empty">暂无 cluster。</p>'}</div>
        <h3 class="sub">跨书语义近邻</h3>
        <div class="evidence-list">{''.join(
            f'<article class="evidence"><div><b>{esc(x.get("a",{}).get("title"))}</b><span>↔</span><b>{esc(x.get("b",{}).get("title"))}</b>'
            f'<span>sim {esc(x.get("similarity"))}</span></div><p>{esc(x.get("a",{}).get("snippet"))}</p>'
            f'<p>{esc(x.get("b",{}).get("snippet"))}</p></article>'
            for x in semantic_pairs[:12]
        ) or '<p class="empty">暂无跨书近邻。</p>'}</div>
        <h3 class="sub">年度 corpus embedding drift</h3>
        <div class="table">{''.join(
            f'<div class="row"><b>{esc(x.get("fromYear"))} → {esc(x.get("toYear"))}</b>'
            f'<span>drift {esc(x.get("drift"))}</span><span>sim {esc(x.get("centroidSimilarity"))}</span>'
            f'<span>{esc(x.get("fromDocuments"))} → {esc(x.get("toDocuments"))} docs</span></div>'
            for x in semantic_drift
        ) or '<p class="empty">年度数据不足。</p>'}</div>
        <h3 class="sub">Source → Self semantic candidates</h3>
        <div class="evidence-list">{''.join(
            f'<article class="evidence"><div><b>{esc(x.get("source",{}).get("title"))}</b><span>→</span>'
            f'<b>{esc(x.get("self",{}).get("title"))}</b><span>sim {esc(x.get("similarity"))}</span>'
            f'<span>{esc(x.get("lagDays"))} days</span></div><p>{esc(x.get("source",{}).get("snippet"))}</p>'
            f'<p>{esc(x.get("self",{}).get("snippet"))}</p></article>'
            for x in semantic_align[:12]
        ) or '<p class="empty">暂无满足门槛的 semantic alignment。</p>'}</div>
        </section>'''
        if semantic.get("enabled")
        else '''<section class="panel" id="semantic"><div class="head"><div><div class="eyebrow">Optional semantic layer</div>
        <h2>Semantic Mining</h2><p>本次没有运行 embedding。Lite 报告仍然完整可用。</p></div><span class="status">not generated</span></div>
        <pre>pip install -r requirements-text-mining.txt
python scripts/build_private_reading_lab.py --include-private --semantic-text --embedding-model "MODEL_OR_LOCAL_PATH"</pre></section>'''
    )

    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>WeRead · Private Text Mining Lab</title>
<style>
:root{{--bg:#f3efe8;--paper:#fffdf9;--ink:#27231e;--muted:#766e64;--line:#ded5c9;--accent:#a95b42;--accent2:#71866e;--paper2:#f8f3eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#171614;--paper:#22201d;--ink:#eee8df;--muted:#aaa096;--line:#403b35;--accent:#df7b60;--accent2:#95ad90;--paper2:#2a2723}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55}}
.shell{{max-width:1320px;margin:auto;padding:24px}}.top{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:18px}}.top a{{color:var(--muted);text-decoration:none;border:1px solid var(--line);padding:7px 10px;border-radius:999px;background:var(--paper)}}.top strong{{margin-right:auto}}
.hero,.panel{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0}}.hero h1{{font-size:40px;margin:6px 0}}.eyebrow{{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}}.muted,.head p,.card p,.evidence span,.evidence p,.status,small{{color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.metric{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:13px}}.metric b{{font-size:22px;display:block}}.metric span{{font-size:10px;color:var(--muted)}}.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}.head h2{{margin:2px 0}}.head p{{margin:3px 0;font-size:11px}}.pills{{display:flex;gap:7px;flex-wrap:wrap}}.pill{{border:1px solid var(--line);border-radius:999px;background:var(--paper2);padding:6px 9px}}.pill b,.pill small{{display:inline}}.pill small{{margin-left:5px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}.card{{border:1px solid var(--line);background:var(--paper2);border-radius:13px;padding:12px}}.card h3{{font-size:13px;margin:4px 0}}.card p{{font-size:11px;margin:4px 0}}.table{{display:grid;gap:5px}}.row{{display:grid;grid-template-columns:minmax(120px,1.5fr) repeat(3,minmax(70px,.7fr));gap:7px;border-bottom:1px solid var(--line);padding:7px;font-size:11px}}.bar{{margin:9px 0}}.bar>div{{display:flex;justify-content:space-between;font-size:11px}}.bar i{{display:block;height:5px;background:var(--accent2);border-radius:99px;margin-top:4px}}.evidence-list{{display:grid;gap:8px}}.evidence{{border:1px solid var(--line);background:var(--paper2);border-radius:12px;padding:10px}}.evidence>div{{display:flex;gap:7px;flex-wrap:wrap;font-size:10px}}.evidence p{{font-family:"Songti SC",serif;font-size:12px;margin:6px 0;white-space:pre-wrap}}.sub{{font-size:13px;margin:18px 0 8px}}pre{{white-space:pre-wrap;background:var(--paper2);border:1px dashed var(--line);padding:11px;border-radius:11px;font-size:11px}}.empty{{color:var(--muted);font-size:11px}}
@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}.cards{{grid-template-columns:1fr 1fr}}.metrics{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:560px){{.shell{{padding:12px}}.cards{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,1fr)}}.row{{grid-template-columns:1fr 1fr}}.hero h1{{font-size:31px}}}}
</style></head><body><main class="shell">
<nav class="top"><strong>Private Text Mining Lab</strong><a href="index.html">← Private Lab</a><a href="#lexical">Lexical</a><a href="#temporal">Temporal</a><a href="#semantic">Semantic</a></nav>
<section class="hero"><div class="eyebrow">Private / Raw Evidence</div><h1>Reading Corpus Lab</h1><p class="muted">把“读了什么”推进到“长期阅读语料如何组织、重复、迁移和重新出现”。Source highlights 与 user-authored thoughts 始终分开；本页包含私有证据，不得上传到公开 Pages。</p></section>
<section class="metrics"><div class="metric"><span>Documents</span><b>{coverage.get("documents",0):,}</b></div><div class="metric"><span>Source highlights</span><b>{coverage.get("sourceHighlights",0):,}</b></div><div class="metric"><span>User thoughts</span><b>{coverage.get("userThoughts",0):,}</b></div><div class="metric"><span>Books</span><b>{coverage.get("books",0):,}</b></div><div class="metric"><span>Years</span><b>{len(coverage.get("years") or []):,}</b></div></section>
<section class="grid2" id="lexical"><article class="panel"><div class="head"><div><div class="eyebrow">Exposure corpus</div><h2>Source highlights · TF-IDF</h2><p>你保存过的原文，不自动代表你的观点。</p></div></div><div class="pills">{pills(source.get("topTerms"))}</div></article><article class="panel"><div class="head"><div><div class="eyebrow">Expression corpus</div><h2>My thoughts · TF-IDF</h2><p>本人写过的文本证据，仍不外推成人格。</p></div></div><div class="pills">{pills(self_corpus.get("topTerms"))}</div></article></section>
<section class="panel"><div class="head"><div><div class="eyebrow">Co-occurrence graph</div><h2>Lexical communities</h2><p>正 PMI + 文档共现形成候选母题，不当作语义主题真值。</p></div></div></div><div class="cards">{community_html}</div></section>
<section class="grid2" id="temporal"><article class="panel"><div class="head"><div><div class="eyebrow">Temporal burst</div><h2>突然升温的词汇</h2></div></div><div class="table">{burst_html}</div></article><article class="panel"><div class="head"><div><div class="eyebrow">Concept resurgence</div><h2>沉寂后重新出现</h2></div></div><div class="table">{resurgence_html}</div></article></section>
<section class="grid2"><article class="panel"><div class="head"><div><div class="eyebrow">Exposure → Expression</div><h2>Lexical lag</h2><p>先出现在 source，后出现在自己的文字；只表示时间重合。</p></div></div><div class="table">{lag_html}</div></article><article class="panel"><div class="head"><div><div class="eyebrow">User-authored language</div><h2>Rhetorical signals</h2><p>问句、质疑、不确定、因果等显式语言标记，不做情绪/人格诊断。</p></div></div>{rhetoric_html}</article></section>
<section class="panel"><div class="head"><div><div class="eyebrow">Lexical novelty</div><h2>新颖 / 重复候选</h2><p>{esc(novelty.get("method"))}</p></div></div><div class="evidence-list">{novelty_html}</div></section>
{semantic_block}
<section class="panel"><div class="head"><div><div class="eyebrow">Guardrails</div><h2>Interpretation boundary</h2></div></div><ul>{''.join(f'<li>{esc(x)}</li>' for x in (lite.get("guardrails") or []) + (semantic.get("guardrails") or []))}</ul></section>
</main></body></html>'''


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=LAB / "text_mining_context.json")
    p.add_argument("--semantic", type=Path, default=LAB / "text_mining_semantic.json")
    p.add_argument("--output", type=Path, default=LAB / "text_mining.html")
    return p.parse_args()


def main():
    args = parse_args()
    lite = read_json(args.input, {})
    if not lite:
        raise SystemExit(f"ERROR: missing/invalid text mining context: {args.input}")
    semantic = read_json(args.semantic, {})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(lite, semantic), encoding="utf-8")
    print(
        f"text-mining-report: {args.output} | docs={(lite.get('coverage') or {}).get('documents',0)} "
        f"semantic={bool(semantic.get('enabled'))} private=true"
    )


if __name__ == "__main__":
    main()
