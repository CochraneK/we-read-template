from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_module("book_to_skill", ROOT / "scripts" / "book_to_skill.py")


class BookToSkillTests(unittest.TestCase):
    def context(self):
        return {"books": [{
            "bookId": "b1", "title": "测试之书", "author": "作者",
            "marks": [{"chapter": "一", "text": "作者原文片段", "createTime": 10}],
            "reviews": [{"chapter": "一", "text": "这是我自己的想法", "createTime": 20}],
        }]}

    def test_user_review_is_prioritized(self):
        book = mod.choose_book(self.context(), book_id="b1")
        items = mod.evidence_items(book, max_items=2)
        self.assertEqual(items[0]["kind"], "user_review")

    def test_generate_writes_private_evidence_backed_skill(self):
        with TemporaryDirectory() as tmp:
            output, manifest = mod.generate(self.context(), Path(tmp), title="测试之书", max_items=10)
            skill = (output / "SKILL.md").read_text(encoding="utf-8")
            evidence = (output / "references" / "evidence.md").read_text(encoding="utf-8")
            self.assertIn("不是整本书的替代品", skill)
            self.assertIn("不得把划线误说成用户本人观点", skill)
            self.assertIn("这是我自己的想法", evidence)
            self.assertEqual(manifest["evidenceItems"], 2)

    def test_ambiguous_title_requires_book_id(self):
        context = {"books": [
            {"bookId": "1", "title": "同名书"},
            {"bookId": "2", "title": "同名书"},
        ]}
        with self.assertRaises(ValueError):
            mod.choose_book(context, title="同名书")


if __name__ == "__main__":
    unittest.main()
