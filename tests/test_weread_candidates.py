#!/usr/bin/env python3
from pathlib import Path
from unittest import mock
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

catalog = load("weread_catalog_test", SCRIPTS / "weread_catalog.py")
verify = load("verify_weread_candidates_test", SCRIPTS / "verify_weread_candidates.py")


class WeReadCandidateTests(unittest.TestCase):
    def context(self):
        return {"books":[
            {"bookId":"read","title":"读过的书","author":"甲","noteCount":12,"progress":90,"inShelf":True},
            {"bookId":"shelf","title":"收藏未读","author":"乙","noteCount":0,"progress":0,"inShelf":True},
        ]}

    def test_flatten_does_not_require_response_scope_to_equal_request_scope(self):
        data={"results":[{"title":"电子书","scope":17,"books":[{"searchIdx":3,"bookInfo":{"bookId":"x","title":"书X","author":"丙","soldout":0},"newRating":88,"readingCount":100}]}]}
        rows=catalog.flatten_search_response(data)
        self.assertEqual(rows[0]["bookId"],"x")
        self.assertEqual(rows[0]["responseScope"],17)

    def test_discovery_marks_already_read_and_shelf_only(self):
        fake={"keyword":"主题","scope":10,"hasMore":0,"items":[
            {"bookId":"read","title":"读过的书","author":"甲","soldout":0,"rating":90,"ratingCount":100,"searchIdx":1},
            {"bookId":"shelf","title":"收藏未读","author":"乙","soldout":0,"rating":80,"ratingCount":50,"searchIdx":2},
        ]}
        with mock.patch.object(verify.weread_catalog,"search_books",return_value=fake):
            result=verify.verify_discovery(self.context(),"主题")
        by_id={x["bookId"]:x for x in result["items"]}
        self.assertTrue(by_id["read"]["alreadyRead"])
        self.assertFalse(by_id["read"]["recommendationEligible"])
        self.assertTrue(by_id["shelf"]["shelvedUnengaged"])
        self.assertTrue(by_id["shelf"]["recommendationEligible"])

    def test_exact_candidate_resolution_preserves_stage(self):
        found={"keyword":"候选书","scope":10,"hasMore":0,"items":[{"bookId":"new","title":"候选书","author":"作者","soldout":0,"rating":90,"ratingCount":10,"searchIdx":1}]}
        with mock.patch.object(verify.weread_catalog,"search_books",return_value=found):
            result=verify.verify_candidates(self.context(),[{"title":"候选书","author":"作者","stage":"intro"}])
        self.assertTrue(result["items"][0]["verifiedAvailable"])
        self.assertEqual(result["items"][0]["stage"],"intro")


if __name__ == "__main__":
    unittest.main()
