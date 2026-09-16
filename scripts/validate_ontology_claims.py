#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the static Ontology Lite + Claim Graph Pages contract."""
from __future__ import annotations

from pathlib import Path
import json

SITE = Path("site")
FORBIDDEN_RAW_KEYS = {"text", "content", "markText", "reviewText", "reviews"}
VALID_STATUS = {"supported", "partial", "unresolved"}


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def validate(site: Path = SITE) -> dict:
    report = json.loads((site / "report-data.json").read_text(encoding="utf-8"))
    html = (site / "index.html").read_text(encoding="utf-8")
    payload = report.get("ontologyClaims") or {}
    contract = payload.get("contract") or {}
    if not payload:
        raise ValueError("missing report.ontologyClaims")
    if contract.get("derivedReadOnly") is not True:
        raise ValueError("ontology must be a read-only derived layer")
    if contract.get("deterministicClaims") is not True:
        raise ValueError("claims must remain deterministic")
    if contract.get("rawTextPublished") is not False:
        raise ValueError("ontology/claims must not publish raw bodies")
    if contract.get("runtimeApiRequired") is not False:
        raise ValueError("GitHub Pages implementation must not require a runtime API")
    for marker in ('id="ontology-lite"', 'id="claim-graph"', 'id="ontologyGraph"', 'id="claimDetail"'):
        if marker not in html:
            raise ValueError(f"missing ontology/claim marker: {marker}")
    if "fetch(" in html or "XMLHttpRequest" in html or "WebSocket(" in html:
        raise ValueError("final Page must remain network-free at runtime")
    keys = set(walk_keys(payload))
    leaked = sorted(keys & FORBIDDEN_RAW_KEYS)
    if leaked:
        raise ValueError("raw-body-shaped fields leaked into ontology contract: " + ", ".join(leaked))

    ontology = payload.get("ontology") or {}
    entities = ontology.get("entityCounts") or {}
    relations = ontology.get("relationCounts") or {}
    for key in ("Book", "Author", "Category", "Chapter", "Evidence"):
        if int(entities.get(key) or 0) < 0:
            raise ValueError(f"invalid entity count: {key}")
    for key in ("writtenBy", "belongsTo", "contains", "evidenceFromBook", "evidenceFromChapter"):
        if int(relations.get(key) or 0) < 0:
            raise ValueError(f"invalid relation count: {key}")
    if int(entities.get("Evidence") or 0) != int(relations.get("evidenceFromBook") or 0):
        raise ValueError("every evidence item must resolve to a book relation")

    claims = ((payload.get("claimGraph") or {}).get("claims") or [])
    if not claims:
        raise ValueError("claim graph must contain at least one deterministic claim")
    ids = set()
    for claim in claims:
        cid = str(claim.get("id") or "")
        if not cid or cid in ids:
            raise ValueError("claim ids must be non-empty and unique")
        ids.add(cid)
        if claim.get("status") not in VALID_STATUS:
            raise ValueError(f"invalid claim status: {claim.get('status')}")
        if not str(claim.get("statement") or "").strip():
            raise ValueError("claim statement is required")
        if not isinstance(claim.get("support"), list) or not claim.get("support"):
            raise ValueError("every claim requires support evidence")
        if not isinstance(claim.get("counter"), list):
            raise ValueError("every claim requires a counter/qualifier list")
        if not isinstance(claim.get("dependencies"), list):
            raise ValueError("every claim requires dependency metadata")

    return {
        "books": int(entities.get("Book") or 0),
        "chapters": int(entities.get("Chapter") or 0),
        "evidence": int(entities.get("Evidence") or 0),
        "claims": len(claims),
        "statuses": (payload.get("claimGraph") or {}).get("statusCounts") or {},
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
