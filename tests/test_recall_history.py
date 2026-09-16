#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RENDERERS = SCRIPTS / "renderers"
for p in (SCRIPTS, RENDERERS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

queue = load("recall_queue_stable", SCRIPTS / "build_recall_queue.py")
ui = load("private_lab_recall_ui_test", SCRIPTS / "private_lab_recall_ui.py")
base = load("private_lab_base_test", RENDERERS / "private_lab.py")


class RecallHistoryTests(unittest.TestCase):
    def test_evidence_id_is_stable_across_queue_reordering(self):
        now = 10_000_000
        context = {"books": [{"bookId":"b","title":"书","author":"甲","reviews":[{"chapter":"一","text":"我的旧想法","createTime":now-100*queue.DAY}],"marks":[]}]}
        a = queue.build_queue(context, limit=1, min_age_days=1, now_ts=now)["items"][0]
        b = queue.build_queue(context, limit=10, min_age_days=1, now_ts=now+queue.DAY)["items"][0]
        self.assertEqual(a["evidenceId"], b["evidenceId"])
        self.assertTrue(a["evidenceId"].startswith("ev-"))

    def test_final_ui_adds_local_history_answers_and_no_network(self):
        data = {"coverage":{},"books":[],"evidence":[],"deep":{},"recall":{"items":[{"id":"recall-001","evidenceId":"ev-1","bookId":"b","title":"书","kind":"review","ageDays":90,"prompt":"回忆？","text":"证据","chapter":"一"}]},"advisor":{},"blindspot":{},"review":{},"quoteCards":False}
        page = ui.augment(base.render(data))
        self.assertIn("wereadPrivateRecallHistoryV1", page)
        self.assertIn("nextReviewAt", page)
        self.assertIn("导出历史", page)
        self.assertIn("data-recall=", page)
        self.assertIn("data-recall-answer", page)
        self.assertIn("answerHistory", page)
        self.assertIn("lexicalOverlap", page)
        self.assertIn("我现在怎么理解", page)
        self.assertNotIn("fetch(", ui.JS)
        self.assertNotIn("XMLHttpRequest", ui.JS)
        self.assertNotIn("WebSocket", ui.JS)


if __name__ == "__main__":
    unittest.main()
