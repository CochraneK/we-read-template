#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare an auditable semantic-review brief for verified WeRead candidates.

The script does not infer schools/paradigms from metadata. It packages official
catalog evidence (intro/category/publisher) together with explicit annotation
slots. A human or semantic model can fill those slots, after which
`apply_candidate_semantics.py` validates completeness before promotion to a
final Advisor recommendation or Reading Path stage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

AXES = ("school_or_viewpoint", "era_or_paradigm", "abstraction_level", "adjacent_discipline")
STAGES = ("intro", "framework", "frontier")


def candidate_rows(payload: dict, mode: str) -> list[dict]:
    if mode == "advisor":
        rows = payload.get("shortlist") or payload.get("items") or []
    else:
        rows = payload.get("items") or payload.get("candidates") or []
    return [x for x in rows if isinstance(x, dict)]


def build(payload: dict, *, mode: str, topic: str = "") -> dict:
    if mode not in {"advisor", "path"}:
        raise ValueError("mode must be advisor or path")
    topic = str(topic or payload.get("topic") or "").strip()
    items = []
    for row in candidate_rows(payload, mode):
        items.append({
            "bookId": str(row.get("bookId") or ""),
            "title": str(row.get("title") or ""),
            "author": str(row.get("author") or ""),
            "category": str(row.get("category") or ""),
            "publisher": str(row.get("publisher") or ""),
            "intro": str(row.get("intro") or ""),
            "deepLink": str(row.get("deepLink") or ""),
            "rating": row.get("rating"),
            "ratingCount": row.get("ratingCount"),
            "verifiedAvailable": bool(row.get("verifiedAvailable")),
            "alreadyRead": bool(row.get("alreadyRead")),
            "shelvedUnengaged": bool(row.get("shelvedUnengaged")),
            "semanticAnnotation": {
                axis: {"value": "", "evidence": "", "confidence": 0.0}
                for axis in AXES
            },
            "conceptualFit": {"value": "", "evidence": "", "confidence": 0.0},
            "stage": "" if mode == "path" else None,
            "stageEvidence": "" if mode == "path" else None,
        })
    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "topic": topic,
        "requiredAxes": list(AXES),
        "allowedStages": list(STAGES) if mode == "path" else [],
        "items": items,
        "ready": False,
        "instructions": [
            "Use official intro/category/publisher only as evidence, not as automatic truth about school/paradigm.",
            "Every required axis needs both a value and a concrete evidence note.",
            "conceptualFit must explain why this candidate fills a gap relative to the user's existing reading evidence.",
            "For Reading Path, stage must be intro/framework/frontier and stageEvidence must explain the pedagogical role.",
            "Low-confidence or ambiguous candidates should stay unpromoted instead of being forced into a recommendation.",
        ],
    }


def main():
    p=argparse.ArgumentParser(description="Prepare semantic-review brief for verified WeRead candidates")
    p.add_argument("--input",type=Path,required=True);p.add_argument("--mode",choices=["advisor","path"],required=True);p.add_argument("--topic",default="");p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    payload=json.loads(a.input.read_text(encoding="utf-8"));result=build(payload,mode=a.mode,topic=a.topic);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"semantic-brief: {a.output} | mode={a.mode} candidates={len(result['items'])} ready=false")

if __name__=="__main__":main()
