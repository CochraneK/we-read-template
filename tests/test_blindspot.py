from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("blindspot_builder", ROOT / "scripts" / "build_blindspot_context.py")
renderer = load_module("blindspot_renderer", ROOT / "scripts" / "renderers" / "blindspot.py")


class BlindspotTests(unittest.TestCase):
    def test_builder_finds_shelf_heavy_category(self):
        context = {
            "coverage": {}, "privacy": {"includePrivate": False},
            "books": [
                {"bookId": "1", "title": "A", "category": "商业", "noteCount": 0, "progress": 0},
                {"bookId": "2", "title": "B", "category": "商业", "noteCount": 0, "progress": 5},
                {"bookId": "3", "title": "C", "category": "商业", "noteCount": 0, "progress": None},
                {"bookId": "4", "title": "D", "category": "文学", "noteCount": 8, "progress": 90},
            ],
        }
        result = builder.build_context(context)
        names = [x["category"] for x in result["facts"]["shelfHeavyLowEngagementCategories"]]
        self.assertIn("商业", names)
        self.assertEqual(result["facts"]["lowEngagementBacklogCount"], 3)

    def test_renderer_requires_items_and_escapes_html(self):
        with self.assertRaises(ValueError):
            renderer.render_html({"blindspots": []})
        html = renderer.render_html({
            "summary": "summary",
            "blindspots": [{
                "label": "<集中>",
                "summary": "可能过度集中",
                "confidence": 1.2,
                "evidence": ["证据A"],
                "counterEvidence": ["限制B"],
                "counterReadingDirections": ["寻找反方论证"],
                "questions": ["什么证据会让我改变看法？"],
            }],
        })
        self.assertIn("&lt;集中&gt;", html)
        self.assertIn("100%", html)
        self.assertIn("寻找反方论证", html)


if __name__ == "__main__":
    unittest.main()
