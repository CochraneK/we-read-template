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


sync = load_module("sync_obsidian", ROOT / "scripts" / "sync_obsidian.py")


class ObsidianSyncTests(unittest.TestCase):
    def sample_context(self):
        return {
            "generatedAt": "2026-01-01T00:00:00+00:00",
            "privacy": {"includePrivate": False},
            "books": [{
                "bookId": "book/1",
                "title": "测试:书名",
                "author": "作者",
                "category": "文学",
                "progress": 42,
                "markCount": 1,
                "reviewCount": 1,
                "marks": [{"chapter": "第一章", "text": "一条划线", "createTime": 1700000000}],
                "reviews": [{"chapter": "第二章", "text": "我的想法", "createTime": 1701000000}],
            }],
        }

    def test_filename_is_cross_platform_safe(self):
        name = sync.target_filename(self.sample_context()["books"][0])
        self.assertNotIn(":", name)
        self.assertNotIn("/", name)
        self.assertTrue(name.endswith(".md"))

    def test_user_zone_is_preserved(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp)
            first = sync.sync_context(self.sample_context(), vault)
            self.assertEqual(first["created"], 1)
            note = next((vault / "WeRead").glob("*.md"))
            text = note.read_text(encoding="utf-8")
            text = text.replace(sync.USER_START + "\n", sync.USER_START + "\n我自己的长期笔记\n", 1)
            note.write_text(text, encoding="utf-8")

            # A user-only edit should be preserved without forcing a rewrite of the
            # managed sync region. The freshly rendered file is already identical.
            second = sync.sync_context(self.sample_context(), vault)
            self.assertEqual(second["unchanged"], 1)
            self.assertEqual(second["updated"], 0)
            updated = note.read_text(encoding="utf-8")
            self.assertIn("我自己的长期笔记", updated)
            self.assertIn("一条划线", updated)
            self.assertIn("我的想法", updated)

    def test_unmanaged_existing_file_is_not_overwritten(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp)
            folder = vault / "WeRead"
            folder.mkdir()
            book = self.sample_context()["books"][0]
            target = folder / sync.target_filename(book)
            target.write_text("手工文件，不允许覆盖", encoding="utf-8")

            result = sync.sync_context(self.sample_context(), vault)
            self.assertEqual(result["skippedUnmanaged"], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "手工文件，不允许覆盖")

    def test_dry_run_makes_no_files(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp)
            result = sync.sync_context(self.sample_context(), vault, dry_run=True)
            self.assertEqual(result["wouldWrite"], 1)
            self.assertFalse((vault / "WeRead").exists())


if __name__ == "__main__":
    unittest.main()
