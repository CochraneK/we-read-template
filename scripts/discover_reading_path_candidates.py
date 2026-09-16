#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover live WeRead candidate pools for each reading-path stage.

Stage-specific query suffixes are only discovery heuristics. Output uses
`stageProposed` and requires explicit stage confirmation before final planning.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))

import verify_weread_candidates as verifier

DEFAULT_SUFFIX={"intro":"入门","framework":"教材 经典","frontier":"前沿 新进展"}


def discover(context: dict, topic: str, *, count: int = 12, queries: dict | None = None) -> dict:
    queries=queries or {}
    items=[]
    searches=[]
    for stage in ("intro","framework","frontier"):
        q=str(queries.get(stage) or f"{topic} {DEFAULT_SUFFIX[stage]}").strip()
        result=verifier.verify_discovery(context,q,count=count)
        searches.append({"stageProposed":stage,"query":q,"returned":len(result["items"]),"hasMore":result.get("hasMore",0)})
        for row in result["items"]:
            if not row.get("verifiedAvailable"):
                continue
            item=dict(row)
            item["stageProposed"]=stage
            item["stageConfirmed"]=False
            item["discoveryQuery"]=q
            items.append(item)
    # Deduplicate same book across heuristic searches while preserving all proposed stages.
    merged={}
    for row in items:
        key=str(row.get("bookId") or f"{row.get('title')}\0{row.get('author')}")
        if key not in merged:
            base=dict(row);base["stageProposals"]=[row["stageProposed"]];merged[key]=base
        elif row["stageProposed"] not in merged[key]["stageProposals"]:
            merged[key]["stageProposals"].append(row["stageProposed"])
    rows=list(merged.values())
    rows.sort(key=lambda x:(0 if x.get("recommendationEligible") else 1,-int(x.get("rating") or 0),-int(x.get("ratingCount") or 0),str(x.get("title") or "")))
    return {
        "version":"1","generatedAt":datetime.now(timezone.utc).isoformat(),"topic":topic,"searches":searches,"items":rows,
        "readyForFinalPlan":False,
        "nextStep":"Confirm one stage for each selected candidate by setting `stage` to intro/framework/frontier, then run verify_weread_candidates.py on that edited candidate file and build_reading_path_plan.py.",
        "guardrails":["Query suffixes are discovery heuristics, not proof that a book belongs to that stage.","Every final path book still needs explicit stage confirmation and current catalog verification."],
    }


def main():
    p=argparse.ArgumentParser();p.add_argument("--context",type=Path,required=True);p.add_argument("--topic",required=True);p.add_argument("--count",type=int,default=12);p.add_argument("--intro-query",default="");p.add_argument("--framework-query",default="");p.add_argument("--frontier-query",default="");p.add_argument("--output",type=Path,required=True);a=p.parse_args();ctx=json.loads(a.context.read_text(encoding="utf-8"));queries={"intro":a.intro_query,"framework":a.framework_query,"frontier":a.frontier_query};result=discover(ctx,a.topic.strip(),count=max(1,min(a.count,30)),queries=queries);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"reading-path-discovery: {a.output} | candidates={len(result['items'])} ready=false")

if __name__=="__main__": main()
