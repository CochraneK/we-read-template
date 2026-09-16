#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信读书 - 全量笔记/划线导出

- 先拉 /user/notebooks 拿到所有有笔记的书
- 对每本书调 /book/bookmarklist（划线）+ /review/list/mine（想法/点评，含翻页）
- 产出 weread_notes_export.json（完整结构化）+ weread_notes_export.md（按书/章节分组的可读版）
- 带重试、进度日志、每 20 本落盘一次（断点保护）

默认数据目录为仓库根目录下的 data/；可通过 WEREAD_DATA_DIR 覆盖。
"""
from pathlib import Path
import datetime
import json
import os
import time
import urllib.error
import urllib.request

URL = "https://i.weread.qq.com/api/agent/gateway"
SV = "1.0.4"
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DATA.mkdir(parents=True, exist_ok=True)

NB_PATH = DATA / "weread_notebooks.json"
JSON_PATH = DATA / "weread_notes_export.json"
MD_PATH = DATA / "weread_notes_export.md"
LOG_PATH = DATA / "export_progress.log"


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def api_key():
    key = os.environ.get("WEREAD_API_KEY", "").strip()
    if not key:
        raise SystemExit("ERROR: WEREAD_API_KEY 未设置")
    if not key.startswith("wrk-"):
        log("WARNING: WEREAD_API_KEY 不以 wrk- 开头，请确认使用的是微信读书 Agent Gateway Key")
    return key


def call(body, tries=3):
    key = api_key()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                URL,
                data=json.dumps(body).encode("utf-8"),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)

            if data.get("upgrade_info"):
                msg = data["upgrade_info"].get("message") if isinstance(data["upgrade_info"], dict) else data["upgrade_info"]
                raise RuntimeError(f"微信读书 Skill 需要升级: {msg}")
            if data.get("errcode", 0) != 0:
                raise RuntimeError(f"gateway errcode={data.get('errcode')}: {data.get('errmsg', 'unknown error')}")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, RuntimeError) as e:
            last = e
            if i + 1 < tries:
                time.sleep(1.0 + i)
    raise last


def dump_json(value, path):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_notebooks():
    if NB_PATH.exists():
        log(f"复用已拉取的 notebooks 列表: {NB_PATH}")
        return json.loads(NB_PATH.read_text(encoding="utf-8"))

    books = []
    last_sort = None
    while True:
        body = {"api_name": "/user/notebooks", "count": 100, "skill_version": SV}
        if last_sort is not None:
            body["lastSort"] = last_sort
        data = call(body)
        page = data.get("books", [])
        books.extend(page)
        if data.get("hasMore") != 1 or not page:
            break
        last_sort = page[-1].get("sort")
        if last_sort is None:
            log("WARNING: hasMore=1 但最后一项没有 sort，停止翻页以避免死循环")
            break

    dump_json(books, NB_PATH)
    log(f"notebooks 拉取完成: {len(books)} 本")
    return books


def chapter_map(chapters):
    return {c.get("chapterUid"): c.get("title", "") for c in (chapters or [])}


def export_book(book_row):
    book = book_row.get("book") or {}
    bid = book_row.get("bookId") or book.get("bookId")
    title = book.get("title", "?")
    author = book.get("author", "")
    if not bid:
        raise ValueError(f"书籍缺少 bookId: {title}")

    out = {
        "bookId": bid,
        "title": title,
        "author": author,
        "noteCount": book_row.get("noteCount", 0),
        "reviewCount": book_row.get("reviewCount", 0),
        "bookmarkCount": book_row.get("bookmarkCount", 0),
        "marks": [],
        "reviews": [],
    }

    try:
        data = call({"api_name": "/book/bookmarklist", "bookId": bid, "skill_version": SV})
        chapters = chapter_map(data.get("chapters"))
        for mark in data.get("updated") or []:
            out["marks"].append(
                {
                    "chapter": chapters.get(mark.get("chapterUid"), ""),
                    "text": mark.get("markText", ""),
                    "createTime": mark.get("createTime", 0),
                }
            )
    except Exception as e:
        log(f"  ! 划线失败 {title}: {e}")

    try:
        synckey = 0
        while True:
            data = call(
                {
                    "api_name": "/review/list/mine",
                    "bookid": bid,
                    "count": 500,
                    "synckey": synckey,
                    "skill_version": SV,
                }
            )
            for item in data.get("reviews") or []:
                review = item.get("review", {}) if isinstance(item, dict) else {}
                out["reviews"].append(
                    {
                        "chapter": review.get("chapterName", "") or "",
                        "abstract": review.get("abstract", ""),
                        "content": review.get("content", ""),
                        "createTime": review.get("createTime", 0),
                        "star": review.get("star", -1),
                    }
                )
            if data.get("hasMore") != 1:
                break
            next_key = data.get("synckey")
            if not next_key or next_key == synckey:
                break
            synckey = next_key
    except Exception as e:
        log(f"  ! 想法失败 {title}: {e}")

    return out


def build_md(results, total_marks, total_reviews, nbooks):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 微信读书 全量笔记/划线导出\n",
        f"> 导出时间：{now}　|　含笔记的书：**{nbooks}** 本　|　划线：**{total_marks}** 条　|　想法/点评：**{total_reviews}** 条\n",
        "\n---\n",
    ]
    for item in results:
        lines.append(f"\n## {item['title']}　*{item['author']}*\n")
        lines.append(
            f"- 划线 {len(item['marks'])} 条 · 想法/点评 {len(item['reviews'])} 条 · "
            f"书签 {item['bookmarkCount']} 个（书签仅计数，不可导出内容）\n"
        )
        if item["marks"]:
            lines.append("\n### 划线\n")
            for mark in item["marks"]:
                chapter = f"〔{mark['chapter']}〕 " if mark["chapter"] else ""
                lines.append(f"> {chapter}{mark['text']}\n")
        if item["reviews"]:
            lines.append("\n### 想法 / 点评\n")
            for review in item["reviews"]:
                chapter = f"〔{review['chapter']}〕 " if review["chapter"] else ""
                if review["abstract"]:
                    lines.append(f"- {chapter}原文：_{review['abstract']}_")
                    lines.append(f"  - 想法：{review['content']}\n")
                else:
                    lines.append(f"- {chapter}{review['content']}\n")
    MD_PATH.write_text("".join(lines), encoding="utf-8")
    log(f"MD 写入: {MD_PATH}")


def main():
    api_key()
    LOG_PATH.write_text("", encoding="utf-8")
    log(f"=== 开始全量导出，数据目录: {DATA} ===")
    books = fetch_notebooks()
    results = []

    for i, book_row in enumerate(books, 1):
        try:
            result = export_book(book_row)
            results.append(result)
            if i % 20 == 0:
                dump_json(results, JSON_PATH)
                log(
                    f"进度 {i}/{len(books)} 已落盘 "
                    f"(本本笔记 {len(result['marks'])} 想法 {len(result['reviews'])})"
                )
        except Exception as e:
            title = (book_row.get("book") or {}).get("title", "?")
            log(f"  !! 整本失败跳过 {title}: {e}")
        time.sleep(0.12)

    dump_json(results, JSON_PATH)
    total_marks = sum(len(item["marks"]) for item in results)
    total_reviews = sum(len(item["reviews"]) for item in results)
    log(f"全部完成: {len(results)} 本 / 划线 {total_marks} / 想法点评 {total_reviews}")
    build_md(results, total_marks, total_reviews, len(results))
    log("Markdown 生成完毕")


if __name__ == "__main__":
    main()
