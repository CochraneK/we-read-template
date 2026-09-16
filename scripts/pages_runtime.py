#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deployment entrypoint for the real-data GitHub Pages report.

It normalizes WeRead daily reading records, chooses the requested publishing
scope, injects deterministic deep insights, and then delegates HTML generation
to ``build_pages_report``. Raw mark/review text is never published.
"""
from __future__ import annotations

import build_pages_report as report
import pages_command_ui
import pages_experience_ui
import pages_insights as filtered_insights
import pages_insights_full as full_insights


_legacy_daily_read_times = report.daily_read_times
_base_build_report = report.build_report


def daily_read_times(readdata: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for period in (readdata.get("monthly") or {}).values():
        for raw_day, raw_seconds in ((period or {}).get("readTimes") or {}).items():
            parsed = report.parse_timestamp(raw_day)
            if not parsed:
                continue
            try:
                seconds = max(0, int(raw_seconds or 0))
            except (TypeError, ValueError):
                continue
            key = parsed.strftime("%Y-%m-%d")
            result[key] = max(result.get(key, 0), seconds)
    if result:
        return dict(sorted(result.items()))
    return _legacy_daily_read_times(readdata)


def build_report(data_dir=report.DATA, include_private=None):
    if include_private is None:
        include_private = report.env_true("WEREAD_PAGES_INCLUDE_PRIVATE", False)
    result = _base_build_report(data_dir, include_private=include_private)
    result["insights"] = (
        full_insights.build_insights(data_dir)
        if include_private
        else filtered_insights.build_insights(data_dir)
    )
    return result


EXTRA_CSS = r'''
.shift-list{display:grid;gap:12px}.shift-card{border:1px solid var(--line);border-radius:18px;padding:16px;display:grid;grid-template-columns:92px 1fr;gap:16px}.shift-year{font-size:28px;font-weight:750;line-height:1}.shift-meta{color:var(--muted);font-size:11px;margin-top:7px}.shift-main{display:grid;gap:9px}.shift-top{display:flex;gap:8px;flex-wrap:wrap}.delta-up{color:var(--accent2)}.delta-down{color:var(--accent)}.evidence-note{font-size:12px;color:var(--muted);margin:0}.knowledge-wrap{overflow-x:auto}.knowledge-svg{width:100%;min-width:900px;height:auto;display:block}.kg-edge{stroke:color-mix(in srgb,var(--muted) 35%,transparent);fill:none}.kg-category{fill:var(--accent2)}.kg-book{fill:var(--accent3)}.kg-author{fill:var(--accent)}.kg-label{fill:var(--ink);font-size:11px}.kg-small{fill:var(--muted);font-size:9px}.bridge-grid,.counter-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.mini-card,.counter-card{border:1px solid var(--line);border-radius:16px;padding:14px;min-height:108px}.mini-card b,.counter-card strong{display:block;margin-bottom:5px}.mini-card p,.counter-card p{margin:0;color:var(--muted);font-size:12px}.mini-card .big{font-size:23px}.engage-line{display:grid;grid-template-columns:minmax(120px,210px) 1fr 58px;gap:10px;align-items:center;font-size:12px;margin:9px 0}.engage-track{height:9px;border-radius:999px;background:var(--line);overflow:hidden}.engage-fill{height:100%;background:var(--accent);border-radius:999px}.insight-callout{border-left:4px solid var(--accent3);padding-left:14px;color:var(--muted);font-size:13px}.investment-table td:nth-child(n+3),.investment-table th:nth-child(n+3){text-align:right}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 7px;font-size:10px;color:var(--muted);margin:2px}.section-kicker{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:5px}
@media(max-width:900px){.bridge-grid,.counter-grid{grid-template-columns:1fr 1fr}.shift-card{grid-template-columns:72px 1fr}}@media(max-width:560px){.bridge-grid,.counter-grid{grid-template-columns:1fr}.shift-card{grid-template-columns:1fr}.engage-line{grid-template-columns:100px 1fr 50px}}
'''

EXTRA_HTML = r'''
  <article class="card wide" id="shift"><div class="title"><div><div class="section-kicker">Evidence-based shift</div><h2>阅读关注迁移</h2></div><small>年度笔记占比变化；不是人格或心理判断</small></div><div class="shift-list" id="deepShift"></div></article>
  <article class="card wide" id="knowledge"><div class="title"><div><div class="section-kicker">Cross-book network</div><h2>跨书知识网络</h2></div><small>类别 → 高投入书 → 作者；边权 = 笔记量</small></div><div class="knowledge-wrap"><svg class="knowledge-svg" id="knowledgeChart" viewBox="0 0 1080 620" role="img" aria-label="跨书知识网络"></svg></div><div class="title" style="margin-top:18px"><h2 style="font-size:15px">跨类别桥接作者</h2><small>同一作者跨越多个阅读类别</small></div><div class="bridge-grid" id="bridgeAuthors"></div></article>
  <article class="card half" id="blindspot"><div class="title"><div><div class="section-kicker">Blindspot evidence</div><h2>书架盲点</h2></div><small>收藏 ≠ 实际投入</small></div><div id="blindSummary" class="insight-callout"></div><div id="blindBars" style="margin-top:14px"></div></article>
  <article class="card half" id="counter"><div class="title"><div><div class="section-kicker">Counter reading</div><h2>反向阅读方向</h2></div><small>从已收藏但投入较低的类别出发</small></div><div class="counter-grid" id="counterDirections"></div></article>
  <article class="card wide" id="investment"><div class="title"><div><div class="section-kicker">Investment depth</div><h2>高投入书目</h2></div><small>聚合计数，不展示原始划线/想法正文</small></div><table class="table investment-table"><thead><tr><th>书</th><th>类别</th><th>笔记</th><th>划线</th><th>想法</th><th>想法占比</th><th>进度</th></tr></thead><tbody id="investmentBooks"></tbody></table></article>
'''

EXTRA_JS = r'''
const I=D.insights||{};
const fmtDelta=v=>v===null||v===undefined?'首年':((v>0?'+':'')+Number(v).toFixed(1)+'pp');
const shifts=I.focusShift||[];
$('deepShift').innerHTML=shifts.map(y=>{const top=(y.topCategories||[]).slice(0,4).map(x=>`<span class="chip">${esc(x.category)} <b>${x.notes}</b> · ${x.share}% ${x.delta===null?'':`<em class="${x.delta>=0?'delta-up':'delta-down'}">${fmtDelta(x.delta)}</em>`}</span>`).join('');const rise=(y.rising||[]).map(x=>`<span class="badge delta-up">↑ ${esc(x.category)} ${fmtDelta(x.delta)}</span>`).join('');const fall=(y.falling||[]).map(x=>`<span class="badge delta-down">↓ ${esc(x.category)} ${fmtDelta(x.delta)}</span>`).join('');return `<div class="shift-card"><div><div class="shift-year">${esc(y.year)}</div><div class="shift-meta">${(+y.notes||0).toLocaleString()} 条笔记<br>想法占比 ${y.reviewRate||0}%</div></div><div class="shift-main"><div class="shift-top">${top}</div><p class="evidence-note">年度笔记最多作者：<b>${esc((y.topAuthor||{}).author||'—')}</b>（${(y.topAuthor||{}).notes||0} 条）</p><div>${rise}${fall}</div></div></div>`}).join('')||'<p class="muted">暂无可计算的年度笔记时间数据。</p>';
function drawKnowledge(){const svg=$('knowledgeChart'),G=I.knowledgeGraph||{},nodes=G.nodes||[],edges=G.edges||[];if(!nodes.length){svg.innerHTML='<text x="30" y="60" class="kg-label">暂无可计算的网络数据</text>';return;}const groups={category:nodes.filter(n=>n.kind==='category'),book:nodes.filter(n=>n.kind==='book'),author:nodes.filter(n=>n.kind==='author')},xs={category:120,book:535,author:950},pos={};Object.keys(groups).forEach(kind=>{const rows=groups[kind],step=520/Math.max(1,rows.length);rows.forEach((n,i)=>pos[n.id]=[xs[kind],55+step*(i+.5)]);});let out='<text x="55" y="28" class="kg-small">类别</text><text x="500" y="28" class="kg-small">高投入书</text><text x="930" y="28" class="kg-small">作者</text>';const max=Math.max(1,...edges.map(e=>+e.value||0));edges.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;const w=.7+5*(+e.value||0)/max;out+=`<path class="kg-edge" stroke-width="${w.toFixed(2)}" d="M${a[0]},${a[1]} C${(a[0]+b[0])/2},${a[1]} ${(a[0]+b[0])/2},${b[1]} ${b[0]},${b[1]}"><title>${e.value} 条笔记</title></path>`});nodes.forEach(n=>{const p=pos[n.id];if(!p)return;const cls=n.kind==='category'?'kg-category':n.kind==='book'?'kg-book':'kg-author',r=n.kind==='book'?7:9,label=String(n.label||''),short=label.length>16?label.slice(0,15)+'…':label,tx=n.kind==='author'?p[0]-14:p[0]+14,anchor=n.kind==='author'?'end':'start';out+=`<circle cx="${p[0]}" cy="${p[1]}" r="${r}" class="${cls}"><title>${esc(label)} · ${(+n.value||0).toLocaleString()} 条</title></circle><text x="${tx}" y="${p[1]+4}" text-anchor="${anchor}" class="kg-label">${esc(short)}</text>`});svg.innerHTML=out}drawKnowledge();
$('bridgeAuthors').innerHTML=((I.knowledgeGraph||{}).bridgeAuthors||[]).map(x=>`<div class="mini-card"><b>${esc(x.author)}</b><div class="big">${x.categoryCount} 类</div><p>${(+x.notes||0).toLocaleString()} 条笔记 · ${(x.categories||[]).map(esc).join(' / ')}</p></div>`).join('')||'<p class="muted">暂无跨类别作者。</p>';
const B=I.blindspots||{},heavy=B.shelfHeavyLowEngagement||[],hhi=+B.categoryConcentrationHHI||0,hhiLabel=hhi>=.25?'较集中':hhi>=.15?'中等集中':'较分散';$('blindSummary').innerHTML=`类别投入集中度 HHI <b>${hhi.toFixed(3)}</b>（${hhiLabel}）；已知低进度且没有笔记的书架书目 <b>${(+B.lowProgressNoNoteBacklogCount||0).toLocaleString()}</b> 本。这里描述的是数据结构，不评价阅读偏好好坏。`;$('blindBars').innerHTML=heavy.slice(0,7).map(x=>`<div class="engage-line"><div title="${esc(x.category)}">${esc(x.category)}</div><div class="engage-track"><div class="engage-fill" style="width:${Math.max(2,Math.min(100,+x.engagementRate||0))}%"></div></div><div>${x.engagementRate}%</div></div>`).join('')||'<p class="muted">没有明显的“收藏多、投入低”类别。</p>';
$('counterDirections').innerHTML=(B.counterReadingDirections||[]).map(x=>`<div class="counter-card"><strong>${esc(x.category)}</strong><p>${esc(x.prompt)}</p></div>`).join('')||'<p class="muted">当前数据没有形成强烈的反向阅读提示。</p>';
const topBooks=(I.investment||{}).topBooks||[];$('investmentBooks').innerHTML=topBooks.map(x=>`<tr><td>${esc(x.title)}<br><small class="muted">${esc(x.author||'')}</small></td><td>${esc(x.category||'未知')}</td><td>${(+x.notes||0).toLocaleString()}</td><td>${(+x.marks||0).toLocaleString()}</td><td>${(+x.reviews||0).toLocaleString()}</td><td>${x.reviewRate||0}%</td><td>${x.progress===null||x.progress===undefined?'—':Number(x.progress).toFixed(0)+'%'}</td></tr>`).join('');
'''


def enhance_template(template: str) -> str:
    template = template.replace("</style>", EXTRA_CSS + "\n</style>", 1)
    template = template.replace("</nav>", '<a href="#shift">迁移</a><a href="#knowledge">知识网络</a><a href="#blindspot">盲点</a><a href="#investment">高投入书</a></nav>', 1)
    marker = '  <article class="card wide privacy">'
    template = template.replace(marker, EXTRA_HTML + "\n" + marker, 1)
    template = template.replace("</script>", EXTRA_JS + "\n</script>", 1)
    template = pages_experience_ui.enhance(template)
    return pages_command_ui.enhance(template)


def main() -> None:
    report.daily_read_times = daily_read_times
    report.build_report = build_report
    report.TEMPLATE = enhance_template(report.TEMPLATE)
    report.main()


if __name__ == "__main__":
    main()
