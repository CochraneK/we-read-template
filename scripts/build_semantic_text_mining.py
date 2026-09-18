#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional local semantic enrichment for the Private Text Mining Lab.

Requires sentence-transformers, numpy and scikit-learn. The model may be a local
path or a model identifier. User text is embedded locally by SentenceTransformer;
no remote inference API is used by this script.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import json
import os

import build_text_mining_context as lite

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_CONTEXT = DATA / "analysis" / "private_lab" / "visualization_context.json"
DEFAULT_OUTPUT = DATA / "analysis" / "private_lab" / "text_mining_semantic.json"


def require_dependencies():
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import KMeans
        from sklearn.neighbors import NearestNeighbors
        from sklearn.decomposition import NMF, LatentDirichletAllocation
        from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    except ImportError as exc:
        raise SystemExit(
            "ERROR: semantic text mining dependencies are missing. "
            "Install: pip install -r requirements-text-mining.txt"
        ) from exc
    return (
        np, SentenceTransformer, KMeans, NearestNeighbors,
        NMF, LatentDirichletAllocation, TfidfVectorizer, CountVectorizer,
    )


def cluster_count(n: int, explicit: int) -> int:
    if explicit > 0:
        return max(2, min(explicit, min(20, n)))
    if n < 6:
        return 2
    return max(3, min(12, round((n / 2) ** 0.5)))


def cluster_labels(rows: list[dict], labels, k: int) -> list[dict]:
    groups = defaultdict(list)
    for row, label in zip(rows, labels):
        groups[int(label)].append(row)
    result = []
    for label in range(k):
        docs = groups.get(label, [])
        terms = Counter()
        role_counts = Counter()
        books = Counter()
        years = Counter()
        for row in docs:
            terms.update(set(lite.tokenize(row["text"])))
            role_counts[row["role"]] += 1
            books[row["title"]] += 1
            if row.get("year"):
                years[row["year"]] += 1
        ranked = [term for term, _ in terms.most_common(12)]
        result.append({
            "cluster": label,
            "label": " / ".join(ranked[:3]) if ranked else f"cluster-{label}",
            "terms": ranked,
            "documents": len(docs),
            "roles": dict(role_counts),
            "topBooks": [{"title": title, "documents": count} for title, count in books.most_common(8)],
            "years": [{"year": year, "documents": count} for year, count in sorted(years.items())],
            "status": "embedding_cluster_candidate",
        })
    result.sort(key=lambda x: (-x["documents"], x["cluster"]))
    return result



def _topic_rows(model, feature_names, assignments, k: int, method: str) -> list[dict]:
    rows = []
    counts = Counter(int(x) for x in assignments)
    for topic_id in range(k):
        component = model.components_[topic_id]
        top = component.argsort()[::-1][:12]
        terms = [str(feature_names[i]) for i in top if component[i] > 0]
        rows.append({
            "topic": topic_id,
            "label": " / ".join(terms[:3]) if terms else f"{method}-{topic_id}",
            "terms": terms,
            "documents": counts.get(topic_id, 0),
            "method": method,
            "status": "classical_topic_candidate",
        })
    rows.sort(key=lambda x: (-x["documents"], x["topic"]))
    return rows


def classical_topics(rows: list[dict], k: int, NMF, LDA, TfidfVectorizer, CountVectorizer) -> dict:
    docs = [" ".join(lite.tokenize(row["text"])) for row in rows]
    docs = [doc if doc.strip() else "__empty__" for doc in docs]
    result = {"nmf": [], "lda": [], "note": "Classical baselines over Lite lexical units; compare with embedding clusters rather than treating one model as truth."}

    try:
        tfidf = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=2, max_features=4000)
        x_tfidf = tfidf.fit_transform(docs)
    except ValueError:
        tfidf = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=1, max_features=4000)
        x_tfidf = tfidf.fit_transform(docs)
    if min(x_tfidf.shape) >= 2:
        topic_k = max(2, min(k, x_tfidf.shape[0], x_tfidf.shape[1]))
        nmf = NMF(n_components=topic_k, random_state=42, init="nndsvda", max_iter=500)
        weights = nmf.fit_transform(x_tfidf)
        result["nmf"] = _topic_rows(
            nmf,
            tfidf.get_feature_names_out(),
            weights.argmax(axis=1),
            topic_k,
            "NMF",
        )

    try:
        count_vec = CountVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=2, max_features=4000)
        x_count = count_vec.fit_transform(docs)
    except ValueError:
        count_vec = CountVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=1, max_features=4000)
        x_count = count_vec.fit_transform(docs)
    if min(x_count.shape) >= 2:
        topic_k = max(2, min(k, x_count.shape[0], x_count.shape[1]))
        lda = LDA(
            n_components=topic_k,
            random_state=42,
            learning_method="batch",
            max_iter=20,
        )
        weights = lda.fit_transform(x_count)
        result["lda"] = _topic_rows(
            lda,
            count_vec.get_feature_names_out(),
            weights.argmax(axis=1),
            topic_k,
            "LDA",
        )
    return result


def cross_book_neighbors(rows, embeddings, NearestNeighbors, limit: int = 80) -> list[dict]:
    n = len(rows)
    if n < 2:
        return []
    neighbors = NearestNeighbors(n_neighbors=min(10, n), metric="cosine")
    neighbors.fit(embeddings)
    distances, indices = neighbors.kneighbors(embeddings)
    pairs = []
    seen = set()
    for i, (ds, js) in enumerate(zip(distances, indices)):
        for distance, j in zip(ds[1:], js[1:]):
            j = int(j)
            if rows[i]["bookId"] == rows[j]["bookId"]:
                continue
            key = tuple(sorted((i, j)))
            if key in seen:
                continue
            seen.add(key)
            similarity = 1.0 - float(distance)
            if similarity < 0.45:
                continue
            a, b = rows[i], rows[j]
            pairs.append({
                "similarity": round(similarity, 4),
                "a": {
                    "evidenceId": a["id"], "role": a["role"], "bookId": a["bookId"],
                    "title": a["title"], "chapter": a["chapter"], "date": a.get("date"),
                    "snippet": a["text"][:180],
                },
                "b": {
                    "evidenceId": b["id"], "role": b["role"], "bookId": b["bookId"],
                    "title": b["title"], "chapter": b["chapter"], "date": b.get("date"),
                    "snippet": b["text"][:180],
                },
                "relation": "semantic_similarity_candidate",
            })
            break
    pairs.sort(key=lambda x: (-x["similarity"], x["a"]["evidenceId"], x["b"]["evidenceId"]))
    return pairs[:limit]


def yearly_drift(rows, embeddings, np) -> list[dict]:
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        if row.get("year"):
            groups[row["year"]].append(index)
    years = sorted(groups)
    centroids = {}
    for year in years:
        centroid = embeddings[groups[year]].mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm:
            centroid = centroid / norm
        centroids[year] = centroid
    result = []
    for previous, current in zip(years, years[1:]):
        similarity = float(np.dot(centroids[previous], centroids[current]))
        result.append({
            "fromYear": previous,
            "toYear": current,
            "centroidSimilarity": round(similarity, 4),
            "drift": round(max(0.0, 1.0 - similarity), 4),
            "fromDocuments": len(groups[previous]),
            "toDocuments": len(groups[current]),
            "status": "corpus_embedding_drift",
        })
    return result


def source_self_alignment(rows, embeddings, NearestNeighbors, limit: int = 60) -> list[dict]:
    source_indices = [i for i, row in enumerate(rows) if row["role"] == "source_text"]
    self_indices = [i for i, row in enumerate(rows) if row["role"] == "user_thought"]
    if not source_indices or not self_indices:
        return []
    source_matrix = embeddings[source_indices]
    nn = NearestNeighbors(n_neighbors=min(16, len(source_indices)), metric="cosine")
    nn.fit(source_matrix)
    distances, local_indices = nn.kneighbors(embeddings[self_indices])
    results = []
    for review_i, ds, candidates in zip(self_indices, distances, local_indices):
        review = rows[review_i]
        review_ts = int(review.get("createTime") or 0)
        chosen = None
        for distance, local_j in zip(ds, candidates):
            source_i = source_indices[int(local_j)]
            source = rows[source_i]
            source_ts = int(source.get("createTime") or 0)
            if review_ts and source_ts and source_ts > review_ts:
                continue
            similarity = 1.0 - float(distance)
            if similarity < 0.45:
                continue
            chosen = (source, similarity)
            break
        if chosen is None:
            continue
        source, similarity = chosen
        lag_days = None
        if review_ts and int(source.get("createTime") or 0):
            lag_days = round((review_ts - int(source["createTime"])) / 86400, 1)
        results.append({
            "similarity": round(similarity, 4),
            "lagDays": lag_days,
            "source": {
                "evidenceId": source["id"], "bookId": source["bookId"], "title": source["title"],
                "chapter": source["chapter"], "date": source.get("date"), "snippet": source["text"][:180],
            },
            "self": {
                "evidenceId": review["id"], "bookId": review["bookId"], "title": review["title"],
                "chapter": review["chapter"], "date": review.get("date"), "snippet": review["text"][:180],
            },
            "status": "semantic_exposure_expression_candidate",
        })
    results.sort(key=lambda x: (-x["similarity"], x["lagDays"] if x["lagDays"] is not None else 10**9))
    return results[:limit]


def build(context: dict, *, model_name: str, clusters: int = 0, max_docs: int = 5000) -> dict:
    (
        np, SentenceTransformer, KMeans, NearestNeighbors,
        NMF, LDA, TfidfVectorizer, CountVectorizer,
    ) = require_dependencies()
    rows = lite.evidence_rows(context)
    if max_docs > 0 and len(rows) > max_docs:
        rows = rows[-max_docs:]
    if len(rows) < 2:
        return {
            "version": "1", "enabled": True, "model": model_name, "documents": len(rows),
            "clusters": [], "crossBookSimilarity": [], "yearlyDrift": [], "sourceSelfAlignment": [],
            "guardrails": ["Too few documents for semantic analysis."],
        }

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        [row["text"] for row in rows],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    k = cluster_count(len(rows), clusters)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)

    return {
        "version": "1",
        "enabled": True,
        "private": True,
        "publicPageSafe": False,
        "model": model_name,
        "documents": len(rows),
        "clusterCount": k,
        "clusters": cluster_labels(rows, labels, k),
        "classicalTopics": classical_topics(
            rows, k, NMF, LDA, TfidfVectorizer, CountVectorizer
        ),
        "crossBookSimilarity": cross_book_neighbors(rows, embeddings, NearestNeighbors),
        "yearlyDrift": yearly_drift(rows, embeddings, np),
        "sourceSelfAlignment": source_self_alignment(rows, embeddings, NearestNeighbors),
        "guardrails": [
            "Embedding similarity means representational proximity, not agreement, causality, truth, or contradiction.",
            "Embedding, NMF and LDA topics are competing candidate views; agreement across methods is stronger evidence than any single model.",
            "Corpus drift describes changes in the reading-text corpus, not a direct measurement of the user's mind.",
            "Source→self alignment is a retrieval candidate, not proof that a source caused a later thought.",
            "This script does not infer sensitive traits, diagnosis, ideology, or personality.",
        ],
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--model", default=os.environ.get("WEREAD_EMBEDDING_MODEL", ""))
    p.add_argument("--clusters", type=int, default=0)
    p.add_argument("--max-docs", type=int, default=5000)
    return p.parse_args()


def main():
    args = parse_args()
    if not args.model.strip():
        raise SystemExit(
            "ERROR: choose a local/model identifier with --model or WEREAD_EMBEDDING_MODEL. "
            "Example: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    if not args.context.exists():
        raise SystemExit(f"ERROR: missing {args.context}")
    context = json.loads(args.context.read_text(encoding="utf-8"))
    result = build(
        context,
        model_name=args.model.strip(),
        clusters=max(0, args.clusters),
        max_docs=max(0, args.max_docs),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"text-mining-semantic: {args.output} | docs={result['documents']} "
        f"clusters={len(result['clusters'])} model={result['model']} private=true"
    )


if __name__ == "__main__":
    main()
