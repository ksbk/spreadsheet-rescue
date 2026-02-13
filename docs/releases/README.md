# Release Notes Convention

When you cut a new tag (`v*`), GitHub Actions publishes a release automatically.

## Rule

Create a release note file at:

* `docs/releases/<tag>.md`

Example:

* tag: `v0.1.2`
* notes file: `docs/releases/v0.1.2.md`

## Safe release flow

Use the helper script:

```bash
./scripts/release.sh v0.1.2
```

What it does:
* validates a clean working tree
* checks local/remote tag collisions
* creates `docs/releases/<tag>.md` from `docs/releases/TEMPLATE.md`
* commits release notes (`release: <tag>`)
* creates annotated tag
* pushes branch + tag

Preview only:

```bash
./scripts/release.sh v0.1.2 --dry-run
```

## Behavior

* If `docs/releases/<tag>.md` exists, that file is used as the release body.
* If the file is missing, GitHub auto-generates release notes as a fallback.
