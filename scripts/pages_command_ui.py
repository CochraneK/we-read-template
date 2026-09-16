#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keyboard command palette for the WeRead personal archive.

The palette searches only already-published chapter labels and bookshelf metadata.
It performs no network requests and never indexes raw marks/reviews.
"""

import pages_queue_io_ui

CSS = r'''
.command-trigger{display:inline-flex;align-items:center;gap:5px}.command-trigger kbd{font:inherit;font-size:9px;border:1px solid color-mix(in srgb,var(--line) 75%,transparent);border-bottom-width:2px;border-radius:5px;padding:1px 4px}.command-backdrop{position:fixed;inset:0;background:rgba(20,18,15,.38);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);z-index:300;display:grid;place-items:start center;padding:10vh 16px 24px}.command-backdrop[hidden]{display:none}.command-panel{width:min(680px,100%);max-height:min(72vh,720px);display:grid;grid-template-rows:auto minmax(0,1fr);background:var(--paper);border:1px solid var(--line);border-radius:22px;box-shadow:0 24px 80px rgba(20,16,12,.22);overflow:hidden}.command-input-wrap{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:14px 16px;border-bottom:1px solid var(--line)}.command-icon{color:var(--muted);font-size:17px}.command-input{width:100%;border:0;outline:0;background:transparent;color:var(--ink);font:inherit;font-size:16px}.command-hint{font-size:9px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 5px}.command-results{overflow:auto;padding:8px}.command-group{padding:7px 9px 4px;color:var(--muted);font-size:9px;letter-spacing:.1em;text-transform:uppercase}.command-row{width:100%;display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;border:0;background:transparent;color:var(--ink);text-align:left;padding:9px 10px;border-radius:12px;font:inherit;cursor:pointer}.command-row:hover,.command-row.active{background:color-mix(in srgb,var(--accent2) 10%,var(--line))}.command-symbol{width:30px;height:30px;border:1px solid var(--line);border-radius:9px;display:grid;place-items:center;color:var(--muted);font-size:11px}.command-main{min-width:0}.command-main b{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.command-main small{display:block;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}.command-kind{color:var(--muted);font-size:9px}.command-empty{padding:32px 16px;text-align:center;color:var(--muted);font-size:12px}
@media(max-width:560px){.command-backdrop{padding:6vh 10px 14px}.command-panel{border-radius:18px;max-height:82vh}.command-input-wrap{padding:12px}.command-input{font-size:16px}.command-kind{display:none}}
'''

JS = r'''
(()=>{
  const nav=document.querySelector('.nav');
  if(!nav||document.getElementById('archiveCommand'))return;
  const trigger=document.createElement('button');
  trigger.id='commandTrigger';trigger.type='button';trigger.className='nav-control command-trigger';trigger.title='搜索章节或书架';
  trigger.innerHTML='<span>搜索</span><kbd>⌘K</kbd>';
  const focusToggle=document.getElementById('focusToggle');
  nav.insertBefore(trigger,focusToggle||null);

  const layer=document.createElement('div');layer.id='archiveCommand';layer.className='command-backdrop';layer.hidden=true;
  layer.innerHTML='<div class="command-panel" role="dialog" aria-modal="true" aria-label="阅读档案命令面板"><div class="command-input-wrap"><span class="command-icon">⌕</span><input class="command-input" id="commandInput" type="search" autocomplete="off" placeholder="搜索章节、书名、作者或类别…"><span class="command-hint">ESC</span></div><div class="command-results" id="commandResults"></div></div>';
  document.body.appendChild(layer);
  const input=document.getElementById('commandInput'),results=document.getElementById('commandResults');
  const chapterCommands=[
    ['chapter-life','阅读生涯','长期累计、年度透镜与里程碑'],
    ['chapter-rhythm','阅读节律','月度、Heatmap、24 小时与星期节律'],
    ['chapter-investment','偏好与投入','官方偏好、进度与真实投入'],
    ['chapter-knowledge','知识与迁移','关注迁移、知识网络与画像'],
    ['chapter-reflection','回顾与反向阅读','Recall、Blindspot 与 Counter Reading'],
    ['chapter-shelf','完整书架','498 本书搜索、过滤、Pin 队列'],
    ['chapter-boundary','数据边界','覆盖率、隐私与发布范围']
  ].map(x=>({kind:'chapter',id:x[0],title:x[1],meta:x[2]}));
  const books=(typeof E!=='undefined'&&E.bookshelf||[]).map(b=>({kind:'book',id:String(b.bookId||''),title:b.title||'未命名',meta:[b.author,b.category,b.progress==null?'进度未知':b.progress+'%',(b.noteCount||0)+' 条笔记'].filter(Boolean).join(' · '),book:b}));
  let rows=[],active=0,lastFocus=null;
  const norm=s=>String(s||'').toLowerCase().replace(/\s+/g,' ').trim();
  function score(item,query){if(!query)return item.kind==='chapter'?50:0;const title=norm(item.title),meta=norm(item.meta),qv=norm(query);if(title===qv)return 100;if(title.startsWith(qv))return 80;if(title.includes(qv))return 60;if(meta.includes(qv))return 35;const tokens=qv.split(' ').filter(Boolean);return tokens.length&&tokens.every(t=>(title+' '+meta).includes(t))?25:-1}
  function currentRows(){const query=input.value;const chapters=chapterCommands.map(x=>({...x,score:score(x,query)})).filter(x=>x.score>=0);let bookRows=books.map(x=>({...x,score:score(x,query)})).filter(x=>x.score>=0);if(!query)bookRows=[...books].sort((a,b)=>String(b.book.lastRead||'').localeCompare(String(a.book.lastRead||''))).slice(0,8).map(x=>({...x,score:0}));else bookRows.sort((a,b)=>b.score-a.score||(b.book.noteCount||0)-(a.book.noteCount||0)||a.title.localeCompare(b.title,'zh-CN'));return [...chapters.sort((a,b)=>b.score-a.score),...bookRows.slice(0,18)]}
  function render(){rows=currentRows();active=Math.min(active,Math.max(0,rows.length-1));if(!rows.length){results.innerHTML='<div class="command-empty">没有匹配的章节或书。</div>';return}let html='',lastKind='';rows.forEach((r,i)=>{if(r.kind!==lastKind){lastKind=r.kind;html+=`<div class="command-group">${r.kind==='chapter'?'章节':'书架'}</div>`}html+=`<button type="button" class="command-row ${i===active?'active':''}" data-index="${i}"><span class="command-symbol">${r.kind==='chapter'?'§':'书'}</span><span class="command-main"><b>${esc(r.title)}</b><small>${esc(r.meta)}</small></span><span class="command-kind">${r.kind==='chapter'?'跳转':'在书架中查看'}</span></button>`});results.innerHTML=html;results.querySelectorAll('.command-row').forEach(btn=>btn.addEventListener('click',()=>activate(+btn.dataset.index)));results.querySelector('.command-row.active')?.scrollIntoView({block:'nearest'})}
  function close(){layer.hidden=true;input.value='';active=0;document.body.style.overflow='';lastFocus?.focus?.()}
  function open(){lastFocus=document.activeElement;layer.hidden=false;document.body.style.overflow='hidden';input.value='';active=0;render();setTimeout(()=>input.focus(),0)}
  function activate(index){const item=rows[index];if(!item)return;close();if(item.kind==='chapter'){document.getElementById(item.id)?.scrollIntoView({behavior:'smooth',block:'start'});return}const shelf=document.getElementById('chapter-shelf');shelf?.scrollIntoView({behavior:'smooth',block:'start'});if(typeof q!=='undefined'&&q){q.value=item.title;if(typeof cat!=='undefined')cat.value='';if(typeof pf!=='undefined')pf.value='';if(typeof sort!=='undefined')sort.value='recent';q.dispatchEvent(new Event('input',{bubbles:true}));if(typeof renderShelf==='function')renderShelf(true);setTimeout(()=>q.focus(),180)}}
  trigger.addEventListener('click',open);layer.addEventListener('click',e=>{if(e.target===layer)close()});input.addEventListener('input',()=>{active=0;render()});
  input.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();active=Math.min(rows.length-1,active+1);render()}else if(e.key==='ArrowUp'){e.preventDefault();active=Math.max(0,active-1);render()}else if(e.key==='Enter'){e.preventDefault();activate(active)}else if(e.key==='Escape'){e.preventDefault();close()}});
  addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();layer.hidden?open():close()}else if(e.key==='Escape'&&!layer.hidden){e.preventDefault();close()}});
})();
'''


def enhance(template: str) -> str:
    template = template.replace('</style>', CSS + '\n</style>', 1)
    template = template.replace('</script>', JS + '\n</script>', 1)
    return pages_queue_io_ui.enhance(template)
