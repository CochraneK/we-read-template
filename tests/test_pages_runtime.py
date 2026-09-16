#!/usr/bin/env python3
from pathlib import Path
import datetime as dt
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


runtime = load_module("weread_pages_runtime", SCRIPTS / "pages_runtime.py")


class PagesRuntimeTests(unittest.TestCase):
    def test_monthly_read_times_are_day_level_source(self):
        day1 = int(dt.datetime(2026, 1, 3, tzinfo=dt.timezone.utc).timestamp())
        day2 = int(dt.datetime(2026, 1, 4, tzinfo=dt.timezone.utc).timestamp())
        data = {
            "monthly": {
                "2026-01": {"readTimes": {str(day1): 120, str(day2): 3600}},
                "2026-02": {"readTimes": {str(day2): 1800}},
            },
            "annually": {},
        }
        daily = runtime.daily_read_times(data)
        self.assertEqual(daily["2026-01-03"], 120)
        self.assertEqual(daily["2026-01-04"], 3600)
        self.assertEqual(len(daily), 2)


if __name__ == "__main__":
    unittest.main()
