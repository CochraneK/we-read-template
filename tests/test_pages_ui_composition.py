#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


story = load_module("weread_pages_story_ui", SCRIPTS / "pages_story_ui.py")
enrich = load_module("weread_pages_enrich_site", SCRIPTS / "pages_enrich_site.py")
experience = load_module("weread_pages_experience_ui", SCRIPTS / "pages_experience_ui.py")
command = load_module("weread_pages_command_ui", SCRIPTS / "pages_command_ui.py")
queue_io = load_module("weread_pages_queue_io_ui", SCRIPTS / "pages_queue_io_ui.py")
theme = load_module("weread_pages_theme_ui", SCRIPTS / "pages_theme_ui.py")


class PagesUiCompositionTests(unittest.TestCase):
    def test_story_ui_includes_year_lens_and_career_views(self):
        self.assertIn('id="year-lens"', story.HTML)
        self.assertIn('id="career"', story.HTML)
        self.assertIn('id="depth-matrix"', story.HTML)
        self.assertIn('id="note-evolution"', story.HTML)
        self.assertIn("renderYearLens", story.JS)
        self.assertIn("drawCareer", story.JS)
        self.assertIn("drawScatter", story.JS)

    def test_enrichment_ui_keeps_explorer_and_rhythm_modules(self):
        self.assertIn('id="clock"', enrich.HTML)
        self.assertIn('id="progress"', enrich.HTML)
        self.assertIn('id="recall"', enrich.HTML)
        self.assertIn('id="shelf-explorer"', enrich.HTML)
        self.assertIn("drawClock", enrich.JS)
        self.assertIn("renderShelf", enrich.JS)
        self.assertIn("optionalSection", enrich.JS)

    def test_experience_layer_keeps_archive_chapters_and_controls(self):
        for chapter in (
            "chapter-life",
            "chapter-rhythm",
            "chapter-investment",
            "chapter-knowledge",
            "chapter-reflection",
            "chapter-shelf",
            "chapter-boundary",
        ):
            self.assertIn(chapter, experience.JS)
        self.assertIn("getElementById('rhythm')", experience.JS)
        self.assertIn("focus-mode", experience.CSS)
        self.assertIn("focusToggle", experience.JS)
        self.assertIn("shelfQuery", experience.JS)
        self.assertIn("e.key==='/'", experience.JS)
        self.assertIn("IntersectionObserver", experience.JS)
        self.assertIn("reading-progress", experience.CSS)
        self.assertIn("skip-link", experience.CSS)
        self.assertIn("content-visibility:auto", experience.CSS)

    def test_daily_resurfacing_uses_recall_metadata_only(self):
        self.assertIn("daily-recall", experience.CSS)
        self.assertIn("recallPool", experience.JS)
        self.assertIn("noteCount", experience.JS)
        self.assertIn("daysSinceLastNote", experience.JS)
        self.assertNotIn("markText", experience.JS)
        self.assertNotIn("reviewText", experience.JS)

    def test_browser_local_state_restores_without_touching_report_data(self):
        self.assertIn("wereadArchiveLastChapter", experience.JS)
        self.assertIn("wereadArchiveShelfStateV1", experience.JS)
        self.assertIn("resumeChapter", experience.JS)
        self.assertIn("继续上次", experience.JS)
        self.assertIn("state.query", experience.JS)
        self.assertIn("state.category", experience.JS)
        self.assertIn("state.progress", experience.JS)
        self.assertIn("state.sort", experience.JS)
        self.assertNotIn("report-data.json", experience.JS)

    def test_local_pin_queue_does_not_require_remote_writes(self):
        self.assertIn("wereadArchivePinsV1", experience.JS)
        self.assertIn("value='pinned'", experience.JS)
        self.assertIn("localStorage.setItem(pinKey", experience.JS)
        self.assertIn("shelf-pin", experience.CSS)
        self.assertIn("不修改微信读书", experience.JS)
        self.assertNotIn("/shelf/", experience.JS)
        self.assertNotIn("fetch(", experience.JS)

    def test_command_palette_searches_only_chapters_and_bookshelf_metadata(self):
        self.assertIn("archiveCommand", command.JS)
        self.assertIn("commandInput", command.JS)
        self.assertIn("chapterCommands", command.JS)
        self.assertIn("E.bookshelf", command.JS)
        self.assertIn("e.metaKey||e.ctrlKey", command.JS)
        self.assertIn("ArrowDown", command.JS)
        self.assertIn("ArrowUp", command.JS)
        self.assertIn("renderShelf(true)", command.JS)
        self.assertIn("chapter-shelf", command.JS)
        self.assertNotIn("fetch(", command.JS)
        self.assertNotIn("markText", command.JS)
        self.assertNotIn("reviewText", command.JS)

    def test_pin_queue_transfer_exports_metadata_and_whitelists_imports(self):
        self.assertIn("we-read-local-pins", queue_io.JS)
        self.assertIn("bookId", queue_io.JS)
        self.assertIn("title", queue_io.JS)
        self.assertIn("author", queue_io.JS)
        self.assertIn("category", queue_io.JS)
        self.assertIn("byId.has(id)", queue_io.JS)
        self.assertIn("new Blob", queue_io.JS)
        self.assertIn("location.reload()", queue_io.JS)
        self.assertIn("导入并合并", queue_io.JS)
        self.assertNotIn("fetch(", queue_io.JS)
        self.assertNotIn("marks", queue_io.JS)
        self.assertNotIn("reviews", queue_io.JS)
        self.assertNotIn("/shelf/", queue_io.JS)

    def test_theme_switcher_is_local_and_supports_three_modes(self):
        self.assertIn("wereadArchiveThemeV1", theme.JS)
        self.assertIn("themeToggle", theme.JS)
        self.assertIn("['system','light','dark']", theme.JS)
        self.assertIn('html[data-theme="light"]', theme.CSS)
        self.assertIn('html[data-theme="dark"]', theme.CSS)
        self.assertIn("localStorage.setItem(key,current)", theme.JS)
        self.assertIn("prefers-color-scheme: dark", theme.JS)
        self.assertNotIn("fetch(", theme.JS)
        self.assertNotIn("report-data.json", theme.JS)

    def test_experience_command_queue_and_theme_enhancers_inject_css_and_js(self):
        base = "<html><head><style>BASE</style></head><body><script>BASEJS</script></body></html>"
        out = experience.enhance(base)
        out = command.enhance(out)
        self.assertIn("chapter-heading", out)
        self.assertIn("wereadArchiveFocus", out)
        self.assertIn("wereadArchivePinsV1", out)
        self.assertIn("wereadArchiveShelfStateV1", out)
        self.assertIn("daily-recall", out)
        self.assertIn("command-backdrop", out)
        self.assertIn("archiveCommand", out)
        self.assertIn("shelf-local-actions", out)
        self.assertIn("we-read-local-pins", out)
        self.assertIn("themeToggle", out)
        self.assertIn("wereadArchiveThemeV1", out)
        self.assertLess(out.index("BASE"), out.index("chapter-heading"))
        self.assertLess(out.index("BASEJS"), out.index("wereadArchiveFocus"))
        self.assertLess(out.index("wereadArchiveFocus"), out.index("archiveCommand"))
        self.assertLess(out.index("archiveCommand"), out.index("we-read-local-pins"))
        self.assertLess(out.index("we-read-local-pins"), out.index("wereadArchiveThemeV1"))


if __name__ == "__main__":
    unittest.main()
