#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_alchemy_context.py"
spec = importlib.util.spec_from_file_location("build_alchemy_context", MODULE_PATH)
alchemy = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(alchemy)


def sample_book(book_id="b1", title="认知科学导论", category="认知科学", marks=2, reviews=1):
    return {
        "bookId": book_id,
        "title": title,
        "author": "作者",
        "category": category,
        "noteCount": marks + reviews,
        "marks": [
            {"chapter": "第一章", "text": f"作者原文 {i}", "createTime": 10 + i}
            for i in range(marks)
        ],
        "reviews": [
            {"chapter": "第一章", "abstract": "摘要", "text": f"我的想法 {i}", "createTime": 20 + i}
            for i in range(reviews)
        ],
    }


class AlchemyContextTests(unittest.TestCase):
    def test_single_book_separates_source_text_and_user_thought(self):
        result = alchemy.build_context({"books": [sample_book()]}, book_id="b1")
        self.assertEqual(result["mode"], "book")
        self.assertFalse(result["privacy"]["publicPageSafe"])
        self.assertTrue(result["privacy"]["containsRawEvidence"])
        chapter = result["books"][0]["chapters"][0]
        self.assertEqual(chapter["marks"][0]["role"], "source_text")
        self.assertEqual(chapter["reviews"][0]["role"], "user_thought")
        self.assertFalse(result["landscape"]["requiresScopeConfirmation"])
        self.assertTrue(result["alchemyContract"]["readyForSynthesis"])

    def test_topic_mode_requires_scope_gate_when_evidence_is_large(self):
        source = {
            "books": [
                sample_book("a", "认知科学A", marks=30, reviews=0),
                sample_book("b", "认知科学B", marks=25, reviews=1),
            ]
        }
        result = alchemy.build_context(source, topic="认知科学", gate_threshold=50)
        self.assertEqual(result["mode"], "topic")
        self.assertEqual(result["coverage"]["evidence"], 56)
        self.assertTrue(result["landscape"]["requiresScopeConfirmation"])
        self.assertFalse(result["alchemyContract"]["readyForSynthesis"])

    def test_topic_mode_keeps_book_attribution(self):
        result = alchemy.build_context(
            {"books": [sample_book("a", "脑科学", category="神经科学")]},
            topic="神经科学",
        )
        row = result["landscape"]["byBook"][0]
        self.assertEqual(row["bookId"], "a")
        self.assertEqual(row["title"], "脑科学")
        self.assertGreater(row["evidence"], 0)

    def test_exact_title_wins_but_ambiguous_partial_requires_book_id(self):
        source = {
            "books": [
                sample_book("a", "思考A"),
                sample_book("b", "思考B"),
                sample_book("c", "精确书名"),
            ]
        }
        exact = alchemy.build_context(source, book_title="精确书名")
        self.assertEqual(exact["books"][0]["bookId"], "c")
        with self.assertRaises(ValueError):
            alchemy.build_context(source, book_title="思考")


if __name__ == "__main__":
    unittest.main()
