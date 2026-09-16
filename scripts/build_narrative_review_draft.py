#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a platform-shaped reading-review draft from deterministic review facts.

The draft is intentionally evidence-bounded. It never invents reasons for focus
shifts, abandonment, or personal change. Unknown motivations are emitted as
explicit edit prompts so a human (or later style model) can add context safely.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

PLATFORM_ALIASES = {
    "朋友圈": "moments",
    "公众号": "wechat",
    "小红书": "xiaohongshu",
    "视频脚本": "video",
    "个人日记": "journal",
    "个人留存": "journal",
}


def normalize_platform(value: str | None) -> str:
    raw = str(value or "").strip()
    return PLATFORM_ALIASES.get(raw, raw)


def book_label(row: dict) -> str:
    title = str(row.get("title") or "未命名")
    author = str(row.get("author") or "").strip()
    return f"《{title}》" + (f"（{author}）" if author else "")


def strongest_books(ctx: dict, limit: int = 3) -> list[dict]:
    rows = list(((ctx.get("narrativeCandidates") or {}).get("topByPeriodNotes") or []))
    # Prefer books with actual period notes, then cumulative note evidence.
    rows.sort(key=lambda x: (-int(x.get("periodNotes") or 0), -int(x.get("noteCount") or 0), str(x.get("title") or "")))
    return rows[:limit]


def concrete_goal(ctx: dict) -> str:
    stalled = ((ctx.get("narrativeCandidates") or {}).get("stalled30To70Percent") or [])
    if stalled:
        first = stalled[0]
        return f"下个周期先处理一个明确的未完成项：重新判断 {book_label(first)} 是否值得继续；如果不值得，就正式放下，而不是长期停在 {first.get('progress')}%。"
    reading = ((ctx.get("bookGroups") or {}).get("reading") or [])
    if reading:
        first = reading[0]
        return f"下个周期把同时在读的范围收窄，优先完成 {book_label(first)}，完成后再新增下一本。"
    return "下个周期保留一个可检查的目标：只设一个主阅读主题，并在周期结束时至少留下 5 条自己的想法，而不只收藏或划线。"


def build_draft(ctx: dict, platform: str | None = None) -> dict:
    contract = ctx.get("reviewContract") or {}
    selected = normalize_platform(platform or contract.get("selectedPlatform"))
    supported = contract.get("supportedPlatforms") or {}
    if selected not in supported:
        raise ValueError("A supported platform must be confirmed before building a narrative draft")

    spec = supported[selected]
    summary = ctx.get("summary") or {}
    totals = ctx.get("readingTotals") or {}
    period = ctx.get("period") or {}
    candidates = ctx.get("narrativeCandidates") or {}
    strongest = strongest_books(ctx)
    shift = candidates.get("focusShiftCandidate")
    stalled = candidates.get("stalled30To70Percent") or []
    top_categories = candidates.get("topNoteCategories") or []
    peak = totals.get("peakMonth") or {}

    title = f"我的 {period.get('start','')} → {period.get('end','')} 阅读复盘"
    lead_bits = [
        f"这个周期我在微信读书有 {summary.get('activeBooks', 0)} 本书留下活动证据",
        f"完成 {summary.get('completed', 0)} 本、在读 {summary.get('reading', 0)} 本",
    ]
    if totals.get("dailyCoverageAvailable"):
        lead_bits.append(f"累计阅读 {totals.get('hours', 0)} 小时，覆盖 {totals.get('activeDays', 0)} 个阅读日")
    lead = "，".join(lead_bits) + "。"

    if peak.get("month"):
        contrast = f"最集中的月份是 {peak['month']}，约 {peak.get('hours',0)} 小时。"
    elif strongest:
        contrast = f"真正留下最多笔记证据的是 {book_label(strongest[0])}。"
    else:
        contrast = "这个周期没有足够密集的数据形成强反差，适合做简短记录而不是强行讲大故事。"

    sections = []
    sections.append({"id": "opening", "heading": "开场", "paragraphs": [lead, contrast]})

    numbers = [
        f"完整读完：{summary.get('completed',0)} 本",
        f"正在读：{summary.get('reading',0)} 本",
        f"浅尝：{summary.get('shallow',0)} 本",
        f"重读：{summary.get('reread',0)} 本",
    ]
    if totals.get("dailyCoverageAvailable"):
        numbers.extend([f"阅读时长：{totals.get('hours',0)} 小时", f"阅读天数：{totals.get('activeDays',0)} 天"])
    if top_categories:
        numbers.append(f"笔记最集中的类别：{top_categories[0].get('category')}（{top_categories[0].get('periodNotes')} 条）")
    sections.append({"id": "numbers", "heading": "数字盘点", "bullets": numbers})

    book_paragraphs = []
    for row in strongest:
        notes = int(row.get("periodNotes") or 0)
        reviews = int(row.get("periodReviews") or 0)
        book_paragraphs.append(
            f"{book_label(row)}：这个周期留下 {notes} 条笔记证据，其中 {reviews} 条是我自己写的想法。"
            "这能证明投入，但不能自动证明‘它改变了我’。这里应补上我现在仍认可的一点、不同意的一点，或真正带走的方法。"
        )
    if not book_paragraphs:
        book_paragraphs = ["这个周期没有足够的单书笔记证据，不强行挑‘最值得讲的三本’。"]
    sections.append({"id": "books", "heading": "最值得讲的书", "paragraphs": book_paragraphs})

    if shift and shift.get("changed"):
        shift_text = (
            f"数据上，前半段笔记最多的类别是“{shift.get('firstHalfTopCategory')}”，后半段变成“{shift.get('secondHalfTopCategory')}”。"
            "这只能说明关注分布发生了变化，不能从数据本身知道原因。"
            "【待补：当时发生了什么？是工作问题、现实事件、某一本书，还是只是偶然连续阅读？】"
        )
    else:
        shift_text = "这个周期没有足够证据支持明显的主题转向，不为了叙事效果硬造‘兴趣改变’。"
    sections.append({"id": "shift", "heading": "一个可能的转向", "paragraphs": [shift_text]})

    if stalled:
        s = stalled[0]
        imperfection = (
            f"不完美的一面也很具体：{book_label(s)} 停在 {s.get('progress')}%，到周期结束已经约 {s.get('daysStaleAtPeriodEnd')} 天没有活动。"
            "数据不知道我为什么停下，所以这里不替自己找理由。真正要决定的是：继续，还是正式放下。"
        )
    elif summary.get("shallow", 0):
        imperfection = f"这个周期还有 {summary.get('shallow')} 本只是浅尝。收藏和打开并不等于真正读过，这部分不包装成阅读成果。"
    else:
        imperfection = "这个周期没有明显的 30–70% 长期卡住项；仍应检查有没有‘读完但没有留下任何自己的想法’的轻读。"
    sections.append({"id": "imperfection", "heading": "没有完成得很漂亮的部分", "paragraphs": [imperfection]})

    goal = concrete_goal(ctx)
    sections.append({"id": "next", "heading": "给下个周期的自己", "paragraphs": [goal]})

    return {
        "version": "1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "platform": selected,
        "platformSpec": spec,
        "title": title,
        "sections": sections,
        "factBoundary": {
            "causalReasonsInvented": False,
            "rawNoteBodiesIncluded": False,
            "humanEditsRequiredForPersonalMeaning": True,
        },
        "editingPrompts": [
            "给最值得讲的书补：我现在仍认可什么、不同意什么、真正带走了什么。",
            "如果主题发生转向，补真实原因；不知道就保留不知道。",
            "检查下一周期目标是否足够具体到可以在周期结束时判断完成/未完成。",
        ],
    }


def to_markdown(draft: dict) -> str:
    lines = [f"# {draft['title']}", "", f"> 平台：{draft['platformSpec'].get('label')} · 建议篇幅 {draft['platformSpec'].get('length')} 字", ""]
    for sec in draft.get("sections") or []:
        lines.extend([f"## {sec.get('heading')}", ""])
        for p in sec.get("paragraphs") or []:
            lines.extend([str(p), ""])
        for bullet in sec.get("bullets") or []:
            lines.append(f"- {bullet}")
        if sec.get("bullets"):
            lines.append("")
    lines.extend(["---", "", "## 编辑前检查", ""])
    lines.extend([f"- {x}" for x in draft.get("editingPrompts") or []])
    return "\n".join(lines).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser(description="Build an evidence-bounded reading-review draft.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--platform", default="")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--markdown", type=Path, default=None)
    a = p.parse_args()
    ctx = json.loads(a.input.read_text(encoding="utf-8"))
    draft = build_draft(ctx, a.platform or None)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = a.markdown or a.output.with_suffix(".md")
    md_path.write_text(to_markdown(draft), encoding="utf-8")
    print(f"narrative-review-draft: {a.output} | platform={draft['platform']} markdown={md_path}")


if __name__ == "__main__":
    main()
