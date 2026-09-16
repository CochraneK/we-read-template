#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build deterministic facts for a period reading review.

This is the factual layer of huashu's review workflow. It classifies books in a
period, aggregates daily reading time from monthly readTimes, measures note/theme
activity, and exposes narrative candidates. It does not write publishable prose;
platform/tone remains an explicit user-confirmation gate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "visualization_context.json"
DEFAULT_READDATA = DATA / "weread_readdata.json"
DEFAULT_OUTPUT = DATA / "analysis" / "narrative_review_context.json"

PLATFORMS = {
    "moments": {"label": "朋友圈", "length": "200-500", "needsImages": False},
    "wechat": {"label": "公众号", "length": "1500-3000", "needsImages": True},
    "xiaohongshu": {"label": "小红书", "length": "300-800", "needsImages": True},
    "video": {"label": "视频脚本", "length": "800-1500", "needsImages": False},
    "journal": {"label": "个人留存", "length": "unlimited", "needsImages": False},
}


def as_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def ts_day(value: int) -> date | None:
    if not value:
        return None
    try:
        ts = int(value)
        if ts > 10_000_000_000:
            ts //= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def in_period(ts: int, start: date, end: date) -> bool:
    day = ts_day(ts)
    return bool(day and start <= day <= end)


def daily_read_times(readdata: dict) -> dict[date, int]:
    """Merge duplicated monthly daily buckets by taking the maximum per day."""
    result: dict[date, int] = {}
    for period in (readdata.get("monthly") or {}).values():
        if not isinstance(period, dict):
            continue
        for raw_day, raw_seconds in (period.get("readTimes") or {}).items():
            day = ts_day(as_int(raw_day))
            if not day:
                continue
            seconds = max(0, as_int(raw_seconds))
            result[day] = max(result.get(day, 0), seconds)
    return result


def book_note_activity(book: dict, start: date, end: date) -> tuple[int, int, int]:
    marks = 0
    reviews = 0
    latest = 0
    for row in book.get("marks") or []:
        ts = as_int((row or {}).get("createTime"))
        if in_period(ts, start, end):
            marks += 1
            latest = max(latest, ts)
    for row in book.get("reviews") or []:
        ts = as_int((row or {}).get("createTime"))
        if in_period(ts, start, end):
            reviews += 1
            latest = max(latest, ts)
    return marks, reviews, latest


def basic_book(book: dict, period_marks: int, period_reviews: int) -> dict:
    progress = as_float(book.get("progress"))
    return {
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or ""),
        "author": str(book.get("author") or ""),
        "category": str(book.get("category") or "未知").strip() or "未知",
        "progress": progress,
        "noteCount": as_int(book.get("noteCount")),
        "periodMarks": period_marks,
        "periodReviews": period_reviews,
        "periodNotes": period_marks + period_reviews,
        "recordReadingTime": as_int(book.get("recordReadingTime")),
        "finishTime": as_int(book.get("finishTime")),
        "activityTime": as_int(book.get("shelfReadUpdateTime") or book.get("updateTime")),
    }


def classify_book(book: dict, start: date, end: date) -> tuple[str | None, dict | None]:
    marks, reviews, latest_note = book_note_activity(book, start, end)
    row = basic_book(book, marks, reviews)
    activity_ts = row["activityTime"] or latest_note
    activity_in_period = in_period(activity_ts, start, end)
    finish_in_period = in_period(row["finishTime"], start, end)
    has_period_evidence = activity_in_period or finish_in_period or (marks + reviews > 0)
    if not has_period_evidence:
        return None, None

    finish_day = ts_day(row["finishTime"])
    progress = row["progress"]
    if finish_day and finish_day < start and activity_in_period:
        status = "reread"
    elif finish_in_period or (progress is not None and progress >= 95 and activity_in_period):
        status = "completed"
    elif progress is not None and 5 <= progress < 95 and activity_in_period:
        status = "reading"
    elif progress is not None and progress < 5 and activity_in_period:
        status = "shallow"
    else:
        status = "active_unknown"

    row["status"] = status
    row["engagementLabel"] = "evidence-rich" if row["noteCount"] >= 5 else "light/no-note"
    return status, row


def note_theme_by_month(books: list[dict], start: date, end: date) -> dict[str, Counter]:
    buckets: dict[str, Counter] = defaultdict(Counter)
    for book in books:
        category = str(book.get("category") or "未知").strip() or "未知"
        for field in ("marks", "reviews"):
            for item in book.get(field) or []:
                ts = as_int((item or {}).get("createTime"))
                day = ts_day(ts)
                if day and start <= day <= end:
                    buckets[day.strftime("%Y-%m")][category] += 1
    return dict(sorted(buckets.items()))


def focus_shift_candidate(monthly_categories: dict[str, Counter]) -> dict | None:
    months = sorted(monthly_categories)
    if len(months) < 2:
        return None
    cut = max(1, len(months) // 2)
    first = Counter()
    second = Counter()
    for month in months[:cut]:
        first.update(monthly_categories[month])
    for month in months[cut:]:
        second.update(monthly_categories[month])
    if not first or not second:
        return None
    first_top = first.most_common(1)[0]
    second_top = second.most_common(1)[0]
    return {
        "firstHalfTopCategory": first_top[0],
        "firstHalfNotes": first_top[1],
        "secondHalfTopCategory": second_top[0],
        "secondHalfNotes": second_top[1],
        "changed": first_top[0] != second_top[0],
        "interpretation": "Candidate narrative shift only; the reason for the change is unknown unless the user supplies context.",
    }


def build_context(
    context: dict,
    readdata: dict,
    *,
    start: date,
    end: date,
    platform: str = "",
) -> dict:
    if end < start:
        raise ValueError("end must be on or after start")
    if platform and platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")

    books = [b for b in (context.get("books") or []) if isinstance(b, dict)]
    groups = {"completed": [], "reading": [], "shallow": [], "reread": [], "active_unknown": []}
    for book in books:
        status, row = classify_book(book, start, end)
        if status and row:
            groups[status].append(row)
    for rows in groups.values():
        rows.sort(key=lambda b: (-b["periodNotes"], -b["recordReadingTime"], b["title"]))

    active = [item for rows in groups.values() for item in rows]
    evidence_rich = [b for b in active if b["noteCount"] >= 5]
    light = [b for b in active if b["noteCount"] < 5]
    top_notes = sorted(active, key=lambda b: (-b["periodNotes"], -b["noteCount"], b["title"]))[:10]
    top_time = sorted(active, key=lambda b: (-b["recordReadingTime"], -b["periodNotes"], b["title"]))[:10]

    stale_cutoff = end - timedelta(days=90)
    stalled = []
    for book in books:
        progress = as_float(book.get("progress"))
        activity = ts_day(as_int(book.get("shelfReadUpdateTime") or book.get("updateTime")))
        if progress is not None and 30 <= progress <= 70 and activity and activity <= stale_cutoff:
            stalled.append({
                "bookId": str(book.get("bookId") or ""),
                "title": str(book.get("title") or ""),
                "author": str(book.get("author") or ""),
                "category": str(book.get("category") or "未知"),
                "progress": progress,
                "lastActivityDate": activity.isoformat(),
                "daysStaleAtPeriodEnd": (end - activity).days,
                "noteCount": as_int(book.get("noteCount")),
            })
    stalled.sort(key=lambda b: (-b["daysStaleAtPeriodEnd"], b["title"]))

    daily = daily_read_times(readdata)
    period_daily = {d: sec for d, sec in daily.items() if start <= d <= end}
    monthly_seconds = Counter()
    for day, seconds in period_daily.items():
        monthly_seconds[day.strftime("%Y-%m")] += seconds
    peak_month = None
    if monthly_seconds:
        month, seconds = monthly_seconds.most_common(1)[0]
        peak_month = {"month": month, "seconds": seconds, "hours": round(seconds / 3600, 2)}

    theme_months = note_theme_by_month(books, start, end)
    shift = focus_shift_candidate(theme_months)
    category_notes = Counter()
    for counter in theme_months.values():
        category_notes.update(counter)

    period_seconds = sum(period_daily.values())
    period_days = sum(1 for seconds in period_daily.values() if seconds > 0)
    platform_gate = not bool(platform)

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
        },
        "privacy": {
            "containsRawEvidence": False,
            "sourcePolicy": context.get("privacy") or {},
            "note": "Facts contain personalized reading metadata but no raw mark/review bodies.",
        },
        "readingTotals": {
            "seconds": period_seconds,
            "hours": round(period_seconds / 3600, 2),
            "activeDays": period_days,
            "dailyCoverageAvailable": bool(daily),
            "peakMonth": peak_month,
            "monthlyHours": [
                {"month": month, "hours": round(seconds / 3600, 2)}
                for month, seconds in sorted(monthly_seconds.items())
            ],
        },
        "bookGroups": groups,
        "summary": {
            "activeBooks": len(active),
            "completed": len(groups["completed"]),
            "reading": len(groups["reading"]),
            "shallow": len(groups["shallow"]),
            "reread": len(groups["reread"]),
            "activeUnknown": len(groups["active_unknown"]),
            "evidenceRichBooks": len(evidence_rich),
            "lightOrNoNoteBooks": len(light),
        },
        "narrativeCandidates": {
            "topByPeriodNotes": top_notes,
            "topByCumulativeRecordedTime": top_time,
            "stalled30To70Percent": stalled[:20],
            "topNoteCategories": [
                {"category": category, "periodNotes": count}
                for category, count in category_notes.most_common(12)
            ],
            "focusShiftCandidate": shift,
        },
        "limitations": [
            "Per-book recordReadingTime is cumulative, not guaranteed to be limited to the review period.",
            "Book status relies on available progress/activity timestamps; missing progress is kept as active_unknown rather than guessed.",
            "A category shift is a narrative candidate only; this context cannot know why the user's interests changed.",
            "Books completed without notes still count as completed, but evidence-rich books should be preferred for detailed narrative sections.",
        ],
        "reviewContract": {
            "readyForNarrative": bool(platform),
            "requiresPlatformConfirmation": platform_gate,
            "selectedPlatform": platform or None,
            "platformSpec": PLATFORMS.get(platform) if platform else None,
            "supportedPlatforms": PLATFORMS,
            "mustIncludeContrast": True,
            "mustIncludeAtLeastOneImperfection": True,
            "mustSetSpecificNextPeriodGoal": True,
            "mustNotInventReasonsForFocusShiftOrAbandonment": True,
        },
        "nextStep": {
            "action": "write_narrative" if platform else "confirm_platform",
            "message": (
                f"Use the '{platform}' platform spec and write from these facts."
                if platform
                else "Confirm destination platform/tone before generating prose."
            ),
        },
    }


def parse_args():
    today = datetime.now().date()
    parser = argparse.ArgumentParser(description="Build deterministic facts for a reading review period.")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--readdata", type=Path, default=DEFAULT_READDATA)
    parser.add_argument("--start", default=f"{today.year}-01-01")
    parser.add_argument("--end", default=today.isoformat())
    parser.add_argument("--platform", choices=sorted(PLATFORMS), default="")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    readdata = json.loads(args.readdata.read_text(encoding="utf-8")) if args.readdata.exists() else {}
    result = build_context(
        context,
        readdata,
        start=parse_day(args.start),
        end=parse_day(args.end),
        platform=args.platform,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"narrative-review-context: {args.output} | {args.start}..{args.end} active={result['summary']['activeBooks']} "
        f"completed={result['summary']['completed']} reading={result['summary']['reading']} platform={args.platform or 'confirm'}"
    )


if __name__ == "__main__":
    main()
