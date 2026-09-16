from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = load_module("shelf_planner", ROOT / "scripts" / "plan_shelf_organization.py")


class ShelfPlannerTests(unittest.TestCase):
    def context(self):
        return {
            "privacy": {"includePrivate": False}, "coverage": {},
            "books": [
                {"bookId": "1", "title": "A", "author": "甲", "category": "计算机-人工智能", "progress": 50, "noteCount": 2, "reviewCount": 0},
                {"bookId": "2", "title": "B", "author": "乙", "category": "计算机-编程", "progress": 100, "noteCount": 0, "reviewCount": 0},
                {"bookId": "3", "title": "C", "author": "丙", "category": "文学-小说", "progress": 5, "noteCount": 12, "reviewCount": 1},
                {"bookId": "4", "title": "D", "author": "丁", "category": "文学-小说", "progress": None, "noteCount": 0, "reviewCount": 0},
            ],
        }

    def test_status_is_exclusive_and_auditable(self):
        plan = planner.build_plan(self.context(), "status")
        groups = {g["name"]: g for g in plan["groups"]}
        self.assertIn("在读", groups)
        self.assertIn("已读", groups)
        self.assertIn("深读", groups)
        self.assertIn("待读", groups)
        self.assertFalse(plan["remoteMutationPerformed"])
        self.assertEqual(sum(g["count"] for g in plan["groups"]), 4)

    def test_hybrid_uses_category_root(self):
        plan = planner.build_plan(self.context(), "hybrid")
        names = [g["name"] for g in plan["groups"]]
        self.assertIn("在读 · 计算机", names)
        self.assertIn("深读 · 文学", names)

    def test_markdown_states_plan_only(self):
        md = planner.render_markdown(planner.build_plan(self.context(), "category"))
        self.assertIn("没有修改微信读书远端书架", md)
        self.assertIn("计算机", md)


if __name__ == "__main__":
    unittest.main()
