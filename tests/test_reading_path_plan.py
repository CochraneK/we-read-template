#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'scripts'/'build_reading_path_plan.py'
spec=importlib.util.spec_from_file_location('reading_path_plan',MODULE);mod=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(mod)

class ReadingPathPlanTests(unittest.TestCase):
    def path_context(self):
        return {"topic":"主题","levelAssessment":{"allowedOverrides":["zero","beginner","intermediate","advanced"]},"pathContract":{"stages":[
            {"id":"intro","label":"入门","purpose":"基础","feynmanCheckpoint":"解释基础"},
            {"id":"framework","label":"进阶","purpose":"框架","feynmanCheckpoint":"比较观点"},
            {"id":"frontier","label":"前沿","purpose":"边界","feynmanCheckpoint":"列争议"},
        ]}}
    def candidates(self):
        items=[]
        for stage in ('intro','framework','frontier'):
            for i in range(2):
                items.append({"bookId":f'{stage}-{i}',"title":f'{stage}{i}',"stage":stage,"verifiedAgainstCatalog":True,"verifiedAvailable":True,"alreadyRead":False,"recommendationEligible":True,"rating":90-i,"wordCount":90000})
        return {"items":items}
    def test_six_verified_books_make_ready_plan(self):
        result=mod.build(self.path_context(),self.candidates(),'beginner')
        self.assertTrue(result['ready'])
        self.assertEqual(sum(len(x['selected']) for x in result['stages']),6)
        self.assertEqual(len(result['minimumVersion']),2)
        self.assertTrue(result['timeEstimate']['complete'])
    def test_unverified_or_already_read_books_do_not_fill_slots(self):
        data=self.candidates();data['items'][0]['alreadyRead']=True;data['items'][1]['verifiedAvailable']=False
        result=mod.build(self.path_context(),data,'beginner')
        self.assertFalse(result['ready'])
        self.assertIn('intro',result['deficits'])

if __name__=='__main__': unittest.main()
