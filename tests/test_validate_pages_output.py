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


validator = load_module("weread_validate_pages_output", ROOT / "scripts" / "validate_pages_output.py")


MARKERS = " ".join(validator.REQUIRED_HTML_MARKERS)
RAW_BODY = "这是一段足够长的测试划线正文，用来确认公开页面不会把原始内容原样泄露出去。"


def write_valid_fixture(root: Path, leak: bool = False):
    site = root / "site"
    data = root / "data"
    site.mkdir()
    data.mkdir()
    extra = RAW_BODY if leak else ""
    (site / "index.html").write_text(
        f"<html><body>{MARKERS}{extra}<script>const ok = true;</script></body></html>",
        encoding="utf-8",
    )
    report = {
        "summary": {"shelfBooks": 1, "notes": 1, "privateIncluded": 0},
        "insights": {
            "scope": {"rawTextPublished": False},
            "enrichment": {
                "bookshelf": [
                    {"bookId": "b1", "title": "测试书", "author": "作者", "category": "测试"}
                ]
            },
        },
    }
    (site / "report-data.json").write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )
    notes = [
        {
            "bookId": "b1",
            "marks": [{"text": RAW_BODY}],
            "reviews": [{"content": "另一段足够长的测试想法正文，也不应该出现在最终公开报告里面。"}],
        }
    ]
    (data / "weread_notes_export.json").write_text(
        json.dumps(notes, ensure_ascii=False), encoding="utf-8"
    )
    return site, data


class ValidatePagesOutputTests(unittest.TestCase):
    def test_valid_artifact_writes_exact_inline_js_for_node_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, data = write_valid_fixture(root)
            js_out = root / "final.js"
            result = validator.validate(site, data, js_out, sample_limit=50)
            self.assertEqual(result["shelfBooks"], 1)
            self.assertEqual(result["inlineScripts"], 1)
            self.assertGreater(result["rawBodiesChecked"], 0)
            self.assertIn("const ok = true", js_out.read_text(encoding="utf-8"))

    def test_raw_body_leak_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, data = write_valid_fixture(root, leak=True)
            with self.assertRaisesRegex(ValueError, "raw mark/review body leaked"):
                validator.validate(site, data, root / "final.js", sample_limit=50)

    def test_bookshelf_count_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, data = write_valid_fixture(root)
            report_path = site / "report-data.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["summary"]["shelfBooks"] = 2
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bookshelf count mismatch"):
                validator.validate(site, data, root / "final.js")

    def test_raw_text_published_flag_must_be_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, data = write_valid_fixture(root)
            report_path = site / "report-data.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["insights"]["scope"]["rawTextPublished"] = True
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rawTextPublished must be false"):
                validator.validate(site, data, root / "final.js")


if __name__ == "__main__":
    unittest.main()
