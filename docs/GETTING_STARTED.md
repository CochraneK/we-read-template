# Getting Started

This template is designed so your raw WeRead account data does not need to enter Git.

## 1. Create your repository

Use this repository as your starter, then clone your new repository locally.

## 2. Create local configuration

```bash
python scripts/weread.py setup
```

Open `.env` and add your WeRead Agent Gateway key:

```text
WEREAD_API_KEY=wrk-...
```

By default raw data is stored at:

```text
~/.local/share/we-read
```

Change `WEREAD_DATA_DIR` if you prefer another local directory.

## 3. Check the environment

```bash
python scripts/weread.py doctor
```

## 4. Fetch your data

```bash
python scripts/weread.py sync
```

This fetches the shelf first, then notes/highlights, then reading statistics, progress and book metadata.

## 5. Build your public archive

```bash
python scripts/weread.py build-public
```

The default public scope is conservative:

- secret/private shelf books are excluded;
- public highlight excerpts are disabled;
- reviews/thoughts and full raw evidence stay private.

## 6. Build your Private Reading Lab

```bash
python scripts/weread.py build-private --include-private --with-text
```

The output lives under your local data directory and is gitignored.

## 7. Optional semantic text mining

Text Mining Lite is already included in every Private Lab build.

For local embedding clusters, cross-book semantic neighbors and corpus drift:

```bash
pip install -r requirements-text-mining.txt
python scripts/weread.py build-private \
  --include-private \
  --semantic-text \
  --embedding-model "MODEL_OR_LOCAL_PATH"
```

The semantic layer is private-only. Similarity is not interpreted as agreement, causality, personality or diagnosis.

Optional NLI over cross-book semantic candidates:

```bash
python scripts/weread.py build-private \
  --include-private \
  --semantic-text --embedding-model "MODEL_OR_LOCAL_PATH" \
  --nli-text --nli-model "NLI_MODEL_OR_LOCAL_PATH"
```

NLI outputs are candidate text-pair relations, not whole-book logical judgments.

See [text-mining.md](text-mining.md).

## 8. Try it without an API key

```bash
python scripts/weread.py sample
```

This builds the UI from synthetic fixtures under `examples/sample-data/`.

## 9. Optional GitHub Pages

For automatic Pages deployment:

1. open **Settings → Pages** and choose **GitHub Actions**;
2. add Actions secret `WEREAD_API_KEY`;
3. add repository variable `ENABLE_GITHUB_PAGES=1`;
4. optionally set `WEREAD_PAGES_INCLUDE_PRIVATE` or `WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES` to `1` only after reviewing the publication policy.

Without `ENABLE_GITHUB_PAGES=1`, the workflow still builds and validates but skips deployment.
