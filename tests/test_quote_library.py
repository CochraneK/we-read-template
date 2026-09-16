#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


quotes = load_module("weread_quotes", ROOT / "scripts" / "build_quote_lib.py")


class QuoteLibraryTests(unittest.TestCase):
    def test_build_library_deduplicates_and_keeps_warning(self):
        data = [
            {
                "bookId": "1",
                "title": "测试书",
                "author": "测试作者",
                "marks": [
                    {"text": "真正的成长，不是得到更多，而是更清楚自己为何选择。", "chapter": "第一章"},
                    {"text": "真正的成长，不是得到更多，而是更清楚自己为何选择。", "chapter": "第二章"},
                ],
                "reviews": [{"content": "我的想法", "chapter": "第一章"}],
            }
        ]
        result = quotes.build_library(data, select_threshold=0, select_cap=10)
        self.assertEqual(result["meta"]["total_marks"], 2)
        self.assertEqual(result["meta"]["after_dedup"], 1)
        self.assertEqual(len(result["insights"]), 1)
        self.assertIn("不是法律结论", result["meta"]["copyright_warning"])
        self.assertTrue(result["quotes"][0]["selected"])

    def test_public_domain_flag_is_only_candidate_hint(self):
        self.assertEqual(quotes.copyright_hint("孔子", "论语"), "pd")
        self.assertEqual(quotes.copyright_hint("测试作者", "测试书"), "protected")

    def test_score_is_bounded(self):
        score = quotes.score_quote("人生不是等待答案，而是在选择中理解自己。", False)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
