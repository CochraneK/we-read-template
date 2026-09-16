# Template Architecture

```text
WeRead Agent Gateway
        |
        v
fetch_shelf.py + export_notes.py + fetch_enrich.py
        |
        v
WEREAD_DATA_DIR (local / gitignored)
        |
        +--> Public Archive
        |      deterministic facts
        |      publication policy
        |      validator
        |      GitHub Pages
        |
        +--> Private Reading Lab
               raw evidence
               Search / Recall / Deep Notes
               Alchemy / Advisor / Path / Review
```

## One upstream, two surfaces

The canonical feature implementation lives in `CochraneK/we-read`. This template is a sanitized distribution surface.

Template-specific files own:

- starter README and onboarding;
- `.env.example`;
- `fetch_shelf.py` and the starter CLI;
- synthetic fixtures;
- safe-default Pages workflow;
- upstream sync policy.

Raw personal data and owner-specific generated artifacts are never part of the template sync allowlist.
