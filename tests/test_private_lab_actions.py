#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts';RENDERERS=SCRIPTS/'renderers'
for p in (SCRIPTS,RENDERERS):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

lab=load('private_lab_build_actions',SCRIPTS/'build_private_reading_lab.py')
base=load('private_lab_base_actions',RENDERERS/'private_lab.py')
final=load('private_lab_final_actions',RENDERERS/'private_lab_final.py')

class PrivateLabActionTests(unittest.TestCase):
    def test_optional_action_steps_cover_advisor_path_and_semantic_briefs(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);candidate=out/'staged.json'
            steps=lab.build_action_steps(out,advisor_query='认知科学',path_topic='心理学',path_candidates=candidate,path_confirmed_level='beginner')
        labels=[x[0] for x in steps]
        for expected in (
            'Advisor Live Candidates','Advisor Shortlist','Advisor Report','Advisor Semantic Brief','Advisor Semantic Editor',
            'Reading Path Context','Reading Path Live Discovery','Reading Path Discovery Report','Reading Path Semantic Brief','Reading Path Semantic Editor',
            'Reading Path Candidate Verification','Reading Path Candidate Info','Reading Path Final Plan','Reading Path Final Report'
        ):
            self.assertIn(expected,labels)

    def test_semantic_annotation_inputs_add_gate_and_result_steps(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);advisor_json=out/'advisor.json';path_json=out/'path.json'
            steps=lab.build_action_steps(out,advisor_query='认知科学',path_topic='心理学',path_confirmed_level='beginner',advisor_semantic_annotations=advisor_json,path_semantic_annotations=path_json)
        labels=[x[0] for x in steps]
        self.assertIn('Advisor Semantic Gate',labels)
        self.assertIn('Advisor Final Semantic Report',labels)
        self.assertIn('Reading Path Semantic Gate',labels)
        self.assertIn('Reading Path Semantic Result',labels)
        self.assertIn('Reading Path Final Plan',labels)

    def test_final_renderer_surfaces_action_hub_spaced_recall_and_semantics(self):
        data={"coverage":{},"books":[],"evidence":[],"deep":{},"recall":{"items":[{"id":"recall-001","evidenceId":"ev-x","bookId":"b","title":"书","kind":"mark","ageDays":50,"prompt":"解释","text":"证据","chapter":"一"}]},"advisor":{},"blindspot":{},"review":{},"quoteCards":False}
        page=final.render_final(data,assets={"alchemyBook":True,"advisor":True,"pathDiscovery":True,"review":True,"advisorSemanticEditor":True,"advisorSemanticResult":True,"pathSemanticEditor":True,"pathSemanticResult":True})
        self.assertIn('id="actions"',page)
        self.assertIn('alchemy_book.html',page)
        self.assertIn('advisor.html',page)
        self.assertIn('reading_path_discovery.html',page)
        self.assertIn('narrative_review.html',page)
        self.assertIn('advisor_semantic_editor.html',page)
        self.assertIn('advisor_semantic.html',page)
        self.assertIn('reading_path_semantic_editor.html',page)
        self.assertIn('reading_path_semantic.html',page)
        self.assertIn('wereadPrivateRecallHistoryV1',page)
        self.assertIn('data-recall=',page)
        self.assertIn('data-recall-answer',page)
        self.assertNotIn('fetch(',page)
        if shutil.which('node'):
            start=page.index('<script>')+len('<script>');end=page.index('</script>',start)
            with tempfile.TemporaryDirectory() as td:
                js=Path(td)/'lab.js';js.write_text(page[start:end],encoding='utf-8')
                result=subprocess.run(['node','--check',str(js)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__': unittest.main()
