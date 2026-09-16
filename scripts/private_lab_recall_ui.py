#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Augment Private Reading Lab HTML with browser-local spaced recall history.

No network calls. Review history and the user's recall answers are stored only in
localStorage and can be exported/imported as JSON. Stable evidenceId values keep
history attached to the same evidence after queue rebuilds.
"""
from __future__ import annotations

CSS = r'''
.recall-history-tools{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.recall-history-tools button{border:1px solid var(--line);border-radius:999px;background:var(--paper2);padding:6px 9px;color:var(--ink);font-size:11px}.recall-grade{display:none;gap:6px;flex-wrap:wrap;margin-top:10px}.recall-card.revealed .recall-grade{display:flex}.recall-grade button{border:1px solid var(--line);border-radius:999px;background:var(--paper);padding:5px 8px}.recall-grade button[data-grade="again"]{color:var(--danger)}.recall-grade button[data-grade="good"],.recall-grade button[data-grade="easy"]{color:var(--accent2)}.recall-schedule{font-size:10px;color:var(--muted);margin-top:6px}.recall-card.not-due.recall-due-only{display:none}.recall-history-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0}.recall-history-summary div{border:1px solid var(--line);border-radius:12px;padding:9px;background:var(--paper2)}.recall-history-summary span{display:block;color:var(--muted);font-size:9px}.recall-history-summary b{font-size:16px}.recall-hidden-input{display:none}.recall-answer{margin-top:10px}.recall-answer textarea{width:100%;min-height:82px;resize:vertical;border:1px solid var(--line);border-radius:12px;padding:9px;background:var(--paper2);color:var(--ink);font:inherit}.recall-answer small,.recall-overlap{display:block;color:var(--muted);font-size:10px;margin-top:5px}.recall-card.revealed .recall-overlap{display:block}.recall-overlap strong{color:var(--accent2)}@media(max-width:580px){.recall-history-summary{grid-template-columns:repeat(2,1fr)}}
'''

HTML = r'''
<section class="panel" id="recall-history" style="margin-top:14px"><div class="section-head"><div><h2>Recall 记忆历史</h2><p>先写下“我现在怎么理解”，再展开当时证据；评价“忘了 / 困难 / 记住 / 很熟”后，本浏览器会保存回答并计算 nextReviewAt。</p></div><div class="recall-history-tools"><button type="button" id="toggleDue">只看到期</button><button type="button" id="exportRecallHistory">导出历史</button><button type="button" id="importRecallHistory">导入历史</button><input class="recall-hidden-input" id="recallHistoryFile" type="file" accept="application/json"></div></div><div class="recall-history-summary" id="recallHistorySummary"></div><p class="muted" style="font-size:11px">“文字重合”只衡量你当前回答与旧证据的表面词/字重合，不代表理解正确；真正有价值的是隔一段时间后比较自己的解释如何变化。</p></section>
'''

JS = r'''
const RECALL_HISTORY_KEY='wereadPrivateRecallHistoryV1';let recallDueOnly=false;
function readRecallHistory(){try{const x=JSON.parse(localStorage.getItem(RECALL_HISTORY_KEY)||'{}');return x&&typeof x==='object'?x:{}}catch(e){return {}}}
function writeRecallHistory(h){localStorage.setItem(RECALL_HISTORY_KEY,JSON.stringify(h))}
function recallKey(item){return String(item.evidenceId||item.id||'')}
function scheduleRecall(prev,rating,now=Date.now()){
  const day=86400000,p=prev&&typeof prev==='object'?prev:{},oldInt=Math.max(0,+p.intervalDays||0),oldEase=Math.max(1.3,+p.ease||2.3);let streak=Math.max(0,+p.streak||0),ease=oldEase,interval=1;
  if(rating==='again'){streak=0;ease=Math.max(1.3,ease-.2);interval=1}
  else if(rating==='hard'){ease=Math.max(1.3,ease-.05);interval=Math.max(2,Math.round(oldInt?oldInt*1.2:3))}
  else if(rating==='good'){streak+=1;interval=streak===1?3:Math.max(4,Math.round((oldInt||3)*ease))}
  else if(rating==='easy'){streak+=1;ease=Math.min(3.0,ease+.1);interval=Math.max(7,Math.round((oldInt||4)*ease*1.3))}
  return {...p,attempts:(+p.attempts||0)+1,streak,ease:+ease.toFixed(2),intervalDays:interval,lastRating:rating,lastReviewedAt:new Date(now).toISOString(),nextReviewAt:new Date(now+interval*day).toISOString()}
}
function recallTokens(text){const raw=String(text||'').toLowerCase();const latin=raw.match(/[a-z0-9]{2,}/g)||[];const cjk=[...raw].filter(ch=>/[\u3400-\u9fff]/.test(ch));return new Set([...latin,...cjk])}
function lexicalOverlap(answer,evidence){const a=recallTokens(answer),b=recallTokens(evidence);if(!a.size||!b.size)return 0;let hit=0;a.forEach(x=>{if(b.has(x))hit++});return Math.round(100*hit/a.size)}
function answerEntry(answer,item){const text=String(answer||'').trim(),overlap=lexicalOverlap(text,item&&item.text);return {answeredAt:new Date().toISOString(),answer:text,lexicalOverlapPercent:overlap,evidenceKind:item&&item.kind||null}}
function decorateRecallCards(root=document){const history=readRecallHistory(),byId=Object.fromEntries(recalls.map(x=>[recallKey(x),x]));root.querySelectorAll('.recall-card[data-recall]').forEach(card=>{if(card.dataset.recallDecorated)return;card.dataset.recallDecorated='1';const id=card.dataset.recall,item=byId[id],state=history[id]||{},due=!state.nextReviewAt||Date.parse(state.nextReviewAt)<=Date.now();card.classList.toggle('not-due',!due);card.classList.toggle('recall-due-only',recallDueOnly);const answer=document.createElement('div');answer.className='recall-answer';const last=(state.answerHistory||[]).slice(-1)[0];answer.innerHTML=`<textarea data-recall-answer placeholder="先不用看原文：用自己的话写下现在还记得什么……">${esc(last&&last.answer||'')}</textarea><small>回答只保存在本浏览器；评分时写入 Recall 历史。</small><span class="recall-overlap">${last?`上次回答与当时证据的表面文字重合：<strong>${last.lexicalOverlapPercent||0}%</strong>`:''}</span>`;const grade=document.createElement('div');grade.className='recall-grade';grade.innerHTML='<button data-grade="again">忘了</button><button data-grade="hard">困难</button><button data-grade="good">记住</button><button data-grade="easy">很熟</button>';const sched=document.createElement('div');sched.className='recall-schedule';sched.textContent=state.nextReviewAt?`下次：${new Date(state.nextReviewAt).toLocaleDateString()} · 连续 ${state.streak||0}`:'尚未复习';card.appendChild(answer);card.appendChild(grade);card.appendChild(sched)})}
function updateRecallSummary(){const h=readRecallHistory(),states=Object.values(h),due=states.filter(x=>!x.nextReviewAt||Date.parse(x.nextReviewAt)<=Date.now()).length,remembered=states.filter(x=>['good','easy'].includes(x.lastRating)).length;const totalAttempts=states.reduce((s,x)=>s+(+x.attempts||0),0);$('recallHistorySummary').innerHTML=[['已进入历史',states.length],['当前到期',due],['最近记住',remembered],['累计复习',totalAttempts]].map(([k,v])=>`<div><span>${k}</span><b>${v}</b></div>`).join('')}
document.addEventListener('click',e=>{const b=e.target.closest('.recall-grade button[data-grade]');if(!b)return;const card=b.closest('.recall-card'),id=card&&card.dataset.recall;if(!id)return;const item=recalls.find(x=>recallKey(x)===id)||{},answer=card.querySelector('[data-recall-answer]')?.value||'',h=readRecallHistory(),next=scheduleRecall(h[id],b.dataset.grade),history=Array.isArray(next.answerHistory)?next.answerHistory.slice(-19):[];history.push(answerEntry(answer,item));next.answerHistory=history;h[id]=next;writeRecallHistory(h);card.dataset.recallDecorated='';card.querySelectorAll('.recall-answer,.recall-grade,.recall-schedule').forEach(x=>x.remove());decorateRecallCards(card.parentElement||document);updateRecallSummary()});
const recallObserver=new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)decorateRecallCards(n)})));recallObserver.observe(document.body,{childList:true,subtree:true});decorateRecallCards();updateRecallSummary();
$('toggleDue').onclick=()=>{recallDueOnly=!recallDueOnly;$('toggleDue').textContent=recallDueOnly?'显示全部':'只看到期';document.querySelectorAll('.recall-card[data-recall]').forEach(c=>c.classList.toggle('recall-due-only',recallDueOnly))};
$('exportRecallHistory').onclick=()=>{const blob=new Blob([JSON.stringify({version:2,exportedAt:new Date().toISOString(),history:readRecallHistory()},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='weread-recall-history.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
$('importRecallHistory').onclick=()=>$('recallHistoryFile').click();$('recallHistoryFile').onchange=async e=>{const file=e.target.files&&e.target.files[0];if(!file)return;try{const parsed=JSON.parse(await file.text()),incoming=parsed.history||parsed;if(!incoming||typeof incoming!=='object')throw new Error('invalid');const known=new Set(recalls.map(recallKey)),current=readRecallHistory();Object.entries(incoming).forEach(([k,v])=>{if(known.has(k)&&v&&typeof v==='object')current[k]=v});writeRecallHistory(current);document.querySelectorAll('.recall-card[data-recall]').forEach(c=>{c.dataset.recallDecorated='';c.querySelectorAll('.recall-answer,.recall-grade,.recall-schedule').forEach(x=>x.remove())});decorateRecallCards();updateRecallSummary()}catch(err){alert('Recall 历史 JSON 无效。')}finally{e.target.value=''}};
'''


def _repair_base_recall_js(page: str) -> str:
    broken = "x.chapter?'\n\n章节：'+esc(x.chapter):''"
    fixed = "x.chapter?'\\n\\n章节：'+esc(x.chapter):''"
    return page.replace(broken, fixed)


def augment(page: str) -> str:
    page = _repair_base_recall_js(page)
    if 'wereadPrivateRecallHistoryV1' in page:
        return page
    page = page.replace('</style>', CSS + '\n</style>', 1)
    page = page.replace('<section class="panel" id="books"', HTML + '\n<section class="panel" id="books"', 1)
    page = page.replace(
        'function recallCard(x){return `<article class="recall-card">',
        'function recallCard(x){return `<article class="recall-card" data-recall="${esc(x.evidenceId||x.id||\'\')}">',
        1,
    )
    page = page.replace('</script>', '\n' + JS + '\n</script>', 1)
    return page
