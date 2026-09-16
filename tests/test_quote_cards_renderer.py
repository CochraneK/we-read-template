#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "renderers" / "quote_cards.py"
spec = importlib.util.spec_from_file_location("quote_cards", MODULE)
renderer = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(renderer)


class QuoteCardsRendererTests(unittest.TestCase):
    def payload(self):
        return {
            "meta": {"copyright_warning": "公开传播前人工核验"},
            "quotes": [
                {"bookId": "1", "title": "书A", "author": "甲", "chapter": "第一章", "text": "这是选中的个人划线文本", "theme": "认知", "score": 45, "selected": True, "tier": "A"},
                {"bookId": "2", "title": "书B", "author": "乙", "chapter": "第二章", "text": "这是未选中的候选划线文本", "theme": "人生", "score": 20, "selected": False, "tier": None},
            ],
        }

    def test_default_renders_selected_quotes_only(self):
        page = renderer.render(self.payload())
        self.assertIn("这是选中的个人划线文本", page)
        self.assertNotIn("这是未选中的候选划线文本", page)
        self.assertIn("data-set-theme=\"a\"", page)
        self.assertIn("data-set-theme=\"b\"", page)
        self.assertIn("data-set-theme=\"c\"", page)
        self.assertIn("weread://reading?bId=1", page)
        self.assertIn("index.html?book=1#book-workbench", page)
        self.assertIn("进入这本书的 Workbench", page)
        self.assertIn("不自动代表你的观点", page)
        self.assertNotIn("fetch(", page)

    def test_all_mode_renders_every_candidate(self):
        page = renderer.render(self.payload(), include_all=True)
        self.assertIn("这是选中的个人划线文本", page)
        self.assertIn("这是未选中的候选划线文本", page)
        self.assertEqual(len(renderer.selected_quotes(self.payload(), include_all=True)), 2)


if __name__ == "__main__":
    unittest.main()
