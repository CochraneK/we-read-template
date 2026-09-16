#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_reading_path_context.py"
spec = importlib.util.spec_from_file_location("build_reading_path_context", MODULE_PATH)
path_builder = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(path_builder)


def book(book_id, title, notes, *, category="神经科学", update=100):
    return {
        "bookId": book_id,
        "title": title,
        "author": "作者",
        "category": category,
        "noteCount": notes,
        "updateTime": update,
    }


def advisor_with_books(*books):
    bands = {"deep20Plus": [], "medium10To19": [], "light3To9": [], "glance1To2": [], "noNotes": []}
    for item in books:
        n = item["noteCount"]
        if n >= 20:
            key = "deep20Plus"
        elif n >= 10:
            key = "medium10To19"
        elif n >= 3:
            key = "light3To9"
        elif n >= 1:
            key = "glance1To2"
        else:
            key = "noNotes"
        bands[key].append(item)
    return {"privacy": {"includePrivate": False}, "coverage": {}, "facts": {"depthBands": bands}}


class ReadingPathContextTests(unittest.TestCase):
    def test_shelf_matches_without_note_evidence_are_zero_level(self):
        result = path_builder.build_context(
            advisor_with_books(book("a", "神经科学入门", 0)), "神经科学"
        )
        self.assertEqual(result["levelAssessment"]["suggestedLevel"], "zero")
        self.assertEqual(result["evidence"]["matchedBookCount"], 1)
        self.assertEqual(result["evidence"]["notedBookCount"], 0)
        self.assertTrue(result["levelAssessment"]["requiresUserConfirmation"])

    def test_one_or_two_weak_topic_books_are_beginner(self):
        result = path_builder.build_context(
            advisor_with_books(
                book("a", "脑与认知", 2),
                book("b", "神经科学导论", 6),
            ),
            "神经科学",
            keywords=["脑"],
        )
        self.assertEqual(result["levelAssessment"]["suggestedLevel"], "beginner")
        self.assertFalse(result["levelAssessment"]["suggestSwitchToAdvisor"])

    def test_three_engaged_books_stop_at_intermediate_and_offer_advisor(self):
        result = path_builder.build_context(
            advisor_with_books(
                book("a", "神经科学A", 30),
                book("b", "神经科学B", 15),
                book("c", "神经科学C", 7),
            ),
            "神经科学",
        )
        level = result["levelAssessment"]
        self.assertEqual(level["suggestedLevel"], "intermediate")
        self.assertTrue(level["suggestSwitchToAdvisor"])
        self.assertTrue(level["advancedRequiresContentEvidence"])
        self.assertNotEqual(level["suggestedLevel"], "advanced")

    def test_contract_requires_confirmation_checkpoints_and_minimum_version(self):
        result = path_builder.build_context(advisor_with_books(), "AI")
        contract = result["pathContract"]
        self.assertFalse(contract["readyForBookSelection"])
        self.assertTrue(contract["mustConfirmLevelBeforeSelection"])
        self.assertEqual(contract["targetBookCount"], {"min": 6, "max": 8})
        self.assertEqual([s["id"] for s in contract["stages"]], ["intro", "framework", "frontier"])
        self.assertTrue(all(s["feynmanCheckpoint"] for s in contract["stages"]))
        self.assertTrue(contract["minimumVersionRequired"])
        self.assertEqual(contract["timeEstimateRule"]["wordsPerMinute"], 300)
        self.assertTrue(contract["availabilityRule"]["mustVerifyCurrentWereadAvailability"])

    def test_empty_topic_is_rejected(self):
        with self.assertRaises(ValueError):
            path_builder.build_context(advisor_with_books(), "  ")


if __name__ == "__main__":
    unittest.main()
