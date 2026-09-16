#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory
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


network = load_module("weread_network", ROOT / "scripts" / "renderers" / "network.py")


class NetworkRendererTests(unittest.TestCase):
    def test_reading_map_filters_invalid_edges(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "reading_map.json"
            path.write_text(
                json.dumps(
                    {
                        "version": "1",
                        "nodes": [
                            {"id": "a", "label": "认知", "weight": 10, "tier": "core", "evidence": ["A"]},
                            {"id": "b", "label": "关系", "weight": 5, "tier": "secondary", "evidence": ["B"]},
                        ],
                        "edges": [
                            {"source": "a", "target": "b", "strength": 2, "reason": "共同证据"},
                            {"source": "a", "target": "missing", "strength": 2, "reason": "invalid"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            raw, nodes, edges = network.load_graph(path, "reading-map")
            self.assertEqual(len(nodes), 2)
            self.assertEqual(len(edges), 1)
            html = network.render_html(raw, nodes, edges, "reading-map")
            self.assertIn("阅读版图", html)
            self.assertIn("认知", html)
            self.assertIn("共同证据", html)

    def test_knowledge_graph_types(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "knowledge_graph.json"
            path.write_text(
                json.dumps(
                    {
                        "version": "1",
                        "nodes": [
                            {"id": "t", "type": "theme", "label": "主题", "weight": 5},
                            {"id": "b", "type": "book", "label": "书籍", "weight": 3},
                            {"id": "q", "type": "quote", "label": "划线", "weight": 1},
                        ],
                        "edges": [
                            {"source": "t", "target": "b", "type": "related", "weight": 2},
                            {"source": "b", "target": "q", "type": "contains", "weight": 1},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            raw, nodes, edges = network.load_graph(path, "knowledge-graph")
            self.assertEqual({n["type"] for n in nodes}, {"theme", "book", "quote"})
            html = network.render_html(raw, nodes, edges, "knowledge-graph")
            self.assertIn("阅读知识图谱", html)
            self.assertIn("书籍", html)
            self.assertIn("划线", html)


if __name__ == "__main__":
    unittest.main()
