#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final presentation polish for the assembled WeRead Pages artifact.

This layer changes presentation only:
- annual summary is absorbed by the interactive year lens and hidden externally;
- 24h clock + weekday rhythm share one row;
- the clock face is compact so it does not over-height the paired weekday card;
- clock Top 3 uses fixed rank / hour / duration columns and stays inside the card;
- seasonality spans the full row so all 12 months stay on one line;
- category migration sits directly below reading focus migration;
- empty official-preference placeholders and noisy title suffixes are cleaned;
- quote action buttons keep identical backgrounds while only dice glyphs differ.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

CSS = r'''
/* Annual summary now lives inside #year-lens as the Total view. */
#annual-summary{display:none!important}
#medals{grid-column:span 12!important}
/* Rhythm chapter: clock + weekday together, seasonality full width beneath. */
#clock,#weekday{grid-column:span 6!important}
#clock .clock-wrap{grid-template-columns:minmax(210px,300px) minmax(160px,1fr);gap:16px;align-items:center}
#clock .clock-svg{width:100%;max-width:288px;margin:auto}
#clock .clock-wrap>div:last-child{min-width:0;min-height:288px;display:flex;flex-direction:column;justify-content:center}
#clock .clock-wrap>div:last-child>.subtle{margin:0 0 12px;line-height:1.65}
#season{grid-column:span 12!important;overflow-x:auto}
#season .season-grid{grid-template-columns:repeat(12,minmax(54px,1fr));gap:8px;row-gap:0;min-height:168px;min-width:720px}
#season .rhythm-bar-wrap{height:100px}
#season .rhythm-label,#season .rhythm-value{font-size:10px}
/* Knowledge chapter: reading focus migration first, category migration directly below. */
#shift,#focus{grid-column:span 12!important}
#shift .shift-card{grid-template-columns:74px minmax(0,1fr);gap:12px;padding:13px}
#shift .shift-year{font-size:22px}
#focus .focus-list{gap:7px}
#focus .focus-row{grid-template-columns:64px 1fr;gap:10px;padding:9px 0}
#focus .focus-year{font-size:18px}
#focus .chips{gap:5px}
#focus .chip{padding:5px 7px;font-size:10px}
/* Compact clock peak ranking: fixed rank / hour / duration columns. */
#clockPeak.clock-peak-list{display:grid;grid-template-columns:1fr;gap:7px}
#clockPeak.clock-peak-list .deep-card{min-width:0;min-height:0;padding:8px 10px;display:grid;grid-template-columns:26px 54px minmax(44px,1fr);align-items:center;gap:8px;border-radius:12px}
.clock-peak-rank{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:color-mix(in srgb,var(--accent3) 15%,var(--paper));color:var(--accent);font-size:10px;font-weight:800}
#clockPeak.clock-peak-list .deep-card b{margin:0;font-size:13px;white-space:nowrap;font-variant-numeric:tabular-nums}
#clockPeak.clock-peak-list .deep-card p{margin:0;color:var(--muted);font-size:11px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.pref-book.no-cover,.year-book-card.no-cover{padding-top:13px}.pref-book.no-cover .pref-book-cover,.year-book-card.no-cover .year-book-cover{display:none}.pref-book-grid.is-empty,.year-book-strip.is-empty{display:none!important}
@media(max-width:1100px){#clock .clock-wrap{grid-template-columns:minmax(190px,260px) minmax(150px,1fr);gap:12px}#clock .clock-svg{max-width:250px}#clock .clock-wrap>div:last-child{min-height:250px}}
@media(max-width:900px){#clock,#weekday,#medals,#shift,#focus{grid-column:span 12!important}#clock .clock-wrap{grid-template-columns:minmax(220px,300px) minmax(180px,1fr);gap:18px}#clock .clock-svg{max-width:288px}#clock .clock-wrap>div:last-child{min-height:288px}#season{grid-column:span 12!important}.year-overview-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){#clock .clock-wrap{grid-template-columns:1fr}#clock .clock-svg{max-width:270px}#clock .clock-wrap>div:last-child{min-height:0}#season .season-grid{min-width:680px}.year-overview-grid{grid-template-columns:1fr 1fr}}
'''

JS = r'''
(()=>{
  function cleanTopTitle(raw){let s=String(raw||'').trim(),prev='';const tail=/\s*(?:（[^（）]{1,60}）|\([^()]{1,60}\)|【[^【】]{1,60}】|\[[^\[\]]{1,60}\])\s*$/;while(s&&s!==prev){prev=s;s=s.replace(tail,'').trim()}return s||String(raw||'').trim()}
  document.querySelectorAll('#longest tr td:first-child').forEach(td=>{const full=td.textContent.trim(),short=cleanTopTitle(full);if(short&&short!==full){td.title=full;td.textContent=short}});

  function cleanPreferenceGrid(id,cardSelector,titleSelector){const grid=document.getElementById(id);if(!grid)return;const cards=[...grid.querySelectorAll(cardSelector)];cards.forEach(card=>{const title=card.querySelector(titleSelector)?.textContent?.trim()||'';if(!title||title==='—'||title==='未命名'){card.remove();return}const cover=card.querySelector('.pref-book-cover,.year-book-cover');if(cover&&!cover.querySelector('img'))card.classList.add('no-cover')});const valid=grid.querySelectorAll(cardSelector).length>0;grid.classList.toggle('is-empty',!valid);const head=grid.previousElementSibling;if(head?.classList?.contains('title'))head.style.display=valid?'':'none';if(!valid&&grid.textContent.trim())grid.textContent=''}
  const cleanOfficial=()=>cleanPreferenceGrid('preferBooks','.pref-book','b');
  const cleanYear=()=>cleanPreferenceGrid('yearBooks','.year-book-card','b');
  cleanOfficial();cleanYear();
  const officialGrid=document.getElementById('preferBooks'),yearGrid=document.getElementById('yearBooks');
  if(officialGrid)new MutationObserver(()=>cleanOfficial()).observe(officialGrid,{childList:true,subtree:true});
  if(yearGrid)new MutationObserver(()=>cleanYear()).observe(yearGrid,{childList:true,subtree:true});

  // Keep category migration immediately after reading focus migration in the same chapter.
  const shift=document.getElementById('shift'),focus=document.getElementById('focus');
  if(shift&&focus&&shift.nextElementSibling!==focus)shift.insertAdjacentElement('afterend',focus);

  const peak=document.getElementById('clockPeak');
  if(peak){const cards=[...peak.querySelectorAll('.deep-card')];if(cards.length){peak.classList.add('clock-peak-list');cards.forEach((card,i)=>{const time=card.querySelector('b')?.textContent?.trim()||'—',hours=card.querySelector('p')?.textContent?.trim()||'';card.innerHTML=`<span class="clock-peak-rank">${i+1}</span><b>${time}</b><p>${hours}</p>`})}}

  const randomDice=document.querySelector('#publicQuoteRandom .dice'),resampleDice=document.querySelector('#publicQuoteResample .dice');
  if(randomDice)randomDice.textContent='⚄';
  if(resampleDice)resampleDice.textContent='⚅';
})();
'''


def polish(site_dir: Path = SITE) -> None:
    path = site_dir / "index.html"
    if not path.exists():
        raise SystemExit(f"ERROR: missing {path}; build Pages first")
    page = path.read_text(encoding="utf-8")
    marker = "clock-peak-list"
    if marker not in page:
        page = page.replace("</style>", CSS + "\n</style>", 1)
        page = page.replace("</script>", JS + "\n</script>", 1)
        path.write_text(page, encoding="utf-8")
    print("Pages polish: compact clock face, aligned peak ranking, annual/rhythm/focus layout")


if __name__ == "__main__":
    polish()
