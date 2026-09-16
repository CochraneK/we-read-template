#!/usr/bin/env python3
from pathlib import Path
import datetime as dt
import importlib.util
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


insights = load_module("weread_pages_insights_full", ROOT / "scripts" / "pages_insights_full.py")


def write_json(root: Path, name: str, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class FullPagesInsightsTests(unittest.TestCase):
    def test_secret_book_metadata_is_included_but_raw_note_text_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            t1 = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp())
            t2 = int(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp())
            write_json(data, "weread_shelf.json", {"books": [
                {"bookId": "s", "title": "私密书", "author": "作者甲", "category": "心理", "secret": 1},
                {"bookId": "p", "title": "公开书", "author": "作者甲", "category": "历史", "secret": 0},
                {"bookId": "u", "title": "未投入书", "author": "作者乙", "category": "科普", "secret": 0},
            ]})
            write_json(data, "weread_notebooks.json", [
                {"bookId": "s", "book": {"bookId": "s", "title": "私密书", "author": "作者甲"}},
                {"bookId": "p", "book": {"bookId": "p", "title": "公开书", "author": "作者甲"}},
            ])
            write_json(data, "weread_notes_export.json", [
                {"bookId": "s", "title": "私密书", "author": "作者甲", "marks": [{"text": "秘密原文", "createTime": t1}], "reviews": [{"content": "秘密想法", "createTime": t2}]},
                {"bookId": "p", "title": "公开书", "author": "作者甲", "marks": [{"text": "公开原文但也不该发布", "createTime": t2}], "reviews": []},
            ])
            write_json(data, "weread_progress.json", {"u": {"progress": 0}})
            write_json(data, "weread_bookinfo.json", {})
            write_json(data, "weread_readdata.json", {})

            result = insights.build_insights(data)
            serialized = json.dumps(result, ensure_ascii=False)

            self.assertTrue(result["scope"]["includePrivate"])
            self.assertEqual(result["scope"]["secretBooks"], 1)
            self.assertIn("私密书", serialized)
            self.assertIn("作者甲", serialized)
            self.assertNotIn("秘密原文", serialized)
            self.assertNotIn("秘密想法", serialized)
            self.assertNotIn("公开原文但也不该发布", serialized)
            self.assertGreaterEqual(len(result["focusShift"]), 2)
            self.assertGreater(len(result["knowledgeGraph"]["nodes"]), 0)
            self.assertGreater(len(result["knowledgeGraph"]["edges"]), 0)
            self.assertTrue(any(x["author"] == "作者甲" for x in result["knowledgeGraph"]["bridgeAuthors"]))
            self.assertEqual(len(result["enrichment"]["bookshelf"]), 3)
            self.assertFalse(result["enrichment"]["scope"]["includePrivate"] is False)


if __name__ == "__main__":
    unittest.main()
