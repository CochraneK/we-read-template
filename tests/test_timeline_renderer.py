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


timeline = load_module("weread_timeline", ROOT / "scripts" / "renderers" / "timeline.py")


class TimelineRendererTests(unittest.TestCase):
    def test_normalize_and_render(self):
        payload = {
            "version": "1",
            "coverage": {"books": 12, "evidenceCount": 30, "years": 3},
            "stages": [
                {
                    "label": "探索",
                    "start": "2024-01",
                    "end": "2024-12",
                    "summary": "从广泛阅读中寻找稳定问题。",
                    "themes": ["心理", "社会"],
                    "books": [{"title": "A", "author": "甲"}],
                    "evidence": [{"text": "证据 A", "source": "A"}],
                    "transition": "开始集中到认知主题",
                    "confidence": 0.8
                },
                {
                    "label": "聚焦",
                    "start": "2025-01",
                    "end": "2026-09",
                    "themes": ["认知"],
                    "books": ["B"],
                    "evidence": ["证据 B"],
                    "confidence": 1.5
                }
            ],
            "insights": ["主题逐渐收敛"]
        }
        stages = timeline.normalize(payload)
        self.assertEqual(len(stages), 2)
        self.assertEqual(stages[1]["confidence"], 1.0)
        self.assertEqual(stages[1]["books"][0]["title"], "B")
        html = timeline.render_html(payload)
        self.assertIn("认知变迁", html)
        self.assertIn("探索", html)
        self.assertIn("证据 A", html)
        self.assertIn("主题逐渐收敛", html)
        self.assertIn("2024-01 → 2024-12", html)

    def test_rejects_empty_stages(self):
        with self.assertRaises(ValueError):
            timeline.render_html({"version": "1", "stages": []})


if __name__ == "__main__":
    unittest.main()
