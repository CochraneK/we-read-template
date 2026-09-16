#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-process the generated real-data Pages site with factual enrichments.

Run after pages_runtime.py. It injects optional sections driven by
pages_enrichment.py and updates site/report-data.json. Raw highlight/review text
is never included.
"""
from __future__ import annotations

from pathlib import Path
import json
import os

import pages_enrichment

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"


def env_true(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


CSS = r'''
.archive-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}.archive-wide{grid-column:span 12}.archive-half{grid-column:span 6}.archive-third{grid-column:span 4}.subtle{color:var(--muted);font-size:12px}.clock-wrap{display:grid;grid-template-columns:minmax(260px,420px) 1fr;gap:28px;align-items:center}.clock-svg{width:100%;height:auto;display:block}.clock-ring{fill:none;stroke:var(--line);stroke-width:1}.clock-spoke{stroke:var(--line);stroke-width:1}.clock-bar{stroke:var(--accent);stroke-linecap:round}.clock-label{fill:var(--muted);font-size:10px}.clock-center{fill:var(--ink);font-size:14px;font-weight:700}.weekday-grid,.season-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:9px;align-items:end;min-height:170px}.season-grid{grid-template-columns:repeat(12,1fr)}.rhythm-col{display:grid;grid-template-rows:1fr auto auto;gap:6px;align-items:end;text-align:center;min-width:0}.rhythm-bar-wrap{height:120px;display:flex;align-items:end;justify-content:center}.rhythm-bar{width:min(28px,70%);background:var(--accent2);border-radius:8px 8px 3px 3px;min-height:2px}.season-grid .rhythm-bar{background:var(--accent3)}.rhythm-value{font-size:10px;color:var(--muted)}.rhythm-label{font-size:11px}.mode-layout{display:grid;grid-template-columns:180px 1fr;gap:22px;align-items:center}.donut{width:160px;height:160px;border-radius:50%;display:grid;place-items:center;position:relative}.donut:after{content:"";position:absolute;inset:25px;border-radius:50%;background:var(--paper)}.donut strong{z-index:1;font-size:24px}.legend-stack{display:grid;gap:10px}.legend-row{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:8px}.legend-dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:7px}.official-stat-grid,.medal-grid,.preference-grid,.deep-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.official-stat,.medal,.pref-card,.deep-card{border:1px solid var(--line);border-radius:16px;padding:14px;min-width:0}.official-stat span,.medal small,.pref-card small,.deep-card small{color:var(--muted);font-size:11px}.official-stat b{display:block;font-size:22px;margin-top:5px}.medal b,.pref-card b,.deep-card b{display:block;margin-bottom:5px}.medal p,.pref-card p,.deep-card p{margin:0;color:var(--muted);font-size:11px}.pref-book-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}.pref-book{min-width:0;border:1px solid var(--line);border-radius:16px;padding:10px}.pref-book-cover{aspect-ratio:2/3;border-radius:10px;background:var(--line);overflow:hidden;margin-bottom:8px}.pref-book-cover img{width:100%;height:100%;object-fit:cover}.pref-book b,.pref-book small,.pref-book em{display:block;overflow:hidden;text-overflow:ellipsis}.pref-book b{font-size:12px;white-space:nowrap}.pref-book small{font-size:10px;color:var(--muted);white-space:nowrap}.pref-book em{font-size:10px;color:var(--accent);font-style:normal;margin-top:5px}.funnel{display:grid;gap:10px}.funnel-row{display:grid;grid-template-columns:100px 1fr 60px;gap:10px;align-items:center;font-size:12px}.funnel-track{height:13px;background:var(--line);border-radius:999px;overflow:hidden}.funnel-fill{height:100%;background:var(--accent2);border-radius:999px}.fingerprint{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.fingerprint-item{padding:15px;border:1px solid var(--line);border-radius:16px}.fingerprint-item span{display:block;color:var(--muted);font-size:11px}.fingerprint-item b{display:block;font-size:21px;margin-top:6px}.explorer-tools{display:grid;grid-template-columns:minmax(220px,1fr) repeat(3,minmax(120px,180px));gap:8px;margin-bottom:14px}.explorer-tools input,.explorer-tools select{width:100%;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:10px;padding:9px 10px;font:inherit;font-size:12px}.shelf-summary{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:12px;margin-bottom:10px}.shelf-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:12px}.shelf-book{min-width:0}.shelf-cover{aspect-ratio:2/3;border-radius:10px;background:var(--line);overflow:hidden;position:relative}.shelf-cover img{width:100%;height:100%;object-fit:cover}.shelf-secret{position:absolute;right:5px;top:5px;font-size:9px;background:color-mix(in srgb,var(--paper) 88%,transparent);padding:3px 5px;border-radius:999px}.shelf-progress{height:4px;background:var(--line);margin-top:6px;border-radius:999px;overflow:hidden}.shelf-progress i{display:block;height:100%;background:var(--accent2)}.shelf-book b{display:block;font-size:11px;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.shelf-book p{margin:2px 0 0;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.load-more{display:block;margin:18px auto 0;border:1px solid var(--line);background:var(--paper);color:var(--ink);padding:9px 16px;border-radius:999px;cursor:pointer}.compact-table td,.compact-table th{font-size:12px}.correlation-note{margin-top:10px;padding:11px 13px;border-left:3px solid var(--accent3);background:color-mix(in srgb,var(--accent3) 6%,transparent);font-size:12px;color:var(--muted)}
@media(max-width:1000px){.pref-book-grid{grid-template-columns:repeat(4,1fr)}.shelf-grid{grid-template-columns:repeat(6,1fr)}.official-stat-grid,.medal-grid,.preference-grid,.deep-grid{grid-template-columns:repeat(2,1fr)}.fingerprint{grid-template-columns:repeat(3,1fr)}}
@media(max-width:800px){.archive-half,.archive-third{grid-column:span 12}.clock-wrap,.mode-layout{grid-template-columns:1fr}.clock-svg{max-width:390px;margin:auto}.explorer-tools{grid-template-columns:1fr 1fr}.shelf-grid{grid-template-columns:repeat(4,1fr)}.pref-book-grid{grid-template-columns:repeat(3,1fr)}.season-grid{grid-template-columns:repeat(6,1fr);row-gap:16px}}
@media(max-width:520px){.weekday-grid{grid-template-columns:repeat(7,1fr);gap:4px}.shelf-grid{grid-template-columns:repeat(3,1fr)}.pref-book-grid{grid-template-columns:repeat(2,1fr)}.official-stat-grid,.medal-grid,.preference-grid,.deep-grid,.fingerprint{grid-template-columns:1fr 1fr}.explorer-tools{grid-template-columns:1fr}.rhythm-label{font-size:9px}}
'''

HTML = r'''
  <article class="card wide" id="lifetime"><div class="title"><div><div class="section-kicker">Reading lifetime</div><h2>阅读生涯档案</h2></div><small>微信读书官方统计字段 + 本地确定性计算</small></div><div class="official-stat-grid" id="officialStats"></div><div id="tenureLine" class="correlation-note" style="display:none"></div></article>
  <article class="card half" id="clock"><div class="title"><div><div class="section-kicker">Circadian rhythm</div><h2>24 小时阅读时钟</h2></div><small id="clockWord"></small></div><div class="clock-wrap"><svg id="clockSvg" class="clock-svg" viewBox="0 0 360 360" role="img" aria-label="24小时阅读时段"></svg><div><p class="subtle">官方 <code>preferTime</code> 从 06:00 开始排列。圆周越长代表该小时累计投入越多。</p><div id="clockPeak" class="deep-grid"></div></div></div></article>
  <article class="card half" id="weekday"><div class="title"><div><div class="section-kicker">Weekly rhythm</div><h2>星期阅读节律</h2></div><small>由每日阅读时长聚合</small></div><div class="weekday-grid" id="weekdayGrid"></div></article>
  <article class="card half" id="season"><div class="title"><div><div class="section-kicker">Seasonality</div><h2>一年中的阅读季节</h2></div><small>跨年份同月份平均</small></div><div class="season-grid" id="seasonGrid"></div></article>
  <article class="card half" id="mode"><div class="title"><div><div class="section-kicker">Reading mode</div><h2>文字阅读 vs 听书</h2></div><small>官方字段有数据时展示</small></div><div id="readingMode"></div></article>
  <article class="card wide" id="official"><div class="title"><div><div class="section-kicker">Official preference</div><h2>微信读书官方偏好</h2></div><small>与“按笔记推导”的画像分开呈现</small></div><div class="preference-grid" id="officialPrefs"></div><div class="title" style="margin-top:20px"><h2 style="font-size:15px">年度偏好书卡</h2><small>来自官方 preferBooks</small></div><div class="pref-book-grid" id="preferBooks"></div></article>
  <article class="card wide" id="medals"><div class="title"><div><div class="section-kicker">Milestones</div><h2>阅读勋章与里程碑</h2></div><small>有官方 medals 时展示</small></div><div class="medal-grid" id="medalGrid"></div></article>
  <article class="card half" id="progress"><div class="title"><div><div class="section-kicker">Shelf honesty</div><h2>书架进度漏斗</h2></div><small id="progressCoverage"></small></div><div class="funnel" id="progressFunnel"></div></article>
  <article class="card half" id="fingerprint"><div class="title"><div><div class="section-kicker">Factual fingerprint</div><h2>阅读行为指纹</h2></div><small>只计算行为比例，不做人格标签</small></div><div class="fingerprint" id="fingerprintGrid"></div><div class="correlation-note" id="correlationNote"></div></article>
  <article class="card wide" id="deepreads"><div class="title"><div><div class="section-kicker">Now reading</div><h2>当前深读中的书</h2></div><small>进度 5–99% 且已形成笔记</small></div><div class="pref-book-grid" id="deepReads"></div></article>
  <article class="card half" id="recall"><div class="title"><div><div class="section-kicker">Knowledge reactivation</div><h2>值得重新激活</h2></div><small>最后一次笔记 ≥ 90 天</small></div><table class="table compact-table"><thead><tr><th>书</th><th>笔记</th><th>距今</th></tr></thead><tbody id="recallRows"></tbody></table></article>
  <article class="card half" id="thinking"><div class="title"><div><div class="section-kicker">Own thoughts</div><h2>想法写得最多的书</h2></div><small>review 数量，不把划线当本人观点</small></div><table class="table compact-table"><thead><tr><th>书</th><th>想法</th><th>占比</th></tr></thead><tbody id="thinkingRows"></tbody></table></article>
  <article class="card wide" id="shelf-explorer"><div class="title"><div><div class="section-kicker">Bookshelf explorer</div><h2>完整书架浏览器</h2></div><small>书名 / 作者 / 类别 / 进度 / 笔记 / 最近阅读；范围遵循当前 publication policy</small></div><div class="explorer-tools"><input id="shelfQuery" type="search" placeholder="搜索书名、作者或类别…"><select id="shelfCategory"><option value="">全部类别</option></select><select id="shelfProgress"><option value="">全部进度</option><option value="noted">有笔记</option><option value="reading">阅读中</option><option value="finished">已读完</option><option value="unknown">进度未知</option></select><select id="shelfSort"><option value="recent">最近阅读</option><option value="notes">笔记最多</option><option value="progress">进度最高</option><option value="title">书名</option></select></div><div class="shelf-summary"><span id="shelfCount"></span><span>只发布书目元数据，不发布原始笔记正文</span></div><div class="shelf-grid" id="shelfGrid"></div><button class="load-more" id="shelfMore" type="button">显示更多</button></article>
'''

JS = r'''
const X=E||{};
function fmtH(v){return Number(v||0).toFixed(1)+'h'}
function optionalSection(id,show){const el=$(id);if(el)el.style.display=show?'':'none'}
// Official lifetime summary.
const off=X.official||{},ten=X.tenure||null,officialStats=off.readStat||[];
optionalSection('lifetime',officialStats.length||ten);
$('officialStats').innerHTML=officialStats.map(x=>`<div class="official-stat"><span>${esc(x.stat)}</span><b>${esc(x.counts)}</b></div>`).join('');
if(ten){$('tenureLine').style.display='block';$('tenureLine').innerHTML=`微信读书记录起点：<b>${esc(ten.registeredDate)}</b> · 已积累约 <b>${ten.years} 年</b>阅读轨迹。`;}
// 24h radial clock.
const clock=X.clock||[];optionalSection('clock',clock.some(x=>(+x.seconds||0)>0));$('clockWord').textContent=off.preferTimeWord||'';
function drawClock(){const svg=$('clockSvg');if(!svg||!clock.length)return;const cx=180,cy=180,inner=72,max=Math.max(1,...clock.map(x=>+x.seconds||0));let out='<circle cx="180" cy="180" r="70" class="clock-ring"/><circle cx="180" cy="180" r="142" class="clock-ring"/>';
clock.forEach((x,i)=>{const a=(i/24)*Math.PI*2-Math.PI/2,ratio=(+x.seconds||0)/max,r2=inner+18+ratio*52,x1=cx+Math.cos(a)*(inner+12),y1=cy+Math.sin(a)*(inner+12),x2=cx+Math.cos(a)*r2,y2=cy+Math.sin(a)*r2,w=2+7*ratio;out+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="clock-bar" stroke-width="${w}"><title>${String(x.hour).padStart(2,'0')}:00 · ${fmtH(x.hours)}</title></line>`;if([0,6,12,18].includes(x.hour)){const lr=158,lx=cx+Math.cos(a)*lr,ly=cy+Math.sin(a)*lr+3;out+=`<text x="${lx}" y="${ly}" text-anchor="middle" class="clock-label">${String(x.hour).padStart(2,'0')}</text>`}});out+='<text x="180" y="178" text-anchor="middle" class="clock-center">READING</text><text x="180" y="196" text-anchor="middle" class="clock-label">24 HOURS</text>';svg.innerHTML=out}drawClock();
const clockTop=[...clock].sort((a,b)=>(+b.seconds||0)-(+a.seconds||0)).slice(0,3);$('clockPeak').innerHTML=clockTop.map((x,i)=>`<div class="deep-card"><small>#${i+1} 活跃时段</small><b>${String(x.hour).padStart(2,'0')}:00</b><p>${fmtH(x.hours)}</p></div>`).join('');
// Weekday / seasonality bars.
function rhythmBars(target,rows,labelKey,valueKey){const max=Math.max(1,...rows.map(x=>+x[valueKey]||0));$(target).innerHTML=rows.map(x=>`<div class="rhythm-col"><div class="rhythm-bar-wrap"><div class="rhythm-bar" style="height:${Math.max(2,100*(+x[valueKey]||0)/max)}%" title="${esc(x[labelKey])}: ${fmtH(x[valueKey])}"></div></div><div class="rhythm-value">${Number(x[valueKey]||0).toFixed(1)}h</div><div class="rhythm-label">${esc(x[labelKey])}</div></div>`).join('')}
const weekdays=X.weekday||[];optionalSection('weekday',weekdays.some(x=>(+x.hours||0)>0));rhythmBars('weekdayGrid',weekdays,'label','hours');
const seasons=(X.seasonality||[]).map(x=>({...x,label:x.month+'月'}));optionalSection('season',seasons.some(x=>(+x.avgHours||0)>0));rhythmBars('seasonGrid',seasons,'label','avgHours');
// Reading/listening split.
const mode=X.readingMode;optionalSection('mode',!!mode);if(mode){const rr=mode.readRate==null?(mode.readHours+mode.listenHours?100*mode.readHours/(mode.readHours+mode.listenHours):0):mode.readRate;$('readingMode').innerHTML=`<div class="mode-layout"><div class="donut" style="background:conic-gradient(var(--accent2) 0 ${rr}%,var(--accent3) ${rr}% 100%)"><strong>${Number(rr).toFixed(0)}%</strong></div><div class="legend-stack"><div class="legend-row"><span><i class="legend-dot" style="background:var(--accent2)"></i>文字阅读</span><b>${fmtH(mode.readHours)}</b></div><div class="legend-row"><span><i class="legend-dot" style="background:var(--accent3)"></i>听书 / TTS</span><b>${fmtH(mode.listenHours)}</b></div></div></div>`}
// Official preferences.
const prefs=[];(off.categories||[]).slice(0,6).forEach(x=>prefs.push({k:'分类',n:x.title,v:(x.readingHours?x.readingHours+'h · ':'')+(x.readingCount?x.readingCount+'本':'')}));(off.publishers||[]).slice(0,5).forEach(x=>prefs.push({k:'出版社',n:x.name,v:x.count+' 本'}));(off.authors||[]).slice(0,5).forEach(x=>prefs.push({k:'作者',n:x.name,v:(x.readTime||'')+(x.count?' · '+x.count+'本':'')}));optionalSection('official',prefs.length||(off.annualPreferBooks||[]).length);$('officialPrefs').innerHTML=prefs.map(x=>`<div class="pref-card"><small>${esc(x.k)}</small><b>${esc(x.n)}</b><p>${esc(x.v)}</p></div>`).join('');
const pbooks=(off.annualPreferBooks||[]).length?off.annualPreferBooks:(off.preferBooks||[]);$('preferBooks').innerHTML=pbooks.slice(-18).reverse().map(x=>`<div class="pref-book"><div class="pref-book-cover">${x.cover?`<img src="${esc(x.cover)}" loading="lazy" alt="">`:''}</div><small>${esc((x.year?x.year+' · ':'')+(x.label||'偏好书'))}</small><b title="${esc(x.title)}">${esc(x.title||'—')}</b><small>${esc(x.author||'')}</small><em>${esc(x.reason||'')}</em></div>`).join('');
// Medals.
const medals=off.medals||[];optionalSection('medals',medals.length);$('medalGrid').innerHTML=medals.slice(0,20).map(x=>`<div class="medal"><small>${esc(x.ctime||'')}</small><b>${esc(x.title)}</b><p>${esc(x.rankText||x.name||'')}</p></div>`).join('');
// Progress funnel and factual fingerprint.
const funnel=X.progressFunnel||{bins:[]},fmax=Math.max(1,...(funnel.bins||[]).map(x=>+x.count||0));$('progressCoverage').textContent=`已知进度 ${funnel.known||0} / ${funnel.total||0} 本`;$('progressFunnel').innerHTML=(funnel.bins||[]).map(x=>`<div class="funnel-row"><span>${esc(x.label)}</span><div class="funnel-track"><div class="funnel-fill" style="width:${100*(+x.count||0)/fmax}%"></div></div><b>${x.count}</b></div>`).join('');
const F=X.fingerprint||{},corr=F.monthlyReadNoteCorrelation;const fp=[['每小时笔记',F.notesPerHour==null?'—':F.notesPerHour+' 条'],['本人想法占比',(F.reviewShare||0)+'%'],['书签',(+F.bookmarks||0).toLocaleString()+' 个'],['每个阅读日',F.avgActiveDayMinutes==null?'—':F.avgActiveDayMinutes+' 分'],['时长↔笔记相关',corr==null?'—':Number(corr).toFixed(3)]];$('fingerprintGrid').innerHTML=fp.map(([k,v])=>`<div class="fingerprint-item"><span>${k}</span><b>${v}</b></div>`).join('');$('correlationNote').textContent=corr==null?'当前月度数据不足以计算稳定相关系数。':`Pearson r = ${Number(corr).toFixed(3)}，基于 ${F.correlationMonths||0} 个月。它只表示月度阅读时长与笔记数量的同步程度，不表示因果关系。`;
// Current deep reads, recall, own thoughts.
function bookMini(b,extra=''){return `<div class="pref-book"><div class="pref-book-cover">${b.cover?`<img src="${esc(b.cover)}" loading="lazy" alt="">`:''}</div><b title="${esc(b.title)}">${esc(b.title)}</b><small>${esc(b.author||'')}</small><em>${extra}</em></div>`}
const deep=X.currentDeepReads||[];optionalSection('deepreads',deep.length);$('deepReads').innerHTML=deep.map(b=>bookMini(b,`${b.progress==null?'—':b.progress+'%'} · ${b.noteCount} 条笔记`)).join('');
const recall=X.recallCandidates||[];optionalSection('recall',recall.length);$('recallRows').innerHTML=recall.slice(0,12).map(b=>`<tr><td>${esc(b.title)}<br><small class="muted">${esc(b.author||'')}</small></td><td>${b.noteCount}</td><td>${b.daysSinceLastNote} 天</td></tr>`).join('');
const thinking=X.thinkingBooks||[];optionalSection('thinking',thinking.length);$('thinkingRows').innerHTML=thinking.slice(0,12).map(b=>`<tr><td>${esc(b.title)}<br><small class="muted">${esc(b.author||'')}</small></td><td>${b.reviewCount}</td><td>${b.reviewRate}%</td></tr>`).join('');
// Full bookshelf explorer.
const allBooks=X.bookshelf||[];let shelfLimit=48;const q=$('shelfQuery'),cat=$('shelfCategory'),pf=$('shelfProgress'),sort=$('shelfSort');const categories=[...new Set(allBooks.map(b=>b.category).filter(x=>x&&x!=='未知'))].sort((a,b)=>a.localeCompare(b,'zh-CN'));cat.innerHTML+categories.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
function shelfFiltered(){const query=(q.value||'').trim().toLowerCase();let rows=allBooks.filter(b=>{if(cat.value&&b.category!==cat.value)return false;if(query&&!(`${b.title} ${b.author} ${b.category}`.toLowerCase().includes(query)))return false;if(pf.value==='noted'&&!(b.noteCount>0))return false;if(pf.value==='reading'&&!(b.progress>0&&b.progress<100))return false;if(pf.value==='finished'&&!(b.progress>=100))return false;if(pf.value==='unknown'&&b.progress!==null)return false;return true});if(sort.value==='notes')rows.sort((a,b)=>b.noteCount-a.noteCount);else if(sort.value==='progress')rows.sort((a,b)=>(b.progress??-1)-(a.progress??-1));else if(sort.value==='title')rows.sort((a,b)=>a.title.localeCompare(b.title,'zh-CN'));else rows.sort((a,b)=>String(b.lastRead||'').localeCompare(String(a.lastRead||''))||b.noteCount-a.noteCount);return rows}
function renderShelf(reset=false){if(reset)shelfLimit=48;const rows=shelfFiltered();$('shelfCount').textContent=`${rows.length} / ${allBooks.length} 本`;const shown=rows.slice(0,shelfLimit);$('shelfGrid').innerHTML=shown.map(b=>`<div class="shelf-book"><div class="shelf-cover">${b.cover?`<img src="${esc(b.cover)}" loading="lazy" alt="">`:''}${b.secret?'<span class="shelf-secret">secret</span>':''}</div><div class="shelf-progress"><i style="width:${b.progress==null?0:b.progress}%"></i></div><b title="${esc(b.title)}">${esc(b.title)}</b><p>${esc(b.author||'')} · ${esc(b.category||'未知')}</p><p>${b.progress==null?'进度未知':b.progress+'%'} · ${b.noteCount} 条笔记</p></div>`).join('');$('shelfMore').style.display=shelfLimit<rows.length?'block':'none'}
[q,cat,pf,sort].forEach(el=>el.addEventListener(el===q?'input':'change',()=>renderShelf(true)));$('shelfMore').addEventListener('click',()=>{shelfLimit+=48;renderShelf(false)});renderShelf(true);
'''


def _inject(html: str, enrichment: dict) -> str:
    encoded = json.dumps(enrichment, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("</style>", CSS + "\n</style>", 1)
    # Add compact navigation entries without replacing existing ones.
    html = html.replace("</nav>", '<a href="#clock">阅读时钟</a><a href="#progress">进度</a><a href="#recall">回顾</a><a href="#shelf-explorer">全书架</a></nav>', 1)
    marker = '  <article class="card wide privacy">'
    if marker in html:
        html = html.replace(marker, HTML + "\n" + marker, 1)
    else:
        html = html.replace("</section>\n<footer>", HTML + "\n</section>\n<footer>", 1)
    html = html.replace("<script>\n", "<script>\nconst E=" + encoded + ";\n", 1)
    html = html.replace("</script>", JS + "\n</script>", 1)
    return html


def main() -> None:
    include_private = env_true("WEREAD_PAGES_INCLUDE_PRIVATE", False)
    enrichment = pages_enrichment.build_enrichment(DATA, include_private=include_private)
    index_path = SITE / "index.html"
    report_path = SITE / "report-data.json"
    if not index_path.exists():
        raise SystemExit(f"ERROR: missing {index_path}; run pages_runtime.py first")
    html = index_path.read_text(encoding="utf-8")
    index_path.write_text(_inject(html, enrichment), encoding="utf-8")
    payload = {}
    if report_path.exists():
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["enrichment"] = enrichment
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "Pages enrichment: "
        f"books={len(enrichment['bookshelf'])} clock={len(enrichment['clock'])} "
        f"medals={len(enrichment['official']['medals'])} "
        f"preferBooks={len(enrichment['official']['annualPreferBooks'])} "
        f"recall={len(enrichment['recallCandidates'])}"
    )


if __name__ == "__main__":
    main()
