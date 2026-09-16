#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the local-only WeRead Private Reading Lab dashboard.

The output intentionally contains private reading evidence (marks/reviews/recall
items). It must never be copied into site/ or a public Pages artifact.
"""
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
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def js_json(value) -> str:
    """JSON safe to inline inside a script element."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def compact_book(book: dict) -> dict:
    return {
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or ""),
        "author": str(book.get("author") or ""),
        "category": str(book.get("category") or ""),
        "secret": bool(book.get("secret")),
        "progress": book.get("progress"),
        "noteCount": int(book.get("noteCount") or 0),
        "markCount": int(book.get("markCount") or 0),
        "reviewCount": int(book.get("reviewCount") or 0),
        "recordReadingTime": int(book.get("recordReadingTime") or 0),
    }


def evidence_rows(context: dict) -> list[dict]:
    rows = []
    for book in context.get("books") or []:
        if not isinstance(book, dict):
            continue
        base = {
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
            "category": str(book.get("category") or ""),
        }
        for key, kind in (("reviews", "review"), ("marks", "mark")):
            for item in book.get(key) or []:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                rows.append({
                    **base,
                    "kind": kind,
                    "chapter": str(item.get("chapter") or ""),
                    "text": text,
                    "createTime": int(item.get("createTime") or 0),
                })
    rows.sort(key=lambda x: (-x["createTime"], x["title"], x["chapter"]))
    return rows


def payload(context: dict, deep: dict, recall: dict, advisor: dict, blindspot: dict, review: dict,
            *, quote_cards_exists: bool) -> dict:
    books = [compact_book(b) for b in (context.get("books") or []) if isinstance(b, dict)]
    evidence = evidence_rows(context)
    return {
        "coverage": context.get("coverage") or {},
        "privacy": context.get("privacy") or {},
        "books": books,
        "evidence": evidence,
        "deep": deep,
        "recall": recall,
        "advisor": advisor,
        "blindspot": blindspot,
        "review": review,
        "quoteCards": bool(quote_cards_exists),
    }


def render(data: dict) -> str:
    serialized = js_json(data)
    return f'''<!doctype html>
<html lang="zh-CN" data-theme="system">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>WeRead Private Reading Lab</title>
<style>
:root{{--bg:#f2eee6;--paper:#fffdf8;--paper2:#f8f3ea;--ink:#28241f;--muted:#756d63;--line:#ded5c8;--accent:#a9573f;--accent2:#71866e;--accent3:#b78c42;--danger:#8f4b46;--shadow:0 12px 36px rgba(52,43,34,.08)}}
@media(prefers-color-scheme:dark){{html[data-theme="system"]{{--bg:#171614;--paper:#22201d;--paper2:#2a2723;--ink:#f0e9df;--muted:#aaa096;--line:#403b35;--accent:#e07a5f;--accent2:#94ad8f;--accent3:#d2aa5d;--danger:#d87972;--shadow:none;color-scheme:dark}}}}
html[data-theme="dark"]{{--bg:#171614;--paper:#22201d;--paper2:#2a2723;--ink:#f0e9df;--muted:#aaa096;--line:#403b35;--accent:#e07a5f;--accent2:#94ad8f;--accent3:#d2aa5d;--danger:#d87972;--shadow:none;color-scheme:dark}}
html[data-theme="light"]{{--bg:#f2eee6;--paper:#fffdf8;--paper2:#f8f3ea;--ink:#28241f;--muted:#756d63;--line:#ded5c8;--accent:#a9573f;--accent2:#71866e;--accent3:#b78c42;--danger:#8f4b46;--shadow:0 12px 36px rgba(52,43,34,.08);color-scheme:light}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55}}button,input,select{{font:inherit}}button{{cursor:pointer}}a{{color:inherit}}.shell{{max-width:1420px;margin:auto;padding:20px 24px 64px}}.topbar{{position:sticky;top:0;z-index:20;margin:0 -24px 20px;padding:10px 24px;border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(14px);display:flex;gap:8px;align-items:center;flex-wrap:wrap}}.brand{{font-weight:800;margin-right:auto}}.topbar a,.topbar button{{border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:7px 10px;text-decoration:none;color:var(--muted)}}.hero{{display:grid;grid-template-columns:1.3fr .7fr;gap:18px;margin:18px 0}}.panel,.metric,.workbench{{background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}}.hero-main{{padding:28px}}.kicker{{font-size:11px;color:var(--accent);letter-spacing:.16em;text-transform:uppercase}}h1{{font-family:"Songti SC","Noto Serif CJK SC",serif;font-size:42px;line-height:1.1;margin:8px 0 10px}}h2{{font-size:20px;margin:0}}h3{{font-size:14px;margin:0}}.muted{{color:var(--muted)}}.privacy{{padding:18px;border-style:dashed}}.privacy strong{{color:var(--danger)}}.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:14px 0 22px}}.metric{{padding:14px}}.metric span{{display:block;font-size:10px;color:var(--muted)}}.metric b{{display:block;font-size:22px;margin-top:5px}}.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}}.panel{{padding:18px;min-width:0}}.section-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:14px}}.section-head p{{margin:3px 0 0;color:var(--muted);font-size:11px}}.bars{{display:grid;gap:8px}}.bar-row{{display:grid;grid-template-columns:72px 1fr 52px;gap:8px;align-items:center;font-size:11px}}.bar-track{{height:14px;border-radius:999px;background:var(--paper2);overflow:hidden}}.bar-fill{{height:100%;border-radius:inherit;background:var(--accent2)}}.bar-fill.alt{{background:var(--accent3)}}.stack{{height:20px;display:flex;border-radius:999px;overflow:hidden;background:var(--paper2)}}.stack span:nth-child(1){{background:var(--accent2)}}.stack span:nth-child(2){{background:var(--accent)}}.stack span:nth-child(3){{background:var(--accent3)}}.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:10px;color:var(--muted);margin-top:8px}}.legend i{{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}}.list{{display:grid;gap:8px}}.list-card{{border:1px solid var(--line);background:var(--paper2);border-radius:13px;padding:11px}}.list-card b{{font-size:12px}}.list-card p{{margin:5px 0 0;font-size:11px;color:var(--muted)}}.raw{{white-space:pre-wrap;color:var(--ink)!important;font-family:"Songti SC","Noto Serif CJK SC",serif;line-height:1.75}}.search-tools{{display:grid;grid-template-columns:1fr 130px 160px;gap:8px;margin-bottom:10px}}input,select{{width:100%;border:1px solid var(--line);border-radius:10px;padding:9px 10px;background:var(--paper2);color:var(--ink)}}.results{{max-height:520px;overflow:auto;display:grid;gap:7px}}.evidence{{border:1px solid var(--line);border-radius:12px;padding:10px;background:var(--paper2)}}.evidence-head{{display:flex;gap:7px;flex-wrap:wrap;align-items:center;font-size:10px;color:var(--muted)}}.badge{{border:1px solid var(--line);border-radius:999px;padding:2px 6px}}.badge.review{{color:var(--accent)}}.evidence p{{font-size:12px;margin:7px 0 0;white-space:pre-wrap}}.workbench{{margin:14px 0;padding:20px;scroll-margin-top:70px}}.workbench.empty{{display:none}}.wb-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}.wb-actions{{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}}.wb-actions button,.wb-actions a{{border:1px solid var(--line);border-radius:999px;background:var(--paper2);padding:7px 10px;font-size:11px;text-decoration:none}}.wb-columns{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.recall-card{{border:1px solid var(--line);border-radius:14px;padding:12px;background:var(--paper2)}}.recall-card .answer{{display:none;margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);white-space:pre-wrap;font-size:12px}}.recall-card.revealed .answer{{display:block}}.recall-card button{{border:0;background:transparent;color:var(--accent);padding:5px 0;font-size:11px}}.book-list{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.book-btn{{text-align:left;border:1px solid var(--line);border-radius:12px;background:var(--paper2);padding:10px;color:var(--ink)}}.book-btn b,.book-btn small{{display:block}}.book-btn small{{color:var(--muted);margin-top:3px}}.empty-state{{padding:18px;color:var(--muted);text-align:center}}.footer-note{{font-size:11px;color:var(--muted);margin-top:20px}}
@media(max-width:950px){{.hero,.grid2,.wb-columns{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(3,1fr)}}.book-list{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:580px){{.shell{{padding:12px 12px 48px}}.topbar{{margin:0 -12px 14px;padding:8px 12px}}h1{{font-size:32px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.search-tools{{grid-template-columns:1fr}}.book-list{{grid-template-columns:1fr}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
</style>
</head><body>
<main class="shell">
<nav class="topbar"><span class="brand">Private Reading Lab</span><a href="#deep">Deep Notes</a><a href="#search">Evidence Search</a><a href="#recall">Recall</a><a href="#books">Books</a><a id="quoteLink" href="quote_cards.html">Quote Cards</a><button id="themeBtn" type="button">主题：系统</button></nav>
<section class="hero"><div class="panel hero-main"><div class="kicker">Local evidence workspace</div><h1>你的微信读书私人实验室</h1><p class="muted">把划线卡片、深度笔记结构、全文证据搜索、Recall、Advisor 与 Review 收进一个本地入口。这里允许出现原始划线和本人想法，因此不能发布到 GitHub Pages。</p></div><div class="panel privacy"><strong>Private / Raw Evidence</strong><p class="muted">本 HTML 内嵌个人阅读证据。请只在本地打开；不要上传到 <code>site/</code>、公开网盘或公开静态站点。</p></div></section>
<section class="metrics" id="metrics"></section>
<section id="book-workbench" class="workbench empty"></section>
<section class="grid2" id="deep"><article class="panel"><div class="section-head"><div><h2>划线长度结构</h2><p>长度是记录行为，不代表内容价值。</p></div></div><div class="bars" id="lengthBars"></div></article><article class="panel"><div class="section-head"><div><h2>划线位置</h2><p>按每本书划线首次出现章节顺序近似为十分位。</p></div></div><div class="bars" id="positionBars"></div></article></section>
<section class="grid2"><article class="panel"><div class="section-head"><div><h2>划线 ↔ 想法章节关系</h2><p>看哪些章节只保存原文、哪些真正写了自己的想法。</p></div></div><div class="stack" id="interplay"></div><div class="legend" id="interplayLegend"></div></article><article class="panel"><div class="section-head"><div><h2>重复划线</h2><p>可能是重要母题，也可能来自重复版本；只作为回看信号。</p></div><small class="muted" id="dupCount"></small></div><div class="list" id="duplicates"></div></article></section>
<section class="grid2"><article class="panel"><div class="section-head"><div><h2>本人想法最密集</h2><p>review 多的书，优先代表“你真正说过什么”。</p></div></div><div class="book-list" id="thoughtBooks"></div></article><article class="panel"><div class="section-head"><div><h2>划线很多、想法较少</h2><p>适合进入 Feynman / Alchemy 再加工。</p></div></div><div class="book-list" id="highlightBooks"></div></article></section>
<section class="panel" id="search"><div class="section-head"><div><h2>私人证据搜索</h2><p>浏览器内搜索 mark/review；不会发网络请求。点击结果可进入单书 Workbench。</p></div><small class="muted" id="resultCount"></small></div><div class="search-tools"><input id="searchInput" type="search" placeholder="搜索原文 / 我的想法 / 书名 / 作者 / 章节"><select id="kindFilter"><option value="">全部类型</option><option value="review">只看我的想法</option><option value="mark">只看划线原文</option></select><select id="bookFilter"><option value="">全部书</option></select></div><div class="results" id="searchResults"></div></section>
<section class="panel" id="recall" style="margin-top:14px"><div class="section-head"><div><h2>Recall / Feynman</h2><p>先回答，再揭示证据。review 优先代表你的历史观点，mark 只是原文。</p></div><small class="muted" id="recallCount"></small></div><div class="book-list" id="recallGrid"></div></section>
<section class="panel" id="books" style="margin-top:14px"><div class="section-head"><div><h2>书籍工作台入口</h2><p>按笔记数排序。点一本书后，Search、Recall、Alchemy 命令集中到顶部 Workbench。</p></div><small class="muted" id="bookCount"></small></div><div class="book-list" id="allBooks"></div></section>
<p class="footer-note">所有数据来自本地 WeRead 导出与确定性 Context。任何“推荐原因、认知变化原因、人格解释”都不应由本页这些结构信号直接推断。</p>
</main>
<script>
const LAB={serialized};
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const fmtHours=s=>((+s||0)/3600).toFixed(1)+'h';
const bookById=Object.fromEntries((LAB.books||[]).map(b=>[String(b.bookId),b]));
const recalls=(LAB.recall&&LAB.recall.items)||[];
function metrics(){{const c=LAB.coverage||{{}},d=LAB.deep.coverage||{{}};const vals=[['书籍',c.contextBooks??LAB.books.length],['有笔记书',c.booksWithNotes??d.booksWithNotes??0],['划线',c.marks??d.marks??0],['我的想法',c.reviews??d.reviews??0],['证据条目',LAB.evidence.length],['Recall',recalls.length]];$('metrics').innerHTML=vals.map(([k,v])=>`<div class="metric"><span>${{k}}</span><b>${{Number(v||0).toLocaleString()}}</b></div>`).join('')}}metrics();
function bars(id,rows,labelKey,valueKey,alt=false){{const el=$(id),max=Math.max(1,...rows.map(x=>+x[valueKey]||0));el.innerHTML=rows.map(x=>`<div class="bar-row"><span>${{esc(x[labelKey])}}</span><div class="bar-track"><div class="bar-fill ${{alt?'alt':''}}" style="width:${{Math.max(1,100*(+x[valueKey]||0)/max)}}%"></div></div><b>${{+x[valueKey]||0}}</b></div>`).join('')}}
bars('lengthBars',(LAB.deep.highlightLength||{{}}).buckets||[],'label','count');bars('positionBars',(LAB.deep.chapterPosition||{{}}).deciles||[],'decile','count',true);
function interplay(){{const x=LAB.deep.markReviewInterplay||{{}},vals=[['划线+想法','both',+x.both||0,'var(--accent2)'],['只划线','onlyMark',+x.onlyMark||0,'var(--accent)'],['只想法','onlyReview',+x.onlyReview||0,'var(--accent3)']],total=Math.max(1,vals.reduce((s,v)=>s+v[2],0));$('interplay').innerHTML=vals.map(v=>`<span style="width:${{100*v[2]/total}}%" title="${{esc(v[0])}} ${{v[2]}}"></span>`).join('');$('interplayLegend').innerHTML=vals.map(v=>`<span><i style="background:${{v[3]}}"></i>${{esc(v[0])}} ${{v[2]}}</span>`).join('')}}interplay();
function bookButton(b,extra=''){{return `<button class="book-btn" data-book="${{esc(b.bookId)}}"><b>${{esc(b.title||'—')}}</b><small>${{esc(b.author||'')}} · ${{b.notes??b.noteCount??0}} 条 ${{extra}}</small></button>`}}
function duplicates(){{const rows=(LAB.deep.duplicateHighlights||[]).slice(0,12);$('dupCount').textContent=`${{LAB.deep.duplicateHighlightCount||0}} 组`;$('duplicates').innerHTML=rows.length?rows.map(x=>`<div class="list-card"><b>${{x.count}}× · ${{esc((x.books||[]).map(b=>b.title).filter(Boolean).slice(0,3).join(' / '))}}</b><p class="raw">${{esc(x.text)}}</p></div>`).join(''):'<div class="empty-state">没有检测到重复划线。</div>'}}duplicates();
$('thoughtBooks').innerHTML=((LAB.deep.thoughtRichBooks)||[]).slice(0,12).map(b=>bookButton(b,`· 想法 ${{b.reviews}} · ${{Math.round((b.reviewShare||0)*100)}}%`)).join('');$('highlightBooks').innerHTML=((LAB.deep.highlightHeavyBooks)||[]).slice(0,12).map(b=>bookButton(b,`· 划线 ${{b.marks}} · 想法 ${{b.reviews}}`)).join('');
const sortedBooks=[...(LAB.books||[])].sort((a,b)=>(b.noteCount||0)-(a.noteCount||0)||String(a.title).localeCompare(String(b.title),'zh-CN'));$('bookCount').textContent=`${{sortedBooks.length}} 本`;$('allBooks').innerHTML=sortedBooks.slice(0,120).map(b=>bookButton(b,`${{b.progress==null?'进度未知':b.progress+'%'}}`)).join('');
$('bookFilter').innerHTML='<option value="">全部书</option>'+sortedBooks.filter(b=>b.noteCount>0).map(b=>`<option value="${{esc(b.bookId)}}">${{esc(b.title)}}</option>`).join('');
function openBook(bookId,mode=''){{const b=bookById[String(bookId)];if(!b)return;history.replaceState(null,'',`?book=${{encodeURIComponent(b.bookId)}}${{mode?'&mode='+encodeURIComponent(mode):''}}#book-workbench`);const ev=(LAB.evidence||[]).filter(x=>String(x.bookId)===String(b.bookId)),rr=recalls.filter(x=>String(x.bookId)===String(b.bookId));const searchCmd=`python scripts/build_search_index.py --db "${{esc('data/analysis/private_lab/search.sqlite')}}" --query "关键词" --book-id "${{String(b.bookId).replace(/"/g,'')}}"`;const alchemyCmd=`python scripts/build_alchemy_context.py --context "data/analysis/private_lab/visualization_context.json" --book-id "${{String(b.bookId).replace(/"/g,'')}}" --output "data/analysis/private_lab/alchemy_book_context.json"`;const weread=`weread://reading?bId=${{encodeURIComponent(b.bookId)}}`;$('book-workbench').classList.remove('empty');$('book-workbench').innerHTML=`<div class="wb-head"><div><div class="kicker">Book workbench</div><h2>${{esc(b.title)}}</h2><p class="muted">${{esc(b.author)}} · ${{esc(b.category)}} · 笔记 ${{b.noteCount}} · ${{b.progress==null?'进度未知':'进度 '+b.progress+'%'}}</p></div><button type="button" id="closeWb">关闭</button></div><div class="wb-actions"><a href="${{weread}}">打开微信读书</a><button type="button" data-copy="${{esc(searchCmd)}}">复制 Search 命令</button><button type="button" data-copy="${{esc(alchemyCmd)}}">复制 Alchemy 命令</button><button type="button" id="searchThis">只搜这本书</button></div><div class="wb-columns"><div><h3>Recall ${{rr.length}}</h3>${{rr.length?rr.map(recallCard).join(''):'<p class="muted">当前 Recall 队列没有这本书。</p>'}}</div><div><h3>最近证据 ${{ev.length}}</h3><div class="results">${{ev.slice(0,12).map(evidenceCard).join('')||'<p class="muted">无证据。</p>'}}</div></div></div>`;$('closeWb').onclick=()=>{{$('book-workbench').classList.add('empty');history.replaceState(null,'',location.pathname)}};$('searchThis').onclick=()=>{{$('bookFilter').value=b.bookId;filterEvidence();$('search').scrollIntoView({{behavior:'smooth'}})}};$('book-workbench').querySelectorAll('[data-copy]').forEach(btn=>btn.onclick=()=>copyText(btn.dataset.copy,btn));wireRecall($('book-workbench'));$('book-workbench').scrollIntoView({{behavior:'smooth',block:'start'}})}}
function copyText(text,btn){{if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(text).then(()=>{{const old=btn.textContent;btn.textContent='已复制';setTimeout(()=>btn.textContent=old,1200)}});else prompt('复制命令：',text)}}
function evidenceCard(x){{return `<article class="evidence" data-book-open="${{esc(x.bookId)}}"><div class="evidence-head"><span class="badge ${{x.kind}}">${{x.kind==='review'?'我的想法':'划线原文'}}</span><b>${{esc(x.title)}}</b><span>${{esc(x.chapter||'')}}</span></div><p>${{esc(x.text)}}</p></article>`}}
function filterEvidence(){{const q=($('searchInput').value||'').trim().toLowerCase(),kind=$('kindFilter').value,bid=$('bookFilter').value;let rows=(LAB.evidence||[]).filter(x=>(!kind||x.kind===kind)&&(!bid||String(x.bookId)===bid));if(q)rows=rows.filter(x=>[x.text,x.title,x.author,x.chapter,x.category].join(' ').toLowerCase().includes(q));$('resultCount').textContent=`${{rows.length}} / ${{LAB.evidence.length}}`;$('searchResults').innerHTML=rows.slice(0,120).map(evidenceCard).join('')||'<div class="empty-state">没有匹配证据。</div>';$('searchResults').querySelectorAll('[data-book-open]').forEach(el=>el.onclick=()=>openBook(el.dataset.bookOpen))}}
['searchInput','kindFilter','bookFilter'].forEach(id=>$(id).addEventListener(id==='searchInput'?'input':'change',filterEvidence));filterEvidence();
function recallCard(x){{return `<article class="recall-card"><div class="evidence-head"><span class="badge ${{x.kind}}">${{x.kind==='review'?'我的想法':'划线原文'}}</span><button type="button" class="open-book-link" data-book="${{esc(x.bookId)}}">${{esc(x.title)}}</button><span>${{x.ageDays}} 天前</span></div><p>${{esc(x.prompt)}}</p><button type="button" class="reveal">揭示证据</button><div class="answer">${{esc(x.text)}}${{x.chapter?'\n\n章节：'+esc(x.chapter):''}}</div></article>`}}
function wireRecall(root=document){{root.querySelectorAll('.recall-card .reveal').forEach(b=>b.onclick=()=>b.closest('.recall-card').classList.toggle('revealed'));root.querySelectorAll('.open-book-link').forEach(b=>b.onclick=()=>openBook(b.dataset.book,'recall'))}}
$('recallCount').textContent=`${{recalls.length}} 条`;$('recallGrid').innerHTML=recalls.map(recallCard).join('')||'<div class="empty-state">当前 Recall 队列为空。</div>';wireRecall($('recallGrid'));
document.querySelectorAll('.book-btn').forEach(b=>b.onclick=()=>openBook(b.dataset.book));
$('quoteLink').style.display=LAB.quoteCards?'inline-block':'none';
const themes=['system','light','dark'],labels={{system:'系统',light:'浅色',dark:'深色'}},saved=localStorage.getItem('wereadPrivateLabThemeV1')||'system';let theme=themes.includes(saved)?saved:'system';function applyTheme(){{document.documentElement.dataset.theme=theme;$('themeBtn').textContent='主题：'+labels[theme];localStorage.setItem('wereadPrivateLabThemeV1',theme)}}applyTheme();$('themeBtn').onclick=()=>{{theme=themes[(themes.indexOf(theme)+1)%themes.length];applyTheme()}};
const params=new URLSearchParams(location.search),initial=params.get('book');if(initial&&bookById[initial])openBook(initial,params.get('mode')||'');
</script></body></html>'''


def parse_args():
    parser = argparse.ArgumentParser(description="Render local-only WeRead Private Reading Lab dashboard.")
    parser.add_argument("--context", type=Path, default=LAB / "visualization_context.json")
    parser.add_argument("--deep", type=Path, default=LAB / "deep_notes_context.json")
    parser.add_argument("--recall", type=Path, default=LAB / "recall_queue.json")
    parser.add_argument("--advisor", type=Path, default=LAB / "advisor_context.json")
    parser.add_argument("--blindspot", type=Path, default=LAB / "blindspot_context.json")
    parser.add_argument("--review", type=Path, default=LAB / "narrative_review_context.json")
    parser.add_argument("--quote-cards", type=Path, default=LAB / "quote_cards.html")
    parser.add_argument("--output", type=Path, default=LAB / "index.html")
    return parser.parse_args()


def main():
    args = parse_args()
    context = read_json(args.context, {})
    if not context:
        raise SystemExit(f"ERROR: missing/invalid context: {args.context}")
    data = payload(
        context,
        read_json(args.deep, {}),
        read_json(args.recall, {}),
        read_json(args.advisor, {}),
        read_json(args.blindspot, {}),
        read_json(args.review, {}),
        quote_cards_exists=args.quote_cards.exists(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    print(
        f"private-lab-dashboard: {args.output} | books={len(data['books'])} "
        f"evidence={len(data['evidence'])} recall={len((data['recall'] or {}).get('items') or [])} private=true"
    )


if __name__ == "__main__":
    main()
