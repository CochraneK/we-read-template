#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enrich verified WeRead candidates with official `/book/info` fields."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import weread_catalog


def enrich(payload: dict) -> dict:
    rows=[]
    for item in payload.get("items") or []:
        row=dict(item)
        bid=str(row.get("bookId") or "")
        if bid and row.get("verifiedAvailable"):
            try:
                info=weread_catalog.book_info(bid)
                row["bookInfoVerified"]=True
                for key in ("wordCount","publishTime","publisher","category","isbn","deepLink","title","author"):
                    if info.get(key) not in (None,""):
                        row[key]=info.get(key)
                if info.get("newRating") is not None:
                    row["rating"]=info.get("newRating")
                if info.get("newRatingCount") is not None:
                    row["ratingCount"]=info.get("newRatingCount")
            except Exception as exc:
                row["bookInfoVerified"]=False
                row["bookInfoError"]=str(exc)
        else:
            row["bookInfoVerified"]=False
        rows.append(row)
    result=dict(payload)
    result["items"]=rows
    result["bookInfoEnrichedAt"]=datetime.now(timezone.utc).isoformat()
    result["bookInfoApi"]="/book/info"
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();payload=json.loads(a.input.read_text(encoding="utf-8"));result=enrich(payload);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");ok=sum(1 for x in result["items"] if x.get("bookInfoVerified"));print(f"candidate-info: {a.output} | enriched={ok}/{len(result['items'])}")

if __name__=="__main__": main()
