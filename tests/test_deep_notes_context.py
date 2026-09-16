#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "build_deep_notes_context.py"
spec = importlib.util.spec_from_file_location("build_deep_notes_context", MODULE)
deep = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(deep)


class DeepNotesContextTests(unittest.TestCase):
    def sample(self):
        return {
            "privacy": {"includePrivate": False},
            "books": [
                {
                    "bookId": "a", "title": "A", "author": "甲", "category": "认知",
                    "marks": [
                        {"chapter": "一", "text": "这是一个会重复出现的划线文本"},
                        {"chapter": "二", "text": "短句测试内容"},
                    ],
                    "reviews": [
                        {"chapter": "二", "text": "我的想法"},
                        {"chapter": "三", "text": "另一个想法"},
                    ],
                },
                {
                    "bookId": "b", "title": "B", "author": "乙", "category": "认知",
                    "marks": [{"chapter": "开篇", "text": "这是一个会重复出现的划线文本"}],
                    "reviews": [],
                },
            ],
        }

    def test_builds_private_duplicate_and_interplay_evidence(self):
        result = deep.build_context(self.sample())
        self.assertFalse(result["privacy"]["publicPageSafe"])
        self.assertTrue(result["privacy"]["containsRawEvidence"])
        self.assertEqual(result["duplicateHighlightCount"], 1)
        self.assertEqual(result["duplicateHighlights"][0]["count"], 2)
        self.assertEqual(result["markReviewInterplay"]["both"], 1)
        self.assertEqual(result["markReviewInterplay"]["onlyMark"], 2)
        self.assertEqual(result["markReviewInterplay"]["onlyReview"], 1)

    def test_length_buckets_and_thought_rich_books_are_deterministic(self):
        result = deep.build_context(self.sample())
        buckets = {row["label"]: row["count"] for row in result["highlightLength"]["buckets"]}
        self.assertEqual(sum(buckets.values()), 3)
        self.assertEqual(result["thoughtRichBooks"][0]["bookId"], "a")
        self.assertGreater(result["thoughtRichBooks"][0]["reviewShare"], 0)
        self.assertIn("method", result["chapterPosition"])


if __name__ == "__main__":
    unittest.main()
