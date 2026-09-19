<div align="center">

# WeRead Intelligence Template

**Build your own local-first, evidence-traceable reading intelligence system from WeRead.**

Public Reading Archive · Private Reading Lab · Search · Recall · Deep Notes · Text Mining · Advisor · Reading Path · Book → Skill

<p>
  <a href="https://github.com/CochraneK/we-read-template/actions/workflows/test.yml"><img alt="tests" src="https://github.com/CochraneK/we-read-template/actions/workflows/test.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-informational">
  <img alt="privacy" src="https://img.shields.io/badge/defaults-privacy--safe-success">
</p>

</div>

---

This is the **sanitized starter distribution** of [CochraneK/we-read](https://github.com/CochraneK/we-read).

It contains the reusable engine, schemas, tests, synthetic fixtures and beginner-friendly bootstrap tooling — **not the upstream owner's personal reading data**.

## Start in 3 minutes

Requirements: Python 3.11+ and a WeRead Agent Gateway key.

```bash
git clone https://github.com/YOUR_NAME/YOUR_REPO.git
cd YOUR_REPO

python scripts/weread.py setup
# edit .env and add WEREAD_API_KEY=wrk-...

python scripts/weread.py doctor
python scripts/weread.py sync
python scripts/weread.py build-public
```

Your public archive is generated at:

```text
site/index.html
```

Your raw account data stays in the external directory configured by `WEREAD_DATA_DIR` (default: `~/.local/share/we-read`) and is not meant to be committed.

## No API key yet?

The template is self-demonstrating:

```bash
python scripts/weread.py sample
```

That builds the full public UI from synthetic fixtures in `examples/sample-data/`.

## Private Reading Lab

After syncing your account:

```bash
python scripts/weread.py build-private --include-private --with-text
```

The Private Lab can contain raw highlights, your own reviews/thoughts, local Search, Recall, Deep Notes, Quote Cards, Alchemy and other evidence-heavy workflows. It stays under your local data directory.

Text Mining Lite is included automatically. Optional semantic analysis:

```bash
pip install -r requirements-text-mining.txt
python scripts/weread.py build-private --include-private --semantic-text --embedding-model "MODEL_OR_LOCAL_PATH"
```

Optional local NLI can be added after semantic candidates:

```bash
python scripts/weread.py build-private \
  --include-private \
  --semantic-text --embedding-model "MODEL_OR_LOCAL_PATH" \
  --nli-text --nli-model "NLI_MODEL_OR_LOCAL_PATH"
```

See [docs/text-mining.md](docs/text-mining.md) for interpretation boundaries.

## Safe public defaults

A fresh template uses:

```text
WEREAD_PAGES_INCLUDE_PRIVATE=0
WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES=0
```

So the public Page:

- excludes books marked private/secret;
- does not publish highlight excerpts;
- never publishes your review/thought bodies through the normal Page builder;
- does not ship your local Search index or Private Reading Lab.

You can deliberately change those switches later. See [docs/publication-policy.md](docs/publication-policy.md).

## GitHub Pages

The included Pages workflow has two modes:

```text
No repository secret
        ↓
synthetic starter data
        ↓
public demo

WEREAD_API_KEY configured as GitHub Actions secret
        ↓
your live WeRead account
        ↓
privacy-safe build
        ↓
validator
        ↓
your GitHub Page
```

For a real account Page:

1. enable **Settings → Pages → Source: GitHub Actions**;
2. add a repository Actions secret named `WEREAD_API_KEY`;
3. add repository variable `ENABLE_GITHUB_PAGES=1`.

Until `ENABLE_GITHUB_PAGES=1` is present, the workflow still builds and validates the archive but deliberately skips deployment.

Optional publication variables:

```text
WEREAD_PAGES_INCLUDE_PRIVATE=0|1
WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES=0|1
```

Both default to `0`.

## What you get

### Public Reading Archive

Deterministic and evidence-bounded views including:

- reading lifetime and rhythm;
- heatmap / weekday / time-of-day patterns;
- reading investment and progress;
- category / author / publisher preferences when available;
- Reading Map / Knowledge Graph / focus shifts;
- Blindspot / Counter Reading;
- bookshelf explorer and local pin queue;
- keyboard navigation, command palette and themes.

### Private Reading Lab

Local evidence workflows including:

- SQLite evidence search;
- Recall / Feynman / spaced review;
- Deep Notes;
- Text Mining Lite: TF-IDF, Source-vs-Self contrastive terms, lexical communities, burst/resurgence, novelty, Source→Self lag;
- optional local semantic layer: embedding clusters + NMF/LDA baselines, cross-book neighbors, corpus drift, and optional NLI relation candidates;
- Quote Cards;
- Alchemy synthesis;
- Narrative Review;
- Advisor;
- Reading Path;
- Book → Skill;
- safe Obsidian sync;
- shelf organization planning.

## Architecture

```text
WeRead Agent Gateway
       ↓
fetch shelf / notes / reading data
       ↓
WEREAD_DATA_DIR  ← stays local
       ↓
normalized facts
       ├── Public Reading Archive
       │      policy → validator → Pages
       └── Private Reading Lab
              raw evidence / search / recall / synthesis
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Commands

| Command | Purpose |
|---|---|
| `python scripts/weread.py setup` | create local config and data directory |
| `python scripts/weread.py doctor` | check environment and data readiness |
| `python scripts/weread.py sync` | fetch shelf, notes, reading stats and enrichment |
| `python scripts/weread.py build-public` | generate the public archive |
| `python scripts/weread.py build-private` | generate the Private Reading Lab + Text Mining Lite |
| `python scripts/weread.py sample` | build with synthetic data |
| `python scripts/weread.py all` | sync and build both surfaces |

## Tests

```bash
python -m unittest discover -s tests -v
```

The template carries the upstream regression suite and runs it on Python 3.11 and 3.13. CI also builds the synthetic starter archive so onboarding cannot silently rot.

## Upstream model

`CochraneK/we-read` remains the canonical feature source. This template syncs reusable implementation while preserving template-owned bootstrap/privacy files.

Check drift:

```bash
python scripts/sync_from_upstream.py --check
```

Maintainers can apply generic upstream changes with:

```bash
python scripts/sync_from_upstream.py --apply
```

See [docs/UPSTREAM.md](docs/UPSTREAM.md).

## What is intentionally not included

- the upstream owner's `data/`;
- personal generated reports;
- personal `site/` artifacts;
- personal quote libraries;
- raw Git history from the personal repository;
- third-party Skill bundles whose redistribution terms are not part of this starter.

## Template repository setting

For the best GitHub UX, enable **Settings → General → Template repository** once. Users will then get GitHub's **Use this template** button instead of needing to fork.

The full one-time repository checklist is in [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md).

## License status

A software license has not yet been selected by the repository owner. Until a license is added, GitHub visibility alone should not be interpreted as a grant of open-source reuse rights.
