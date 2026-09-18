# AGENTS.md — WeRead Intelligence Template

## Goal

Keep this repository a safe, reproducible starter for building a personal WeRead Intelligence archive.

## Non-negotiable boundaries

1. Never commit a user's raw WeRead exports, API key, reviews/thoughts, local search index or Private Reading Lab.
2. New-user defaults must remain privacy-safe: private books excluded and public highlight publication disabled.
3. Never hard-code owner-specific book counts, dates, titles or reading claims into generic UI.
4. Deterministic facts belong in shared builders/metrics; renderers should not invent values.
5. Public artifacts must pass `scripts/validate_pages_output.py`.
6. Remote WeRead writes remain plan-first and explicit-confirmation only.
7. Do not import third-party Skill bundles into the template without checking redistribution terms.

## Upstream model

`CochraneK/we-read` is the canonical feature upstream.

Generic implementation under `scripts/`, `schemas/` and `tests/` may be synced, but template-owned onboarding/privacy/bootstrap files are preserved according to `template-manifest.json`.

## Starter UX

The supported path is:

```text
python scripts/weread.py setup
python scripts/weread.py doctor
python scripts/weread.py sync
python scripts/weread.py build-public
python scripts/weread.py build-private --include-private --with-text
```

A no-key demo must continue to work through:

```bash
python scripts/weread.py sample
```


## Text Mining

The Private Lab always builds zero-dependency Text Mining Lite. Keep `source_text` and `user_thought` separate.

Optional semantic analysis is local-only and opt-in through `--semantic-text --embedding-model ...`.

Never turn lexical or embedding similarity into claims of agreement, causality, personality, diagnosis, ideology or other sensitive traits. Treat clusters, drift and Source→Self links as evidence candidates. See `docs/text-mining.md`.
