#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


ocg = load_module("pages_ontology_claims_test", ROOT / "scripts" / "pages_ontology_claims.py")
validator = load_module("validate_ontology_claims_test", ROOT / "scripts" / "validate_ontology_claims.py")


class OntologyClaimGraphTests(unittest.TestCase):
    def fixture(self, root: Path):
        shelf = {"books": [
            {"bookId": "1", "title": "甲书", "author": "作者甲", "category": "哲学"},
            {"bookId": "2", "title": "乙书", "author": "作者甲", "category": "文学"},
            {"bookId": "3", "title": "丙书", "author": "作者乙", "category": "哲学"},
        ]}
        notes = [
            {"bookId": "1", "title": "甲书", "author": "作者甲", "marks": [
                {"chapter": "第一章", "text": "不会进入公开 contract 的正文一", "createTime": 1672531200},
                {"chapter": "第二章", "text": "不会进入公开 contract 的正文二", "createTime": 1704067200},
                {"chapter": "第三章", "text": "不会进入公开 contract 的正文三", "createTime": 1735689600},
            ], "reviews": [{"chapter": "第二章", "content": "私人想法", "createTime": 1735689700}]},
            {"bookId": "2", "title": "乙书", "author": "作者甲", "marks": [
                {"chapter": "开篇", "text": "文学划线", "createTime": 1735689800},
            ], "reviews": []},
            {"bookId": "3", "title": "丙书", "author": "作者乙", "marks": [
                {"chapter": "A", "text": "A", "createTime": 1767225600},
                {"chapter": "B", "text": "B", "createTime": 1767225700},
                {"chapter": "C", "text": "C", "createTime": 1767225800},
            ] * 7, "reviews": []},
        ]
        (root / "weread_shelf.json").write_text(json.dumps(shelf, ensure_ascii=False), encoding="utf-8")
        (root / "weread_notebooks.json").write_text("[]", encoding="utf-8")
        (root / "weread_notes_export.json").write_text(json.dumps(notes, ensure_ascii=False), encoding="utf-8")
        (root / "weread_progress.json").write_text(json.dumps({"1": {"progress": 100}}, ensure_ascii=False), encoding="utf-8")

    def test_payload_is_read_only_and_raw_text_free(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            self.fixture(data)
            payload = ocg.build_payload(data)
        contract = payload["contract"]
        self.assertTrue(contract["derivedReadOnly"])
        self.assertTrue(contract["deterministicClaims"])
        self.assertFalse(contract["rawTextPublished"])
        self.assertFalse(contract["runtimeApiRequired"])
        self.assertEqual(payload["ontology"]["entityCounts"]["Evidence"], 26)
        self.assertEqual(payload["ontology"]["relationCounts"]["evidenceFromBook"], 26)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("不会进入公开 contract", serialized)
        self.assertNotIn("私人想法", serialized)
        self.assertIn("Chapter", serialized)

    def test_claims_have_evidence_status_and_uncertainty(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            self.fixture(data)
            payload = ocg.build_payload(data)
        claims = payload["claimGraph"]["claims"]
        self.assertTrue(claims)
        self.assertTrue(any(c["type"] == "bridge-author" for c in claims))
        self.assertTrue(any(c["type"] == "unresolved" for c in claims))
        for claim in claims:
            self.assertIn(claim["status"], {"supported", "partial", "unresolved"})
            self.assertTrue(claim["support"])
            self.assertIsInstance(claim["counter"], list)
            self.assertIsInstance(claim["dependencies"], list)

    def test_augment_and_validator_work_without_runtime_network(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / "data"
            site = root / "site"
            data.mkdir(); site.mkdir()
            self.fixture(data)
            (site / "report-data.json").write_text(json.dumps({"privacyMode": "full"}), encoding="utf-8")
            (site / "index.html").write_text(
                '<html><head><style></style></head><body><nav></nav>\n'
                '  <article class="card half" id="blindspot"></article><script>const x=1;</script></body></html>',
                encoding="utf-8",
            )
            payload = ocg.augment(site, data)
            result = validator.validate(site)
            html = (site / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ontology-lite"', html)
        self.assertIn('id="claim-graph"', html)
        self.assertNotIn("fetch(", html)
        self.assertEqual(result["claims"], payload["claimGraph"]["count"])


if __name__ == "__main__":
    unittest.main()
