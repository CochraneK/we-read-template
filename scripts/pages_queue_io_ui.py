#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import/export controls for the browser-local pinned reading queue.

Exports only bookshelf metadata for pinned ids. Imports validate ids against the
already-published bookshelf and merge them into localStorage. No network request
or WeRead write API is used.
"""

import pages_theme_ui

CSS = r'''
.shelf-local-actions{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0 14px}.shelf-local-btn{border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:7px 10px;font:inherit;font-size:10px;cursor:pointer}.shelf-local-btn:hover{border-color:var(--accent2)}.shelf-local-btn:disabled{opacity:.45;cursor:not-allowed}.shelf-local-status{align-self:center;color:var(--muted);font-size:10px}.shelf-import-input{display:none}
'''

JS = r'''
(()=>{
  const explorer=document.getElementById('shelf-explorer');
  if(!explorer||document.getElementById('shelfLocalActions')||typeof E==='undefined')return;
  const books=E.bookshelf||[],byId=new Map(books.map(b=>[String(b.bookId||''),b]).filter(([id])=>id));
  const pinKey='wereadArchivePinsV1';
  const title=explorer.querySelector('.title');if(!title)return;
  const box=document.createElement('div');box.id='shelfLocalActions';box.className='shelf-local-actions';
  box.innerHTML='<button type="button" class="shelf-local-btn" id="exportPins">导出 Pin JSON</button><button type="button" class="shelf-local-btn" id="importPins">导入并合并</button><input class="shelf-import-input" id="pinImportFile" type="file" accept="application/json,.json"><span class="shelf-local-status" id="pinIoStatus">仅本地浏览器状态</span>';
  title.insertAdjacentElement('afterend',box);
  const exportBtn=document.getElementById('exportPins'),importBtn=document.getElementById('importPins'),file=document.getElementById('pinImportFile'),status=document.getElementById('pinIoStatus');
  function currentPins(){try{const raw=JSON.parse(localStorage.getItem(pinKey)||'[]');return Array.isArray(raw)?[...new Set(raw.map(String).filter(id=>byId.has(id)))]:[]}catch(_){return []}}
  function refreshLabel(){const n=currentPins().length;exportBtn.disabled=!n;status.textContent=`当前已 Pin ${n} 本 · 导入/导出不修改微信读书`}
  function exportPins(){const ids=currentPins(),rows=ids.map(id=>byId.get(id)).filter(Boolean).map(b=>({bookId:String(b.bookId||''),title:b.title||'',author:b.author||'',category:b.category||''}));const payload={version:1,kind:'we-read-local-pins',exportedAt:new Date().toISOString(),count:rows.length,books:rows};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a'),stamp=new Date().toISOString().slice(0,10);a.href=url;a.download=`we-read-pins-${stamp}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);status.textContent=`已导出 ${rows.length} 本本地 Pin`}
  async function importPins(selected){try{const text=await selected.text(),payload=JSON.parse(text),incoming=Array.isArray(payload)?payload:(payload&&Array.isArray(payload.books)?payload.books:[]);const ids=incoming.map(x=>typeof x==='string'?x:String((x||{}).bookId||'')).filter(id=>byId.has(id)),merged=[...new Set([...currentPins(),...ids])];localStorage.setItem(pinKey,JSON.stringify(merged));status.textContent=`已合并 ${ids.length} 个有效条目，共 ${merged.length} 本；正在刷新…`;setTimeout(()=>location.reload(),350)}catch(_){status.textContent='导入失败：请选择本页面导出的 JSON 或含 bookId 的数组';file.value=''}}
  exportBtn.addEventListener('click',exportPins);importBtn.addEventListener('click',()=>file.click());file.addEventListener('change',()=>{const selected=file.files&&file.files[0];if(selected)importPins(selected)});refreshLabel();
})();
'''


def enhance(template: str) -> str:
    template = template.replace('</style>', CSS + '\n</style>', 1)
    template = template.replace('</script>', JS + '\n</script>', 1)
    return pages_theme_ui.enhance(template)
