# Release Notes Convention

When you cut a new tag (`v*`), GitHub Actions can publish a release automatically.

## Rule

Create a release note file at:

* `docs/releases/<tag>.md`

Example:

* tag: `v0.1.4`
* notes file: `docs/releases/v0.1.4.md`

## Safe release flow

Use the helper script:

```bash
./scripts/release.sh
```

What it does:
* runs quality checks (`ruff`, `mypy`, `pytest`)
* runs `scripts/smoke_install.sh`
* runs `make customer-pack`
* validates a clean working tree
* checks local/remote tag collisions
* bumps package version to `0.1.4`
* commits release changes (`release: v0.1.4`)
* creates annotated tag `v0.1.4`

Preview only:

```bash
./scripts/release.sh --dry-run
```

## GitHub release helper

Use the helper script to create/update the release and upload the customer pack zip:

```bash
python scripts/gh_release.py --tag v0.1.4 --build-pack
```

It uses:
* release notes: `docs/releases/v0.1.4.md`
* asset: `dist/customer-demo-pack.zip`
