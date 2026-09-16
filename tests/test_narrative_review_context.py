#!/usr/bin/env python3
from datetime import date, datetime, timezone
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_narrative_review_context.py"
spec = importlib.util.spec_from_file_location("build_narrative_review_context", MODULE_PATH)
review = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(review)


def ts(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def book(book_id, title, *, progress, update, finish=0, notes=6, category="主题A"):
    return {
        "bookId": book_id,
        "title": title,
        "author": "作者",
        "category": category,
        "progress": progress,
        "shelfReadUpdateTime": ts(update) if update else 0,
        "finishTime": ts(finish) if finish else 0,
        "recordReadingTime": 7200,
        "noteCount": notes,
        "marks": [{"createTime": ts(update), "text": "x", "chapter": "c"}] if update and notes else [],
        "reviews": [],
    }


class NarrativeReviewContextTests(unittest.TestCase):
    def test_period_classification_keeps_completed_reading_shallow_and_reread_distinct(self):
        source = {
            "books": [
                book("done", "完成", progress=100, update="2026-05-10", finish="2026-05-09"),
                book("reading", "在读", progress=50, update="2026-05-11"),
                book("shallow", "浅尝", progress=2, update="2026-05-12", notes=0),
                book("reread", "重读", progress=100, update="2026-05-13", finish="2025-12-20"),
            ]
        }
        result = review.build_context(source, {}, start=date(2026, 1, 1), end=date(2026, 6, 30))
        self.assertEqual([b["bookId"] for b in result["bookGroups"]["completed"]], ["done"])
        self.assertEqual([b["bookId"] for b in result["bookGroups"]["reading"]], ["reading"])
        self.assertEqual([b["bookId"] for b in result["bookGroups"]["shallow"]], ["shallow"])
        self.assertEqual([b["bookId"] for b in result["bookGroups"]["reread"]], ["reread"])

    def test_daily_read_time_is_deduplicated_and_filtered_to_period(self):
        day1 = str(ts("2026-05-01"))
        day2 = str(ts("2026-05-02"))
        outside = str(ts("2026-04-30"))
        readdata = {
            "monthly": {
                "2026-05": {"readTimes": {day1: 3600, day2: 1800, outside: 999}},
                "duplicate": {"readTimes": {day1: 3000}},
            }
        }
        result = review.build_context(
            {"books": []}, readdata, start=date(2026, 5, 1), end=date(2026, 5, 31)
        )
        self.assertEqual(result["readingTotals"]["seconds"], 5400)
        self.assertEqual(result["readingTotals"]["activeDays"], 2)
        self.assertEqual(result["readingTotals"]["peakMonth"]["month"], "2026-05")

    def test_platform_is_an_explicit_gate(self):
        pending = review.build_context({"books": []}, {}, start=date(2026, 1, 1), end=date(2026, 1, 31))
        self.assertFalse(pending["reviewContract"]["readyForNarrative"])
        self.assertTrue(pending["reviewContract"]["requiresPlatformConfirmation"])
        self.assertEqual(pending["nextStep"]["action"], "confirm_platform")

        ready = review.build_context(
            {"books": []}, {}, start=date(2026, 1, 1), end=date(2026, 1, 31), platform="wechat"
        )
        self.assertTrue(ready["reviewContract"]["readyForNarrative"])
        self.assertEqual(ready["reviewContract"]["platformSpec"]["label"], "公众号")
        self.assertEqual(ready["nextStep"]["action"], "write_narrative")

    def test_focus_shift_is_candidate_not_causal_story(self):
        source = {
            "books": [
                book("a", "A", progress=50, update="2026-01-10", category="主题A"),
                book("b", "B", progress=50, update="2026-06-10", category="主题B"),
            ]
        }
        # Give the second book a later-period note so month buckets differ.
        source["books"][1]["marks"] = [{"createTime": ts("2026-06-10"), "text": "x", "chapter": "c"}]
        result = review.build_context(source, {}, start=date(2026, 1, 1), end=date(2026, 6, 30))
        shift = result["narrativeCandidates"]["focusShiftCandidate"]
        self.assertIsNotNone(shift)
        self.assertTrue(shift["changed"])
        self.assertIn("reason", shift["interpretation"])
        self.assertTrue(result["reviewContract"]["mustNotInventReasonsForFocusShiftOrAbandonment"])


if __name__ == "__main__":
    unittest.main()
