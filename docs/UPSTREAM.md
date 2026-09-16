# Upstream Policy

Canonical upstream: `CochraneK/we-read`.

This repository intentionally does **not** mirror the upstream repository wholesale.

## Synced surface

- reusable `scripts/` implementation;
- `schemas/`;
- regression `tests/`.

## Template-owned surface

- README;
- starter CLI and shelf bootstrap;
- `.env.example`;
- synthetic fixtures;
- GitHub Actions for template users;
- onboarding/security/publication docs.

## Never synced

- `data/`;
- generated `site/`;
- reports and quote-library artifacts;
- owner-specific reading records;
- Git history containing personal data;
- third-party Skill packages whose redistribution terms are not part of this template.

Run `python scripts/sync_from_upstream.py --check` to inspect drift. Use `--apply` only as a maintainer action.
