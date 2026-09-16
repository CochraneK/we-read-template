#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信读书数据增强抓取：readdata/detail + getprogress + info。

默认数据目录为仓库根目录下的 data/，可通过 WEREAD_DATA_DIR 覆盖。
年度统计会根据 overall.readTimes 自动发现有阅读记录的年份；
月度统计默认抓最近 48 个自然月，可通过 WEREAD_MONTHLY_HISTORY_MONTHS 调整。
"""
from pathlib import Path
import datetime
import json
import os
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DATA.mkdir(parents=True, exist_ok=True)

KEY = os.environ.get("WEREAD_API_KEY", "").strip()
URL = "https://i.weread.qq.com/api/agent/gateway"
SV = "1.0.4"
OUT_READ = DATA / "weread_readdata.json"
OUT_PROG = DATA / "weread_progress.json"
OUT_INFO = DATA / "weread_bookinfo.json"
LOG = DATA / "enrich_progress.log"
NOTES = DATA / "weread_notes_export.json"


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def dump_json(value, path):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")


def call(body, retries=5):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                URL,
                data=json.dumps(body).encode("utf-8"),
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("upgrade_info"):
                info = data["upgrade_info"]
                msg = info.get("message") if isinstance(info, dict) else info
                raise RuntimeError(f"微信读书 Skill 需要升级: {msg}")
            if data.get("errcode", 0) != 0:
                raise RuntimeError(
                    f"gateway errcode={data.get('errcode')}: {data.get('errmsg', 'unknown error')}"
                )
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, RuntimeError) as e:
            last = str(e)
            log(f"  request error: {last[:120]}, retry {i + 1}/{retries}")
            if i + 1 < retries:
                time.sleep(1.5 + i * 0.5)
    log(f"  FAILED after retries: {body.get('api_name')} {last}")
    return None


def year_from_bucket_key(value):
    """兼容秒/毫秒时间戳；解析不了返回 None。"""
    try:
        ts = int(value)
        if ts > 10_000_000_000:
            ts //= 1000
        year = datetime.datetime.fromtimestamp(ts).year
        if 2010 <= year <= datetime.datetime.now().year:
            return year
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return None


def discover_years(overall):
    now_year = datetime.datetime.now().year
    override = os.environ.get("WEREAD_START_YEAR")
    if override:
        try:
            start = max(2010, min(int(override), now_year))
            return list(range(start, now_year + 1))
        except ValueError:
            log(f"WARNING: WEREAD_START_YEAR={override!r} 无效，改用自动发现")

    years = {
        year_from_bucket_key(key)
        for key in (overall or {}).get("readTimes", {}).keys()
    }
    years.discard(None)
    if years:
        start = min(years)
        return list(range(start, now_year + 1))
    return [now_year]


def recent_months(count):
    count = max(1, count)
    now = datetime.datetime.now()
    year, month = now.year, now.month
    items = []
    for _ in range(count):
        items.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    items.reverse()
    return items


def fetch_readdata():
    log("=== 抓取 readdata/detail ===")
    result = {"overall": None, "annually": {}, "monthly": {}}

    overall = call({"api_name": "/readdata/detail", "skill_version": SV, "mode": "overall"})
    if overall:
        result["overall"] = overall
    log(
        "  overall done: totalReadTime=%s readDays=%s"
        % (
            overall.get("totalReadTime") if overall else None,
            overall.get("readDays") if overall else None,
        )
    )
    time.sleep(0.2)

    years = discover_years(overall)
    log(f"  annual range: {years[0]}..{years[-1]} ({len(years)} years)")
    for year in years:
        base_time = int(datetime.datetime(year, 6, 1, 12, 0).timestamp())
        data = call(
            {
                "api_name": "/readdata/detail",
                "skill_version": SV,
                "mode": "annually",
                "baseTime": base_time,
            }
        )
        if data:
            result["annually"][str(year)] = data
        log(
            f"  annually {year}: totalReadTime={data.get('totalReadTime') if data else None} "
            f"readDays={data.get('readDays') if data else None}"
        )
        time.sleep(0.2)

    try:
        month_count = int(os.environ.get("WEREAD_MONTHLY_HISTORY_MONTHS", "48"))
    except ValueError:
        month_count = 48
        log("WARNING: WEREAD_MONTHLY_HISTORY_MONTHS 无效，使用 48")
    month_count = max(1, min(month_count, 240))

    months = recent_months(month_count)
    log(f"  monthly range: {months[0][0]}-{months[0][1]:02d}..{months[-1][0]}-{months[-1][1]:02d}")
    for year, month in months:
        base_time = int(datetime.datetime(year, month, 15, 12, 0).timestamp())
        data = call(
            {
                "api_name": "/readdata/detail",
                "skill_version": SV,
                "mode": "monthly",
                "baseTime": base_time,
            }
        )
        if data:
            result["monthly"][f"{year}-{month:02d}"] = data
        time.sleep(0.12)
    log(f"  monthly done: {len(result['monthly'])} months")

    dump_json(result, OUT_READ)
    log(f"  saved -> {OUT_READ}")
    return result


def load_bookids():
    if not NOTES.exists():
        raise SystemExit(f"ERROR: 缺少 {NOTES}，请先运行 scripts/export_notes.py")
    books = json.loads(NOTES.read_text(encoding="utf-8"))
    ids = [book["bookId"] for book in books if book.get("bookId")]
    log(f"笔记书总数: {len(ids)}")
    return ids


def fetch_per_book(ids):
    progress = {}
    info = {}
    total = len(ids)
    for i, bid in enumerate(ids, 1):
        data = call({"api_name": "/book/getprogress", "bookId": bid, "skill_version": SV})
        if data and data.get("book"):
            book = data["book"]
            progress[bid] = {
                "progress": book.get("progress"),
                "recordReadingTime": book.get("recordReadingTime"),
                "finishTime": book.get("finishTime"),
                "updateTime": book.get("updateTime"),
                "isStartReading": book.get("isStartReading"),
            }

        book_info = call({"api_name": "/book/info", "bookId": bid, "skill_version": SV})
        if book_info:
            info[bid] = {
                "publishTime": book_info.get("publishTime"),
                "wordCount": book_info.get("wordCount"),
                "publisher": book_info.get("publisher"),
                "newRating": book_info.get("newRating"),
                "newRatingCount": book_info.get("newRatingCount"),
                "translator": book_info.get("translator"),
                "category": book_info.get("category"),
                "intro": (book_info.get("intro") or "")[:200],
            }

        time.sleep(0.12)
        if i % 40 == 0 or i == total:
            dump_json(progress, OUT_PROG)
            dump_json(info, OUT_INFO)
            log(f"  进度 {i}/{total}  进度书={len(progress)} info书={len(info)}")

    dump_json(progress, OUT_PROG)
    dump_json(info, OUT_INFO)
    log(f"=== 抓取完成: progress={len(progress)} info={len(info)} ===")


def main():
    if not KEY:
        raise SystemExit("ERROR: WEREAD_API_KEY 未设置")
    if not KEY.startswith("wrk-"):
        log("WARNING: WEREAD_API_KEY 不以 wrk- 开头，请确认使用的是微信读书 Agent Gateway Key")
    LOG.write_text("", encoding="utf-8")
    log(f"数据目录: {DATA}")
    ids = load_bookids()
    fetch_readdata()
    fetch_per_book(ids)
    log("ALL DONE")


if __name__ == "__main__":
    main()
