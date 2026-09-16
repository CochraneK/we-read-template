# Public Publication Policy

This file is the canonical policy for the starter template's GitHub Pages output.

## Default

Fresh template repositories default to:

```text
WEREAD_PAGES_INCLUDE_PRIVATE=0
WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES=0
```

That means private/secret shelf books and highlight excerpts are excluded unless the new repository owner explicitly opts in.

## Public Page may contain by default

- aggregate reading time and day counts;
- non-private book metadata;
- progress and note counts;
- deterministic category/author/publisher summaries;
- evidence-bounded structural analyses that do not include raw note bodies.

## Private by default

- books marked private/secret;
- full highlights/marks;
- all user review/thought bodies;
- local search indexes;
- Recall answers/history;
- Private Reading Lab;
- private synthesis and semantic-review artifacts;
- credentials.

## Optional private-book metadata

Setting:

```text
WEREAD_PAGES_INCLUDE_PRIVATE=1
```

allows private-book metadata into the public archive. This is an explicit publication decision by that repository owner.

## Optional public highlight excerpts

Setting:

```text
WEREAD_PAGES_INCLUDE_PUBLIC_QUOTES=1
```

enables the bounded marks-only publication module. This is independent of the private-book switch.

Reviews/thoughts are not authorized by this switch.

## Validation

Every real public build should pass:

```bash
python scripts/validate_pages_output.py --js-out /tmp/we-read-pages-inline.js
node --check /tmp/we-read-pages-inline.js
```

Do not weaken the validator merely to make a publication build pass.
