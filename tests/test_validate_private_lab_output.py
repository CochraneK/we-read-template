#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'scripts'/'validate_private_lab_output.py'
spec=importlib.util.spec_from_file_location('validate_private_lab_output',MODULE);mod=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(mod)

class ValidatePrivateLabTests(unittest.TestCase):
    def valid(self):
        return '''<!doctype html><meta name="robots" content="noindex,nofollow,noarchive"><div>Private / Raw Evidence</div><section id="deep"></section><section id="search"></section><section id="recall"></section><section id="recall-history"></section><section id="actions"></section><section id="books"></section><div data-recall="ev-x"></div><script>const k='wereadPrivateRecallHistoryV1';</script>'''
    def test_valid_contract_is_accepted(self):
        info=mod.validate_text(self.valid())
        self.assertEqual(info['inlineScripts'],1)
    def test_browser_network_is_rejected(self):
        with self.assertRaises(ValueError): mod.validate_text(self.valid().replace('</script>','fetch("x")</script>'))
    def test_missing_private_marker_is_rejected(self):
        with self.assertRaises(ValueError): mod.validate_text(self.valid().replace('Private / Raw Evidence',''))

if __name__=='__main__': unittest.main()
