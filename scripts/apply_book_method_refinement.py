#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate and render an evidence-linked 3–7 step method for Book→Skill."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json


def validate(brief: dict) -> dict:
    evidence={str(x.get('evidenceId') or ''):x for x in brief.get('evidence') or [] if x.get('evidenceId')}
    method=brief.get('method') or {}
    steps=[x for x in method.get('steps') or [] if isinstance(x,dict)]
    problems=[]
    if not 3 <= len(steps) <= 7:
        problems.append('method must contain 3–7 steps')
    seen=set();normalized=[]
    for index,step in enumerate(steps,1):
        action=str(step.get('action') or '').strip();why=str(step.get('why') or '').strip();ids=[str(x) for x in step.get('evidenceIds') or [] if str(x)]
        row_problems=[]
        if not action: row_problems.append('missing action')
        if not why: row_problems.append('missing why')
        if not ids: row_problems.append('missing evidenceIds')
        unknown=[x for x in ids if x not in evidence]
        if unknown: row_problems.append('unknown evidenceIds: '+','.join(unknown))
        if len(set(ids)) != len(ids): row_problems.append('duplicate evidenceId in step')
        seen.update(x for x in ids if x in evidence)
        normalized.append({'step':index,'action':action,'why':why,'evidenceIds':ids,'problems':row_problems})
        problems.extend(f'step {index}: {p}' for p in row_problems)
    user_reviews={eid for eid,row in evidence.items() if row.get('kind')=='user_review'}
    if user_reviews and not (seen & user_reviews):
        problems.append('method has user_review evidence available but none is used')
    ready=not problems
    return {
        'version':'1','generatedAt':datetime.now(timezone.utc).isoformat(),
        'book':brief.get('book') or {},'title':str(method.get('title') or '').strip(),'purpose':str(method.get('purpose') or '').strip(),
        'steps':normalized,'ready':ready,'problems':problems,
        'evidenceUsed':[evidence[eid] for eid in sorted(seen) if eid in evidence],
        'guardrails':['Every step is linked to personal exported evidence.','Highlights remain source text, not automatically user beliefs.','No external book knowledge was added by this validator.']
    }


def to_markdown(result: dict) -> str:
    book=result.get('book') or {};lines=[f"# {result.get('title') or '待命名方法'}",'',f"> 来源：《{book.get('title') or ''}》个人阅读证据",'']
    if result.get('purpose'): lines += [result['purpose'],'']
    if not result.get('ready'):
        lines += ['## 尚未通过 refinement gate','']+[f'- {p}' for p in result.get('problems') or []]
        return '\n'.join(lines).rstrip()+'\n'
    evidence={x.get('evidenceId'):x for x in result.get('evidenceUsed') or []}
    for step in result.get('steps') or []:
        lines += [f"## {step['step']}. {step['action']}",'',step['why'],'','证据：']
        for eid in step.get('evidenceIds') or []:
            row=evidence.get(eid) or {};kind='我的想法' if row.get('kind')=='user_review' else '我的划线'
            lines.append(f"- `{eid}` · {kind} · {row.get('chapter') or '未标章节'}")
        lines.append('')
    lines += ['## 证据边界','', '- 这是基于个人笔记提炼的方法，不等于完整书籍内容。','- 证据不足的步骤不应靠模型常识补写。']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--markdown',type=Path,default=None);a=p.parse_args();brief=json.loads(a.input.read_text(encoding='utf-8'));result=validate(brief);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');md=a.markdown or a.output.with_suffix('.md');md.write_text(to_markdown(result),encoding='utf-8');print(f"book-method-refinement: {a.output} | ready={result['ready']} steps={len(result['steps'])} markdown={md}")
if __name__=='__main__':main()
