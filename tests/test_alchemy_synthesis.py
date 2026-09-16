#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "build_alchemy_synthesis.py"
spec = importlib.util.spec_from_file_location("alchemy_synthesis", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


class AlchemySynthesisTests(unittest.TestCase):
    def context(self):
        return {
            "mode":"book","selector":{"title":"测试书"},"privacy":{"publicPageSafe":False},
            "landscape":{"requiresScopeConfirmation":False},
            "books":[{"bookId":"1","title":"测试书","author":"甲","category":"认知","chapters":[
                {"chapter":"第一章","marks":[{"text":"注意力决定我们看到什么","createTime":1},{"text":"注意力也影响判断","createTime":2}],"reviews":[{"text":"我觉得注意力训练需要结合环境设计","createTime":3}]},
                {"chapter":"第二章","marks":[],"reviews":[{"text":"注意力不是纯意志问题","createTime":4}]},
            ]}],
        }

    def test_builds_private_heuristic_clusters_and_separates_roles(self):
        result = mod.build(self.context(), max_clusters=4)
        self.assertTrue(result["ready"])
        self.assertFalse(result["privacy"]["publicPageSafe"])
        self.assertGreaterEqual(len(result["clusters"]), 1)
        cluster = result["clusters"][0]
        self.assertEqual(cluster["status"], "heuristic_lexical_cluster")
        self.assertIn("representativeSourceText", cluster)
        self.assertIn("representativeUserThought", cluster)

    def test_scope_gate_stops_synthesis(self):
        ctx = self.context(); ctx["landscape"]["requiresScopeConfirmation"] = True
        result = mod.build(ctx)
        self.assertFalse(result["ready"])
        self.assertEqual(result["reason"], "scope_confirmation_required")


if __name__ == "__main__":
    unittest.main()
