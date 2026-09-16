#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


heatmap = load_module("weread_heatmap", ROOT / "scripts" / "renderers" / "heatmap.py")
context_builder = load_module("weread_context", ROOT / "scripts" / "build_visualization_context.py")


class HeatmapTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(heatmap.level_for(0), 0)
        self.assertEqual(heatmap.level_for(59), 0)
        self.assertEqual(heatmap.level_for(60), 1)
        self.assertEqual(heatmap.level_for(600), 2)
        self.assertEqual(heatmap.level_for(1800), 3)
        self.assertEqual(heatmap.level_for(3600), 4)

    def test_daily_times_and_html(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "readdata.json"
            day1 = int(datetime(2026, 1, 2, 12).timestamp())
            day2 = int(datetime(2026, 1, 3, 12).timestamp())
            payload = {
                "annually": {
                    "2026": {
                        "dailyReadTimes": {str(day1): 600, str(day2): 3600}
                    }
                }
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            daily = heatmap.load_daily_read_times(path)
            self.assertEqual(len(daily), 2)
            html = heatmap.render_html(daily, [2026])
            self.assertIn("阅读热力图", html)
            self.assertIn("2026-01-02", html)
            self.assertIn("60 分钟以上", html)


class VisualizationContextTests(unittest.TestCase):
    def test_private_books_are_excluded_by_default(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "weread_shelf.json").write_text(
                json.dumps(
                    {
                        "books": [
                            {"bookId": "1", "title": "Public", "secret": 0},
                            {"bookId": "2", "title": "Private", "secret": 1},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (data / "weread_notes_export.json").write_text(
                json.dumps(
                    [
                        {"bookId": "1", "title": "Public", "marks": [{"text": "a"}], "reviews": []},
                        {"bookId": "2", "title": "Private", "marks": [{"text": "b"}], "reviews": []},
                    ]
                ),
                encoding="utf-8",
            )
            (data / "weread_progress.json").write_text("{}", encoding="utf-8")
            (data / "weread_bookinfo.json").write_text("{}", encoding="utf-8")
            (data / "weread_readdata.json").write_text("{}", encoding="utf-8")

            result = context_builder.build_context(data)
            self.assertEqual(result["coverage"]["contextBooks"], 1)
            self.assertEqual(result["coverage"]["excludedPrivateBooks"], 1)
            self.assertEqual(result["books"][0]["title"], "Public")

            included = context_builder.build_context(data, include_private=True)
            self.assertEqual(included["coverage"]["contextBooks"], 2)


if __name__ == "__main__":
    unittest.main()
