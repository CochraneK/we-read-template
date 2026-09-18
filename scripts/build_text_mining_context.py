#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a private, deterministic text-mining layer over WeRead evidence.

The Lite layer is standard-library only. It separates source highlights from
user-authored reviews, then computes lexical statistics without pretending that
saved source text is the user's belief.

Outputs are private-only because selected evidence snippets and review-language
signals may expose personal reading content.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from itertools import combinations
from math import log, log2, sqrt
from pathlib import Path
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "private_lab" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "private_lab" / "text_mining_context.json"

EN_STOP = {
    "the","a","an","and","or","but","if","then","than","of","to","in","on","for","from","with",
    "as","at","by","is","are","was","were","be","been","being","it","its","this","that","these",
    "those","i","me","my","we","our","you","your","he","she","they","them","their","not","no",
    "do","does","did","can","could","may","might","will","would","should","have","has","had",
    "what","why","how","when","where","who","which","because","so","therefore","also","very",
    "more","most","some","any","all","one","two","about","into","out","up","down","over","under",
}
ZH_STOP = {
    "我们","他们","自己","这个","那个","这些","那些","因为","所以","但是","如果","不是","一个","一种",
    "可以","可能","没有","什么","就是","以及","对于","这种","已经","还是","时候","这样","进行","需要",
    "认为","觉得","关于","通过","如何","其中","同时","非常","比较","为了","由于","而且","或者","应该",
    "能够","问题","东西","事情","其实","只是","只是","之后","之前","现在","然后","这里","那里","很多",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]+|[\u4e00-\u9fff]+")
SPACE_RE = re.compile(r"\s+")

RHETORICAL_MARKERS = {
    "question": ("?", "？", "为什么", "如何", "是否", "what if", "why ", "how "),
    "challenge": ("但是", "然而", "未必", "不一定", "忽略", "问题在于", "不同意", "值得怀疑", "不能简单", "however", "disagree", "overlook"),
    "agreement": ("同意", "赞同", "确实", "有道理", "认同", "agree", "makes sense"),
    "uncertainty": ("可能", "也许", "似乎", "或许", "不确定", "恐怕", "maybe", "perhaps", "uncertain", "seems"),
    "qualification": ("不过", "除非", "前提是", "取决于", "在一定程度", "另一方面", "except", "unless", "depends"),
    "causal": ("因为", "所以", "导致", "因此", "由于", "因而", "because", "therefore", "cause", "leads to"),
    "metacognitive": ("我觉得", "我认为", "我理解", "我想到", "让我想到", "不明白", "没懂", "我怀疑", "I think", "I wonder", "I don't understand"),
}


def parse_time(raw) -> datetime | None:
    try:
        value = int(float(raw or 0))
        if value <= 0:
            return None
        if value > 10_000_000_000:
            value //= 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", str(value or "")).strip()


def tokenize(text: str) -> list[str]:
    """Dependency-free lexical units for mixed Chinese/English text.

    English uses lower-cased word tokens. Chinese uses character bigrams and
    trigrams inside contiguous Han spans; this is intentionally described as
    lexical n-grams rather than word segmentation.
    """
    out: list[str] = []
    for match in TOKEN_RE.findall(normalize_text(text)):
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9'_-]+", match):
            token = match.lower().strip("_-'")
            if len(token) >= 2 and token not in EN_STOP:
                out.append(token)
            continue
        chars = match
        if len(chars) == 1:
            continue
        for n in (2, 3):
            if len(chars) < n:
                continue
            for i in range(len(chars) - n + 1):
                token = chars[i:i+n]
                if token not in ZH_STOP:
                    out.append(token)
    return out


def evidence_rows(context: dict) -> list[dict]:
    rows = []
    for book in context.get("books") or []:
        if not isinstance(book, dict):
            continue
        base = {
            "bookId": str(book.get("bookId") or ""),
            "title": str(book.get("title") or ""),
            "author": str(book.get("author") or ""),
            "category": str(book.get("category") or ""),
        }
        for key, role in (("marks", "source_text"), ("reviews", "user_thought")):
            for index, item in enumerate(book.get(key) or []):
                if not isinstance(item, dict):
                    continue
                text = normalize_text(item.get("text") or item.get("content") or item.get("abstract") or "")
                if not text:
                    continue
                when = parse_time(item.get("createTime"))
                stable = str(item.get("bookmarkId") or item.get("reviewId") or item.get("range") or index)
                rows.append({
                    **base,
                    "id": f"{role}:{base['bookId']}:{stable}",
                    "role": role,
                    "chapter": str(item.get("chapter") or ""),
                    "text": text,
                    "createTime": int(item.get("createTime") or 0),
                    "date": when.date().isoformat() if when else None,
                    "year": str(when.year) if when else None,
                })
    rows.sort(key=lambda x: (int(x.get("createTime") or 0), x["id"]))
    return rows


def document_tokens(rows: list[dict]) -> tuple[list[Counter], Counter, dict[str, float]]:
    counters = []
    df = Counter()
    for row in rows:
        counter = Counter(tokenize(row["text"]))
        counters.append(counter)
        df.update(counter.keys())
    n_docs = max(1, len(rows))
    idf = {term: log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()}
    return counters, df, idf


def top_terms(rows: list[dict], counters: list[Counter], idf: dict[str, float], *, role: str | None = None, limit: int = 40) -> list[dict]:
    score = Counter()
    docs = Counter()
    for row, counter in zip(rows, counters):
        if role and row["role"] != role:
            continue
        length = max(1, sum(counter.values()))
        for term, count in counter.items():
            score[term] += (count / length) * idf.get(term, 1.0)
            docs[term] += 1
    return [
        {"term": term, "score": round(value, 6), "documents": docs[term]}
        for term, value in score.most_common(limit)
    ]


def lexical_diversity(rows: list[dict], counters: list[Counter], role: str) -> dict:
    merged = Counter()
    docs = 0
    for row, counter in zip(rows, counters):
        if row["role"] != role:
            continue
        merged.update(counter)
        docs += 1
    total = sum(merged.values())
    types = len(merged)
    hapax = sum(1 for value in merged.values() if value == 1)
    return {
        "documents": docs,
        "tokens": total,
        "types": types,
        "typeTokenRatio": round(types / total, 4) if total else 0.0,
        "hapaxShare": round(hapax / types, 4) if types else 0.0,
        "unit": "English words + Chinese character bi/tri-grams",
    }



def contrastive_terms(rows: list[dict], counters: list[Counter], limit: int = 30) -> dict:
    """Smoothed log-ratio terms that distinguish exposure vs expression corpora."""
    source = Counter()
    self_words = Counter()
    for row, counter in zip(rows, counters):
        (source if row["role"] == "source_text" else self_words).update(counter)
    vocab = set(source) | set(self_words)
    source_total = sum(source.values())
    self_total = sum(self_words.values())
    alpha = 0.5
    denom_source = source_total + alpha * max(1, len(vocab))
    denom_self = self_total + alpha * max(1, len(vocab))
    scored = []
    for term in vocab:
        ps = (source[term] + alpha) / denom_source
        pu = (self_words[term] + alpha) / denom_self
        scored.append((log(ps / pu), term))
    source_ranked = sorted((x for x in scored if x[0] > 0), reverse=True)[:limit]
    self_ranked = sorted((x for x in scored if x[0] < 0))[:limit]
    return {
        "sourceDistinctive": [
            {"term": term, "logRatio": round(score, 4), "sourceCount": source[term], "selfCount": self_words[term]}
            for score, term in source_ranked
        ],
        "selfDistinctive": [
            {"term": term, "logRatio": round(-score, 4), "sourceCount": source[term], "selfCount": self_words[term]}
            for score, term in self_ranked
        ],
        "method": "add-0.5 smoothed token-frequency log ratio; lexical contrast, not belief contrast",
    }


def cooccurrence(rows: list[dict], counters: list[Counter], df: Counter, idf: dict[str, float], limit: int = 100) -> tuple[list[dict], list[dict]]:
    n_docs = max(1, len(rows))
    eligible = {term for term, count in df.items() if count >= 2}
    pair_counts = Counter()
    for counter in counters:
        terms = sorted(
            (term for term in counter if term in eligible),
            key=lambda t: (-idf.get(t, 0.0), t),
        )[:12]
        for a, b in combinations(sorted(set(terms)), 2):
            pair_counts[(a, b)] += 1

    edges = []
    for (a, b), support in pair_counts.items():
        if support < 2:
            continue
        pmi = log2((support * n_docs) / max(1, df[a] * df[b]))
        if pmi <= 0:
            continue
        edges.append({
            "source": a,
            "target": b,
            "support": support,
            "pmi": round(pmi, 3),
        })
    edges.sort(key=lambda x: (-x["support"], -x["pmi"], x["source"], x["target"]))
    edges = edges[:limit]

    # Conservative lexical communities: union only reasonably strong edges.
    parent: dict[str, str] = {}
    strength = Counter()

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for edge in edges:
        strength[edge["source"]] += edge["support"]
        strength[edge["target"]] += edge["support"]
        if edge["support"] >= 2 and edge["pmi"] >= 1.0:
            union(edge["source"], edge["target"])

    groups = defaultdict(set)
    for term in parent:
        groups[find(term)].add(term)
    communities = []
    for terms in groups.values():
        if len(terms) < 3:
            continue
        ranked = sorted(terms, key=lambda t: (-strength[t], -df[t], t))
        communities.append({
            "label": " / ".join(ranked[:3]),
            "terms": ranked[:12],
            "size": len(terms),
            "documentSupport": sum(df[t] for t in terms),
            "status": "lexical_cooccurrence_candidate",
        })
    communities.sort(key=lambda x: (-x["size"], -x["documentSupport"], x["label"]))
    return edges, communities[:16]


def temporal_terms(rows: list[dict], counters: list[Counter], idf: dict[str, float]) -> list[dict]:
    years = sorted({row["year"] for row in rows if row.get("year")})
    result = []
    for year in years:
        indices = [i for i, row in enumerate(rows) if row.get("year") == year]
        role_payload = {}
        for role in ("source_text", "user_thought"):
            scoped_rows = [rows[i] for i in indices]
            scoped_counters = [counters[i] for i in indices]
            role_payload[role] = top_terms(scoped_rows, scoped_counters, idf, role=role, limit=12)
        result.append({"year": year, "documents": len(indices), "topTerms": role_payload})
    return result


def burst_and_resurgence(rows: list[dict], counters: list[Counter], df: Counter, limit: int = 30) -> tuple[list[dict], list[dict]]:
    years = sorted({int(row["year"]) for row in rows if row.get("year")})
    if not years:
        return [], []
    by_year: dict[int, Counter] = {year: Counter() for year in years}
    docs_per_year = Counter()
    for row, counter in zip(rows, counters):
        if not row.get("year"):
            continue
        year = int(row["year"])
        docs_per_year[year] += 1
        by_year[year].update(counter.keys())

    terms = [term for term, count in df.most_common(300) if count >= 2]
    bursts = []
    resurgence = []
    for term in terms:
        series = []
        for year in years:
            share = by_year[year][term] / max(1, docs_per_year[year])
            series.append((year, by_year[year][term], share))
        shares = [x[2] for x in series]
        mean = sum(shares) / len(shares)
        std = sqrt(sum((x - mean) ** 2 for x in shares) / len(shares)) if len(shares) > 1 else 0.0
        peak = max(series, key=lambda x: (x[2], x[1], x[0]))
        z = (peak[2] - mean) / std if std > 1e-12 else 0.0
        if peak[1] >= 2 and (z >= 1.0 or peak[2] >= max(0.15, mean * 1.8)):
            bursts.append({
                "term": term,
                "peakYear": str(peak[0]),
                "peakDocuments": peak[1],
                "peakShare": round(peak[2], 4),
                "z": round(z, 3),
                "series": [{"year": str(y), "documents": c, "share": round(s, 4)} for y, c, s in series],
            })
        active = [(y, c, s) for y, c, s in series if c > 0]
        if len(active) >= 2:
            first, later = active[0], max(active[1:], key=lambda x: (x[2], x[1], x[0]))
            if later[0] - first[0] >= 2 and later[1] >= 2 and later[2] >= max(first[2] * 1.5, 0.08):
                resurgence.append({
                    "term": term,
                    "firstYear": str(first[0]),
                    "resurgenceYear": str(later[0]),
                    "gapYears": later[0] - first[0],
                    "firstShare": round(first[2], 4),
                    "resurgenceShare": round(later[2], 4),
                })
    bursts.sort(key=lambda x: (-x["z"], -x["peakShare"], x["term"]))
    resurgence.sort(key=lambda x: (-x["gapYears"], -x["resurgenceShare"], x["term"]))
    return bursts[:limit], resurgence[:limit]


def sparse_vector(counter: Counter, idf: dict[str, float]) -> dict[str, float]:
    length = max(1, sum(counter.values()))
    vec = {term: (count / length) * idf.get(term, 1.0) for term, count in counter.items()}
    norm = sqrt(sum(value * value for value in vec.values()))
    if norm:
        vec = {term: value / norm for term, value in vec.items()}
    return vec


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(term, 0.0) for term, value in a.items())


def novelty(rows: list[dict], counters: list[Counter], idf: dict[str, float]) -> dict:
    vectors = [sparse_vector(counter, idf) for counter in counters]
    postings: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=24))
    year_values = defaultdict(list)
    role_values = defaultdict(list)
    top_novel = []
    seen_terms = set()

    for i, (row, counter, vector) in enumerate(zip(rows, counters, vectors)):
        if not row.get("createTime"):
            continue
        candidates = Counter()
        for term in vector:
            for previous in postings[term]:
                candidates[previous] += 1
        best = 0.0
        best_index = None
        for previous, _shared in candidates.most_common(120):
            score = cosine(vector, vectors[previous])
            if score > best:
                best, best_index = score, previous
        unique_terms = set(counter)
        new_share = len(unique_terms - seen_terms) / max(1, len(unique_terms))
        seen_terms.update(unique_terms)
        value = max(0.0, 1.0 - best)
        year = row.get("year")
        if year:
            year_values[year].append(value)
        role_values[row["role"]].append(value)
        top_novel.append({
            "evidenceId": row["id"],
            "role": row["role"],
            "bookId": row["bookId"],
            "title": row["title"],
            "date": row.get("date"),
            "novelty": round(value, 4),
            "maxPriorLexicalSimilarity": round(best, 4),
            "newLexicalUnitShare": round(new_share, 4),
            "nearestPriorEvidenceId": rows[best_index]["id"] if best_index is not None else None,
            "snippet": row["text"][:180],
        })
        for term in vector:
            postings[term].append(i)

    top_novel.sort(key=lambda x: (-x["novelty"], -x["newLexicalUnitShare"], x["evidenceId"]))
    return {
        "method": "TF-IDF cosine against candidate prior documents sharing lexical units; not semantic novelty",
        "byYear": [
            {"year": year, "meanNovelty": round(sum(vals) / len(vals), 4), "documents": len(vals)}
            for year, vals in sorted(year_values.items())
        ],
        "byRole": {
            role: {"meanNovelty": round(sum(vals) / len(vals), 4), "documents": len(vals)}
            for role, vals in sorted(role_values.items()) if vals
        },
        "mostNovel": top_novel[:30],
    }


def exposure_expression_lag(rows: list[dict], counters: list[Counter], df: Counter, limit: int = 40) -> list[dict]:
    first_source: dict[str, tuple[int, str]] = {}
    first_self: dict[str, tuple[int, str]] = {}
    source_docs = Counter()
    self_docs = Counter()
    for row, counter in zip(rows, counters):
        ts = int(row.get("createTime") or 0)
        if not ts:
            continue
        target = first_source if row["role"] == "source_text" else first_self
        doc_counter = source_docs if row["role"] == "source_text" else self_docs
        for term in counter:
            doc_counter[term] += 1
            current = target.get(term)
            if current is None or ts < current[0]:
                target[term] = (ts, row["id"])

    items = []
    for term in set(first_source) & set(first_self):
        src_ts, src_id = first_source[term]
        self_ts, self_id = first_self[term]
        if self_ts <= src_ts:
            continue
        lag_days = round((self_ts - src_ts) / 86400, 1)
        if source_docs[term] < 2 or self_docs[term] < 1:
            continue
        items.append({
            "term": term,
            "lagDays": lag_days,
            "firstSourceEvidenceId": src_id,
            "firstSelfEvidenceId": self_id,
            "sourceDocuments": source_docs[term],
            "selfDocuments": self_docs[term],
            "status": "lexical_exposure_expression_lag",
        })
    items.sort(key=lambda x: (-x["selfDocuments"], -x["sourceDocuments"], x["lagDays"], x["term"]))
    return items[:limit]


def rhetorical_signals(rows: list[dict]) -> dict:
    review_rows = [row for row in rows if row["role"] == "user_thought"]
    counts = Counter()
    examples = defaultdict(list)
    for row in review_rows:
        lowered = row["text"].lower()
        for label, markers in RHETORICAL_MARKERS.items():
            if any(marker.lower() in lowered for marker in markers):
                counts[label] += 1
                if len(examples[label]) < 8:
                    examples[label].append(row["id"])
    return {
        "documents": len(review_rows),
        "signals": [
            {
                "signal": label,
                "documents": counts[label],
                "share": round(counts[label] / len(review_rows), 4) if review_rows else 0.0,
                "exampleEvidenceIds": examples[label],
            }
            for label in RHETORICAL_MARKERS
        ],
        "status": "surface_language_heuristic",
        "note": "These are explicit language markers in user-authored reviews, not inferred personality, emotion, ideology, or clinical state.",
    }


def build(context: dict) -> dict:
    rows = evidence_rows(context)
    counters, df, idf = document_tokens(rows)
    edges, communities = cooccurrence(rows, counters, df, idf)
    bursts, resurgence = burst_and_resurgence(rows, counters, df)
    source_count = sum(1 for row in rows if row["role"] == "source_text")
    self_count = len(rows) - source_count
    return {
        "version": "1",
        "private": True,
        "publicPageSafe": False,
        "containsRawEvidenceSnippets": True,
        "coverage": {
            "documents": len(rows),
            "sourceHighlights": source_count,
            "userThoughts": self_count,
            "books": len({row["bookId"] for row in rows}),
            "years": sorted({row["year"] for row in rows if row.get("year")}),
        },
        "corpora": {
            "source": {
                "meaning": "Saved source highlights: exposure evidence, not automatically the user's belief.",
                "topTerms": top_terms(rows, counters, idf, role="source_text"),
                "lexicalDiversity": lexical_diversity(rows, counters, "source_text"),
            },
            "self": {
                "meaning": "User-authored reviews/thoughts: expression evidence, still bounded to what was actually written.",
                "topTerms": top_terms(rows, counters, idf, role="user_thought"),
                "lexicalDiversity": lexical_diversity(rows, counters, "user_thought"),
            },
            "allTopTerms": top_terms(rows, counters, idf),
        },
        "contrast": contrastive_terms(rows, counters),
        "cooccurrence": {
            "edges": edges,
            "communities": communities,
            "method": "document-level lexical co-occurrence with positive PMI; communities are candidates, not semantic topics",
        },
        "temporal": {
            "yearlyTerms": temporal_terms(rows, counters, idf),
            "bursts": bursts,
            "resurgence": resurgence,
        },
        "novelty": novelty(rows, counters, idf),
        "exposureExpression": {
            "items": exposure_expression_lag(rows, counters, df),
            "meaning": "Time from first saved source-text lexical unit to first later appearance in user-authored text; not proof of internalization or causality.",
        },
        "rhetoricalLanguage": rhetorical_signals(rows),
        "guardrails": [
            "Source highlights are exposure evidence, not automatically the user's beliefs.",
            "User reviews are expression evidence but must not be generalized into personality or sensitive-trait claims.",
            "Chinese Lite tokenization uses character bi/tri-grams, not linguistic word segmentation.",
            "Lexical communities are topic candidates, not semantic topic labels.",
            "Lexical novelty is not semantic novelty.",
            "Exposure→expression lag is temporal lexical overlap, not proof that a book caused a later belief.",
            "All raw snippets in this artifact are private-only.",
        ],
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main():
    args = parse_args()
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}; build visualization_context first")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    result = build(context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    c = result["coverage"]
    print(
        f"text-mining-lite: {args.output} | docs={c['documents']} source={c['sourceHighlights']} "
        f"self={c['userThoughts']} communities={len(result['cooccurrence']['communities'])} "
        f"bursts={len(result['temporal']['bursts'])} private=true"
    )


if __name__ == "__main__":
    main()
