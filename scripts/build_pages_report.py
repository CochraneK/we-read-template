#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a GitHub Pages report from real WeRead data.

By default the report excludes shelf entries marked ``secret=1``. Set
``WEREAD_PAGES_INCLUDE_PRIVATE=1`` to include them explicitly. Raw highlight and
review text is never published by this builder; visible conclusions are
aggregated facts only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "scripts"))

from metrics import category_participation, engagement_summary  # noqa: E402


def env_true(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def book_id(item: dict) -> str:
    return str(item.get("bookId") or (item.get("book") or {}).get("bookId") or "")


def note_count(item: dict) -> int:
    if "marks" in item or "reviews" in item:
        return len(item.get("marks") or []) + len(item.get("reviews") or [])
    return int(item.get("noteCount") or 0) + int(item.get("reviewCount") or 0)


def category_of(item: dict) -> str:
    book = item.get("book") or item
    category = str(book.get("category") or "").strip()
    if category:
        return category
    for raw in book.get("categories") or []:
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            value = raw.get("title") or raw.get("category") or raw.get("name")
            if value:
                return str(value).strip()
    return "未知"


def author_of(item: dict) -> str:
    book = item.get("book") or item
    return str(book.get("author") or item.get("author") or "").strip()


def fmt_hours(seconds: float) -> float:
    return round(float(seconds or 0) / 3600, 1)


def parse_timestamp(raw) -> dt.datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(float(text))
        if value > 10_000_000_000:
            value //= 1000
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def safe_date(ts) -> str:
    parsed = parse_timestamp(ts)
    return parsed.strftime("%Y-%m-%d") if parsed else "—"


def daily_read_times(readdata: dict) -> dict[str, int]:
    """Flatten annual dailyReadTimes into YYYY-MM-DD -> seconds.

    The Pages runtime also supports the real monthly ``readTimes`` payload and
    monkeypatches this function at deployment time.
    """
    result: dict[str, int] = {}
    for period in (readdata.get("annually") or {}).values():
        for raw_day, raw_seconds in ((period or {}).get("dailyReadTimes") or {}).items():
            parsed = parse_timestamp(raw_day)
            if not parsed:
                continue
            try:
                seconds = max(0, int(raw_seconds or 0))
            except (TypeError, ValueError):
                continue
            key = parsed.strftime("%Y-%m-%d")
            result[key] = max(result.get(key, 0), seconds)
    return dict(sorted(result.items()))


def heat_level(seconds: int) -> int:
    minutes = seconds / 60
    if minutes < 1:
        return 0
    if minutes < 10:
        return 1
    if minutes < 30:
        return 2
    if minutes < 60:
        return 3
    return 4


def streaks(daily: dict[str, int]) -> tuple[int, int]:
    active = []
    for key, seconds in daily.items():
        if seconds < 60:
            continue
        try:
            active.append(dt.date.fromisoformat(key))
        except ValueError:
            continue
    active.sort()
    if not active:
        return 0, 0
    longest = run = 1
    for previous, current in zip(active, active[1:]):
        if current == previous + dt.timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    active_set = set(active)
    anchor = max(active)
    current = 0
    while anchor in active_set:
        current += 1
        anchor -= dt.timedelta(days=1)
    return longest, current


def iter_note_events(note_books: list[dict]):
    for book in note_books:
        bid = book_id(book)
        for kind, rows in (("mark", book.get("marks") or []), ("review", book.get("reviews") or [])):
            for item in rows:
                parsed = parse_timestamp(item.get("createTime"))
                if parsed:
                    yield bid, kind, parsed


def build_report(data_dir: Path = DATA, include_private: bool | None = None) -> dict:
    if include_private is None:
        include_private = env_true("WEREAD_PAGES_INCLUDE_PRIVATE", False)

    shelf = load_json(data_dir / "weread_shelf.json", {})
    notebooks = load_json(data_dir / "weread_notebooks.json", [])
    notes_export = load_json(data_dir / "weread_notes_export.json", [])
    readdata = load_json(data_dir / "weread_readdata.json", {})

    shelf_books = list(shelf.get("books") or [])
    secret_ids = {book_id(b) for b in shelf_books if int(b.get("secret") or 0) == 1 and book_id(b)}
    visible_shelf = list(shelf_books) if include_private else [b for b in shelf_books if book_id(b) not in secret_ids]
    visible_notebooks = list(notebooks) if include_private else [n for n in notebooks if book_id(n) not in secret_ids]
    visible_notes = list(notes_export) if include_private else [n for n in notes_export if book_id(n) not in secret_ids]

    shelf_by_id = {book_id(b): b for b in visible_shelf if book_id(b)}
    notebook_by_id = {book_id(n): n for n in visible_notebooks if book_id(n)}
    notes_by_id = {book_id(n): n for n in visible_notes if book_id(n)}

    def metadata_for(bid: str) -> dict:
        return shelf_by_id.get(bid) or notebook_by_id.get(bid) or notes_by_id.get(bid) or {}

    cat = category_participation(visible_shelf, visible_notebooks)
    categories = [row for row in cat["rows"] if row["category"] != "未知"][:12]

    actual_note_counts = {book_id(n): note_count(n) for n in visible_notes if book_id(n)}
    author_notes = Counter()
    author_books = Counter()
    edge_weights = Counter()
    category_note_weights = Counter()
    author_note_weights = Counter()
    for bid, row in notebook_by_id.items():
        meta = metadata_for(bid)
        author = author_of(meta) or author_of(row) or "未知"
        category = category_of(meta)
        count = actual_note_counts.get(bid, note_count(row))
        author_notes[author] += count
        author_books[author] += 1
        if author != "未知" and category != "未知" and count > 0:
            edge_weights[(category, author)] += count
            category_note_weights[category] += count
            author_note_weights[author] += count

    authors = [
        {"author": author, "notes": author_notes[author], "books": author_books[author]}
        for author, _ in author_notes.most_common(14)
        if author != "未知"
    ][:12]

    top_network_categories = {name for name, _ in category_note_weights.most_common(8)}
    top_network_authors = {name for name, _ in author_note_weights.most_common(10)}
    network = {
        "categories": [{"name": name, "value": value} for name, value in category_note_weights.most_common(8)],
        "authors": [{"name": name, "value": value} for name, value in author_note_weights.most_common(10)],
        "edges": [
            {"category": category, "author": author, "value": value}
            for (category, author), value in edge_weights.most_common()
            if category in top_network_categories and author in top_network_authors
        ],
    }

    overall = readdata.get("overall") or {}
    read_times = overall.get("readTimes") or {}
    total_seconds = sum(float(v or 0) for v in read_times.values())
    read_days = int(overall.get("readDays") or 0)

    note_by_month = Counter()
    note_by_year = Counter()
    focus_by_year: dict[str, Counter] = defaultdict(Counter)
    total_marks = 0
    total_reviews = 0
    for note_book in visible_notes:
        total_marks += len(note_book.get("marks") or [])
        total_reviews += len(note_book.get("reviews") or [])
    for bid, _kind, created in iter_note_events(visible_notes):
        month = created.strftime("%Y-%m")
        year = created.strftime("%Y")
        note_by_month[month] += 1
        note_by_year[year] += 1
        category = category_of(metadata_for(bid))
        if category != "未知":
            focus_by_year[year][category] += 1

    monthly = []
    for month, payload in sorted((readdata.get("monthly") or {}).items()):
        monthly.append({"month": month, "hours": fmt_hours((payload or {}).get("totalReadTime") or 0), "notes": note_by_month.get(month, 0)})

    peak = max(monthly, key=lambda x: x["hours"], default={"month": "—", "hours": 0, "notes": 0})
    active_months = sum(1 for x in monthly if x["hours"] > 0)

    daily_raw = daily_read_times(readdata)
    daily = [{"date": date, "seconds": seconds, "level": heat_level(seconds)} for date, seconds in daily_raw.items() if seconds > 0]
    longest_streak, current_streak = streaks(daily_raw)
    peak_day = max(daily, key=lambda row: row["seconds"], default={"date": "—", "seconds": 0, "level": 0})

    annual_seconds = Counter()
    annual_days = Counter()
    for date, seconds in daily_raw.items():
        year = date[:4]
        annual_seconds[year] += seconds
        if seconds >= 60:
            annual_days[year] += 1
    for year, payload in (readdata.get("annually") or {}).items():
        label = str(year)[:4]
        if label.isdigit() and label not in annual_seconds:
            annual_seconds[label] = int((payload or {}).get("totalReadTime") or 0)
            annual_days[label] = int((payload or {}).get("readDays") or 0)
    annual_years = sorted(set(annual_seconds) | set(note_by_year))
    annual = [
        {"year": year, "hours": fmt_hours(annual_seconds.get(year, 0)), "days": annual_days.get(year, 0), "notes": note_by_year.get(year, 0)}
        for year in annual_years
        if annual_seconds.get(year, 0) > 0 or note_by_year.get(year, 0) > 0
    ]

    focus = []
    for year in sorted(focus_by_year):
        top = focus_by_year[year].most_common(4)
        if top:
            focus.append({"year": year, "top": [{"category": category, "notes": count} for category, count in top]})

    longest = []
    for item in overall.get("readLongest") or []:
        book = item.get("book") or {}
        bid = str(book.get("bookId") or "")
        if not include_private and bid and bid in secret_ids:
            continue
        longest.append({"title": book.get("title") or "未命名", "author": book.get("author") or "", "hours": fmt_hours(item.get("readTime") or 0)})
    longest = longest[:10]

    recent = []
    for book in sorted(visible_shelf, key=lambda b: int(b.get("readUpdateTime") or 0), reverse=True):
        if not book.get("readUpdateTime"):
            continue
        recent.append({
            "title": book.get("title") or "未命名",
            "author": book.get("author") or "",
            "category": book.get("category") or "未分类",
            "cover": book.get("cover") or "",
            "date": safe_date(book.get("readUpdateTime")),
        })
        if len(recent) >= 10:
            break

    engagement = engagement_summary(visible_shelf, visible_notebooks)
    invested_rate = round(100 * engagement["shelfAndNotes"] / len(visible_shelf), 1) if visible_shelf else 0.0
    total_notes = total_marks + total_reviews
    avg_minutes = round(total_seconds / 60 / read_days, 1) if read_days else 0.0
    note_density = round(total_notes / len(visible_notes), 1) if visible_notes else 0.0
    top_category = categories[0]["category"] if categories else "—"
    top_author = authors[0]["author"] if authors else "—"

    profile = [
        {"label": "每个阅读日", "value": f"{avg_minutes} 分钟", "note": "累计阅读时长 ÷ 阅读天数"},
        {"label": "最长连续阅读", "value": f"{longest_streak} 天", "note": "单日 ≥ 1 分钟视为活跃"},
        {"label": "数据末端连续", "value": f"{current_streak} 天", "note": "以数据中最后一个活跃日为锚点"},
        {"label": "每本笔记书", "value": f"{note_density} 条", "note": "划线 + 想法，不含书签"},
        {"label": "书架→笔记投入率", "value": f"{invested_rate}%", "note": "当前页面纳入书架中有 notebook 记录的比例"},
        {"label": "覆盖最广类别", "value": top_category, "note": "按唯一 bookId 统计"},
        {"label": "笔记最多作者", "value": top_author, "note": "按当前页面纳入书目聚合"},
        {"label": "单日峰值", "value": f"{fmt_hours(peak_day['seconds'])} 小时", "note": str(peak_day["date"])},
    ]

    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "privacyMode": "full" if include_private else "filtered",
        "summary": {
            "shelfBooks": len(visible_shelf),
            "privateBooks": len(secret_ids),
            "privateIncluded": len(secret_ids) if include_private else 0,
            "privateExcluded": 0 if include_private else len(secret_ids),
            "notebookBooks": len(visible_notebooks),
            "marks": total_marks,
            "reviews": total_reviews,
            "notes": total_notes,
            "readDays": read_days,
            "totalHours": round(total_seconds / 3600, 1),
            "activeMonths": active_months,
            "peakMonth": peak["month"],
            "peakHours": peak["hours"],
            "longestStreak": longest_streak,
            "investedRate": invested_rate,
        },
        "monthly": monthly,
        "daily": daily,
        "annual": annual,
        "focus": focus,
        "categories": categories,
        "authors": authors,
        "network": network,
        "profile": profile,
        "longest": longest,
        "recent": recent,
    }


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>我的微信读书 · 数据报告</title>
<style>
:root{--bg:#f5f1e8;--paper:#fffdf7;--ink:#25231f;--muted:#777166;--line:#dfd7c8;--accent:#b4573f;--accent2:#708b77;--accent3:#c4953c;--heat0:#eee9e1;--heat1:#e9c9a8;--heat2:#d9a06c;--heat3:#c2724b;--heat4:#8d4a31;--shadow:0 18px 50px rgba(54,45,34,.08)}
@media(prefers-color-scheme:dark){:root{--bg:#171613;--paper:#211f1b;--ink:#f2ede4;--muted:#a8a095;--line:#3a352d;--accent:#dd7a61;--accent2:#91ab95;--accent3:#ddb25a;--heat0:#302d28;--heat1:#5e4536;--heat2:#8f5d3e;--heat3:#bd704d;--heat4:#e18a64;--shadow:none}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55}.wrap{max-width:1180px;margin:auto;padding:44px 22px 70px}.hero{display:grid;grid-template-columns:1.5fr .7fr;gap:24px;align-items:end;margin-bottom:28px}.eyebrow{font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:800}.hero h1{font-family:ui-serif,"Songti SC","STSong",serif;font-size:clamp(38px,6vw,78px);line-height:1.02;margin:8px 0 14px;font-weight:650}.hero p{max-width:760px;color:var(--muted);font-size:17px}.stamp{text-align:right;color:var(--muted);font-size:13px}.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}.nav a{color:var(--muted);text-decoration:none;border:1px solid var(--line);background:var(--paper);padding:7px 11px;border-radius:999px;font-size:12px}.nav a:hover{color:var(--ink);border-color:var(--accent2)}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}.card{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:var(--shadow)}.stat{grid-column:span 3;min-height:122px}.stat b{font-size:29px;display:block;margin-top:10px}.stat span{font-size:13px;color:var(--muted)}.wide{grid-column:span 12}.half{grid-column:span 6}.third{grid-column:span 4}.title{display:flex;justify-content:space-between;gap:12px;align-items:baseline;margin-bottom:16px}.title h2{font-size:20px;margin:0}.title small{color:var(--muted)}#hoursChart,#notesChart,#networkChart{width:100%;height:auto;display:block}.bars{display:grid;gap:10px}.barrow{display:grid;grid-template-columns:minmax(130px,220px) 1fr 74px;gap:12px;align-items:center;font-size:13px}.track{height:10px;border-radius:999px;background:color-mix(in srgb,var(--line) 70%,transparent);overflow:hidden}.fill{height:100%;border-radius:999px;background:var(--accent2)}.fill.notes{background:var(--accent3)}.value{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}.books{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}.book{min-width:0}.cover{aspect-ratio:2/3;border-radius:12px;background:var(--line);overflow:hidden;margin-bottom:8px}.cover img{width:100%;height:100%;object-fit:cover}.book h3{font-size:13px;margin:0 0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.book p{margin:0;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);font-size:13px}.table th{color:var(--muted);font-weight:600}.profile-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.profile-item{border:1px solid var(--line);border-radius:16px;padding:14px;min-height:108px}.profile-item span{display:block;color:var(--muted);font-size:12px}.profile-item b{display:block;font-size:19px;margin:7px 0}.profile-item small{color:var(--muted);font-size:11px}.heat-years{display:grid;gap:18px}.heat-year{overflow-x:auto}.heat-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:13px}.heat-grid{display:grid;grid-template-rows:repeat(7,12px);grid-auto-flow:column;grid-auto-columns:12px;gap:3px;width:max-content}.heat-cell,.heat-blank{width:12px;height:12px;border-radius:3px}.heat-cell{outline:1px solid color-mix(in srgb,var(--line) 55%,transparent)}.l0{background:var(--heat0)}.l1{background:var(--heat1)}.l2{background:var(--heat2)}.l3{background:var(--heat3)}.l4{background:var(--heat4)}.legend{display:flex;gap:5px;align-items:center;color:var(--muted);font-size:11px}.legend i{width:11px;height:11px;border-radius:3px;display:inline-block}.focus-list{display:grid;gap:12px}.focus-row{display:grid;grid-template-columns:72px 1fr;gap:14px;align-items:start;padding:12px 0;border-bottom:1px solid var(--line)}.focus-year{font-size:22px;font-weight:700}.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{border:1px solid var(--line);border-radius:999px;padding:7px 10px;font-size:12px}.chip b{color:var(--accent)}.privacy{border-left:4px solid var(--accent2)}footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}footer a{color:inherit}.muted{color:var(--muted)}
@media(max-width:900px){.hero{grid-template-columns:1fr}.stamp{text-align:left}.stat{grid-column:span 6}.half,.third{grid-column:span 12}.books{grid-template-columns:repeat(3,1fr)}.profile-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.wrap{padding:28px 14px 50px}.stat{grid-column:span 6}.books{grid-template-columns:repeat(2,1fr)}.barrow{grid-template-columns:110px 1fr 58px}.card{padding:17px}.profile-grid{grid-template-columns:1fr}.focus-row{grid-template-columns:58px 1fr}}
</style>
</head>
<body>
<div class="wrap">
<section class="hero"><div><div class="eyebrow">WeRead · Personal Data Report</div><h1>我的微信读书</h1><p>直接由真实微信读书数据重新计算的个人阅读档案。这里展示阅读强度、时间轨迹、关注类别、作者投入和书目关系；是否包含 secret=1 书目由部署配置明确决定，原始划线/想法正文不会发布。</p></div><div class="stamp" id="generated"></div></section>
<nav class="nav"><a href="#rhythm">阅读节奏</a><a href="#heatmap">每日热力图</a><a href="#focus">关注迁移</a><a href="#map">阅读版图</a><a href="#profile">事实画像</a><a href="#books">书目</a></nav>
<section class="grid" id="stats"></section>
<section class="grid" style="margin-top:16px">
  <article class="card wide" id="rhythm"><div class="title"><h2>月度阅读时长</h2><small id="range"></small></div><svg id="hoursChart" viewBox="0 0 1040 310" role="img" aria-label="月度阅读时长趋势"></svg></article>
  <article class="card wide"><div class="title"><h2>月度笔记量</h2><small>划线 + 想法</small></div><svg id="notesChart" viewBox="0 0 1040 260" role="img" aria-label="月度笔记量"></svg></article>
  <article class="card wide" id="heatmap"><div class="title"><h2>每日阅读热力图</h2><div class="legend"><span>少</span><i class="l0"></i><i class="l1"></i><i class="l2"></i><i class="l3"></i><i class="l4"></i><span>多</span></div></div><div class="heat-years" id="heatYears"></div></article>
  <article class="card half"><div class="title"><h2>年度汇总</h2><small>每日阅读聚合</small></div><table class="table"><thead><tr><th>年份</th><th>小时</th><th>活跃天</th><th>笔记</th></tr></thead><tbody id="annual"></tbody></table></article>
  <article class="card half" id="focus"><div class="title"><h2>关注类别迁移</h2><small>按笔记创建时间聚合，不是人格推断</small></div><div class="focus-list" id="focusList"></div></article>
  <article class="card half"><div class="title"><h2>阅读类别</h2><small>按唯一 bookId 去重</small></div><div class="bars" id="categories"></div></article>
  <article class="card half"><div class="title"><h2>笔记最多的作者</h2><small>按当前页面纳入书目</small></div><div class="bars" id="authors"></div></article>
  <article class="card wide" id="map"><div class="title"><h2>阅读版图 · 类别 ↔ 作者</h2><small>连线粗细 = 笔记投入量</small></div><svg id="networkChart" viewBox="0 0 1040 520" role="img" aria-label="类别和作者阅读版图"></svg></article>
  <article class="card wide" id="profile"><div class="title"><h2>事实型 Reading Profile</h2><small>只陈述可计算事实</small></div><div class="profile-grid" id="profileGrid"></div></article>
  <article class="card half" id="books"><div class="title"><h2>阅读时长 Top</h2><small>官方 readLongest</small></div><table class="table"><thead><tr><th>书名</th><th>作者</th><th>小时</th></tr></thead><tbody id="longest"></tbody></table></article>
  <article class="card half"><div class="title"><h2>最近阅读</h2><small>按 readUpdateTime</small></div><div class="books" id="recent"></div></article>
  <article class="card wide privacy"><div class="title"><h2>数据边界</h2><small>explicit publishing policy</small></div><p id="privacyText" style="margin:0;color:var(--muted)"></p></article>
</section>
<footer>Generated from real WeRead data · deterministic build · <a href="report-data.json">聚合数据 JSON</a> · raw highlights/reviews are not published</footer>
</div>
<script>
const D=__REPORT_JSON__;
const $=id=>document.getElementById(id);
$('generated').textContent='生成于 '+D.generatedAt;
const S=D.summary;
const stats=[['累计阅读',S.totalHours+' h'],['阅读天数',S.readDays+' 天'],['书架',S.shelfBooks+' 本'],['有笔记书',S.notebookBooks+' 本'],['划线 + 想法',S.notes.toLocaleString()+' 条'],['最长连续',S.longestStreak+' 天'],['书架→笔记',S.investedRate+'%'],['峰值月份',S.peakMonth+' · '+S.peakHours+'h']];
$('stats').innerHTML=stats.map(([k,v])=>`<article class="card stat"><span>${k}</span><b>${v}</b></article>`).join('');
if(D.monthly.length){$('range').textContent=D.monthly[0].month+' → '+D.monthly[D.monthly.length-1].month+' · '+S.activeMonths+' 个活跃月';}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function drawLine(svgId,key,stroke,H=310){const svg=$(svgId),data=D.monthly,W=1040,p={l:48,r:18,t:18,b:40};const max=Math.max(1,...data.map(d=>+d[key]||0));let out='';for(let i=0;i<5;i++){const y=p.t+(H-p.t-p.b)*i/4;const val=(max*(1-i/4)).toFixed(0);out+=`<line x1="${p.l}" y1="${y}" x2="${W-p.r}" y2="${y}" stroke="var(--line)"/><text x="6" y="${y+4}" fill="var(--muted)" font-size="11">${val}</text>`;}const pts=data.map((d,i)=>{const x=p.l+(W-p.l-p.r)*(data.length===1?0:i/(data.length-1));const y=p.t+(H-p.t-p.b)*(1-(+d[key]||0)/max);return [x,y];});out+=`<polyline fill="none" stroke="${stroke}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="${pts.map(p=>p.join(',')).join(' ')}"/>`;pts.forEach((pt,i)=>{if(i%6===0||i===pts.length-1)out+=`<text x="${pt[0]}" y="${H-12}" text-anchor="middle" fill="var(--muted)" font-size="10">${esc(data[i].month)}</text>`;});svg.innerHTML=out;}
function drawBars(svgId,key,fill,H=260){const svg=$(svgId),data=D.monthly,W=1040,p={l:48,r:18,t:16,b:38};const max=Math.max(1,...data.map(d=>+d[key]||0));const gap=3,bw=(W-p.l-p.r)/Math.max(1,data.length);let out='';data.forEach((d,i)=>{const v=+d[key]||0,h=(H-p.t-p.b)*v/max,x=p.l+i*bw+gap/2,y=H-p.b-h;out+=`<rect x="${x}" y="${y}" width="${Math.max(1,bw-gap)}" height="${h}" rx="2" fill="${fill}"><title>${esc(d.month)} · ${v}</title></rect>`;if(i%6===0||i===data.length-1)out+=`<text x="${x+bw/2}" y="${H-12}" text-anchor="middle" fill="var(--muted)" font-size="10">${esc(d.month)}</text>`;});svg.innerHTML=out;}
drawLine('hoursChart','hours','var(--accent)');drawBars('notesChart','notes','var(--accent3)');
function barList(rows,labelKey,valueKey,unit,cls=''){const max=Math.max(1,...rows.map(r=>+r[valueKey]||0));return rows.map(r=>`<div class="barrow"><div title="${esc(r[labelKey])}">${esc(r[labelKey])}</div><div class="track"><div class="fill ${cls}" style="width:${((+r[valueKey]||0)/max*100).toFixed(1)}%"></div></div><div class="value">${(+r[valueKey]||0).toLocaleString()}${unit}</div></div>`).join('');}
$('categories').innerHTML=barList(D.categories,'category','bookCount',' 本');$('authors').innerHTML=barList(D.authors,'author','notes',' 条','notes');
$('annual').innerHTML=D.annual.map(x=>`<tr><td>${esc(x.year)}</td><td>${x.hours}</td><td>${x.days}</td><td>${x.notes.toLocaleString()}</td></tr>`).join('');
$('focusList').innerHTML=D.focus.map(y=>`<div class="focus-row"><div class="focus-year">${esc(y.year)}</div><div class="chips">${y.top.map(x=>`<span class="chip">${esc(x.category)} <b>${x.notes}</b></span>`).join('')}</div></div>`).join('');
$('profileGrid').innerHTML=D.profile.map(x=>`<div class="profile-item"><span>${esc(x.label)}</span><b>${esc(x.value)}</b><small>${esc(x.note)}</small></div>`).join('');
$('longest').innerHTML=D.longest.map(x=>`<tr><td>${esc(x.title)}</td><td>${esc(x.author)}</td><td>${x.hours}</td></tr>`).join('');
$('recent').innerHTML=D.recent.map(x=>`<div class="book"><div class="cover">${x.cover?`<img loading="lazy" referrerpolicy="no-referrer" src="${esc(x.cover)}" alt="">`:''}</div><h3 title="${esc(x.title)}">${esc(x.title)}</h3><p>${esc(x.author||x.category)} · ${esc(x.date)}</p></div>`).join('');
function renderHeatmaps(){const rows=D.daily||[],byYear={};rows.forEach(r=>(byYear[r.date.slice(0,4)]??=[]).push(r));const lookup=Object.fromEntries(rows.map(r=>[r.date,r]));const years=Object.keys(byYear).sort();$('heatYears').innerHTML=years.map(year=>{const start=new Date(year+'-01-01T00:00:00Z'),end=new Date(year+'-12-31T00:00:00Z');const first=new Date(start);first.setUTCDate(first.getUTCDate()-((first.getUTCDay()+6)%7));let cells='';let active=0;for(let cur=new Date(first);cur<=end||((cur.getUTCDay()+6)%7)!==0;cur.setUTCDate(cur.getUTCDate()+1)){const key=cur.toISOString().slice(0,10),inside=key.slice(0,4)===year,row=lookup[key];if(inside&&row&&row.seconds>=60)active++;cells+=inside?`<div class="heat-cell l${row?.level||0}" title="${key} · ${row?Math.round(row.seconds/60):0} 分钟"></div>`:'<div class="heat-blank"></div>';if(cur>end&&((cur.getUTCDay()+6)%7)===6)break;}return `<div class="heat-year"><div class="heat-head"><b>${year}</b><span class="muted">${active} 个活跃日</span></div><div class="heat-grid">${cells}</div></div>`;}).join('');}
renderHeatmaps();
function drawNetwork(){const svg=$('networkChart'),C=D.network.categories||[],A=D.network.authors||[],E=D.network.edges||[],W=1040,H=520;const cy=i=>55+i*(H-110)/Math.max(1,C.length-1),ay=i=>55+i*(H-110)/Math.max(1,A.length-1),cp={},ap={};C.forEach((x,i)=>cp[x.name]=[150,cy(i)]);A.forEach((x,i)=>ap[x.name]=[890,ay(i)]);const maxE=Math.max(1,...E.map(e=>e.value));let out='';E.forEach(e=>{const c=cp[e.category],a=ap[e.author];if(!c||!a)return;const w=.6+5*e.value/maxE;out+=`<path d="M${c[0]},${c[1]} C430,${c[1]} 610,${a[1]} ${a[0]},${a[1]}" fill="none" stroke="var(--line)" stroke-width="${w}" opacity=".72"><title>${esc(e.category)} ↔ ${esc(e.author)} · ${e.value} 条笔记</title></path>`;});C.forEach(x=>{const p=cp[x.name];out+=`<circle cx="${p[0]}" cy="${p[1]}" r="8" fill="var(--accent2)"/><text x="${p[0]+14}" y="${p[1]+4}" fill="var(--ink)" font-size="11">${esc(x.name)}</text>`;});A.forEach(x=>{const p=ap[x.name];out+=`<circle cx="${p[0]}" cy="${p[1]}" r="8" fill="var(--accent)"/><text x="${p[0]-14}" y="${p[1]+4}" text-anchor="end" fill="var(--ink)" font-size="11">${esc(x.name)}</text>`;});svg.innerHTML=out;}
drawNetwork();
$('privacyText').textContent=D.privacyMode==='full'?`本页面已按你的部署设置纳入全部书目，包括 ${S.privateIncluded} 本 secret=1 书。仍不会发布原始划线、想法正文或本地搜索索引；只发布聚合统计和书目元数据。`:`本页面排除了 ${S.privateExcluded} 本 secret=1 书；同时不会发布原始划线、想法正文或本地搜索索引。`;
</script>
</body></html>'''


def main() -> None:
    report = build_report()
    SITE.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    output = TEMPLATE.replace("__REPORT_JSON__", payload)
    (SITE / "index.html").write_text(output, encoding="utf-8")
    (SITE / "report-data.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {SITE / 'index.html'}")
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
