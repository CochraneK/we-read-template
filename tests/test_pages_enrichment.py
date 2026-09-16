#!/usr/bin/env python3
from pathlib import Path
import datetime as dt
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


enrichment = load_module("weread_pages_enrichment", ROOT / "scripts" / "pages_enrichment.py")


def write_json(root: Path, name: str, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class PagesEnrichmentTests(unittest.TestCase):
    def make_data(self, root: Path):
        old = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp())
        d1 = int(dt.datetime(2026, 1, 5, tzinfo=dt.timezone.utc).timestamp())  # Monday
        d2 = int(dt.datetime(2026, 1, 6, tzinfo=dt.timezone.utc).timestamp())
        write_json(root, "weread_shelf.json", {"books": [
            {"bookId": "a", "title": "公开书", "author": "甲", "category": "历史", "secret": 0, "cover": "a.jpg", "readUpdateTime": d2},
            {"bookId": "b", "title": "私密书", "author": "乙", "category": "心理", "secret": 1, "cover": "b.jpg", "readUpdateTime": old},
        ]})
        write_json(root, "weread_notebooks.json", [
            {"bookId": "a", "readingProgress": 55, "bookmarkCount": 3, "markedStatus": 0},
            {"bookId": "b", "bookmarkCount": 2, "markedStatus": 1},
        ])
        write_json(root, "weread_notes_export.json", [
            {"bookId": "a", "title": "公开书", "author": "甲",
             "marks": [{"text": "RAW-MARK-A", "createTime": old}, {"text": "RAW-MARK-A2", "createTime": old}],
             "reviews": [{"content": "RAW-REVIEW-A", "createTime": old}]},
            {"bookId": "b", "title": "私密书", "author": "乙",
             "marks": [{"text": "RAW-SECRET", "createTime": old}], "reviews": []},
        ])
        write_json(root, "weread_progress.json", {"a": {"progress": 55, "updateTime": d2}})
        write_json(root, "weread_bookinfo.json", {"a": {"category": "历史"}, "b": {"category": "心理"}})
        write_json(root, "weread_readdata.json", {
            "overall": {
                "totalReadTime": 14400,
                "readDays": 2,
                "preferTime": [3600] + [0] * 23,
                "preferTimeWord": "偏好上午阅读",
                "readRate": 75,
                "wrReadTime": 10800,
                "wrListenTime": 3600,
                "readStat": [{"stat": "读过", "counts": "2本"}],
                "preferCategory": [{"categoryTitle": "历史", "readingTime": 7200, "readingCount": 1, "val": 1}],
                "preferAuthor": [{"name": "甲", "count": 1, "readTime": "2小时"}],
                "preferPublisher": [{"name": "测试出版社", "count": 2}],
                "preferBooks": [{"type": 1, "title": "近期偏爱", "reason": "最近常读", "bookInfo": {"bookId": "a", "title": "公开书", "author": "甲", "cover": "a.jpg"}}],
                "medals": [{"id": "m1", "displayText": "阅读 100 本书籍", "name": "阅读书籍", "ctime": old}],
                "registTime": old,
            },
            "monthly": {
                "2026-01": {"totalReadTime": 10800, "readTimes": {str(d1): 7200, str(d2): 3600}},
                "2026-02": {"totalReadTime": 3600, "readTimes": {}},
                "2026-03": {"totalReadTime": 0, "readTimes": {}},
            },
            "annually": {
                "2026": {"preferBooks": [{"type": 5, "title": "思考最多", "reason": "笔记最多", "bookInfo": {"bookId": "a", "title": "公开书", "author": "甲"}}]}
            },
        })

    def test_official_fields_and_time_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_data(root)
            result = enrichment.build_enrichment(root, include_private=True)
            self.assertEqual(result["clock"][0]["hour"], 6)
            self.assertEqual(result["clock"][0]["seconds"], 3600)
            self.assertEqual(result["readingMode"]["readRate"], 75.0)
            self.assertEqual(result["official"]["publishers"][0]["name"], "测试出版社")
            self.assertEqual(result["official"]["annualPreferBooks"][0]["label"], "思考最多")
            self.assertEqual(result["official"]["medals"][0]["title"], "阅读 100 本书籍")
            self.assertEqual(result["weekday"][0]["hours"], 2.0)

    def test_scope_progress_and_no_raw_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_data(root)
            filtered = enrichment.build_enrichment(root, include_private=False)
            full = enrichment.build_enrichment(root, include_private=True)
            self.assertEqual(len(filtered["bookshelf"]), 1)
            self.assertEqual(len(full["bookshelf"]), 2)
            bins = {x["key"]: x["count"] for x in full["progressFunnel"]["bins"]}
            self.assertEqual(bins["p50_89"], 1)
            self.assertEqual(bins["finished"], 1)
            self.assertEqual(full["fingerprint"]["bookmarks"], 5)
            self.assertGreaterEqual(len(full["recallCandidates"]), 1)
            serialized = json.dumps(full, ensure_ascii=False)
            self.assertNotIn("RAW-MARK-A", serialized)
            self.assertNotIn("RAW-REVIEW-A", serialized)
            self.assertNotIn("RAW-SECRET", serialized)
            self.assertIn("私密书", serialized)


if __name__ == "__main__":
    unittest.main()
