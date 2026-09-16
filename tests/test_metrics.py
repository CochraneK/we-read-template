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


metrics = load_module("weread_metrics", ROOT / "scripts" / "metrics.py")


class MetricsTests(unittest.TestCase):
    def test_category_participation_counts_union_not_sum(self):
        shelf = [
            {"bookId": "1", "title": "A", "category": "心理"},
            {"bookId": "2", "title": "B", "category": "历史"},
        ]
        notebooks = [
            {"bookId": "1", "title": "A", "category": "旧分类", "marks": [{"text": "x"}], "reviews": [{"content": "y"}]},
            {"bookId": "3", "title": "C", "category": "心理", "marks": [{"text": "z"}], "reviews": []},
        ]
        result = metrics.category_participation(shelf, notebooks)
        self.assertEqual(result["uniqueBooks"], 3)
        self.assertEqual(result["bookCount"]["心理"], 2)
        self.assertEqual(result["bookCount"]["历史"], 1)
        self.assertNotIn("旧分类", result["bookCount"])
        self.assertEqual(result["noteCount"]["心理"], 3)
        psychological = next(row for row in result["rows"] if row["category"] == "心理")
        self.assertEqual(psychological["notesPerBook"], 1.5)

    def test_engagement_summary_separates_overlap(self):
        shelf = [{"bookId": "1"}, {"bookId": "2"}]
        notebooks = [{"bookId": "2"}, {"bookId": "3"}]
        result = metrics.engagement_summary(shelf, notebooks)
        self.assertEqual(result, {
            "shelfBooks": 2,
            "notebookBooks": 2,
            "shelfAndNotes": 1,
            "notesOnlyBooks": 1,
            "shelfOnlyBooks": 1,
        })


if __name__ == "__main__":
    unittest.main()
