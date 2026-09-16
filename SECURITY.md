# Security & Privacy

This template processes personal reading history. Treat raw shelf data, highlights, reviews/thoughts, local search indexes and Private Reading Lab artifacts as sensitive.

## Safe defaults

- `.env` is ignored.
- `data/` and the default external data directory are not committed.
- Public Pages exclude private shelf books by default.
- Public highlight excerpts are disabled by default.
- Reviews/thoughts and full raw evidence are not public Page inputs.

## If a credential leaks

Revoke or rotate the credential first. Deleting a file or adding it to `.gitignore` does not invalidate an exposed API key or erase Git history.

## Reports

Do not paste private reading content into a public issue. Use a private security channel when the repository owner provides one.
