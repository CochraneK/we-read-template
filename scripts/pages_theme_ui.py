#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Browser-local theme switcher for the WeRead archive.

Supports system / light / dark. The preference stays in localStorage and only
changes CSS variables; report facts and published data are untouched.
"""

CSS = r'''
html[data-theme="light"]{color-scheme:light;--bg:#f5f1e8;--paper:#fffdf7;--ink:#25231f;--muted:#777166;--line:#dfd7c8;--accent:#b4573f;--accent2:#708b77;--accent3:#c4953c;--heat0:#eee9e1;--heat1:#e9c9a8;--heat2:#d9a06c;--heat3:#c2724b;--heat4:#8d4a31;--shadow:0 18px 50px rgba(54,45,34,.08)}
html[data-theme="dark"]{color-scheme:dark;--bg:#171613;--paper:#211f1b;--ink:#f2ede4;--muted:#a8a095;--line:#3a352d;--accent:#dd7a61;--accent2:#91ab95;--accent3:#ddb25a;--heat0:#302d28;--heat1:#5e4536;--heat2:#8f5d3e;--heat3:#bd704d;--heat4:#e18a64;--shadow:none}
.theme-toggle{display:inline-flex;align-items:center;gap:6px}.theme-toggle .theme-icon{font-size:12px}.theme-toggle .theme-label{font-size:10px}
'''

JS = r'''
(()=>{
  const nav=document.querySelector('.nav');
  if(!nav||document.getElementById('themeToggle'))return;
  const key='wereadArchiveThemeV1',allowed=['system','light','dark'];
  let current='system';
  try{const saved=localStorage.getItem(key);if(allowed.includes(saved))current=saved}catch(_){}
  const labels={system:['◐','系统'],light:['☀','浅色'],dark:['●','深色']};
  const button=document.createElement('button');button.id='themeToggle';button.type='button';button.className='nav-control theme-toggle';
  const focus=document.getElementById('focusToggle');nav.insertBefore(button,focus||null);
  function apply(value,save=true){current=allowed.includes(value)?value:'system';if(current==='system')document.documentElement.removeAttribute('data-theme');else document.documentElement.setAttribute('data-theme',current);const [icon,label]=labels[current];button.innerHTML=`<span class="theme-icon" aria-hidden="true">${icon}</span><span class="theme-label">${label}</span>`;button.title=`主题：${label} · 点击切换`;button.setAttribute('aria-label',button.title);button.dataset.theme=current;if(save){try{localStorage.setItem(key,current)}catch(_){}}}
  function next(){const index=allowed.indexOf(current);apply(allowed[(index+1)%allowed.length])}
  button.addEventListener('click',next);apply(current,false);
  const media=window.matchMedia?.('(prefers-color-scheme: dark)');media?.addEventListener?.('change',()=>{if(current==='system')apply('system',false)});
})();
'''


def enhance(template: str) -> str:
    template = template.replace('</style>', CSS + '\n</style>', 1)
    template = template.replace('</script>', JS + '\n</script>', 1)
    return template
