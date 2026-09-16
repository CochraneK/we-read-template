#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a conservative advisor shortlist from live verified candidates.

This is not the final huashu recommendation layer: it ranks only catalog-verified,
not-already-read books and explicitly keeps semantic knowledge-gap enrichment as
a remaining gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import re


def norm(s):
    return re.sub(r"\s+", "", str(s or "").lower())


def topic_evidence(advisor: dict, topic: str) -> dict:
    terms=[x for x in re.split(r"[,，、/|;；\s]+", str(topic or "")) if x]
    books=[]
    bands=((advisor.get("facts") or {}).get("depthBands") or {})
    for key in ("deep20Plus","medium10To19","light3To9","glance1To2"):
        for b in bands.get(key) or []:
            hay=norm(" ".join([str(b.get("title") or ""),str(b.get("author") or ""),str(b.get("category") or "")]))
            if terms and any(norm(t) in hay for t in terms):
                row=dict(b);row["depthBand"]=key;books.append(row)
    books.sort(key=lambda x:-int(x.get("noteCount") or 0))
    cats={}
    for row in (advisor.get("facts") or {}).get("categories") or []:
        if any(norm(t) in norm(row.get("category")) for t in terms):
            cats[row.get("category")]=row
    return {"matchedBooks":books[:20],"matchedCategories":list(cats.values())[:10]}


def build(advisor: dict, verified: dict, topic: str, limit: int = 5) -> dict:
    eligible=[dict(x) for x in (verified.get("items") or []) if x.get("verifiedAvailable") and not x.get("alreadyRead")]
    eligible.sort(key=lambda x:(0 if x.get("recommendationEligible") else 1,-int(x.get("rating") or 0),-int(x.get("ratingCount") or 0),int(x.get("searchIdx") or 0)))
    selected=[]
    for row in eligible[:max(1,limit)]:
        reasons=["微信读书实时目录已验证可用","当前本地阅读证据未显示已深读"]
        if row.get("shelvedUnengaged"):
            reasons.append("已在书架但尚未形成笔记，可视为已有兴趣未转化为投入")
        if row.get("rating"):
            reasons.append(f"平台评分 {row.get('rating')}/100（仅作候选排序信号）")
        row["evidenceBoundedReasons"]=reasons
        selected.append(row)
    return {
        "version":"1","generatedAt":datetime.now(timezone.utc).isoformat(),"topic":topic,
        "readingEvidence":topic_evidence(advisor,topic),"shortlist":selected,
        "readyForShortlist":bool(selected),"readyForFinalRecommendation":False,
        "remainingGate":{
            "requiredAxes":["school_or_viewpoint","era_or_paradigm","abstraction_level","adjacent_discipline"],
            "message":"Use content/book enrichment to decide which verified candidate truly fills a knowledge gap before calling it a final recommendation."
        },
        "guardrails":["Catalog availability and ratings do not prove conceptual fit.","Do not turn metadata similarity into a school/paradigm claim.","Already-read books are excluded from the new-book shortlist."],
    }


def main():
    p=argparse.ArgumentParser();p.add_argument("--advisor",type=Path,required=True);p.add_argument("--verified",type=Path,required=True);p.add_argument("--topic",required=True);p.add_argument("--limit",type=int,default=5);p.add_argument("--output",type=Path,required=True);a=p.parse_args();advisor=json.loads(a.advisor.read_text(encoding="utf-8"));verified=json.loads(a.verified.read_text(encoding="utf-8"));result=build(advisor,verified,a.topic.strip(),max(1,min(a.limit,10)));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"advisor-shortlist: {a.output} | shortlist={len(result['shortlist'])} final=false")

if __name__=="__main__": main()
