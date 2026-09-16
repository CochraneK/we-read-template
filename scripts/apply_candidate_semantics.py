#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate filled semantic candidate briefs before promotion.

This module is intentionally strict: missing evidence, unsupported stage labels,
or weak confidence leave the candidate unpromoted. It never fills semantic fields
itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

AXES = ("school_or_viewpoint", "era_or_paradigm", "abstraction_level", "adjacent_discipline")
STAGES = ("intro", "framework", "frontier")


def _valid_annotation(row: dict, min_confidence: float) -> tuple[bool, list[str]]:
    problems = []
    annotations = row.get("semanticAnnotation") or {}
    for axis in AXES:
        value = annotations.get(axis) or {}
        if not str(value.get("value") or "").strip():
            problems.append(f"missing:{axis}:value")
        if not str(value.get("evidence") or "").strip():
            problems.append(f"missing:{axis}:evidence")
        try:
            confidence = float(value.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0
        if confidence < min_confidence:
            problems.append(f"low_confidence:{axis}")
    fit = row.get("conceptualFit") or {}
    if not str(fit.get("value") or "").strip():
        problems.append("missing:conceptualFit:value")
    if not str(fit.get("evidence") or "").strip():
        problems.append("missing:conceptualFit:evidence")
    try:
        fit_conf = float(fit.get("confidence") or 0)
    except (TypeError, ValueError):
        fit_conf = 0
    if fit_conf < min_confidence:
        problems.append("low_confidence:conceptualFit")
    return not problems, problems


def apply(brief: dict, *, min_confidence: float = 0.55) -> dict:
    mode = brief.get("mode")
    if mode not in {"advisor", "path"}:
        raise ValueError("brief mode must be advisor or path")
    promoted = []
    rejected = []
    for source in brief.get("items") or []:
        row = dict(source)
        ok, problems = _valid_annotation(row, min_confidence)
        if row.get("alreadyRead"):
            problems.append("already_read")
            ok = False
        if not row.get("verifiedAvailable"):
            problems.append("not_verified_available")
            ok = False
        if mode == "path":
            stage = str(row.get("stage") or "")
            if stage not in STAGES:
                problems.append("missing_or_invalid_stage")
                ok = False
            if not str(row.get("stageEvidence") or "").strip():
                problems.append("missing_stage_evidence")
                ok = False
        row["semanticGatePassed"] = bool(ok)
        row["semanticGateProblems"] = problems
        (promoted if ok else rejected).append(row)
    result = {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "topic": brief.get("topic"),
        "minConfidence": min_confidence,
        "promoted": promoted,
        "items": promoted,
        "rejected": rejected,
        "readyForFinalRecommendation": mode == "advisor" and bool(promoted),
        "readyForPathPlan": mode == "path" and bool(promoted),
        "guardrails": [
            "Semantic fields were supplied upstream; this validator does not invent them.",
            "Every promoted candidate has evidence on all required semantic axes plus conceptual fit.",
            "Reading Path candidates additionally require an explicit pedagogical stage and evidence.",
        ],
    }
    return result


def main():
    p=argparse.ArgumentParser(description="Validate filled candidate semantic annotations")
    p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--min-confidence",type=float,default=.55);a=p.parse_args()
    brief=json.loads(a.input.read_text(encoding="utf-8"));result=apply(brief,min_confidence=max(0,min(1,a.min_confidence)));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"semantic-apply: {a.output} | promoted={len(result['promoted'])} rejected={len(result['rejected'])}")

if __name__=="__main__":main()
