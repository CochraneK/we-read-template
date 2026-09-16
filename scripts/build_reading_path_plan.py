#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finalize a staged reading path from verified, stage-labelled WeRead candidates.

This script does not infer stage semantics. Candidates must already carry an
explicit `stage` (intro/framework/frontier) and live verification status. It then
checks the huashu contract, excludes already-read books from the new-reading load,
and computes time estimates when wordCount is available.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

STAGES=("intro","framework","frontier")


def hours(word_count, wpm=300):
    try:
        words=int(word_count or 0)
    except (TypeError,ValueError):
        return None
    return round(words/max(1,wpm)/60,1) if words>0 else None


def build(path_context: dict, candidates: dict, confirmed_level: str) -> dict:
    allowed=set((path_context.get("levelAssessment") or {}).get("allowedOverrides") or [])
    if confirmed_level not in allowed:
        raise ValueError(f"confirmed_level must be one of {sorted(allowed)}")
    rows=[dict(x) for x in (candidates.get("items") or []) if isinstance(x,dict)]
    by_stage={s:[] for s in STAGES};unassigned=[]
    for row in rows:
        stage=str(row.get("stage") or "")
        if stage not in by_stage:
            unassigned.append(row);continue
        if not row.get("verifiedAgainstCatalog") or not row.get("verifiedAvailable"):
            continue
        row["estimatedHoursAt300Wpm"]=hours(row.get("wordCount"),300)
        row["planStatus"]="skip_already_read" if row.get("alreadyRead") else "candidate"
        by_stage[stage].append(row)
    for stage in STAGES:
        by_stage[stage].sort(key=lambda x:(0 if x.get("recommendationEligible") else 1,-int(x.get("rating") or 0),-int(x.get("ratingCount") or 0),int(x.get("searchIdx") or 0)))
    selected={};alternates={};deficits={}
    for stage in STAGES:
        fresh=[x for x in by_stage[stage] if not x.get("alreadyRead")]
        selected[stage]=fresh[:2]
        alternates[stage]=fresh[2:5]
        if len(selected[stage])<2:
            deficits[stage]=2-len(selected[stage])
    flat=[x for s in STAGES for x in selected[s]]
    word_known=sum(1 for x in flat if x.get("estimatedHoursAt300Wpm") is not None)
    total_hours=round(sum(x.get("estimatedHoursAt300Wpm") or 0 for x in flat),1) if flat else 0
    stage_contract={x.get("id"):x for x in (path_context.get("pathContract") or {}).get("stages") or []}
    ready=not deficits and len(flat)==6
    minimum=[]
    if selected["intro"]:
        minimum.append(selected["intro"][0])
    bridge=(selected["framework"] or selected["frontier"])
    if bridge:
        minimum.append(bridge[0])
    return {
        "version":"1","generatedAt":datetime.now(timezone.utc).isoformat(),"topic":path_context.get("topic"),"confirmedLevel":confirmed_level,
        "ready":ready,"deficits":deficits,"unassignedCount":len(unassigned),
        "stages":[{
            "id":s,"label":stage_contract.get(s,{}).get("label",s),"purpose":stage_contract.get(s,{}).get("purpose",""),
            "feynmanCheckpoint":stage_contract.get(s,{}).get("feynmanCheckpoint",""),"selected":selected[s],"alternates":alternates[s],
            "alreadyReadKeptAsContext":[x for x in by_stage[s] if x.get("alreadyRead")][:5],
        } for s in STAGES],
        "minimumVersion":minimum,
        "timeEstimate":{"wordsPerMinute":300,"booksSelected":len(flat),"booksWithWordCount":word_known,"estimatedHoursKnownBooks":total_hours,"complete":word_known==len(flat)},
        "contract":{"requiresExactlySixFreshBooks":True,"twoPerStage":True,"catalogMustBeVerified":True,"stageSemanticsMustBeConfirmedUpstream":True},
        "guardrails":["Stage labels are accepted as upstream decisions; this script does not infer them.","Already-read books remain visible as context but do not count toward the six new books.","Time estimates are omitted for books whose official wordCount is unavailable."],
    }


def main():
    p=argparse.ArgumentParser();p.add_argument("--path-context",type=Path,required=True);p.add_argument("--candidates",type=Path,required=True);p.add_argument("--confirmed-level",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();ctx=json.loads(a.path_context.read_text(encoding="utf-8"));cand=json.loads(a.candidates.read_text(encoding="utf-8"));result=build(ctx,cand,a.confirmed_level);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"reading-path-plan: {a.output} | ready={result['ready']} deficits={result['deficits']}")

if __name__=="__main__": main()
