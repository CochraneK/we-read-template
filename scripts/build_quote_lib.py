#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从微信读书划线筛选金句候选，打分、去重并给出版权人工复核提示。

默认输入：data/weread_notes_export.json
默认输出：quote_lib/金句库.json + quote_lib/金句库_top60.md

纯标准库，无需联网。`public_domain` 字段仅为历史兼容的规则候选标记，
绝不应被视为法律结论；出版/公开传播前必须人工核验具体版本、译本与地区版权状态。
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_SRC = DATA_DIR / "weread_notes_export.json"
DEFAULT_OUT = ROOT / "quote_lib"

# 仅作“可能需要优先核验为公版”的候选集合，不构成法律判断。
# 同一作者不同作品/译本/整理本可能具有不同权利状态。
PD_AUTHORS = {
    "老子","李耳","庄周","庄子","列子","列御寇","孔子","孔丘","仲尼","孟轲","孟子",
    "荀况","荀子","韩非","墨翟","墨子","司马迁","李白","杜甫","王维","白居易","苏轼",
    "苏东坡","辛弃疾","李清照","曹操","陶渊明","屈原","王阳明","王守仁","曹雪芹",
    "罗贯中","施耐庵","吴承恩","蒲松龄","关汉卿","汤显祖","鲁迅","周树人","王国维",
    "莎士比亚","托尔斯泰","列夫·托尔斯泰","陀思妥耶夫斯基","费奥多尔·陀思妥耶夫斯基",
    "歌德","卡夫卡","加缪","阿尔贝·加缪","叔本华","尼采","伏尔泰","卢梭","培根",
    "蒙田","梭罗","爱默生","纪伯伦","泰戈尔","芥川龙之介","夏目漱石","川端康成",
    "太宰治","三岛由纪夫","紫式部","清少纳言","荷马","但丁","塞万提斯","雨果",
    "巴尔扎克","狄更斯","福楼拜","莫泊桑","契诃夫","欧·亨利","海明威","马克·吐温",
    "屠格涅夫","果戈里","易卜生","安徒生","王尔德",
}
PD_TITLE_HINTS = [
    "论语","道德经","老子","庄子","孟子","荀子","韩非子","墨子","列子","史记",
    "诗经","楚辞","周易","易经","尚书","礼记","大学","中庸","资治通鉴","红楼梦",
    "三国演义","西游记","水浒传","聊斋志异","世说新语","唐诗","宋词","千家诗",
    "金刚经","心经","坛经","孙子兵法","鬼谷子","古文观止",
]

WISDOM = [
    "人生","生命","活着","生活","命运","意义","自我","自己","本真","真实","伪装",
    "孤独","自由","灵魂","内心","爱","心","情感","思念","温柔","时间","时光","岁月",
    "当下","现在","过去","未来","青春","知识","真理","智慧","思考","理解","认知",
    "无知","学习","读书","朋友","他人","陪伴","宽容","痛苦","苦难","悲伤","绝望",
    "勇气","坚强","挫折","成长","遗憾","希望","现实","理想","人性","平静","选择",
    "死亡","记忆","幸福","平和","独立","尊严","信仰","世界","平凡","伟大",
    "坚持","善良","真诚","放下","释怀","故乡","远方","包容","控制","永恒",
    "正义","平等","诚实","原谅","谦逊","清醒","热爱","等待","失去","得到",
]
THEME_MAP = {
    "人生": ["人生","生命","活着","生活","命运","意义","遗憾","平凡","伟大"],
    "自我": ["自我","自己","本真","真实","伪装","孤独","自由","灵魂","内心","独立","尊严"],
    "情感": ["爱","心","情感","思念","温柔","喜欢","幸福","悲伤"],
    "时间": ["时间","时光","岁月","当下","现在","过去","未来","青春"],
    "认知": ["知识","真理","智慧","思考","理解","认知","无知","学习","读书"],
    "关系": ["朋友","他人","陪伴","宽容","理解","人际"],
    "苦难": ["痛苦","苦难","悲伤","绝望","勇气","坚强","挫折","成长"],
    "社会": ["社会","时代","历史","权力","公平","世界","人性","现实","理想"],
}
NOISE = re.compile(r"z-lib|1lib|\.pdf|http|https|证书|下载|微盘|百度网盘|pan\.baidu|kindle|epub", re.I)
YEAR = re.compile(r"(19|20)\d\d")
QUOTE_OPEN = ("「", '"', "“", "'", "‘", "『")
QUOTE_CLOSE = ("」", '"', "”", "'", "’", "』")
PLOT_START = re.compile(r"^(他|她|它|他们|她们|它们|那人|此人|这家|本书|小说|故事|这天|那天|这时|那时)")


def clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^[\s"\'「」『』“”‘’]+', "", text)
    text = re.sub(r'[\s"\'「」『』“”‘’]+$', "", text)
    text = re.sub(r'^[。，、；：！？…—~·\s]+', "", text)
    text = re.sub(r'[。，、；：！？…—~·\s]+$', "", text)
    return text


def theme_of(text: str) -> str:
    for theme, words in THEME_MAP.items():
        if any(word in text for word in words):
            return theme
    return "其他"


def clean_title(title: str) -> str:
    title = title.strip()
    match = re.search(r"《([^》]+)》", title)
    if match:
        return match.group(1).strip()
    return re.split(r"[（(【\[]", title)[0].strip()


def score_quote(text: str, has_bookref: bool) -> int:
    score = 0
    length = len(text)
    if 12 <= length <= 26:
        score += 22
    elif 27 <= length <= 38:
        score += 18
    elif 39 <= length <= 50:
        score += 10
    elif 51 <= length <= 64:
        score += 2
    else:
        score -= 15
    score += min(sum(1 for word in WISDOM if word in text), 4) * 6
    if re.search(r"[像如仿佛如同好似犹如]", text):
        score += 7
    if "？" in text or "?" in text:
        score += 7
    if re.search(r"不是.*而是|与其.*不如|不在于.*而在于|越是.*越|与其说.*不如", text):
        score += 8
    if re.search(r"没有.*(就|才|不)|不.*(才|就|也)|并非|不要|不必", text):
        score += 6
    if text.count("，") >= 1 and ("；" in text or text.count("，") >= 2):
        score += 4
    score -= min(text.count("他") + text.count("她") + text.count("它"), 4) * 3
    if has_bookref:
        score -= 3
    if YEAR.search(text):
        score -= 6
    if "（" in text or "(" in text:
        score -= 3
    if PLOT_START.match(text):
        score -= 22
    return max(0, min(100, score))


def copyright_hint(author: str, title: str) -> str:
    """Compatibility values only: `pd` means candidate-for-review, not legal status."""
    author = author.strip()
    if author in PD_AUTHORS or any(hint in title for hint in PD_TITLE_HINTS):
        return "pd"
    return "protected"


def normalize_quote(text: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text))


def build_library(data, select_threshold=30, select_cap=500):
    quotes = []
    insights = []
    for book in data:
        title = clean_title(book.get("title", ""))
        author = book.get("author", "")
        hint = copyright_hint(author, title)
        for mark in book.get("marks", []):
            raw = mark.get("text", "")
            if not raw or NOISE.search(raw):
                continue
            stripped = raw.strip()
            if stripped.startswith(QUOTE_OPEN) and any(char in raw for char in QUOTE_CLOSE):
                continue
            text = clean(raw)
            if not (8 <= len(text) <= 64):
                continue
            if not re.match(r"^[\u4e00-\u9fff我你他它这那一是不没如人在当若有若此]", text):
                continue
            if PLOT_START.match(text):
                continue
            score = score_quote(text, "《" in raw)
            quotes.append({
                "bookId": book.get("bookId"),
                "title": title,
                "author": author,
                "chapter": mark.get("chapter", ""),
                "text": text,
                "score": score,
                "theme": theme_of(text),
                "public_domain": hint,
                "selected": False,
            })
        for review in book.get("reviews", []):
            insights.append({
                "title": title,
                "author": author,
                "chapter": review.get("chapter", ""),
                "abstract": review.get("abstract", ""),
                "content": review.get("content", ""),
                "createTime": review.get("createTime", 0),
            })

    seen = {}
    for quote in quotes:
        key = normalize_quote(quote["text"])
        if not key:
            continue
        if key not in seen or quote["score"] > seen[key]["score"]:
            seen[key] = quote
    dedup = sorted(seen.values(), key=lambda item: item["score"], reverse=True)

    selected = [quote for quote in dedup if quote["score"] >= select_threshold][:select_cap]
    selected_ids = {id(quote) for quote in selected}
    for quote in dedup:
        if id(quote) in selected_ids:
            quote["selected"] = True
            quote["tier"] = "A" if quote["score"] >= 42 else "B"
        else:
            quote["selected"] = False
            quote["tier"] = None

    result = {
        "meta": {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "total_marks": sum(len(book.get("marks", [])) for book in data),
            "candidates_after_filter": len(quotes),
            "after_dedup": len(dedup),
            "selected": len(selected),
            "select_threshold": select_threshold,
            "select_cap": select_cap,
            "pd_selected": sum(1 for quote in selected if quote["public_domain"] == "pd"),
            "insights_count": len(insights),
            "copyright_warning": (
                "public_domain='pd' 仅表示规则筛出的优先人工复核候选，不是法律结论。"
                "出版或公开传播前必须核验具体作品、版本、译本和适用地区的权利状态。"
            ),
            "note": "score 为启发式金句度(0-100)，不代表文学价值或版权安全性。",
        },
        "quotes": dedup,
        "insights": insights,
    }
    return result


def write_outputs(result, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "金句库.json"
    md_path = out_dir / "金句库_top60.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 金句库 Top 60（按金句度排序，人工抽检用）\n"]
    for index, quote in enumerate(result["quotes"][:60], 1):
        lines.append(
            f"{index}. {quote['text']}  \n"
            f"   —— {quote['author']}《{quote['title']}》 "
            f"〔{quote['theme']}·{quote['public_domain']}·{quote['score']}〕\n"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def parse_args():
    parser = argparse.ArgumentParser(description="Build a scored WeRead quote candidate library.")
    parser.add_argument("--input", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--threshold", type=int, default=30)
    parser.add_argument("--cap", type=int, default=500)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"ERROR: missing {args.input}; run scripts/export_notes.py first")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = build_library(data, max(0, min(100, args.threshold)), max(1, args.cap))
    json_path, md_path = write_outputs(result, args.output_dir)
    selected = [quote for quote in result["quotes"] if quote["selected"]]
    theme_count = Counter(quote["theme"] for quote in selected)
    meta = result["meta"]
    print(
        f"候选={meta['candidates_after_filter']} 去重={meta['after_dedup']} "
        f"选中={meta['selected']} 版权候选待复核={meta['pd_selected']}"
    )
    print(f"主题分布(选中): {dict(theme_count)}")
    print(f"已写出 {json_path} 与 {md_path}")


if __name__ == "__main__":
    main()
