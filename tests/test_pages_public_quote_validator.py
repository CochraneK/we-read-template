#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "validate_pages_output.py"
spec = importlib.util.spec_from_file_location("validate_pages_output_public_quotes", MODULE)
validator = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(validator)


def policy(candidate_count=1):
    return {
        "enabled": True,
        "userAuthorized": True,
        "source": "marks_only",
        "reviewsPublished": False,
        "fullRawPublished": False,
        "allNonEmptyMarksMayBeSampled": True,
        "candidateCount": candidate_count,
        "maxCharsPerExcerpt": 90,
        "maxPerBook": 1,
        "maxTotal": 48,
    }


def payload(item):
    return {
        "publicQuotes": {
            "policy": policy(1),
            "count": 1,
            "items": [item],
        }
    }


class PublicQuoteValidatorTests(unittest.TestCase):
    def test_allows_one_short_authorized_mark(self):
        report = payload({
            "bookId": "b1", "title": "书", "excerpt": "一条短划线摘录。",
            "truncated": False, "sourceKind": "mark",
        })
        allowed, count = validator.validate_public_quotes(report, '<section id="public-quotes"></section>')
        self.assertEqual(count, 1)
        self.assertIn("一条短划线摘录。", allowed)

    def test_rejects_review_text(self):
        report = payload({
            "bookId": "b1", "title": "书", "excerpt": "这是我的想法。",
            "truncated": False, "sourceKind": "review",
        })
        with self.assertRaises(ValueError):
            validator.validate_public_quotes(report, '<section id="public-quotes"></section>')

    def test_rejects_overlong_excerpt(self):
        report = payload({
            "bookId": "b1", "title": "书", "excerpt": "长" * 121,
            "truncated": True, "sourceKind": "mark",
        })
        with self.assertRaises(ValueError):
            validator.validate_public_quotes(report, '<section id="public-quotes"></section>')

    def test_rejects_second_quote_from_same_book(self):
        report = {
            "publicQuotes": {
                "policy": policy(2),
                "count": 2,
                "items": [
                    {"bookId": "b1", "excerpt": "第一条划线。", "truncated": False, "sourceKind": "mark"},
                    {"bookId": "b1", "excerpt": "第二条划线。", "truncated": False, "sourceKind": "mark"},
                ],
            }
        }
        with self.assertRaises(ValueError):
            validator.validate_public_quotes(report, '<section id="public-quotes"></section>')


if __name__ == "__main__":
    unittest.main()
