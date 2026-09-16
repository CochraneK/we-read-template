#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose the Private Reading Lab base renderer with experience modules."""
from __future__ import annotations

from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import private_lab as base
import private_lab_recall_ui
import private_lab_action_ui


def render_final(data: dict, *, assets: dict[str, bool] | None = None) -> str:
    page = base.render(data)
    page = private_lab_recall_ui.augment(page)
    page = private_lab_action_ui.augment(page, assets or {})
    return page


def parse_args():
    parser = argparse.ArgumentParser(description="Render composed local-only WeRead Private Reading Lab.")
    parser.add_argument("--context", type=Path, default=base.LAB / "visualization_context.json")
    parser.add_argument("--deep", type=Path, default=base.LAB / "deep_notes_context.json")
    parser.add_argument("--recall", type=Path, default=base.LAB / "recall_queue.json")
    parser.add_argument("--advisor", type=Path, default=base.LAB / "advisor_context.json")
    parser.add_argument("--blindspot", type=Path, default=base.LAB / "blindspot_context.json")
    parser.add_argument("--review", type=Path, default=base.LAB / "narrative_review_context.json")
    parser.add_argument("--quote-cards", type=Path, default=base.LAB / "quote_cards.html")
    parser.add_argument("--alchemy-topic-report", type=Path, default=base.LAB / "alchemy_topic.html")
    parser.add_argument("--alchemy-book-report", type=Path, default=base.LAB / "alchemy_book.html")
    parser.add_argument("--advisor-report", type=Path, default=base.LAB / "advisor.html")
    parser.add_argument("--advisor-semantic-editor", type=Path, default=base.LAB / "advisor_semantic_editor.html")
    parser.add_argument("--advisor-semantic-result", type=Path, default=base.LAB / "advisor_semantic.html")
    parser.add_argument("--path-discovery-report", type=Path, default=base.LAB / "reading_path_discovery.html")
    parser.add_argument("--path-semantic-editor", type=Path, default=base.LAB / "reading_path_semantic_editor.html")
    parser.add_argument("--path-semantic-result", type=Path, default=base.LAB / "reading_path_semantic.html")
    parser.add_argument("--path-plan-report", type=Path, default=base.LAB / "reading_path.html")
    parser.add_argument("--review-report", type=Path, default=base.LAB / "narrative_review.html")
    parser.add_argument("--output", type=Path, default=base.LAB / "index.html")
    return parser.parse_args()


def _asset_exists(explicit: Path, out_dir: Path, filename: str) -> bool:
    """Prefer a sibling artifact beside the requested output, then explicit path."""
    sibling = out_dir / filename
    return sibling.exists() or explicit.exists()


def main():
    args = parse_args()
    context = base.read_json(args.context, {})
    if not context:
        raise SystemExit(f"ERROR: missing/invalid context: {args.context}")
    out_dir = args.output.parent
    quote_cards_exists = (out_dir / "quote_cards.html").exists() or args.quote_cards.exists()
    data = base.payload(
        context,
        base.read_json(args.deep, {}),
        base.read_json(args.recall, {}),
        base.read_json(args.advisor, {}),
        base.read_json(args.blindspot, {}),
        base.read_json(args.review, {}),
        quote_cards_exists=quote_cards_exists,
    )
    assets = {
        "alchemyTopic": _asset_exists(args.alchemy_topic_report, out_dir, "alchemy_topic.html"),
        "alchemyBook": _asset_exists(args.alchemy_book_report, out_dir, "alchemy_book.html"),
        "advisor": _asset_exists(args.advisor_report, out_dir, "advisor.html"),
        "advisorSemanticEditor": _asset_exists(args.advisor_semantic_editor, out_dir, "advisor_semantic_editor.html"),
        "advisorSemanticResult": _asset_exists(args.advisor_semantic_result, out_dir, "advisor_semantic.html"),
        "pathDiscovery": _asset_exists(args.path_discovery_report, out_dir, "reading_path_discovery.html"),
        "pathSemanticEditor": _asset_exists(args.path_semantic_editor, out_dir, "reading_path_semantic_editor.html"),
        "pathSemanticResult": _asset_exists(args.path_semantic_result, out_dir, "reading_path_semantic.html"),
        "pathPlan": _asset_exists(args.path_plan_report, out_dir, "reading_path.html"),
        "review": _asset_exists(args.review_report, out_dir, "narrative_review.html"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_final(data, assets=assets), encoding="utf-8")
    print(
        f"private-lab-final: {args.output} | books={len(data['books'])} "
        f"evidence={len(data['evidence'])} recall={len((data['recall'] or {}).get('items') or [])} "
        f"actions={sum(1 for x in assets.values() if x)} private=true"
    )


if __name__ == "__main__":
    main()
