# Release Notes Convention

When you cut a new tag (`v*`), GitHub Actions publishes a release automatically.

## Rule

Create a release note file at:

* `docs/releases/<tag>.md`

Example:

* tag: `v0.1.2`
* notes file: `docs/releases/v0.1.2.md`

## Behavior

* If `docs/releases/<tag>.md` exists, that file is used as the release body.
* If the file is missing, GitHub auto-generates release notes as a fallback.
