#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare a 3–7 step method-refinement brief from one book's personal evidence.

This does not invent a method. It creates stable evidence IDs and empty method
slots that a human or semantic model must fill. Finalization is handled by
`apply_book_method_refinement.py`, which rejects steps without evidence links.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
import book_to_skill


def evidence_id(book_id: str, item: dict) -> str:
    raw='\0'.join([str(book_id),str(item.get('kind') or ''),str(item.get('createTime') or 0),str(item.get('chapter') or ''),str(item.get('text') or '')]).encode('utf-8')
    return 'be-'+hashlib.sha256(raw).hexdigest()[:16]


def build(context: dict, *, book_id: str|None=None, title: str|None=None, max_items: int=80) -> dict:
    book=book_to_skill.choose_book(context,book_id=book_id,title=title)
    items=[]
    for item in book_to_skill.evidence_items(book,max_items=max_items):
        row=dict(item);row['evidenceId']=evidence_id(str(book.get('bookId') or ''),row);items.append(row)
    chapters={}
    for row in items:
        chapters.setdefault(row.get('chapter') or '未标章节',[]).append(row['evidenceId'])
    return {
        'version':'1','generatedAt':datetime.now(timezone.utc).isoformat(),
        'book':{'bookId':str(book.get('bookId') or ''),'title':str(book.get('title') or ''),'author':str(book.get('author') or '')},
        'evidence':items,'chapterEvidence':chapters,
        'method':{'title':'','purpose':'','steps':[]},
        'contract':{
            'minSteps':3,'maxSteps':7,'everyStepRequiresEvidence':True,
            'preferUserReviewEvidence':True,'noExternalBookKnowledge':True,
            'ready':False,
        },
        'instructions':[
            'Fill 3–7 executable steps; do not summarize the whole book.',
            'Each step needs action, why, and at least one evidenceId from this brief.',
            'Prefer user_review evidence when available; highlights are source text, not the user’s belief.',
            'If the evidence does not support an executable method, leave the brief unfinished rather than inventing one.',
        ]
    }


def main():
    p=argparse.ArgumentParser();p.add_argument('--context',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--book-id');g.add_argument('--title');p.add_argument('--max-items',type=int,default=80);p.add_argument('--output',type=Path,required=True);a=p.parse_args();ctx=json.loads(a.context.read_text(encoding='utf-8'));result=build(ctx,book_id=a.book_id,title=a.title,max_items=max(1,a.max_items));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(f"book-method-brief: {a.output} | evidence={len(result['evidence'])} ready=false")
if __name__=='__main__':main()
