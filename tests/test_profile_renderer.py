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


profile = load_module("weread_profile", ROOT / "scripts" / "renderers" / "profile.py")


class ProfileRendererTests(unittest.TestCase):
    def test_profile_separates_facts_and_interpretations(self):
        payload = {
            "version": "1",
            "headline": "跨领域连接型读者",
            "summary": "这是一个示例总结。",
            "facts": [
                {"label": "有笔记书", "value": 42, "source": "notebooks"},
                {"label": "累计阅读", "value": "120小时", "source": "readdata"}
            ],
            "interpretations": [
                {
                    "label": "偏好跨领域连接",
                    "summary": "多个不同分类出现重复概念。",
                    "confidence": 0.82,
                    "evidence": ["A/B/C 三本书共享主题"],
                    "counterEvidence": ["近半年主题更集中"]
                }
            ],
            "themes": ["认知", "社会"],
            "coverage": {"books": 80}
        }
        facts, interpretations = profile.normalize(payload)
        self.assertEqual(len(facts), 2)
        self.assertEqual(len(interpretations), 1)
        html = profile.render_html(payload)
        self.assertIn("事实卡与解释卡必须分开阅读", html)
        self.assertIn("偏好跨领域连接", html)
        self.assertIn("反证 / 限制", html)
        self.assertIn("82%", html)

    def test_confidence_is_clamped(self):
        payload = {
            "headline": "测试",
            "facts": [],
            "interpretations": [
                {"label": "X", "summary": "Y", "confidence": 5, "evidence": []}
            ]
        }
        _, interpretations = profile.normalize(payload)
        self.assertEqual(interpretations[0]["confidence"], 1.0)

    def test_empty_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            profile.render_html({"headline": "空", "facts": [], "interpretations": []})


if __name__ == "__main__":
    unittest.main()
