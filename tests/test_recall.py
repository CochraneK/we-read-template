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


queue_mod = load_module("weread_recall_queue", ROOT / "scripts" / "build_recall_queue.py")
render_mod = load_module("weread_recall_render", ROOT / "scripts" / "renderers" / "recall.py")


class RecallTests(unittest.TestCase):
    def context(self):
        now = 2_000_000
        return now, {
            "privacy": {"includePrivate": False},
            "books": [
                {
                    "bookId": "a",
                    "title": "A书",
                    "author": "甲",
                    "reviews": [
                        {"chapter": "一", "text": "旧想法", "createTime": now - 100 * queue_mod.DAY},
                        {"chapter": "二", "text": "另一个旧想法", "createTime": now - 90 * queue_mod.DAY},
                    ],
                    "marks": [
                        {"chapter": "三", "text": "旧划线", "createTime": now - 80 * queue_mod.DAY}
                    ],
                },
                {
                    "bookId": "b",
                    "title": "B书",
                    "author": "乙",
                    "reviews": [],
                    "marks": [
                        {"chapter": "一", "text": "第二本书证据", "createTime": now - 70 * queue_mod.DAY}
                    ],
                },
            ],
        }

    def test_queue_respects_age_and_book_diversity(self):
        now, context = self.context()
        queue = queue_mod.build_queue(context, limit=4, min_age_days=30, max_per_book=2, now_ts=now)
        self.assertEqual(queue["coverage"]["selected"], 3)
        self.assertEqual(queue["coverage"]["books"], 2)
        self.assertEqual(sum(1 for x in queue["items"] if x["bookId"] == "a"), 2)
        self.assertEqual(queue["items"][0]["kind"], "review")

    def test_recent_items_are_excluded(self):
        now, context = self.context()
        context["books"][1]["marks"][0]["createTime"] = now - 5 * queue_mod.DAY
        candidates = queue_mod.collect_candidates(context, now_ts=now, min_age_days=30)
        self.assertFalse(any(x["bookId"] == "b" for x in candidates))

    def test_renderer_hides_source_until_reveal(self):
        now, context = self.context()
        queue = queue_mod.build_queue(context, limit=2, min_age_days=30, max_per_book=1, now_ts=now)
        html = render_mod.render_html(queue)
        self.assertIn("阅读回顾卡", html)
        self.assertIn("查看原始证据", html)
        self.assertIn("不看原文", html)
        self.assertIn("<details>", html)


if __name__ == "__main__":
    unittest.main()
