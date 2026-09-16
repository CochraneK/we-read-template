#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

brief=load('semantic_brief',ROOT/'scripts'/'build_candidate_semantic_brief.py')
apply_sem=load('semantic_apply',ROOT/'scripts'/'apply_candidate_semantics.py')


def fill(item, *, stage=None):
    for axis in apply_sem.AXES:
        item['semanticAnnotation'][axis]={'value':axis,'evidence':f'{axis} evidence','confidence':0.8}
    item['conceptualFit']={'value':'fills gap','evidence':'fit evidence','confidence':0.9}
    if stage:
        item['stage']=stage;item['stageEvidence']='pedagogical role evidence'
    return item


class CandidateSemanticTests(unittest.TestCase):
    def test_brief_does_not_infer_semantics(self):
        payload={'topic':'认知科学','shortlist':[{'bookId':'1','title':'书A','author':'甲','intro':'官方简介','verifiedAvailable':True,'alreadyRead':False}]}
        result=brief.build(payload,mode='advisor')
        item=result['items'][0]
        self.assertEqual(item['semanticAnnotation']['school_or_viewpoint']['value'],'')
        self.assertEqual(item['conceptualFit']['value'],'')
        self.assertFalse(result['ready'])

    def test_advisor_promotes_only_fully_evidenced_candidate(self):
        source=brief.build({'topic':'主题','shortlist':[{'bookId':'1','title':'书A','verifiedAvailable':True,'alreadyRead':False}]},mode='advisor')
        failed=apply_sem.apply(source)
        self.assertFalse(failed['readyForFinalRecommendation'])
        fill(source['items'][0])
        passed=apply_sem.apply(source)
        self.assertTrue(passed['readyForFinalRecommendation'])
        self.assertEqual(len(passed['items']),1)
        self.assertTrue(passed['items'][0]['semanticGatePassed'])

    def test_path_requires_stage_and_stage_evidence(self):
        source=brief.build({'topic':'心理学','items':[{'bookId':'1','title':'书A','verifiedAvailable':True,'alreadyRead':False}]},mode='path')
        fill(source['items'][0])
        failed=apply_sem.apply(source)
        self.assertFalse(failed['readyForPathPlan'])
        self.assertIn('missing_or_invalid_stage',failed['rejected'][0]['semanticGateProblems'])
        fill(source['items'][0],stage='framework')
        passed=apply_sem.apply(source)
        self.assertTrue(passed['readyForPathPlan'])
        self.assertEqual(passed['items'][0]['stage'],'framework')

    def test_already_read_never_promotes(self):
        source=brief.build({'topic':'主题','shortlist':[{'bookId':'1','title':'书A','verifiedAvailable':True,'alreadyRead':True}]},mode='advisor')
        fill(source['items'][0])
        result=apply_sem.apply(source)
        self.assertFalse(result['readyForFinalRecommendation'])
        self.assertIn('already_read',result['rejected'][0]['semanticGateProblems'])

if __name__=='__main__': unittest.main()
