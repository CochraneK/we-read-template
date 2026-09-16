#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experience layer for the GitHub Pages reading archive.

This module does not compute facts. It reorganizes the already rendered report
into navigable chapters, adds a compact sticky archive bar, preserves browser-
local interaction state, and improves keyboard/mobile use. Raw note/review text
is never introduced here.
"""

CSS = r'''
:root{--sticky-offset:78px}
body:before{content:"";position:fixed;inset:0 0 auto 0;height:3px;background:var(--line);z-index:120;pointer-events:none}.reading-progress{position:fixed;left:0;top:0;width:100%;height:3px;z-index:121;pointer-events:none}.reading-progress i{display:block;width:0;height:100%;background:linear-gradient(90deg,var(--accent2),var(--accent3),var(--accent));transition:width .08s linear}.skip-link{position:fixed;left:12px;top:10px;z-index:200;transform:translateY(-160%);background:var(--ink);color:var(--paper);padding:8px 12px;border-radius:10px;text-decoration:none;font-size:12px}.skip-link:focus{transform:none}.wrap{padding-top:34px}.hero{position:relative;padding:26px 0 8px}.hero:before{content:"";position:absolute;left:-22px;top:4px;width:92px;height:92px;border:1px solid color-mix(in srgb,var(--accent) 28%,transparent);border-radius:50%;z-index:-1}.hero h1{max-width:850px;letter-spacing:-.035em}.hero p{max-width:860px}.stamp{font-variant-numeric:tabular-nums}.hero-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:-2px 0 12px}.hero-metric{border:1px solid var(--line);border-radius:16px;padding:12px 14px;background:color-mix(in srgb,var(--paper) 88%,transparent);min-width:0}.hero-metric span{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em}.hero-metric b{display:block;font-size:20px;margin-top:3px;font-variant-numeric:tabular-nums;white-space:nowrap}.daily-recall{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;border:1px solid color-mix(in srgb,var(--accent3) 42%,var(--line));border-radius:18px;padding:14px 16px;margin:0 0 18px;background:linear-gradient(120deg,color-mix(in srgb,var(--accent3) 7%,var(--paper)),var(--paper))}.daily-recall-kicker{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent3);font-weight:800}.daily-recall b{display:block;font-family:ui-serif,"Songti SC","STSong",serif;font-size:18px;margin:3px 0}.daily-recall p{margin:0;color:var(--muted);font-size:11px}.daily-recall button{border:1px solid var(--line);background:var(--ink);color:var(--paper);border-radius:999px;padding:8px 12px;font:inherit;font-size:11px;cursor:pointer;white-space:nowrap}.nav{position:sticky;top:10px;z-index:100;align-items:center;flex-wrap:nowrap;overflow-x:auto;overscroll-behavior-inline:contain;scrollbar-width:none;padding:7px;border:1px solid color-mix(in srgb,var(--line) 88%,transparent);border-radius:18px;background:color-mix(in srgb,var(--paper) 88%,transparent);backdrop-filter:blur(18px) saturate(1.25);-webkit-backdrop-filter:blur(18px) saturate(1.25);box-shadow:0 10px 30px rgba(30,24,18,.07)}.nav::-webkit-scrollbar{display:none}.nav a{flex:0 0 auto;border-color:transparent;background:transparent;padding:7px 10px}.nav a:hover{background:color-mix(in srgb,var(--line) 42%,transparent);border-color:transparent}.nav a.active{background:var(--ink);color:var(--paper);border-color:var(--ink)}.nav-spacer{flex:1 0 12px}.nav-control{flex:0 0 auto;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:7px 10px;font:inherit;font-size:11px;cursor:pointer;white-space:nowrap}.nav-control[aria-pressed="true"]{background:var(--accent2);color:var(--paper);border-color:var(--accent2)}.nav-control.resume{border-color:color-mix(in srgb,var(--accent3) 65%,var(--line));color:var(--accent)}.chapter-heading{grid-column:1/-1!important;display:grid;grid-template-columns:74px minmax(0,1fr) auto;gap:14px;align-items:end;padding:26px 4px 2px;margin-top:12px;scroll-margin-top:var(--sticky-offset)}.chapter-index{font-family:ui-serif,"Songti SC","STSong",serif;color:var(--accent);font-size:13px;letter-spacing:.12em}.chapter-heading h2{font-family:ui-serif,"Songti SC","STSong",serif;font-size:clamp(27px,3.4vw,42px);line-height:1;margin:0;font-weight:650;letter-spacing:-.025em}.chapter-heading p{margin:7px 0 0;color:var(--muted);font-size:12px}.chapter-heading:after{content:"";height:1px;background:var(--line);min-width:80px;margin-bottom:5px}.card{scroll-margin-top:var(--sticky-offset);transition:border-color .18s ease,transform .18s ease,box-shadow .18s ease}.card.wide,.card.half,.card.third{content-visibility:auto;contain-intrinsic-size:auto 420px}.card:hover{border-color:color-mix(in srgb,var(--line) 62%,var(--accent2));transform:translateY(-1px)}.title h2{letter-spacing:-.015em}.section-kicker{opacity:.86}.focus-mode .optional-depth{display:none!important}.focus-mode .chapter-heading[data-chapter="reflection"] p:after{content:" · 精简模式已隐藏次要明细"}.archive-tools{position:fixed;right:20px;bottom:20px;z-index:110;display:flex;gap:7px}.float-btn{width:42px;height:42px;border:1px solid var(--line);border-radius:50%;background:color-mix(in srgb,var(--paper) 91%,transparent);color:var(--ink);box-shadow:var(--shadow);backdrop-filter:blur(12px);font:inherit;font-size:14px;cursor:pointer;display:grid;place-items:center;opacity:.92}.float-btn:hover{opacity:1;border-color:var(--accent2)}.shelf-shortcut{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:10px;margin-left:8px}.shelf-shortcut kbd{border:1px solid var(--line);background:var(--bg);border-bottom-width:2px;border-radius:5px;padding:1px 5px;font:inherit}.shelf-pin{position:absolute;left:5px;top:5px;width:27px;height:27px;display:grid;place-items:center;border:1px solid color-mix(in srgb,var(--line) 72%,transparent);border-radius:50%;background:color-mix(in srgb,var(--paper) 88%,transparent);color:var(--muted);font:inherit;font-size:14px;line-height:1;cursor:pointer;backdrop-filter:blur(8px);z-index:3}.shelf-pin:hover{color:var(--ink);border-color:var(--accent3)}.shelf-pin.pinned{background:var(--accent3);border-color:var(--accent3);color:var(--paper)}.shelf-empty{grid-column:1/-1;border:1px dashed var(--line);border-radius:16px;padding:28px;text-align:center;color:var(--muted);font-size:12px}.shelf-empty button{display:block;margin:10px auto 0;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:7px 11px;font:inherit;font-size:11px;cursor:pointer}.card :focus-visible,.nav :focus-visible,.float-btn:focus-visible,.shelf-pin:focus-visible,.daily-recall button:focus-visible{outline:3px solid color-mix(in srgb,var(--accent3) 48%,transparent);outline-offset:2px}.privacy{margin-top:12px}.table{font-variant-numeric:tabular-nums}.shelf-cover,.pref-book-cover,.cover{box-shadow:0 3px 14px rgba(40,31,23,.08)}
@media(max-width:900px){:root{--sticky-offset:70px}.hero-strip{grid-template-columns:repeat(3,1fr)}.nav{top:6px;border-radius:15px}.chapter-heading{grid-template-columns:56px minmax(0,1fr)}.chapter-heading:after{display:none}.archive-tools{right:12px;bottom:12px}}
@media(max-width:560px){.wrap{padding-top:20px}.hero{padding-top:16px}.hero h1{font-size:42px}.hero p{font-size:14px}.hero-strip{grid-template-columns:repeat(2,1fr);gap:7px}.hero-metric{padding:10px 11px}.hero-metric b{font-size:17px}.daily-recall{grid-template-columns:1fr;gap:10px}.daily-recall button{justify-self:start}.nav{margin-inline:-2px}.nav a{padding:6px 8px;font-size:11px}.nav-control{padding:6px 8px}.chapter-heading{grid-template-columns:1fr;gap:4px;padding-top:22px}.chapter-index{font-size:10px}.chapter-heading h2{font-size:29px}.chapter-heading p{font-size:11px}.card:hover{transform:none}.archive-tools{bottom:10px}.float-btn{width:39px;height:39px}.title{align-items:flex-start;flex-direction:column;gap:3px}.title small{font-size:10px}.table{display:block;overflow-x:auto;white-space:nowrap}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card,.reading-progress i{transition:none}.card:hover{transform:none}}
'''

JS = r'''
(()=>{
  const rhythmCard=document.getElementById('rhythm');
  const mainGrid=rhythmCard?.parentElement;
  if(!mainGrid||!mainGrid.classList.contains('grid'))return;

  const idByTitle={
    '月度笔记量':'notes-trend','年度汇总':'annual-summary','阅读类别':'category-summary',
    '笔记最多的作者':'author-summary','最近阅读':'recent-books','数据边界':'data-boundary'
  };
  [...mainGrid.querySelectorAll(':scope > article')].forEach(card=>{
    if(card.id)return;
    const title=card.querySelector('h2')?.textContent?.trim();
    if(title&&idByTitle[title])card.id=idByTitle[title];
  });

  const chapters=[
    {id:'chapter-life',key:'life',n:'01',label:'阅读生涯',desc:'把阅读放回时间轴：从长期累计、年度章节到里程碑。',items:['lifetime','career','year-lens','annual-summary','medals']},
    {id:'chapter-rhythm',key:'rhythm',n:'02',label:'阅读节律',desc:'月、日、星期与 24 小时，观察阅读真正发生在什么时候。',items:['rhythm','notes-trend','heatmap','clock','weekday','season','mode']},
    {id:'chapter-investment',key:'investment',n:'03',label:'偏好与投入',desc:'区分官方偏好、收藏意图、阅读进度与真实笔记投入。',items:['official','progress','fingerprint','deepreads','books','recent-books','category-summary','author-summary']},
    {id:'chapter-knowledge',key:'knowledge',n:'04',label:'知识与迁移',desc:'从年度关注变化进入跨书关系、深度投入和事实型画像。',items:['shift','focus','map','knowledge','depth-matrix','note-evolution','profile','investment']},
    {id:'chapter-reflection',key:'reflection',n:'05',label:'回顾与反向阅读',desc:'重新激活旧知识，同时看见收藏很多但投入较少的方向。',items:['recall','thinking','blindspot','counter']},
    {id:'chapter-shelf',key:'shelf',n:'06',label:'完整书架',desc:'把 498 本书从静态数字变成可以搜索、过滤和排序的档案。',items:['shelf-explorer']},
    {id:'chapter-boundary',key:'boundary',n:'07',label:'数据边界',desc:'清楚标注覆盖率、私密书范围和哪些内容从未被公开。',items:['data-boundary']}
  ];
  const secondary=new Set(['notes-trend','season','mode','medals','recent-books','category-summary','author-summary','map','note-evolution','investment','thinking','counter']);
  chapters.forEach(ch=>{
    const cards=ch.items.map(id=>document.getElementById(id)).filter(Boolean);
    if(!cards.length)return;
    const head=document.createElement('div');
    head.className='chapter-heading';head.id=ch.id;head.dataset.chapter=ch.key;
    head.innerHTML=`<div class="chapter-index">CHAPTER ${ch.n}</div><div><h2>${ch.label}</h2><p>${ch.desc}</p></div>`;
    mainGrid.appendChild(head);
    cards.forEach(card=>{if(secondary.has(card.id))card.classList.add('optional-depth');mainGrid.appendChild(card)});
  });

  document.title='我的阅读档案 · WeRead Intelligence';
  const eyebrow=document.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='WeRead Intelligence · Personal Reading Archive';
  const heroTitle=document.querySelector('.hero h1');if(heroTitle)heroTitle.textContent='我的阅读档案';
  const heroP=document.querySelector('.hero p');if(heroP)heroP.textContent='一份持续生长的个人阅读档案：从长期节律、年度迁移和真实投入，到跨书知识关系与 498 本完整书架。所有数值由数据计算；原始划线和想法正文不在公开页面出现。';
  const s=D.summary||{};
  const strip=document.createElement('div');strip.className='hero-strip';
  const metrics=[['累计阅读',`${Number(s.totalHours||0).toFixed(1)}h`],['阅读天数',`${(+s.readDays||0).toLocaleString()} 天`],['完整书架',`${(+s.shelfBooks||0).toLocaleString()} 本`],['笔记证据',`${(+s.notes||0).toLocaleString()} 条`],['最长连续',`${+s.longestStreak||0} 天`]];
  strip.innerHTML=metrics.map(([k,v])=>`<div class="hero-metric"><span>${k}</span><b>${v}</b></div>`).join('');
  document.querySelector('.hero')?.insertAdjacentElement('afterend',strip);

  const recallPool=(typeof E!=='undefined'&&E.recallCandidates)||[];
  if(recallPool.length){const now=new Date(),serial=Math.floor(Date.UTC(now.getFullYear(),now.getMonth(),now.getDate())/86400000),pick=recallPool[Math.abs(serial)%recallPool.length],daily=document.createElement('div');daily.className='daily-recall';daily.innerHTML=`<div><div class="daily-recall-kicker">Today · Knowledge reactivation</div><b>${esc(pick.title||'未命名')}</b><p>${esc(pick.author||'')} · ${+pick.noteCount||0} 条笔记 · 距最后一次笔记 ${+pick.daysSinceLastNote||0} 天</p></div><button type="button">去回顾</button>`;daily.querySelector('button').addEventListener('click',()=>document.getElementById('recall')?.scrollIntoView({behavior:'smooth',block:'start'}));strip.insertAdjacentElement('afterend',daily)}

  const nav=document.querySelector('.nav');
  const navItems=[['chapter-life','生涯'],['chapter-rhythm','节律'],['chapter-investment','投入'],['chapter-knowledge','知识'],['chapter-reflection','回顾'],['chapter-shelf','书架']];
  let lastChapter='';try{lastChapter=localStorage.getItem('wereadArchiveLastChapter')||''}catch(_){}
  if(nav){
    nav.innerHTML=navItems.map(([id,label])=>`<a href="#${id}" data-chapter-link="${id}">${label}</a>`).join('')+'<span class="nav-spacer"></span>'+(lastChapter&&document.getElementById(lastChapter)?'<button class="nav-control resume" id="resumeChapter" type="button">继续上次</button>':'')+'<button class="nav-control" id="focusToggle" type="button" aria-pressed="false" title="隐藏次要明细，保留核心档案">精简</button>';
    nav.setAttribute('aria-label','阅读档案章节导航');
  }
  $('resumeChapter')?.addEventListener('click',()=>document.getElementById(lastChapter)?.scrollIntoView({behavior:'smooth',block:'start'}));

  const skip=document.createElement('a');skip.className='skip-link';skip.href='#chapter-life';skip.textContent='跳到阅读档案正文';document.body.prepend(skip);
  const progress=document.createElement('div');progress.className='reading-progress';progress.innerHTML='<i></i>';document.body.prepend(progress);
  const tools=document.createElement('div');tools.className='archive-tools';tools.innerHTML='<button class="float-btn" id="toTop" type="button" title="回到顶部" aria-label="回到顶部">↑</button>';document.body.appendChild(tools);
  $('toTop')?.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));

  const focusButton=$('focusToggle');
  function setFocus(on){document.body.classList.toggle('focus-mode',on);if(focusButton){focusButton.setAttribute('aria-pressed',String(on));focusButton.textContent=on?'完整':'精简'}try{localStorage.setItem('wereadArchiveFocus',on?'1':'0')}catch(_){}}
  let saved=false;try{saved=localStorage.getItem('wereadArchiveFocus')==='1'}catch(_){}
  setFocus(saved);focusButton?.addEventListener('click',()=>setFocus(!document.body.classList.contains('focus-mode')));

  const links=[...document.querySelectorAll('[data-chapter-link]')];
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(!visible)return;links.forEach(a=>a.classList.toggle('active',a.dataset.chapterLink===visible.target.id));try{localStorage.setItem('wereadArchiveLastChapter',visible.target.id)}catch(_){}},{rootMargin:'-18% 0px -68% 0px',threshold:[0,.2,.6,1]});
    chapters.forEach(ch=>{const el=$(ch.id);if(el)observer.observe(el)});
  }
  let ticking=false;function updateProgress(){const max=Math.max(1,document.documentElement.scrollHeight-innerHeight),pct=Math.max(0,Math.min(1,scrollY/max));const bar=document.querySelector('.reading-progress i');if(bar)bar.style.width=(pct*100).toFixed(2)+'%';ticking=false}addEventListener('scroll',()=>{if(!ticking){ticking=true;requestAnimationFrame(updateProgress)}},{passive:true});updateProgress();

  const query=$('shelfQuery');if(query){query.autocomplete='off';const hint=document.createElement('span');hint.className='shelf-shortcut';hint.innerHTML='<kbd>/</kbd> 搜索书架';query.insertAdjacentElement('afterend',hint)}
  addEventListener('keydown',e=>{const tag=(document.activeElement?.tagName||'').toLowerCase();const typing=['input','textarea','select'].includes(tag)||document.activeElement?.isContentEditable;if(e.key==='/'&&!typing&&query){e.preventDefault();$('chapter-shelf')?.scrollIntoView({behavior:'smooth',block:'start'});setTimeout(()=>query.focus(),180)}if(e.key==='Escape'&&typing)document.activeElement.blur();});

  if(typeof shelfFiltered==='function'&&typeof renderShelf==='function'&&typeof allBooks!=='undefined'&&typeof pf!=='undefined'&&$('shelfGrid')){
    const pinKey='wereadArchivePinsV1',stateKey='wereadArchiveShelfStateV1';let pins=new Set();
    try{const raw=JSON.parse(localStorage.getItem(pinKey)||'[]');if(Array.isArray(raw))pins=new Set(raw.map(String))}catch(_){}
    if(![...pf.options].some(o=>o.value==='pinned')){const opt=document.createElement('option');opt.value='pinned';opt.textContent='已 Pin';pf.appendChild(opt)}
    const optionHas=(select,value)=>[...select.options].some(o=>o.value===value);
    try{const state=JSON.parse(localStorage.getItem(stateKey)||'{}');if(state&&typeof state==='object'){if(query&&typeof state.query==='string')query.value=state.query;if(typeof cat!=='undefined'&&optionHas(cat,state.category||''))cat.value=state.category||'';if(optionHas(pf,state.progress||''))pf.value=state.progress||'';if(typeof sort!=='undefined'&&optionHas(sort,state.sort||'recent'))sort.value=state.sort||'recent'}}catch(_){}
    const saveShelfState=()=>{try{localStorage.setItem(stateKey,JSON.stringify({query:query?.value||'',category:typeof cat!=='undefined'?cat.value:'',progress:pf.value||'',sort:typeof sort!=='undefined'?sort.value:'recent'}))}catch(_){}};
    [query,typeof cat!=='undefined'?cat:null,pf,typeof sort!=='undefined'?sort:null].filter(Boolean).forEach(el=>el.addEventListener(el===query?'input':'change',saveShelfState));
    const note=document.querySelector('#shelf-explorer .shelf-summary span:last-child');if(note)note.textContent='Pin 与筛选状态仅保存在当前浏览器，不修改微信读书；页面仍不发布原始笔记正文';
    const savePins=()=>{try{localStorage.setItem(pinKey,JSON.stringify([...pins]))}catch(_){}};
    const baseFilter=shelfFiltered;
    shelfFiltered=function(){const rows=baseFilter();return pf.value==='pinned'?rows.filter(b=>pins.has(String(b.bookId))):rows};
    const baseRender=renderShelf;
    renderShelf=function(reset=false){
      baseRender(reset);const rows=shelfFiltered(),shown=rows.slice(0,shelfLimit),grid=$('shelfGrid');
      if(!rows.length){grid.innerHTML='<div class="shelf-empty">没有符合当前条件的书。<button type="button">清除筛选</button></div>';grid.querySelector('button').addEventListener('click',()=>{if(query)query.value='';if(typeof cat!=='undefined')cat.value='';pf.value='';if(typeof sort!=='undefined')sort.value='recent';saveShelfState();renderShelf(true)})}
      else [...grid.children].forEach((card,i)=>{const b=shown[i],cover=card.querySelector?.('.shelf-cover');if(!b||!cover)return;const id=String(b.bookId||'');if(!id)return;const button=document.createElement('button');const on=pins.has(id);button.type='button';button.className='shelf-pin'+(on?' pinned':'');button.textContent=on?'★':'☆';button.title=on?'取消 Pin（仅当前浏览器）':'Pin 到本地阅读队列';button.setAttribute('aria-label',button.title);button.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();if(pins.has(id))pins.delete(id);else pins.add(id);savePins();renderShelf(pf.value==='pinned')});cover.appendChild(button)});
      const count=$('shelfCount');if(count)count.textContent+=` · 已 Pin ${pins.size}`;
    };
    renderShelf(true);
  }
})();
'''


def enhance(template: str) -> str:
    template = template.replace('</style>', CSS + '\n</style>', 1)
    template = template.replace('</script>', JS + '\n</script>', 1)
    return template
