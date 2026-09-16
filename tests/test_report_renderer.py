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


report = load_module("weread_report", ROOT / "scripts" / "renderers" / "report.py")


class ReportRendererTests(unittest.TestCase):
    def sample_context(self):
        return {
            "privacy": {"includePrivate": False},
            "coverage": {
                "contextBooks": 12,
                "booksWithNotes": 7,
                "marks": 80,
                "reviews": 9,
                "excludedPrivateBooks": 2,
            },
            "reading": {
                "overall": {"totalReadTime": 3660, "readDays": 15},
                "annual": [{"year": "2025"}, {"year": "2026"}],
            },
        }

    def test_format_duration(self):
        self.assertEqual(report.format_duration(0), "0分")
        self.assertEqual(report.format_duration(3600), "1小时")
        self.assertEqual(report.format_duration(3660), "1小时1分")

    def test_build_and_render_full_report(self):
        reading_map = {
            "nodes": [
                {"label": "自我成长", "weight": 10, "tier": "core", "confidence": 0.9, "evidence": [1, 2, 3]},
                {"label": "社会观察", "weight": 4, "tier": "secondary", "confidence": 0.7, "evidence": [1]},
            ]
        }
        shift = {
            "stages": [
                {"label": "探索期", "start": "2025", "end": "2026", "themes": ["自我成长"], "summary": "阅读重心开始收敛", "confidence": 0.8}
            ]
        }
        graph = {
            "nodes": [
                {"type": "book", "label": "A", "weight": 1},
                {"type": "theme", "label": "自我成长", "weight": 5},
                {"type": "concept", "label": "选择", "weight": 4},
            ],
            "edges": [{"source": "a", "target": "b", "type": "related", "weight": 1}],
        }
        profile = {
            "summary": "一份证据驱动的阅读画像。",
            "interpretations": [
                {"label": "主动反思", "summary": "想法记录具有连续性。", "confidence": 0.75, "evidence": ["多本书存在个人想法"]}
            ],
        }
        narrative = {
            "version": "1",
            "title": "2026 阅读报告",
            "takeaways": [{"title": "主线收敛", "summary": "核心主题更加集中。", "confidence": 0.8}],
            "nextActions": [{"title": "做一次主题复盘", "reason": "把跨书证据重新组织。"}],
        }
        model = report.build_model(self.sample_context(), narrative, reading_map, shift, graph, profile)
        html = report.render_html(model, {"阅读热力图": "reading_heatmap.html"})
        self.assertIn("2026 阅读报告", html)
        self.assertIn("1小时1分", html)
        self.assertIn("自我成长", html)
        self.assertIn("探索期", html)
        self.assertIn("3 节点 · 1 关系", html)
        self.assertIn("主动反思", html)
        self.assertIn("排除 2 本", html)
        self.assertIn("reading_heatmap.html", html)

    def test_missing_optional_analyses_degrades_cleanly(self):
        model = report.build_model(self.sample_context())
        html = report.render_html(model)
        self.assertIn("尚未生成 Reading Map", html)
        self.assertIn("尚未生成 Cognitive Shift", html)
        self.assertIn("尚未生成 Knowledge Graph", html)
        self.assertIn("尚未生成 Reading Profile", html)


if __name__ == "__main__":
    unittest.main()
