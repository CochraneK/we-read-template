#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_visualization_context.py"
spec = importlib.util.spec_from_file_location("build_visualization_context", MODULE_PATH)
context_builder = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(context_builder)


class VisualizationContextProvenanceTests(unittest.TestCase):
    def test_source_membership_and_shelf_activity_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "weread_shelf.json").write_text(json.dumps({
                "books": [{
                    "bookId": "shelf-only",
                    "title": "Shelf",
                    "author": "A",
                    "readUpdateTime": 123456,
                }]
            }), encoding="utf-8")
            (data / "weread_notes_export.json").write_text(json.dumps([{
                "bookId": "notes-only",
                "title": "Notes",
                "author": "B",
                "marks": [{"text": "evidence", "createTime": 10}],
                "reviews": [],
            }]), encoding="utf-8")
            (data / "weread_progress.json").write_text("{}", encoding="utf-8")
            (data / "weread_bookinfo.json").write_text("{}", encoding="utf-8")
            (data / "weread_readdata.json").write_text("{}", encoding="utf-8")

            result = context_builder.build_context(data)
            by_id = {b["bookId"]: b for b in result["books"]}
            self.assertTrue(by_id["shelf-only"]["inShelf"])
            self.assertFalse(by_id["shelf-only"]["inNotebook"])
            self.assertEqual(by_id["shelf-only"]["shelfReadUpdateTime"], 123456)
            self.assertFalse(by_id["notes-only"]["inShelf"])
            self.assertTrue(by_id["notes-only"]["inNotebook"])
            self.assertEqual(by_id["notes-only"]["shelfReadUpdateTime"], 0)


if __name__ == "__main__":
    unittest.main()
