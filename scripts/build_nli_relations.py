#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional local NLI pass over semantic cross-book candidate pairs.

This script consumes the semantic layer's candidate pairs, then applies a local
Hugging Face sequence-classification model whose labels explicitly include
entailment / contradiction / neutral.

NLI here is a text-pair signal only. It does not establish factual truth,
author intent, user agreement, or logical contradiction between whole books.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_SEMANTIC = DATA / "analysis" / "private_lab" / "text_mining_semantic.json"
DEFAULT_OUTPUT = DATA / "analysis" / "private_lab" / "text_mining_nli.json"


def normalize_label(value: str) -> str:
    raw = str(value or "").strip().lower()
    if "contrad" in raw:
        return "contradiction"
    if "entail" in raw:
        return "entailment"
    if "neutral" in raw:
        return "neutral"
    return raw


def label_map(config) -> dict[int, str]:
    raw = getattr(config, "id2label", None) or {}
    mapped = {int(index): normalize_label(label) for index, label in raw.items()}
    values = set(mapped.values())
    required = {"entailment", "contradiction"}
    if not required.issubset(values):
        raise ValueError(
            "NLI model id2label must explicitly expose entailment and contradiction labels; "
            f"got {sorted(values)}"
        )
    return mapped


def require_dependencies():
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(
            "ERROR: NLI dependencies are missing. Install: "
            "pip install -r requirements-text-mining.txt"
        ) from exc
    return torch, AutoModelForSequenceClassification, AutoTokenizer


def classify_pair(premise: str, hypothesis: str, *, tokenizer, model, torch, labels: dict[int, str], max_length: int = 512) -> dict:
    encoded = tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    with torch.no_grad():
        logits = model(**encoded).logits[0]
        probs = torch.softmax(logits, dim=-1).detach().cpu().tolist()
    scores = {labels.get(i, f"label_{i}"): round(float(score), 4) for i, score in enumerate(probs)}
    winner = max(scores, key=scores.get)
    return {"label": winner, "confidence": scores[winner], "scores": scores}


def relation(row: dict, *, tokenizer, model, torch, labels: dict[int, str], threshold: float) -> dict:
    a = row.get("a") or {}
    b = row.get("b") or {}
    a_text = str(a.get("snippet") or "").strip()
    b_text = str(b.get("snippet") or "").strip()
    ab = classify_pair(a_text, b_text, tokenizer=tokenizer, model=model, torch=torch, labels=labels)
    ba = classify_pair(b_text, a_text, tokenizer=tokenizer, model=model, torch=torch, labels=labels)

    contradiction = max(
        ab["scores"].get("contradiction", 0.0),
        ba["scores"].get("contradiction", 0.0),
    )
    entailment = max(
        ab["scores"].get("entailment", 0.0),
        ba["scores"].get("entailment", 0.0),
    )
    if contradiction >= threshold:
        candidate = "contradiction_candidate"
        candidate_confidence = contradiction
    elif entailment >= threshold:
        candidate = "textual_entailment_candidate"
        candidate_confidence = entailment
    else:
        candidate = "unresolved_nli_candidate"
        candidate_confidence = max(contradiction, entailment)

    return {
        "semanticSimilarity": row.get("similarity"),
        "candidate": candidate,
        "candidateConfidence": round(float(candidate_confidence), 4),
        "a": a,
        "b": b,
        "aToB": ab,
        "bToA": ba,
        "status": "local_nli_text_pair_candidate",
    }


def build(semantic: dict, *, model_name: str, limit: int = 80, threshold: float = 0.65) -> dict:
    torch, AutoModel, AutoTokenizer = require_dependencies()
    candidates = list(semantic.get("crossBookSimilarity") or [])[:max(0, limit)]
    if not candidates:
        return {
            "version": "1",
            "enabled": True,
            "private": True,
            "model": model_name,
            "threshold": threshold,
            "pairs": [],
            "coverage": {"semanticCandidates": 0, "classifiedPairs": 0},
            "guardrails": ["No semantic candidate pairs were available for NLI."],
        }

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    labels = label_map(model.config)

    pairs = [
        relation(
            row,
            tokenizer=tokenizer,
            model=model,
            torch=torch,
            labels=labels,
            threshold=threshold,
        )
        for row in candidates
    ]
    counts = {}
    for row in pairs:
        key = row["candidate"]
        counts[key] = counts.get(key, 0) + 1
    pairs.sort(key=lambda x: (-x["candidateConfidence"], -(x.get("semanticSimilarity") or 0.0)))

    return {
        "version": "1",
        "enabled": True,
        "private": True,
        "publicPageSafe": False,
        "model": model_name,
        "threshold": threshold,
        "coverage": {
            "semanticCandidates": len(candidates),
            "classifiedPairs": len(pairs),
            "candidateCounts": counts,
        },
        "pairs": pairs,
        "guardrails": [
            "NLI is applied to short text snippets, not whole books or complete arguments.",
            "Contradiction is a model-generated text-pair candidate, not proof that two authors or books logically contradict each other.",
            "Entailment is textual entailment between snippets, not factual validation or endorsement.",
            "NLI does not infer the user's stance toward either passage.",
            "Inspect the original evidence before interpreting any pair.",
        ],
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semantic", type=Path, default=DEFAULT_SEMANTIC)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--model", default=os.environ.get("WEREAD_NLI_MODEL", ""))
    p.add_argument("--limit", type=int, default=80)
    p.add_argument("--threshold", type=float, default=0.65)
    return p.parse_args()


def main():
    args = parse_args()
    if not args.model.strip():
        raise SystemExit("ERROR: choose --model or WEREAD_NLI_MODEL for a local/model identifier.")
    if not args.semantic.exists():
        raise SystemExit(f"ERROR: missing semantic candidate file: {args.semantic}")
    semantic = json.loads(args.semantic.read_text(encoding="utf-8"))
    result = build(
        semantic,
        model_name=args.model.strip(),
        limit=max(0, args.limit),
        threshold=min(0.99, max(0.5, args.threshold)),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"text-mining-nli: {args.output} | pairs={result['coverage']['classifiedPairs']} "
        f"model={result['model']} private=true"
    )


if __name__ == "__main__":
    main()
