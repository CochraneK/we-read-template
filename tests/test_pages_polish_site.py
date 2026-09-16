#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


quotes = load("pages_public_quotes_polish_test", ROOT / "scripts" / "pages_public_quotes.py")
hidden = load("pages_hidden_search_polish_test", ROOT / "scripts" / "pages_hidden_search_ui.py")
polish = load("pages_polish_site_test", ROOT / "scripts" / "pages_polish_site.py")
year_lens = load("pages_year_lens_polish_test", ROOT / "scripts" / "pages_year_lens_ui.py")


class PagesPolishTests(unittest.TestCase):
    def test_quote_controls_include_random_resample_and_symbol_search(self):
        section = quotes.render_section({"items": [], "policy": {"candidateCount": 6099}})
        self.assertIn('id="publicQuoteRandom"', section)
        self.assertIn('id="publicQuoteResample"', section)
        self.assertIn('class="dice"', section)
        self.assertIn('id="publicQuoteSearchSymbol"', section)
        self.assertIn('aria-label="全量搜索"', section)
        self.assertIn('>🔎</button>', section)
        self.assertIn("sampleMarks(48,90)", quotes.JS)
        self.assertNotIn("#publicQuoteResample{background:", quotes.CSS)
        self.assertIn("#publicQuoteRandom .dice", quotes.CSS)
        self.assertIn("#publicQuoteResample .dice", quotes.CSS)
        self.assertIn("randomDice.textContent='⚄'", polish.JS)
        self.assertIn("resampleDice.textContent='⚅'", polish.JS)

    def test_we_read_links_use_https_search_not_app_scheme(self):
        self.assertTrue(quotes.web_search_link("测试书").startswith("https://weread.qq.com/web/search/books?keyword="))
        self.assertNotIn("weread://reading", quotes.JS)
        self.assertNotIn("weread://reading", hidden.JS)
        self.assertIn("https://weread.qq.com/web/search/books?keyword=", hidden.JS)

    def test_hidden_search_auto_uses_built_in_marks_only_index(self):
        self.assertIn("DOMContentLoaded", hidden.JS)
        self.assertIn("window.__WEREAD_BUILTIN_MARKS__", hidden.JS)
        self.assertIn("window.WeReadHiddenEvidenceSearch={open,close,sampleMarks,hydrate:ensureBuiltIn}", hidden.JS)
        self.assertIn("wereadPublicMarksV2", hidden.JS)
        self.assertIn("indexedDB.open", hidden.JS)
        self.assertNotIn("hesImport", hidden.HTML)
        self.assertNotIn("仅想法", hidden.HTML)
        self.assertNotIn("fetch(", hidden.JS)
        self.assertNotIn("XMLHttpRequest", hidden.JS)

    def test_public_mark_index_writer_contains_marks_global(self):
        rows = [{"id":"m:1:1","bookId":"1","title":"书","author":"甲","chapter":"一","text":"划线正文"}]
        with tempfile.TemporaryDirectory() as td:
            path = quotes.write_public_mark_index(Path(td), rows)
            text = path.read_text(encoding="utf-8")
        prefix = "window.__WEREAD_BUILTIN_MARKS__="
        payload = text[text.index(prefix)+len(prefix):].strip().rstrip(";")
        parsed = json.loads(payload)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["text"], "划线正文")
        self.assertNotIn("content", parsed[0])
        self.assertNotIn("review", parsed[0])

    def test_year_lens_absorbs_annual_summary_with_total_and_overview(self):
        self.assertIn("TOTAL_YEAR='__total__'", year_lens.JS)
        self.assertIn('>总计</button>', year_lens.JS)
        self.assertIn('id="yearOverviewGrid"', year_lens.HTML)
        self.assertIn("totalYearModel", year_lens.JS)
        self.assertIn("跨年 12 个月累计", year_lens.JS)
        self.assertIn("年度一览", year_lens.HTML)
        self.assertIn("#annual-summary{display:none!important}", polish.CSS)

    def test_rhythm_layout_pairs_clock_weekday_and_keeps_twelve_months_one_row(self):
        self.assertIn("#clock,#weekday{grid-column:span 6!important}", polish.CSS)
        self.assertIn("#season{grid-column:span 12!important", polish.CSS)
        self.assertIn("repeat(12,minmax(54px,1fr))", polish.CSS)
        self.assertIn("min-width:720px", polish.CSS)
        self.assertNotIn("#weekday,#season{grid-column:span 6", polish.CSS)

    def test_clock_face_is_compact_and_peak_columns_do_not_overflow(self):
        self.assertIn("#clock .clock-svg{width:100%;max-width:288px;margin:auto}", polish.CSS)
        self.assertIn("grid-template-columns:minmax(210px,300px) minmax(160px,1fr)", polish.CSS)
        self.assertIn("grid-template-columns:26px 54px minmax(44px,1fr)", polish.CSS)
        self.assertIn("white-space:nowrap", polish.CSS)
        self.assertIn("text-align:right", polish.CSS)
        self.assertIn("min-height:288px", polish.CSS)

    def test_focus_category_migration_sits_below_reading_focus(self):
        self.assertIn("#shift,#focus{grid-column:span 12!important}", polish.CSS)
        self.assertIn("shift.insertAdjacentElement('afterend',focus)", polish.JS)

    def test_polish_cleans_placeholders_and_noisy_titles(self):
        self.assertIn("cleanPreferenceGrid", polish.JS)
        self.assertIn("cleanTopTitle", polish.JS)
        self.assertIn("MutationObserver", polish.JS)

    def test_clock_peak_ranking_is_compact(self):
        self.assertIn("clock-peak-list", polish.CSS)
        self.assertIn("clock-peak-rank", polish.JS)
        self.assertNotIn("#1 活跃时段", polish.JS)


if __name__ == "__main__":
    unittest.main()
