#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_advisor_context.py"
spec = importlib.util.spec_from_file_location("build_advisor_context", MODULE_PATH)
advisor = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(advisor)


DAY = 86400
AS_OF = 2_000_000_000


def book(book_id, title, notes, *, in_shelf=True, category="主题A", days_ago=5, progress=50):
    return {
        "bookId": book_id,
        "title": title,
        "author": "作者",
        "category": category,
        "noteCount": notes,
        "markCount": notes,
        "reviewCount": 0,
        "progress": progress,
        "updateTime": AS_OF - days_ago * DAY,
        "privacyKnown": in_shelf,
    }


class AdvisorContextTests(unittest.TestCase):
    def test_depth_bands_hidden_deep_and_recent_windows(self):
        source = {
            "privacy": {"includePrivate": False},
            "coverage": {"contextBooks": 6},
            "books": [
                book("deep", "深读", 25, days_ago=2),
                book("medium", "中读", 12, days_ago=10),
                book("light", "轻读", 6, days_ago=40),
                book("glance", "浅尝", 1, days_ago=4),
                book("shelf", "放着", 0, days_ago=100),
                book("hidden", "隐藏深读", 15, in_shelf=False, category="主题B", days_ago=3),
            ],
        }
        result = advisor.build_context(source, as_of=AS_OF)
        facts = result["facts"]
        self.assertEqual([b["bookId"] for b in facts["depthBands"]["deep20Plus"]], ["deep"])
        self.assertEqual({b["bookId"] for b in facts["depthBands"]["medium10To19"]}, {"hidden", "medium"})
        self.assertEqual([b["bookId"] for b in facts["hiddenDeepBooks"]], ["hidden"])
        self.assertEqual({b["bookId"] for b in facts["recent7d"]}, {"deep", "glance", "hidden"})
        self.assertEqual({b["bookId"] for b in facts["recent30d"]}, {"deep", "medium", "glance", "hidden"})

    def test_category_engagement_and_shelf_heavy_gap(self):
        source = {
            "books": [
                book("a", "A", 0, category="囤书类", days_ago=90),
                book("b", "B", 0, category="囤书类", days_ago=90),
                book("c", "C", 0, category="囤书类", days_ago=90),
                book("d", "D", 20, category="深读类", days_ago=2),
            ]
        }
        result = advisor.build_context(source, as_of=AS_OF)
        gaps = result["facts"]["shelfHeavyLowEngagementCategories"]
        self.assertEqual(gaps[0]["category"], "囤书类")
        self.assertEqual(gaps[0]["engagementRate"], 0.0)
        self.assertEqual(result["facts"]["deepCategories"][0]["category"], "深读类")

    def test_context_stops_before_recommendation(self):
        result = advisor.build_context({"books": []}, as_of=AS_OF)
        contract = result["advisorContract"]
        self.assertFalse(contract["readyForRecommendation"])
        self.assertTrue(contract["mustVerifyAvailability"])
        self.assertIn("school_or_viewpoint", contract["gapAxesRequiringEnrichment"])
        self.assertTrue(any("must not itself recommend" in x for x in result["guardrails"]))


if __name__ == "__main__":
    unittest.main()
