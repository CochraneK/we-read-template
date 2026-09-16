#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'scripts'/'build_narrative_review_draft.py'
spec=importlib.util.spec_from_file_location('narrative_review_draft',MODULE);draft=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(draft)


def context(platform='wechat'):
    return {
        'period':{'start':'2026-01-01','end':'2026-09-14'},
        'readingTotals':{'hours':42.5,'activeDays':88,'dailyCoverageAvailable':True,'peakMonth':{'month':'2026-03','hours':10.2}},
        'summary':{'activeBooks':12,'completed':4,'reading':3,'shallow':2,'reread':1},
        'bookGroups':{'reading':[{'title':'在读书','author':'甲'}]},
        'narrativeCandidates':{
            'topByPeriodNotes':[{'title':'重点书','author':'乙','periodNotes':20,'periodReviews':5,'noteCount':30}],
            'stalled30To70Percent':[{'title':'卡住的书','author':'丙','progress':50,'daysStaleAtPeriodEnd':120}],
            'topNoteCategories':[{'category':'历史','periodNotes':30}],
            'focusShiftCandidate':{'changed':True,'firstHalfTopCategory':'历史','secondHalfTopCategory':'文学'}
        },
        'reviewContract':{
            'selectedPlatform':platform,
            'supportedPlatforms':{
                'wechat':{'label':'公众号','length':'1500-3000'},
                'moments':{'label':'朋友圈','length':'200-500'}
            }
        }
    }


class NarrativeReviewDraftTests(unittest.TestCase):
    def test_requires_confirmed_supported_platform(self):
        with self.assertRaises(ValueError):
            draft.build_draft(context(platform=''), None)

    def test_draft_keeps_unknown_causes_explicit(self):
        result=draft.build_draft(context(),None)
        text='\n'.join(p for sec in result['sections'] for p in sec.get('paragraphs',[]))
        self.assertIn('不能从数据本身知道原因',text)
        self.assertIn('待补',text)
        self.assertFalse(result['factBoundary']['causalReasonsInvented'])
        self.assertFalse(result['factBoundary']['rawNoteBodiesIncluded'])
        self.assertIn('卡住的书',text)

    def test_chinese_platform_alias_and_markdown(self):
        result=draft.build_draft(context(),platform='公众号')
        self.assertEqual(result['platform'],'wechat')
        md=draft.to_markdown(result)
        self.assertIn('# 我的 2026-01-01 → 2026-09-14 阅读复盘',md)
        self.assertIn('平台：公众号',md)
        self.assertIn('编辑前检查',md)

if __name__=='__main__': unittest.main()
