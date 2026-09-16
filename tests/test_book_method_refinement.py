#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

brief=load('book_method_brief',ROOT/'scripts'/'build_book_method_brief.py')
apply_method=load('book_method_apply',ROOT/'scripts'/'apply_book_method_refinement.py')
editor=load('book_method_editor',ROOT/'scripts'/'renderers'/'book_method_editor.py')


def context():
    return {'books':[{'bookId':'b1','title':'方法之书','author':'作者','marks':[{'chapter':'一','text':'作者原文一','createTime':10},{'chapter':'二','text':'作者原文二','createTime':11}], 'reviews':[{'chapter':'一','text':'我的理解一','createTime':20},{'chapter':'三','text':'我的理解二','createTime':21}]}]}

class BookMethodRefinementTests(unittest.TestCase):
    def test_brief_assigns_stable_evidence_ids_and_empty_method(self):
        a=brief.build(context(),book_id='b1');b=brief.build(context(),book_id='b1')
        self.assertEqual([x['evidenceId'] for x in a['evidence']],[x['evidenceId'] for x in b['evidence']])
        self.assertTrue(all(x['evidenceId'].startswith('be-') for x in a['evidence']))
        self.assertEqual(a['method']['steps'],[])
        self.assertFalse(a['contract']['ready'])

    def test_refinement_rejects_too_few_steps_and_unknown_evidence(self):
        data=brief.build(context(),book_id='b1')
        data['method']={'title':'两步法','purpose':'测试','steps':[{'action':'A','why':'W','evidenceIds':['missing']},{'action':'B','why':'W','evidenceIds':['missing']} ]}
        result=apply_method.validate(data)
        self.assertFalse(result['ready'])
        self.assertTrue(any('3–7' in p for p in result['problems']))
        self.assertTrue(any('unknown evidenceIds' in p for p in result['problems']))

    def test_ready_method_requires_real_evidence_and_user_review(self):
        data=brief.build(context(),book_id='b1');ids=[x['evidenceId'] for x in data['evidence']];review_id=next(x['evidenceId'] for x in data['evidence'] if x['kind']=='user_review')
        data['method']={'title':'三步法','purpose':'把证据变成行动','steps':[{'action':'先观察','why':'先收集','evidenceIds':[review_id]},{'action':'再比较','why':'避免单点','evidenceIds':[ids[1]]},{'action':'最后行动','why':'形成闭环','evidenceIds':[ids[2]]}]}
        result=apply_method.validate(data)
        self.assertTrue(result['ready'])
        md=apply_method.to_markdown(result)
        self.assertIn('# 三步法',md)
        self.assertIn('## 1. 先观察',md)
        self.assertIn('证据边界',md)

    def test_editor_is_offline_and_exports_refinement_json(self):
        page=editor.render(brief.build(context(),book_id='b1'))
        self.assertIn('方法型 Book→Skill',page)
        self.assertIn('导出 refinement JSON',page)
        self.assertIn('Evidence Pool',page)
        self.assertNotIn('fetch(',page)
        self.assertNotIn('XMLHttpRequest',page)
        self.assertNotIn('WebSocket',page)

if __name__=='__main__':unittest.main()
