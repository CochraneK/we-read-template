#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an evidence-first context for a staged reading path.

This implements the factual/checkpoint layer of huashu's path workflow. It does
not invent a book list. A topic is matched against the deterministic advisor
facts, a provisional level is suggested, and a three-stage path contract is
emitted for later candidate enrichment and explicit user confirmation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_ADVISOR = DATA / "analysis" / "advisor_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "reading_path_context.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").lower())


def topic_terms(topic: str, keywords: list[str] | None = None) -> list[str]:
    values = [topic, *(keywords or [])]
    terms = []
    for value in values:
        for part in re.split(r"[,，、/|;；\s]+", str(value or "")):
            item = normalize(part)
            if item and item not in terms:
                terms.append(item)
    return terms


def flatten_books(advisor: dict) -> list[dict]:
    bands = ((advisor.get("facts") or {}).get("depthBands") or {})
    ordered_keys = ("deep20Plus", "medium10To19", "light3To9", "glance1To2", "noNotes")
    by_id = {}
    for key in ordered_keys:
        for book in bands.get(key) or []:
            if not isinstance(book, dict):
                continue
            bid = str(book.get("bookId") or "")
            identity = bid or f"{book.get('title','')}\0{book.get('author','')}"
            by_id.setdefault(identity, book)
    return list(by_id.values())


def matches_topic(book: dict, terms: list[str]) -> bool:
    if not terms:
        return False
    haystack = normalize(" ".join([
        str(book.get("title") or ""),
        str(book.get("author") or ""),
        str(book.get("category") or ""),
    ]))
    return any(term in haystack for term in terms)


def suggest_level(relevant: list[dict]) -> tuple[str, str, bool]:
    noted = [b for b in relevant if int(b.get("noteCount") or 0) > 0]
    engaged = [b for b in relevant if int(b.get("noteCount") or 0) >= 5]
    noted_count = len(noted)
    engaged_count = len(engaged)

    # Path.md bases its starting level on evidence of actual topic reading, not
    # merely on books sitting on the shelf. Advanced additionally requires
    # frontier/primary-source evidence that this metadata layer cannot prove.
    if noted_count == 0:
        return (
            "zero",
            f"Found {len(relevant)} topic-matched shelf/archive records, but no topic-matched book has note evidence.",
            False,
        )
    if engaged_count <= 2:
        return (
            "beginner",
            f"Found {noted_count} topic-matched books with note evidence; only {engaged_count} have at least 5 notes.",
            False,
        )
    return (
        "intermediate",
        f"Found {engaged_count} topic-matched books with at least 5 notes. Metadata alone cannot justify an advanced label because frontier/primary-source evidence is still missing.",
        True,
    )


def build_context(advisor: dict, topic: str, *, keywords: list[str] | None = None) -> dict:
    topic = str(topic or "").strip()
    if not topic:
        raise ValueError("topic is required")
    terms = topic_terms(topic, keywords)
    relevant = [b for b in flatten_books(advisor) if matches_topic(b, terms)]
    relevant.sort(key=lambda b: (-int(b.get("noteCount") or 0), -int(b.get("updateTime") or 0), str(b.get("title") or "")))

    level, reason, suggest_advisor = suggest_level(relevant)
    noted = [b for b in relevant if int(b.get("noteCount") or 0) > 0]
    engaged = [b for b in relevant if int(b.get("noteCount") or 0) >= 5]
    already_read = [b for b in relevant if int(b.get("noteCount") or 0) >= 3]

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "topicTerms": terms,
        "privacy": advisor.get("privacy") or {},
        "coverage": advisor.get("coverage") or {},
        "evidence": {
            "matchedBooks": relevant,
            "matchedBookCount": len(relevant),
            "notedBooks": noted,
            "notedBookCount": len(noted),
            "engagedBooks5Plus": engaged,
            "engagedBookCount": len(engaged),
            "alreadyRead3Plus": already_read,
            "alreadyReadCount": len(already_read),
        },
        "levelAssessment": {
            "suggestedLevel": level,
            "reason": reason,
            "requiresUserConfirmation": True,
            "suggestSwitchToAdvisor": suggest_advisor,
            "advancedRequiresContentEvidence": True,
            "allowedOverrides": ["zero", "beginner", "intermediate", "advanced"],
        },
        "pathContract": {
            "readyForBookSelection": False,
            "mustConfirmLevelBeforeSelection": True,
            "targetBookCount": {"min": 6, "max": 8},
            "stages": [
                {
                    "id": "intro",
                    "label": "入门",
                    "purpose": "建立兴趣、基础术语和领域问题意识",
                    "selectionRule": "一线作者的科普或大众版；读得动优先于全面",
                    "targetBooks": {"min": 2, "max": 3},
                    "feynmanCheckpoint": "能用一句话给朋友解释这个领域主要在研究什么吗？",
                },
                {
                    "id": "framework",
                    "label": "进阶",
                    "purpose": "建立主要学派、概念和争议框架",
                    "selectionRule": "代表作、综合性教材或能对照主要观点的作品",
                    "targetBooks": {"min": 2, "max": 3},
                    "feynmanCheckpoint": "能说出这个领域 2–3 个主要学派或观点的差异吗？",
                },
                {
                    "id": "frontier",
                    "label": "前沿",
                    "purpose": "看到当前研究边界、范式变化和未解决问题",
                    "selectionRule": "优先 2020 年后新作、前沿综述或范式转换作品",
                    "targetBooks": {"min": 2, "max": 3},
                    "feynmanCheckpoint": "能列出 2–3 个当下最有争议或尚未解决的问题吗？",
                },
            ],
            "minimumVersionRequired": True,
            "minimumVersionRule": "After candidates are verified, choose one foundation book and one framework/frontier bridge as the smallest useful path.",
            "timeEstimateRule": {
                "wordsPerMinute": 300,
                "requiresBookWordCounts": True,
                "requiresDailyHoursInputOrExplicitDefault": True,
            },
            "availabilityRule": {
                "mustVerifyCurrentWereadAvailability": True,
                "firstStageAllUnavailableIsFailureSignal": True,
                "keepAlreadyReadInPositionButMarkAndSkip": True,
            },
        },
        "nextStep": {
            "action": "confirm_level",
            "message": f"Confirm or override the suggested level '{level}' before selecting books.",
            "afterConfirmation": "Enrich candidate books, verify availability and word counts, then construct the three stages and minimum version.",
        },
        "guardrails": [
            "Topic matching here is deterministic metadata matching, not semantic proof of subject mastery.",
            "A provisional level is only a suggestion; user confirmation is mandatory before path generation.",
            "Do not invent candidate books from this context alone.",
            "Advanced cannot be inferred from note volume alone; it needs frontier or primary-source evidence or an explicit user override.",
            "Intermediate signals should normally offer a switch to Advisor instead of forcing a beginner path.",
            "Every selected book must be checked for current availability and already-read status before final output.",
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Build deterministic WeRead reading-path context.")
    parser.add_argument("--advisor", type=Path, default=DEFAULT_ADVISOR)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keywords", default="", help="Optional comma-separated aliases/keywords for deterministic matching.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.advisor.exists():
        raise SystemExit(f"ERROR: missing {args.advisor}; run build_advisor_context.py first")
    advisor = json.loads(args.advisor.read_text(encoding="utf-8"))
    keywords = [x.strip() for x in re.split(r"[,，、;；]+", args.keywords) if x.strip()]
    result = build_context(advisor, args.topic, keywords=keywords)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    level = result["levelAssessment"]
    print(
        f"reading-path-context: {args.output} | topic={result['topic']} matched={result['evidence']['matchedBookCount']} "
        f"engaged={result['evidence']['engagedBookCount']} level={level['suggestedLevel']} confirm={level['requiresUserConfirmation']}"
    )


if __name__ == "__main__":
    main()
