#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a standalone GitHub-style WeRead reading heatmap.

Input:
  data/weread_readdata.json

Output:
  data/analysis/reading_heatmap.html

No third-party dependencies.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_INPUT = DEFAULT_DATA / "weread_readdata.json"
DEFAULT_OUTPUT = DEFAULT_DATA / "analysis" / "reading_heatmap.html"

PALETTE = {
    0: "#EEE9E1",
    1: "#E9C9A8",
    2: "#D9A06C",
    3: "#C2724B",
    4: "#8D4A31",
}
MONTHS_ZH = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
WEEKDAYS = {0: "一", 2: "三", 4: "五", 6: "日"}


def _timestamp_to_date(raw) -> date | None:
    """Parse seconds/ms timestamps and YYYY-MM-DD-ish strings."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "-" in text:
        try:
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            pass
    try:
        value = int(float(text))
        if value > 10_000_000_000:
            value //= 1000
        return datetime.fromtimestamp(value).date()
    except (ValueError, OSError, OverflowError):
        return None


def load_daily_read_times(path: Path) -> dict[date, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_day: dict[date, int] = defaultdict(int)

    annually = payload.get("annually") or {}
    for _, period in annually.items():
        for raw_day, raw_seconds in (period or {}).get("dailyReadTimes", {}).items():
            day = _timestamp_to_date(raw_day)
            if not day:
                continue
            try:
                seconds = max(0, int(raw_seconds or 0))
            except (TypeError, ValueError):
                continue
            # One natural day belongs to exactly one annual response. max() avoids
            # accidental duplication if cached input contains the same year twice.
            by_day[day] = max(by_day[day], seconds)

    return dict(sorted(by_day.items()))


def level_for(seconds: int) -> int:
    """Fixed, explainable thresholds from visualization-spec.md."""
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


def format_duration(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分"


def streaks(by_day: dict[date, int]) -> tuple[int, int]:
    active = sorted(day for day, sec in by_day.items() if sec >= 60)
    if not active:
        return 0, 0

    longest = 1
    run = 1
    for prev, cur in zip(active, active[1:]):
        if cur == prev + timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    today = date.today()
    active_set = set(active)
    anchor = today if today in active_set else today - timedelta(days=1)
    current = 0
    while anchor in active_set:
        current += 1
        anchor -= timedelta(days=1)
    return longest, current


def year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def year_svg(year: int, by_day: dict[date, int]) -> str:
    cell = 13
    gap = 3
    step = cell + gap
    left = 34
    top = 28
    first, last = year_bounds(year)
    grid_start = first - timedelta(days=first.weekday())
    grid_end = last + timedelta(days=(6 - last.weekday()))
    weeks = ((grid_end - grid_start).days // 7) + 1
    width = left + weeks * step + 8
    height = top + 7 * step + 12

    parts = [
        f'<svg class="heatmap-svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{year} 年每日阅读热力图">'
    ]

    for weekday, label in WEEKDAYS.items():
        y = top + weekday * step + cell - 2
        parts.append(f'<text class="weekday" x="2" y="{y}">{label}</text>')

    seen_months: set[int] = set()
    cursor = grid_start
    while cursor <= grid_end:
        week = (cursor - grid_start).days // 7
        if cursor.year == year and cursor.month not in seen_months and cursor.day <= 7:
            x = left + week * step
            parts.append(f'<text class="month" x="{x}" y="13">{MONTHS_ZH[cursor.month - 1]}</text>')
            seen_months.add(cursor.month)
        cursor += timedelta(days=7)

    day = grid_start
    while day <= grid_end:
        week = (day - grid_start).days // 7
        weekday = day.weekday()
        x = left + week * step
        y = top + weekday * step
        in_year = day.year == year
        seconds = by_day.get(day, 0) if in_year else 0
        level = level_for(seconds) if in_year else 0
        fill = PALETTE[level] if in_year else "transparent"
        stroke = "#E9E2D7" if in_year else "transparent"
        readable = f"{day.isoformat()} · {format_duration(seconds)}" if in_year else ""
        cls = f"day level-{level}" if in_year else "day outside"
        parts.append(
            f'<rect class="{cls}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{fill}" stroke="{stroke}" data-date="{day.isoformat()}" '
            f'data-seconds="{seconds}"><title>{escape(readable)}</title></rect>'
        )
        day += timedelta(days=1)

    parts.append("</svg>")
    return "".join(parts)


def summary(by_day: dict[date, int], years: list[int]) -> dict[str, str]:
    visible = {d: s for d, s in by_day.items() if d.year in years}
    total = sum(visible.values())
    active = {d: s for d, s in visible.items() if s >= 60}
    longest, current = streaks(visible)
    max_day = max(active.items(), key=lambda item: item[1], default=(None, 0))
    return {
        "总阅读": format_duration(total),
        "有效阅读天": f"{len(active)} 天",
        "最长连续": f"{longest} 天",
        "当前连续": f"{current} 天",
        "单日最高": (
            f"{max_day[0].isoformat()} · {format_duration(max_day[1])}"
            if max_day[0]
            else "—"
        ),
    }


def render_html(by_day: dict[date, int], years: list[int]) -> str:
    stats = summary(by_day, years)
    buttons = "".join(
        f'<button type="button" class="year-btn{" active" if i == 0 else ""}" '
        f'data-year="{year}">{year}</button>'
        for i, year in enumerate(years)
    )
    panels = "".join(
        f'<section class="year-panel{" active" if i == 0 else ""}" data-year="{year}">'
        f'<div class="year-heading"><h2>{year}</h2>'
        f'<span>{sum(1 for d, s in by_day.items() if d.year == year and s >= 60)} 个有效阅读日</span></div>'
        f'<div class="svg-wrap">{year_svg(year, by_day)}</div></section>'
        for i, year in enumerate(years)
    )
    cards = "".join(
        f'<div class="metric"><div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-label">{escape(label)}</div></div>'
        for label, value in stats.items()
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>微信读书 · 阅读热力图</title>
<style>
:root {{
  --bg:#F7F3EC; --panel:#FFFCF7; --text:#2B2724; --muted:#7A7066;
  --border:#E6DECF; --accent:#C2724B;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family:"SF Pro Display","Inter","PingFang SC","Microsoft YaHei",sans-serif;
}}
main {{ width:min(1120px, calc(100% - 32px)); margin:0 auto; padding:44px 0 64px; }}
.eyebrow {{ color:var(--accent); font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }}
h1 {{ margin:8px 0 8px; font-size:clamp(28px,5vw,48px); letter-spacing:-.03em; }}
.lead {{ margin:0; max-width:720px; color:var(--muted); line-height:1.7; }}
.metrics {{
  display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; margin:28px 0;
}}
.metric {{
  min-width:0; background:var(--panel); border:1px solid var(--border);
  border-radius:18px; padding:18px;
}}
.metric-value {{ font-size:20px; font-weight:760; overflow-wrap:anywhere; }}
.metric-label {{ margin-top:5px; color:var(--muted); font-size:12px; }}
.toolbar {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:4px 0 16px; }}
.year-btn {{
  appearance:none; border:1px solid var(--border); background:var(--panel); color:var(--text);
  border-radius:999px; padding:9px 14px; font:inherit; cursor:pointer;
}}
.year-btn.active {{ background:var(--text); color:var(--panel); border-color:var(--text); }}
.year-panel {{
  display:none; background:var(--panel); border:1px solid var(--border);
  border-radius:22px; padding:20px;
}}
.year-panel.active {{ display:block; }}
.year-heading {{ display:flex; justify-content:space-between; gap:16px; align-items:baseline; }}
.year-heading h2 {{ margin:0 0 12px; font-size:20px; }}
.year-heading span {{ color:var(--muted); font-size:13px; }}
.svg-wrap {{ overflow-x:auto; padding-bottom:4px; }}
.heatmap-svg {{ display:block; width:max(760px,100%); height:auto; }}
.month,.weekday {{ fill:var(--muted); font-size:10px; }}
.day {{ transition:opacity .12s ease, stroke-width .12s ease; }}
.day:hover {{ opacity:.78; stroke-width:2px; }}
.legend {{ display:flex; align-items:center; justify-content:flex-end; gap:6px; margin:12px 3px 0; color:var(--muted); font-size:12px; }}
.swatch {{ width:13px; height:13px; border-radius:3px; border:1px solid var(--border); }}
.note {{ margin-top:14px; color:var(--muted); font-size:12px; line-height:1.6; }}
@media (max-width:820px) {{
  .metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .metric:last-child {{ grid-column:1 / -1; }}
  main {{ width:min(100% - 20px,1120px); padding-top:28px; }}
}}
</style>
</head>
<body>
<main>
  <div class="eyebrow">WeRead Intelligence · deterministic view</div>
  <h1>阅读热力图</h1>
  <p class="lead">每一个方格代表一个自然日。这里只呈现微信读书返回的每日阅读时长，不使用 AI 推断。</p>
  <div class="metrics">{cards}</div>
  <div class="toolbar" aria-label="选择年份">{buttons}</div>
  {panels}
  <div class="legend">
    <span>少</span>
    {''.join(f'<span class="swatch" style="background:{PALETTE[i]}"></span>' for i in range(5))}
    <span>多</span>
  </div>
  <p class="note">分级口径：不足 1 分钟 / 1–10 分钟 / 10–30 分钟 / 30–60 分钟 / 60 分钟以上。有效阅读日按单日 ≥ 1 分钟计算。</p>
</main>
<script>
(() => {{
  const buttons = [...document.querySelectorAll('.year-btn')];
  const panels = [...document.querySelectorAll('.year-panel')];
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    const year = btn.dataset.year;
    buttons.forEach(x => x.classList.toggle('active', x === btn));
    panels.forEach(x => x.classList.toggle('active', x.dataset.year === year));
  }}));
}})();
</script>
</body>
</html>
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead annual dailyReadTimes as a standalone HTML heatmap.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--years", type=int, default=6, help="Show the most recent N years (default: 6).")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"ERROR: missing input {args.input}; run scripts/fetch_enrich.py first")

    by_day = load_daily_read_times(args.input)
    if not by_day:
        raise SystemExit("ERROR: no annually[*].dailyReadTimes found in readdata input")

    available_years = sorted({day.year for day in by_day}, reverse=True)
    years = available_years[: max(1, args.years)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(by_day, years), encoding="utf-8")
    print(f"heatmap: {args.output} ({len(by_day)} daily buckets, years={','.join(map(str, years))})")


if __name__ == "__main__":
    main()
