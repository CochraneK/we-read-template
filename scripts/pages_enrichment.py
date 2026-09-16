#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic enrichment data for the real WeRead GitHub Pages archive.

This layer absorbs high-value patterns found across the WeRead skill ecosystem
without publishing raw highlights/reviews. It prefers official readdata fields
when available and derives additional factual views from local exports:

- 24-hour reading clock and weekday rhythm
- reading/listening split, official readStat and preference cards
- publisher/category/author preferences and medals
- progress funnel, stale in-progress books and full bookshelf explorer
- notes/hour, review ratio and monthly read/notes correlation
- recall candidates and books with the most self-written reviews

All sections are optional: missing fields produce empty arrays/None rather than
invented values.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json
import math


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _book_id(item: dict) -> str:
    return str(item.get("bookId") or (item.get("book") or {}).get("bookId") or "")


def _book_obj(item: dict) -> dict:
    nested = item.get("book")
    return nested if isinstance(nested, dict) else item


def _as_int(value, default=0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dt(raw):
    try:
        value = int(float(raw or 0))
        if not value:
            return None
        if value > 10_000_000_000:
            value //= 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _iso_date(raw):
    parsed = _dt(raw)
    return parsed.date().isoformat() if parsed else None


def _category(item: dict, info: dict | None = None) -> str:
    book = _book_obj(item)
    value = str(book.get("category") or item.get("category") or "").strip()
    if value:
        return value
    for raw in book.get("categories") or []:
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            value = raw.get("title") or raw.get("category") or raw.get("name")
            if value:
                return str(value).strip()
    if info:
        value = str(info.get("category") or "").strip()
        if value:
            return value
    return "未知"


def _author(item: dict) -> str:
    book = _book_obj(item)
    return str(book.get("author") or item.get("author") or "").strip()


def _title(item: dict) -> str:
    book = _book_obj(item)
    return str(book.get("title") or item.get("title") or "未命名").strip() or "未命名"


def _cover(item: dict) -> str:
    book = _book_obj(item)
    return str(book.get("cover") or item.get("cover") or "")


def _daily_read_times(readdata: dict) -> dict[str, int]:
    """Normalize cached month/day data to YYYY-MM-DD -> seconds."""
    result: dict[str, int] = {}
    for period in (readdata.get("monthly") or {}).values():
        for raw, sec in ((period or {}).get("readTimes") or {}).items():
            parsed = _dt(raw)
            if not parsed:
                continue
            try:
                seconds = max(0, int(sec or 0))
            except (TypeError, ValueError):
                continue
            key = parsed.date().isoformat()
            result[key] = max(result.get(key, 0), seconds)
    if result:
        return dict(sorted(result.items()))
    for period in (readdata.get("annually") or {}).values():
        for raw, sec in ((period or {}).get("dailyReadTimes") or {}).items():
            parsed = _dt(raw)
            if not parsed:
                continue
            try:
                seconds = max(0, int(sec or 0))
            except (TypeError, ValueError):
                continue
            key = parsed.date().isoformat()
            result[key] = max(result.get(key, 0), seconds)
    return dict(sorted(result.items()))


def _note_months(notes: list[dict]) -> Counter:
    result = Counter()
    for book in notes:
        for rows in (book.get("marks") or [], book.get("reviews") or []):
            for item in rows:
                when = _dt((item or {}).get("createTime"))
                if when:
                    result[when.strftime("%Y-%m")] += 1
    return result


def _pearson(xs: list[float], ys: list[float]):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if not denom:
        return None
    return round(sum(x * y for x, y in zip(dx, dy)) / denom, 3)


def _normalize_prefer_book(row: dict) -> dict:
    book = row.get("bookInfo") or row.get("book") or {}
    return {
        "type": row.get("type"),
        "label": str(row.get("title") or row.get("name") or "偏好书").strip(),
        "reason": str(row.get("reason") or "").strip(),
        "bookId": str(book.get("bookId") or ""),
        "title": str(book.get("title") or "").strip(),
        "author": str(book.get("author") or "").strip(),
        "cover": str(book.get("cover") or ""),
    }


def _progress_value(bid: str, progress: dict, notebook: dict | None):
    row = progress.get(bid) or {}
    value = _as_float(row.get("progress"))
    if value is None and notebook:
        value = _as_float(notebook.get("readingProgress"))
    if value is None and notebook and _as_int(notebook.get("markedStatus"), -1) == 1:
        value = 100.0
    if value is None:
        return None
    return max(0.0, min(100.0, value))


def build_enrichment(data_dir: Path, include_private: bool = False) -> dict:
    shelf_payload = _load(data_dir / "weread_shelf.json", {})
    shelf = list((shelf_payload or {}).get("books") or [])
    notebooks = _load(data_dir / "weread_notebooks.json", [])
    notes_export = _load(data_dir / "weread_notes_export.json", [])
    progress = _load(data_dir / "weread_progress.json", {})
    info = _load(data_dir / "weread_bookinfo.json", {})
    readdata = _load(data_dir / "weread_readdata.json", {})

    secret_ids = {
        _book_id(row) for row in shelf
        if _book_id(row) and _as_int(row.get("secret")) == 1
    }
    if include_private:
        visible_shelf = shelf
        visible_notebooks = notebooks
        visible_notes = notes_export
    else:
        visible_shelf = [row for row in shelf if _book_id(row) not in secret_ids]
        visible_notebooks = [row for row in notebooks if _book_id(row) not in secret_ids]
        visible_notes = [row for row in notes_export if _book_id(row) not in secret_ids]

    shelf_by_id = {_book_id(row): row for row in visible_shelf if _book_id(row)}
    notebooks_by_id = {_book_id(row): row for row in visible_notebooks if _book_id(row)}
    notes_by_id = {_book_id(row): row for row in visible_notes if _book_id(row)}

    overall = readdata.get("overall") or {}
    annual = readdata.get("annually") or {}

    # Official 24h reading clock. Tencent returns 6:00..23:00, 0:00..5:00.
    prefer_time = overall.get("preferTime") or []
    if not prefer_time:
        for _, period in sorted(annual.items(), reverse=True):
            if (period or {}).get("preferTime"):
                prefer_time = period.get("preferTime") or []
                break
    clock = []
    hours = list(range(6, 24)) + list(range(0, 6))
    if isinstance(prefer_time, list):
        for hour, raw in zip(hours, prefer_time[:24]):
            try:
                seconds = max(0, int(raw or 0))
            except (TypeError, ValueError):
                seconds = 0
            clock.append({"hour": hour, "seconds": seconds, "hours": round(seconds / 3600, 2)})

    daily = _daily_read_times(readdata)
    weekday_seconds = Counter()
    weekday_days = Counter()
    weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for date_key, seconds in daily.items():
        try:
            day = datetime.fromisoformat(date_key).date()
        except ValueError:
            continue
        weekday_seconds[day.weekday()] += seconds
        if seconds >= 60:
            weekday_days[day.weekday()] += 1
    weekday = [
        {
            "weekday": i,
            "label": weekday_labels[i],
            "seconds": weekday_seconds[i],
            "hours": round(weekday_seconds[i] / 3600, 1),
            "activeDays": weekday_days[i],
            "avgMinutes": round(weekday_seconds[i] / 60 / weekday_days[i], 1) if weekday_days[i] else 0,
        }
        for i in range(7)
    ]

    # Calendar-month seasonality across all cached years.
    season_seconds = Counter()
    season_periods = Counter()
    for month_key, period in (readdata.get("monthly") or {}).items():
        try:
            month_no = int(str(month_key)[5:7])
        except (ValueError, IndexError):
            continue
        sec = _as_int((period or {}).get("totalReadTime"))
        season_seconds[month_no] += sec
        season_periods[month_no] += 1
    seasonality = [
        {
            "month": month,
            "totalHours": round(season_seconds[month] / 3600, 1),
            "avgHours": round(season_seconds[month] / 3600 / season_periods[month], 1) if season_periods[month] else 0,
            "periods": season_periods[month],
        }
        for month in range(1, 13)
    ]

    read_seconds = _as_int(overall.get("wrReadTime"))
    listen_seconds = _as_int(overall.get("wrListenTime"))
    read_rate = _as_float(overall.get("readRate"))
    reading_mode = None
    if read_seconds or listen_seconds or read_rate is not None:
        total_mode = read_seconds + listen_seconds
        if read_rate is None and total_mode:
            read_rate = 100 * read_seconds / total_mode
        reading_mode = {
            "readSeconds": read_seconds,
            "listenSeconds": listen_seconds,
            "readHours": round(read_seconds / 3600, 1),
            "listenHours": round(listen_seconds / 3600, 1),
            "readRate": round(read_rate, 1) if read_rate is not None else None,
        }

    official = {
        "preferTimeWord": str(overall.get("preferTimeWord") or ""),
        "readStat": [
            {"stat": str(x.get("stat") or ""), "counts": str(x.get("counts") or "")}
            for x in (overall.get("readStat") or []) if isinstance(x, dict)
        ],
        "categories": [
            {
                "title": str(x.get("categoryTitle") or x.get("parentCategoryTitle") or ""),
                "readingTime": _as_int(x.get("readingTime")),
                "readingHours": round(_as_int(x.get("readingTime")) / 3600, 1),
                "readingCount": _as_int(x.get("readingCount")),
                "weight": _as_float(x.get("val")),
            }
            for x in (overall.get("preferCategory") or [])
            if isinstance(x, dict) and (x.get("categoryTitle") or x.get("parentCategoryTitle"))
        ],
        "authors": [
            {
                "name": str(x.get("name") or ""),
                "count": _as_int(x.get("count")),
                "readTime": str(x.get("readTime") or ""),
            }
            for x in (overall.get("preferAuthor") or [])
            if isinstance(x, dict) and x.get("name")
        ],
        "publishers": [
            {"name": str(x.get("name") or ""), "count": _as_int(x.get("count"))}
            for x in (overall.get("preferPublisher") or [])
            if isinstance(x, dict) and x.get("name")
        ],
        "preferBooks": [
            _normalize_prefer_book(x)
            for x in (overall.get("preferBooks") or [])
            if isinstance(x, dict)
        ],
        "medals": [
            {
                "id": str(x.get("id") or ""),
                "title": str(x.get("displayText") or x.get("hint") or x.get("title") or x.get("name") or "勋章"),
                "name": str(x.get("name") or x.get("title") or ""),
                "level": x.get("level"),
                "ctime": _iso_date(x.get("ctime")),
                "rankText": str(x.get("rankText") or ""),
            }
            for x in (overall.get("medals") or [])
            if isinstance(x, dict)
        ],
        "recordReadingHours": round(_as_int(overall.get("recordReadingTime")) / 3600, 1),
    }

    # Annual prefer-book cards are often richer than overall. De-duplicate by label/book/year.
    annual_cards = []
    seen_cards = set()
    for year, period in sorted(annual.items()):
        for row in (period or {}).get("preferBooks") or []:
            if not isinstance(row, dict):
                continue
            card = _normalize_prefer_book(row)
            key = (str(year), card["label"], card["bookId"], card["title"])
            if key in seen_cards:
                continue
            seen_cards.add(key)
            card["year"] = str(year)
            annual_cards.append(card)
    official["annualPreferBooks"] = annual_cards

    registered = _dt(overall.get("registTime"))
    tenure = None
    if registered:
        now = datetime.now(timezone.utc)
        tenure = {
            "registeredDate": registered.date().isoformat(),
            "years": round((now - registered).days / 365.2425, 1),
        }

    # Note metadata / last note dates, but never raw text.
    note_meta = {}
    total_marks = total_reviews = total_bookmarks = 0
    note_months = _note_months(visible_notes)
    for bid, row in notes_by_id.items():
        marks = row.get("marks") or []
        reviews = row.get("reviews") or []
        times = []
        for entries in (marks, reviews):
            for item in entries:
                when = _dt((item or {}).get("createTime"))
                if when:
                    times.append(when)
        total_marks += len(marks)
        total_reviews += len(reviews)
        note_meta[bid] = {
            "marks": len(marks),
            "reviews": len(reviews),
            "notes": len(marks) + len(reviews),
            "firstNote": min(times).date().isoformat() if times else None,
            "lastNote": max(times).date().isoformat() if times else None,
        }
    for row in visible_notebooks:
        total_bookmarks += _as_int(row.get("bookmarkCount"))

    # Progress funnel, current deep reads and full bookshelf explorer.
    bins = Counter()
    full_books = []
    stale = []
    now = datetime.now(timezone.utc)
    for row in visible_shelf:
        bid = _book_id(row)
        if not bid:
            continue
        notebook = notebooks_by_id.get(bid)
        p = _progress_value(bid, progress, notebook)
        if p is None:
            bins["unknown"] += 1
        elif p <= 0:
            bins["notStarted"] += 1
        elif p < 25:
            bins["p1_24"] += 1
        elif p < 50:
            bins["p25_49"] += 1
        elif p < 90:
            bins["p50_89"] += 1
        elif p < 100:
            bins["p90_99"] += 1
        else:
            bins["finished"] += 1
        meta = info.get(bid) or {}
        notes = note_meta.get(bid) or {"marks": 0, "reviews": 0, "notes": 0, "firstNote": None, "lastNote": None}
        update_raw = (progress.get(bid) or {}).get("updateTime") or row.get("readUpdateTime")
        update_dt = _dt(update_raw)
        book = {
            "bookId": bid,
            "title": _title(row),
            "author": _author(row),
            "category": _category(row, meta),
            "cover": _cover(row),
            "progress": round(p, 1) if p is not None else None,
            "lastRead": update_dt.date().isoformat() if update_dt else None,
            "noteCount": notes["notes"],
            "markCount": notes["marks"],
            "reviewCount": notes["reviews"],
            "lastNote": notes["lastNote"],
            "secret": _as_int(row.get("secret")) == 1,
        }
        full_books.append(book)
        if p is not None and 0 < p < 100 and update_dt:
            age = (now - update_dt).days
            if age >= 120:
                stale.append({**book, "staleDays": age})

    full_books.sort(key=lambda x: (x["lastRead"] or "", x["noteCount"]), reverse=True)
    stale.sort(key=lambda x: (-x["staleDays"], -(x["progress"] or 0)))
    progress_funnel = {
        "total": len(visible_shelf),
        "known": len(visible_shelf) - bins["unknown"],
        "unknown": bins["unknown"],
        "bins": [
            {"key": "notStarted", "label": "未开始", "count": bins["notStarted"]},
            {"key": "p1_24", "label": "1–24%", "count": bins["p1_24"]},
            {"key": "p25_49", "label": "25–49%", "count": bins["p25_49"]},
            {"key": "p50_89", "label": "50–89%", "count": bins["p50_89"]},
            {"key": "p90_99", "label": "90–99%", "count": bins["p90_99"]},
            {"key": "finished", "label": "100% / 读完", "count": bins["finished"]},
            {"key": "unknown", "label": "进度未知", "count": bins["unknown"]},
        ],
    }

    current_deep_reads = [
        b for b in full_books
        if b["progress"] is not None and 5 <= b["progress"] < 100 and b["noteCount"] > 0
    ][:12]

    recall = []
    for book in full_books:
        if book["noteCount"] < 3 or not book["lastNote"]:
            continue
        try:
            last = datetime.fromisoformat(book["lastNote"]).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        age = (now - last).days
        if age >= 90:
            recall.append({**book, "daysSinceLastNote": age})
    recall.sort(key=lambda x: (-x["daysSinceLastNote"], -x["noteCount"]))

    thinking_books = [b for b in full_books if b["reviewCount"] > 0]
    for book in thinking_books:
        book["reviewRate"] = round(100 * book["reviewCount"] / book["noteCount"], 1) if book["noteCount"] else 0
    thinking_books.sort(key=lambda x: (-x["reviewCount"], -x["reviewRate"], -x["noteCount"]))

    # Reading time x note-event correlation for months with cached statistics.
    corr_months = []
    xs, ys = [], []
    for month, period in sorted((readdata.get("monthly") or {}).items()):
        hours_value = _as_int((period or {}).get("totalReadTime")) / 3600
        notes_value = note_months.get(month, 0)
        corr_months.append({"month": month, "hours": round(hours_value, 2), "notes": notes_value})
        xs.append(hours_value)
        ys.append(float(notes_value))
    correlation = _pearson(xs, ys)

    total_seconds = _as_int(overall.get("totalReadTime"))
    if not total_seconds:
        total_seconds = sum(_as_int(v) for v in (overall.get("readTimes") or {}).values())
    total_notes = total_marks + total_reviews
    read_days = _as_int(overall.get("readDays"))
    fingerprint = {
        "notesPerHour": round(total_notes / (total_seconds / 3600), 2) if total_seconds else None,
        "reviewShare": round(100 * total_reviews / total_notes, 1) if total_notes else 0,
        "bookmarks": total_bookmarks,
        "avgActiveDayMinutes": round(total_seconds / 60 / read_days, 1) if read_days else None,
        "monthlyReadNoteCorrelation": correlation,
        "correlationMonths": len(corr_months),
    }

    return {
        "version": "1",
        "scope": {
            "includePrivate": include_private,
            "shelfBooks": len(visible_shelf),
            "privateBooks": len(secret_ids),
        },
        "clock": clock,
        "weekday": weekday,
        "seasonality": seasonality,
        "readingMode": reading_mode,
        "official": official,
        "tenure": tenure,
        "progressFunnel": progress_funnel,
        "currentDeepReads": current_deep_reads,
        "staleInProgress": stale[:20],
        "recallCandidates": recall[:20],
        "thinkingBooks": thinking_books[:20],
        "fingerprint": fingerprint,
        "correlation": {"value": correlation, "months": corr_months},
        "bookshelf": full_books,
    }
