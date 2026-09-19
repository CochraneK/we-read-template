#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


lite = load("weread_text_mining", ROOT / "scripts" / "build_text_mining_context.py")
semantic = load("weread_semantic_text_mining", ROOT / "scripts" / "build_semantic_text_mining.py")
nli = load("weread_nli_text_mining", ROOT / "scripts" / "build_nli_relations.py")
renderer = load("weread_text_mining_renderer", ROOT / "scripts" / "renderers" / "text_mining_private.py")


def fixture():
    return {
        "books": [
            {
                "bookId": "b1",
                "title": "Systems",
                "author": "A",
                "category": "Science",
                "marks": [
                    {"text": "反馈系统会因为延迟产生意外结果。", "chapter": "反馈", "createTime": 1609459200},
                    {"text": "复杂系统中的反馈回路值得反复观察。", "chapter": "回路", "createTime": 1640995200},
                ],
                "reviews": [
                    {"text": "我觉得反馈很重要，但是这个解释可能忽略了制度约束。", "chapter": "想法", "createTime": 1672531200},
                ],
            },
            {
                "bookId": "b2",
                "title": "Institutions",
                "author": "B",
                "category": "History",
                "marks": [
                    {"text": "制度约束会改变个体选择的空间。", "chapter": "制度", "createTime": 1704067200},
                    {"text": "反馈和制度可以共同塑造行为。", "chapter": "关系", "createTime": 1735689600},
                ],
                "reviews": [
                    {"text": "为什么制度和反馈会在不同尺度上产生类似模式？", "chapter": "问题", "createTime": 1767225600},
                ],
            },
        ]
    }


class TextMiningTests(unittest.TestCase):
    def test_source_and_self_corpora_stay_separate(self):
        result = lite.build(fixture())
        self.assertEqual(result["coverage"]["sourceHighlights"], 4)
        self.assertEqual(result["coverage"]["userThoughts"], 2)
        self.assertIn("topTerms", result["corpora"]["source"])
        self.assertIn("topTerms", result["corpora"]["self"])
        self.assertFalse(result["publicPageSafe"])

    def test_source_self_contrastive_terms_are_explicitly_lexical(self):
        result = lite.build(fixture())
        contrast = result["contrast"]
        self.assertIn("sourceDistinctive", contrast)
        self.assertIn("selfDistinctive", contrast)
        self.assertIn("lexical contrast", contrast["method"])

    def test_exposure_expression_lag_is_bounded_as_lexical_overlap(self):
        result = lite.build(fixture())
        items = result["exposureExpression"]["items"]
        self.assertTrue(all(x["status"] == "lexical_exposure_expression_lag" for x in items))
        self.assertIn("not proof", result["exposureExpression"]["meaning"].lower())

    def test_rhetorical_signals_only_use_user_thoughts(self):
        result = lite.build(fixture())
        rhet = result["rhetoricalLanguage"]
        self.assertEqual(rhet["documents"], 2)
        counts = {x["signal"]: x["documents"] for x in rhet["signals"]}
        self.assertGreaterEqual(counts["question"], 1)
        self.assertGreaterEqual(counts["challenge"], 1)
        self.assertIn("not inferred personality", rhet["note"])

    def test_novelty_is_explicitly_lexical(self):
        result = lite.build(fixture())
        self.assertIn("not semantic novelty", result["novelty"]["method"])
        self.assertTrue(result["novelty"]["mostNovel"])

    def test_temporal_change_points_and_exploration_are_bounded(self):
        result = lite.build(fixture())
        change = result["temporal"]["changePoints"]
        self.assertIn("Jensen-Shannon", change["method"])
        self.assertTrue(change["transitions"])
        balance = result["novelty"]["explorationExploitation"]
        self.assertIn("not a utility", balance["meaning"])
        self.assertTrue(balance["byYear"])

    def test_concept_network_evolution_is_lexical(self):
        result = lite.build(fixture())
        network = result["temporal"]["networkEvolution"]
        self.assertIn("lexical", network["method"])
        self.assertTrue(network["snapshots"])

    def test_nli_label_mapping_requires_semantic_labels(self):
        class Good:
            id2label = {0: "contradiction", 1: "neutral", 2: "entailment"}
        class Bad:
            id2label = {0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"}
        mapped = nli.label_map(Good())
        self.assertEqual(mapped[0], "contradiction")
        with self.assertRaises(ValueError):
            nli.label_map(Bad())

    def test_semantic_cluster_count_is_bounded_without_loading_models(self):
        self.assertEqual(semantic.cluster_count(4, 0), 2)
        self.assertLessEqual(semantic.cluster_count(5000, 0), 12)
        self.assertEqual(semantic.cluster_count(100, 7), 7)

    def test_renderer_marks_private_boundary_and_optional_semantic(self):
        result = lite.build(fixture())
        page = renderer.render(result, {}, {})
        self.assertIn("Private / Raw Evidence", page)
        self.assertIn("Reading Corpus Lab", page)
        self.assertIn("Semantic Mining", page)
        self.assertIn("年度语料分布转折", page)
        self.assertIn("Support / Contradiction Candidates", page)
        self.assertIn("not generated", page)
        self.assertNotIn("fetch(", page)


if __name__ == "__main__":
    unittest.main()
