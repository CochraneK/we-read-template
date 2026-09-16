#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


search = load_module("weread_search", ROOT / "scripts" / "build_search_index.py")


class SearchIndexTests(unittest.TestCase):
    def context(self):
        return {
            "privacy": {"includePrivate": False},
            "books": [
                {
                    "bookId": "1",
                    "title": "测试之书",
                    "author": "作者甲",
                    "category": "心理",
                    "marks": [
                        {"chapter": "第一章", "text": "真正的自由来自清醒的选择。", "createTime": 100}
                    ],
                    "reviews": [
                        {"chapter": "第二章", "abstract": "关于选择", "text": "我更关心如何行动。", "createTime": 200}
                    ],
                }
            ],
        }

    def test_documents_include_book_mark_and_review(self):
        docs = list(search.iter_documents(self.context()))
        self.assertEqual([d["kind"] for d in docs], ["book", "mark", "review"])

    def test_search_supports_cjk_substring_and_kind_filter(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "search.sqlite"
            meta = search.build_index(self.context(), db)
            self.assertEqual(meta["documents"], 3)
            results = search.search_index(db, "自由", limit=10)
            self.assertTrue(any(r["kind"] == "mark" for r in results))
            filtered = search.search_index(db, "选择", limit=10, kind="review")
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["kind"], "review")

    def test_empty_query_returns_nothing(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "search.sqlite"
            search.build_index(self.context(), db)
            self.assertEqual(search.search_index(db, ""), [])


if __name__ == "__main__":
    unittest.main()
