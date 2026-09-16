#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a private, deterministic synthesis scaffold from Alchemy evidence.

This is deliberately conservative: lexical clusters are labelled as heuristic
issue candidates, not semantic claims. It separates source text and user thoughts
and surfaces evidence/questions for later human or model synthesis.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import re

STOP = {
    "一个","我们","他们","自己","这个","这种","就是","不是","可以","没有","因为","所以","如果","但是","而且","以及","对于","什么","怎么","如何","其实","已经","只是","还是","非常","应该","不能","很多","一些","进行","通过","这样","那些","其中","可能","需要","问题","时候","作者","认为",
}


def tokens(text: str) -> set[str]:
    text = str(text or "").lower()
    out = {w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", text)}
    for seq in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if 2 <= len(seq) <= 8 and seq not in STOP:
            out.add(seq)
        for n in (2, 3, 4):
            if len(seq) >= n:
                for i in range(len(seq) - n + 1):
                    t = seq[i:i+n]
                    if t not in STOP:
                        out.add(t)
    return out


def clip(text: str, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    return value if len(value) <= limit else value[:limit].rstrip() + "…"


def flatten(context: dict) -> list[dict]:
    rows = []
    for book in context.get("books") or []:
        base = {k: book.get(k) for k in ("bookId","title","author","category")}
        for chapter in book.get("chapters") or []:
            for key, kind in (("marks","source_text"),("reviews","user_thought")):
                for row in chapter.get(key) or []:
                    text = str(row.get("text") or "").strip()
                    if text:
                        rows.append({**base,"chapter":chapter.get("chapter") or "未分章","kind":kind,"text":text,"createTime":int(row.get("createTime") or 0)})
    return rows


def build(context: dict, max_clusters: int = 6) -> dict:
    if (context.get("landscape") or {}).get("requiresScopeConfirmation"):
        return {
            "version":"1","generatedAt":datetime.now(timezone.utc).isoformat(),"ready":False,
            "reason":"scope_confirmation_required","privacy":context.get("privacy") or {},"clusters":[],
            "questions":["先缩小主题范围，再重新生成 Alchemy synthesis。"],
        }
    rows = flatten(context)
    docs = [(row, tokens(row["text"])) for row in rows]
    df = Counter()
    user_df = Counter()
    for row, ts in docs:
        for t in ts:
            df[t] += 1
            if row["kind"] == "user_thought":
                user_df[t] += 1
    ranked = [t for t,_ in sorted(df.items(), key=lambda kv:(-(kv[1]*10 + user_df[kv[0]]*4), -len(kv[0]), kv[0])) if df[t] >= 2]
    labels = ranked[:max(1,max_clusters)]
    buckets = defaultdict(list)
    for row, ts in docs:
        label = next((t for t in labels if t in ts), "其他证据")
        buckets[label].append(row)
    clusters = []
    for label, items in sorted(buckets.items(), key=lambda kv:-len(kv[1])):
        marks=[x for x in items if x["kind"]=="source_text"]
        reviews=[x for x in items if x["kind"]=="user_thought"]
        books=sorted({x.get("title") or "" for x in items if x.get("title")})
        if marks and reviews:
            q="你的这些想法是在支持、修正，还是反驳这组来源文本？"
        elif marks:
            q="这组原文目前还缺少你的判断：你认同什么、反对什么、为什么？"
        else:
            q="这些个人想法可以回到哪些作者原文或章节寻找支撑与反例？"
        clusters.append({
            "label":label,"status":"heuristic_lexical_cluster","evidenceCount":len(items),"sourceCount":len(marks),"userThoughtCount":len(reviews),"books":books,
            "representativeSourceText":[{"title":x.get("title"),"chapter":x.get("chapter"),"text":clip(x["text"])} for x in marks[:3]],
            "representativeUserThought":[{"title":x.get("title"),"chapter":x.get("chapter"),"text":clip(x["text"])} for x in reviews[:3]],
            "question":q,
        })
    return {
        "version":"1","generatedAt":datetime.now(timezone.utc).isoformat(),"ready":True,"mode":context.get("mode"),"selector":context.get("selector"),
        "privacy":{"publicPageSafe":False,"containsRawEvidence":True},
        "coverage":{"evidence":len(rows),"clusters":len(clusters),"books":len({x.get('bookId') for x in rows})},
        "clusters":clusters,
        "questions":["哪些议题只是作者反复出现，而你其实没有形成自己的判断？","哪些个人想法缺少原文或跨书反证？","哪些议题值得进入下一轮 Search / Recall / 深读？"],
        "guardrails":["Clusters are lexical heuristics, not semantic conclusions.","Source text is not the user's belief.","User thoughts must not be generalized beyond the evidence shown."],
    }


def parse_args():
    p=argparse.ArgumentParser(description="Build private deterministic Alchemy synthesis scaffold.")
    p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--max-clusters",type=int,default=6);return p.parse_args()


def main():
    a=parse_args();ctx=json.loads(a.input.read_text(encoding="utf-8"));result=build(ctx,max_clusters=max(1,min(a.max_clusters,12)));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(f"alchemy-synthesis: {a.output} | ready={result['ready']} clusters={len(result['clusters'])} private=true")

if __name__=="__main__": main()
