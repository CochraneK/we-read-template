#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


starter = load_module("weread_starter_cli", ROOT / "scripts" / "weread.py")


class TemplateStarterTests(unittest.TestCase):
    def test_env_example_is_privacy_safe(self):
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("WEREAD_PAGES_INCLUDE_PRIVATE=0", text)
        self.assertIn("WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES=0", text)
        self.assertNotIn("wrk-", text)

    def test_synthetic_fixture_contains_public_and_private_examples(self):
        shelf = json.loads((ROOT / "examples" / "sample-data" / "weread_shelf.json").read_text(encoding="utf-8"))
        flags = {int(row.get("secret") or 0) for row in shelf.get("books") or []}
        self.assertEqual(flags, {0, 1})

    def test_dotenv_loader_does_not_override_existing_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("WEREAD_API_KEY=from-file\nWEREAD_PAGES_INCLUDE_PRIVATE=1\n", encoding="utf-8")
            previous = os.environ.get("WEREAD_API_KEY")
            os.environ["WEREAD_API_KEY"] = "already-set"
            try:
                starter.load_dotenv(path)
                self.assertEqual(os.environ["WEREAD_API_KEY"], "already-set")
                self.assertEqual(os.environ["WEREAD_PAGES_INCLUDE_PRIVATE"], "1")
            finally:
                if previous is None:
                    os.environ.pop("WEREAD_API_KEY", None)
                else:
                    os.environ["WEREAD_API_KEY"] = previous
                os.environ.pop("WEREAD_PAGES_INCLUDE_PRIVATE", None)


if __name__ == "__main__":
    unittest.main()
