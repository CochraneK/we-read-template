#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the local/private WeRead Reading Lab.

This is the integration entry point for the user's original highlight-card work
and the newer evidence-first WeRead Intelligence modules. It intentionally writes
outside `site/` so raw evidence can never be published by the Pages workflow.

Important: the core lab already contains private raw evidence because Search,
Recall and Deep Notes operate on mark/review text. `--with-text` means “also
build browsable quote-card and optional Alchemy assets”, not “turn privacy on”.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()
DEFAULT_OUT = DATA / "analysis" / "private_lab"
REVIEW_PLATFORM_CODES = {
    "朋友圈": "moments",
    "公众号": "wechat",
    "小红书": "xiaohongshu",
    "视频脚本": "video",
    "个人日记": "journal",
}


def run_step(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def filtered_notes(raw_notes: list, context: dict) -> list[dict]:
    allowed = {str(b.get("bookId") or "") for b in (context.get("books") or []) if isinstance(b, dict)}
    return [row for row in raw_notes if isinstance(row, dict) and str(row.get("bookId") or "") in allowed]


def build_steps(out_dir: Path, *, include_private: bool, with_text: bool, topic: str, book_id: str,
                review_start: str, review_end: str, review_platform: str) -> list[tuple[str, list[str]]]:
    context = out_dir / "visualization_context.json"
    steps: list[tuple[str, list[str]]] = []
    context_cmd = ["scripts/build_visualization_context.py", "--output", str(context)]
    if include_private:
        context_cmd.append("--include-private")
    steps.append(("统一事实层", context_cmd))
    steps.extend([
        ("Advisor Context", ["scripts/build_advisor_context.py", "--context", str(context), "--output", str(out_dir / "advisor_context.json")]),
        ("Blindspot Context", ["scripts/build_blindspot_context.py", "--context", str(context), "--output", str(out_dir / "blindspot_context.json")]),
        ("Recall Queue", ["scripts/build_recall_queue.py", "--context", str(context), "--output", str(out_dir / "recall_queue.json"), "--min-age-days", "30", "--limit", "40", "--max-per-book", "2"]),
        ("Search Index", ["scripts/build_search_index.py", "--context", str(context), "--db", str(out_dir / "search.sqlite"), "--rebuild"]),
        ("Deep Notes Context", ["scripts/build_deep_notes_context.py", "--context", str(context), "--output", str(out_dir / "deep_notes_context.json")]),
    ])
    review_platform_code = REVIEW_PLATFORM_CODES.get(review_platform, review_platform)
    review_context = out_dir / "narrative_review_context.json"
    review = [
        "scripts/build_narrative_review_context.py", "--context", str(context),
        "--readdata", str(DATA / "weread_readdata.json"), "--start", review_start,
        "--end", review_end, "--output", str(review_context),
    ]
    if review_platform_code:
        review.extend(["--platform", review_platform_code])
    steps.append(("Narrative Review Context", review))
    if review_platform_code:
        review_draft = out_dir / "narrative_review_draft.json"
        steps.extend([
            ("Narrative Review Draft", ["scripts/build_narrative_review_draft.py", "--input", str(review_context), "--platform", review_platform_code, "--output", str(review_draft), "--markdown", str(out_dir / "narrative_review.md")]),
            ("Narrative Review Report", ["scripts/renderers/narrative_review_private.py", "--input", str(review_draft), "--output", str(out_dir / "narrative_review.html")]),
        ])

    if with_text and topic:
        ctx = out_dir / "alchemy_topic_context.json"
        syn = out_dir / "alchemy_topic_synthesis.json"
        steps.extend([
            ("Alchemy Topic Context", ["scripts/build_alchemy_context.py", "--context", str(context), "--topic", topic, "--output", str(ctx)]),
            ("Alchemy Topic Synthesis", ["scripts/build_alchemy_synthesis.py", "--input", str(ctx), "--output", str(syn)]),
            ("Alchemy Topic Report", ["scripts/renderers/alchemy_private.py", "--input", str(syn), "--output", str(out_dir / "alchemy_topic.html")]),
        ])
    if with_text and book_id:
        ctx = out_dir / "alchemy_book_context.json"
        syn = out_dir / "alchemy_book_synthesis.json"
        steps.extend([
            ("Alchemy Book Context", ["scripts/build_alchemy_context.py", "--context", str(context), "--book-id", book_id, "--output", str(ctx)]),
            ("Alchemy Book Synthesis", ["scripts/build_alchemy_synthesis.py", "--input", str(ctx), "--output", str(syn)]),
            ("Alchemy Book Report", ["scripts/renderers/alchemy_private.py", "--input", str(syn), "--output", str(out_dir / "alchemy_book.html")]),
        ])
    return steps


def build_action_steps(out_dir: Path, *, advisor_query: str = "", path_topic: str = "",
                       path_candidates: Path | None = None, path_confirmed_level: str = "",
                       advisor_semantic_annotations: Path | None = None,
                       path_semantic_annotations: Path | None = None) -> list[tuple[str, list[str]]]:
    """Build optional live-catalog and semantic-review actions."""
    context = out_dir / "visualization_context.json"
    advisor = out_dir / "advisor_context.json"
    steps: list[tuple[str, list[str]]] = []
    if advisor_query:
        verified = out_dir / "advisor_candidates.json"
        shortlist = out_dir / "advisor_shortlist.json"
        brief = out_dir / "advisor_semantic_brief.json"
        steps.extend([
            ("Advisor Live Candidates", ["scripts/verify_weread_candidates.py", "--context", str(context), "--query", advisor_query, "--output", str(verified)]),
            ("Advisor Shortlist", ["scripts/build_advisor_shortlist.py", "--advisor", str(advisor), "--verified", str(verified), "--topic", advisor_query, "--output", str(shortlist)]),
            ("Advisor Report", ["scripts/renderers/advisor_private.py", "--input", str(shortlist), "--output", str(out_dir / "advisor.html")]),
            ("Advisor Semantic Brief", ["scripts/build_candidate_semantic_brief.py", "--input", str(shortlist), "--mode", "advisor", "--topic", advisor_query, "--output", str(brief)]),
            ("Advisor Semantic Editor", ["scripts/renderers/semantic_brief_private.py", "--input", str(brief), "--output", str(out_dir / "advisor_semantic_editor.html")]),
        ])
        if advisor_semantic_annotations is not None:
            applied = out_dir / "advisor_semantic_applied.json"
            steps.extend([
                ("Advisor Semantic Gate", ["scripts/apply_candidate_semantics.py", "--input", str(advisor_semantic_annotations), "--output", str(applied)]),
                ("Advisor Final Semantic Report", ["scripts/renderers/semantic_result_private.py", "--input", str(applied), "--output", str(out_dir / "advisor_semantic.html")]),
            ])
    if path_topic:
        path_context = out_dir / "reading_path_context.json"
        discovery = out_dir / "reading_path_discovery.json"
        path_brief = out_dir / "reading_path_semantic_brief.json"
        steps.extend([
            ("Reading Path Context", ["scripts/build_reading_path_context.py", "--advisor", str(advisor), "--topic", path_topic, "--output", str(path_context)]),
            ("Reading Path Live Discovery", ["scripts/discover_reading_path_candidates.py", "--context", str(context), "--topic", path_topic, "--output", str(discovery)]),
            ("Reading Path Discovery Report", ["scripts/renderers/reading_path_private.py", "--input", str(discovery), "--output", str(out_dir / "reading_path_discovery.html")]),
            ("Reading Path Semantic Brief", ["scripts/build_candidate_semantic_brief.py", "--input", str(discovery), "--mode", "path", "--topic", path_topic, "--output", str(path_brief)]),
            ("Reading Path Semantic Editor", ["scripts/renderers/semantic_brief_private.py", "--input", str(path_brief), "--output", str(out_dir / "reading_path_semantic_editor.html")]),
        ])
        semantic_source = path_candidates
        if path_semantic_annotations is not None:
            semantic_applied = out_dir / "reading_path_semantic_applied.json"
            steps.extend([
                ("Reading Path Semantic Gate", ["scripts/apply_candidate_semantics.py", "--input", str(path_semantic_annotations), "--output", str(semantic_applied)]),
                ("Reading Path Semantic Result", ["scripts/renderers/semantic_result_private.py", "--input", str(semantic_applied), "--output", str(out_dir / "reading_path_semantic.html")]),
            ])
            semantic_source = semantic_applied
        if semantic_source is not None:
            if not path_confirmed_level:
                raise ValueError("path_confirmed_level is required when finalizing a path")
            verified = out_dir / "reading_path_candidates_verified.json"
            enriched = out_dir / "reading_path_candidates_enriched.json"
            plan = out_dir / "reading_path_plan.json"
            steps.extend([
                ("Reading Path Candidate Verification", ["scripts/verify_weread_candidates.py", "--context", str(context), "--candidates", str(semantic_source), "--output", str(verified)]),
                ("Reading Path Candidate Info", ["scripts/enrich_weread_candidate_info.py", "--input", str(verified), "--output", str(enriched)]),
                ("Reading Path Final Plan", ["scripts/build_reading_path_plan.py", "--path-context", str(path_context), "--candidates", str(enriched), "--confirmed-level", path_confirmed_level, "--output", str(plan)]),
                ("Reading Path Final Report", ["scripts/renderers/reading_path_private.py", "--input", str(plan), "--output", str(out_dir / "reading_path.html")]),
            ])
    return steps


def write_private_text_assets(out_dir: Path, context_path: Path) -> None:
    raw_path = DATA / "weread_notes_export.json"
    if not raw_path.exists():
        raise SystemExit(f"ERROR: missing {raw_path}; run scripts/export_notes.py first")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    raw_notes = json.loads(raw_path.read_text(encoding="utf-8"))
    notes = filtered_notes(raw_notes if isinstance(raw_notes, list) else [], context)
    filtered = out_dir / "filtered_notes_private.json"
    filtered.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    quote_dir = out_dir / "quotes"
    run_step(["scripts/build_quote_lib.py", "--input", str(filtered), "--output-dir", str(quote_dir)])
    run_step(["scripts/renderers/quote_cards.py", "--input", str(quote_dir / "金句库.json"), "--output", str(out_dir / "quote_cards.html")])


def render_dashboard(out_dir: Path) -> None:
    output = out_dir / "index.html"
    run_step([
        "scripts/renderers/private_lab_final.py",
        "--context", str(out_dir / "visualization_context.json"),
        "--deep", str(out_dir / "deep_notes_context.json"),
        "--recall", str(out_dir / "recall_queue.json"),
        "--advisor", str(out_dir / "advisor_context.json"),
        "--blindspot", str(out_dir / "blindspot_context.json"),
        "--review", str(out_dir / "narrative_review_context.json"),
        "--quote-cards", str(out_dir / "quote_cards.html"),
        "--output", str(output),
    ])
    run_step(["scripts/validate_private_lab_output.py", "--html", str(output)])


def parse_args():
    today = date.today()
    parser = argparse.ArgumentParser(description="Build the local/private WeRead Reading Lab.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-private", action="store_true", help="Include secret=1 books in the private lab context. Off by default.")
    parser.add_argument("--with-text", action="store_true", help="Also build quote cards and optional Alchemy reports. Core lab already contains private evidence text.")
    parser.add_argument("--topic", default="", help="Optional Alchemy topic; requires --with-text.")
    parser.add_argument("--book-id", default="", help="Optional single-book Alchemy context; requires --with-text.")
    parser.add_argument("--advisor-query", default="", help="Optional live Advisor catalog query. Requires WEREAD_API_KEY.")
    parser.add_argument("--advisor-semantic-annotations", type=Path, default=None, help="Filled Advisor semantic brief exported by the local editor.")
    parser.add_argument("--path-topic", default="", help="Optional Reading Path topic. Live discovery requires WEREAD_API_KEY.")
    parser.add_argument("--path-candidates", type=Path, default=None, help="Legacy stage-labelled candidate JSON; semantic annotations are preferred.")
    parser.add_argument("--path-semantic-annotations", type=Path, default=None, help="Filled Reading Path semantic brief exported by the local editor.")
    parser.add_argument("--path-confirmed-level", choices=["", "zero", "beginner", "intermediate", "advanced"], default="")
    parser.add_argument("--review-start", default=f"{today.year}-01-01")
    parser.add_argument("--review-end", default=today.isoformat())
    parser.add_argument("--review-platform", choices=["", "朋友圈", "公众号", "小红书", "视频脚本", "个人日记"], default="")
    return parser.parse_args()


def main():
    args = parse_args()
    if (args.topic.strip() or args.book_id.strip()) and not args.with_text:
        raise SystemExit("ERROR: --topic/--book-id require --with-text because Alchemy contains raw evidence")
    if (args.path_candidates or args.path_semantic_annotations) and not args.path_topic.strip():
        raise SystemExit("ERROR: path candidates/semantic annotations require --path-topic")
    if (args.path_candidates or args.path_semantic_annotations) and not args.path_confirmed_level:
        raise SystemExit("ERROR: final Reading Path requires --path-confirmed-level")
    if args.advisor_semantic_annotations and not args.advisor_query.strip():
        raise SystemExit("ERROR: --advisor-semantic-annotations requires --advisor-query")

    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, command in build_steps(
        out_dir, include_private=args.include_private, with_text=args.with_text,
        topic=args.topic.strip(), book_id=args.book_id.strip(), review_start=args.review_start,
        review_end=args.review_end, review_platform=args.review_platform,
    ):
        print(f"==> {label}")
        run_step(command)

    for label, command in build_action_steps(
        out_dir,
        advisor_query=args.advisor_query.strip(),
        path_topic=args.path_topic.strip(),
        path_candidates=args.path_candidates.expanduser().resolve() if args.path_candidates else None,
        path_confirmed_level=args.path_confirmed_level,
        advisor_semantic_annotations=args.advisor_semantic_annotations.expanduser().resolve() if args.advisor_semantic_annotations else None,
        path_semantic_annotations=args.path_semantic_annotations.expanduser().resolve() if args.path_semantic_annotations else None,
    ):
        print(f"==> {label}")
        run_step(command)

    context_path = out_dir / "visualization_context.json"
    if args.with_text:
        print("==> Quote Library + Cards")
        write_private_text_assets(out_dir, context_path)

    print("==> Interactive Private Lab + validation")
    render_dashboard(out_dir)

    manifest = {
        "version": 7,
        "private": True,
        "publicPageSafe": False,
        "containsRawEvidence": True,
        "outputDir": str(out_dir),
        "includePrivateBooks": bool(args.include_private),
        "includesQuoteCards": bool(args.with_text),
        "includesBrowserLocalRecallHistory": True,
        "includesRecallAnswerHistory": True,
        "includesAlchemySynthesisReport": bool(args.with_text and (args.topic.strip() or args.book_id.strip())),
        "includesNarrativeReviewDraft": bool(args.review_platform),
        "includesAdvisorLiveCatalog": bool(args.advisor_query.strip()),
        "includesAdvisorSemanticReview": bool(args.advisor_query.strip()),
        "includesAdvisorFinalSemanticResult": bool(args.advisor_semantic_annotations),
        "includesReadingPathDiscovery": bool(args.path_topic.strip()),
        "includesReadingPathSemanticReview": bool(args.path_topic.strip()),
        "includesReadingPathFinalPlan": bool(args.path_candidates or args.path_semantic_annotations),
        "artifactValidation": True,
        "topicAlchemy": args.topic.strip() or None,
        "bookAlchemy": args.book_id.strip() or None,
        "advisorQuery": args.advisor_query.strip() or None,
        "pathTopic": args.path_topic.strip() or None,
        "reviewPlatform": REVIEW_PLATFORM_CODES.get(args.review_platform, args.review_platform) or None,
        "entry": "index.html",
        "privacyNote": "Search/Recall/context artifacts contain mark/review text even without --with-text; keep the entire directory private.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"private-reading-lab: {out_dir / 'index.html'} | quote_cards={args.with_text} "
        f"review={bool(args.review_platform)} advisor_live={bool(args.advisor_query.strip())} path={bool(args.path_topic.strip())} "
        f"validated=true raw_evidence=true recall_history=browser-local public_page_safe=false"
    )


if __name__ == "__main__":
    main()
