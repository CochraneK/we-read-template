# Private Text Mining Lab

The Text Mining Lab deepens `we-read` from reading-behavior analytics into a private reading-corpus analysis system.

It is deliberately split into two layers.

## 1. Lite — zero extra dependencies

Built automatically as part of the Private Reading Lab:

```bash
python scripts/build_private_reading_lab.py --include-private
```

Outputs:

```text
text_mining_context.json
text_mining.html
```

Lite includes:

- mixed Chinese/English lexical units;
- TF-IDF term ranking;
- Source-vs-Self contrastive lexical terms (smoothed log ratio);
- source-highlight vs user-thought corpora;
- lexical diversity;
- document-level co-occurrence and positive-PMI edges;
- lexical topic/community candidates;
- yearly term profiles;
- burst detection;
- concept resurgence candidates;
- TF-IDF lexical novelty / redundancy;
- lexical exposure → expression lag;
- explicit rhetorical-language signals in user-authored reviews.

### Important interpretation limits

`mark` and `review` are never merged into one psychological corpus:

```text
source_text
= saved author/source text
= exposure evidence
≠ user's belief

user_thought
= user-authored review/thought
= expression evidence
≠ unrestricted personality inference
```

Chinese Lite tokenization uses character bi/tri-grams. These are lexical units, not claimed linguistic word segmentation.

“Topic” output in Lite is therefore called **lexical community / topic candidate**, not a semantic topic truth.

## 2. Semantic — optional local embeddings

Install optional dependencies:

```bash
pip install -r requirements-text-mining.txt
```

Choose a SentenceTransformer model or local model path:

```bash
python scripts/build_private_reading_lab.py \
  --include-private \
  --semantic-text \
  --embedding-model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

You can also set:

```bash
export WEREAD_EMBEDDING_MODEL="/path/to/local/model"
```

The semantic layer adds multiple competing topic views so no single model is treated as ground truth:

- embedding clusters;
- NMF classical topic baseline;
- LDA classical topic baseline;
- cross-book nearest-neighbor evidence;
- yearly corpus centroid drift;
- source → self semantic-alignment candidates.

The script performs local embedding/inference. A model identifier may cause the model library to download model weights, but this implementation does not send reading text to a remote inference API.

## 3. What it intentionally does not claim

The following are prohibited interpretations:

- semantic similarity = agreement;
- similarity = causality;
- cluster = objective topic taxonomy;
- source → self alignment = proof of internalization;
- corpus drift = direct measurement of the user's mind;
- rhetorical markers = emotion, diagnosis, personality, ideology, religion, politics, or other sensitive traits.

The right language is:

```text
candidate
signal
lexical overlap
semantic proximity
corpus shift
evidence to inspect
```

not:

```text
you believe
you became
this book changed you
your personality is
```

## 4. Core research objects

The Text Mining Lab treats five layers separately:

```text
Words
  ↓
Lexical communities
  ↓
Semantic clusters (optional)
  ↓
Source / Self evidence relationships
  ↓
Trajectory over time
```

Useful questions include:

- Which concepts repeatedly occur across books?
- Which concepts appear in source highlights before later appearing in my own writing?
- Which lexical units disappear and later resurge?
- Which passages from different books occupy nearby semantic space?
- Is recent reading lexically repetitive or exploratory?
- How does the reading corpus change across years?

Every result should remain traceable to book / evidence IDs rather than becoming an unsupported personality story.

## 5. Privacy

All Text Mining Lab artifacts are private-only.

They may include evidence snippets and semantic relationships derived from raw highlights/reviews. Keep them under the Private Reading Lab directory and never copy them into `site/`.

Public GitHub Pages does not consume these artifacts.
