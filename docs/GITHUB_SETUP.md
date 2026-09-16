# One-time GitHub Setup

The code is ready without these settings. These are repository-owner switches that GitHub does not expose through the current connector.

## 1. Mark this repository as a template

```text
Settings → General → Template repository
```

This enables the **Use this template** button for downstream users.

## 2. Enable GitHub Pages

```text
Settings → Pages → Source → GitHub Actions
```

Then add repository variable:

```text
ENABLE_GITHUB_PAGES=1
```

The workflow deploys synthetic fixtures until a real `WEREAD_API_KEY` Actions secret is configured.

## 3. Add the WeRead key only if you want live Pages

```text
Settings → Secrets and variables → Actions → Secrets
WEREAD_API_KEY=wrk-...
```

Do not put the key in README, workflow YAML, committed `.env`, issues or logs.

## 4. Choose a software license

No license has been selected automatically because reuse terms are an owner/legal choice.

For a public starter intended for broad reuse, choose the license deliberately and add a root `LICENSE` file.

## 5. Optional discoverability metadata

Suggested repository description:

```text
A privacy-safe starter for building your own WeRead Intelligence archive and local reading lab.
```

Suggested topics:

```text
weread, reading, knowledge-management, local-first, personal-knowledge-management,
reading-analytics, spaced-repetition, knowledge-graph, python, github-pages
```
