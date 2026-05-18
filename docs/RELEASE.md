# Release Checklist

Use this checklist when promoting Carta Arcanum from `main` to `stable`.
`main` is the development branch. `stable` is the production release branch.

## Version Tags

Stable releases use tags like `v0.1.0`.

- The first stable release is `v0.1.0`.
- The first number is for major feature eras.
- The second number is for minor feature updates.
- The third number is for hotfix or bugfix updates.

Create the tag after the release PR is merged into `stable`, so the tag points
at the exact commit deployed by production installs.

## Before Opening The Stable PR

- Confirm the work on `main` is intended for the next stable release.
- Confirm local development-only changes are not part of the release.
- Confirm no generated, secret, or environment files are being committed.
- Confirm the normal CI workflow is green on `main`. Normal CI is intentionally
  lighter than stable verification: quality checks plus one representative
  MySQL-backed full suite.
- Draft release notes from [RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md)
  or confirm the stable PR description lists user-visible changes, upgrade
  notes, and any known risks.
- Confirm the database and `.env` backup plan for the target deployment.

## Stable PR

- Open a pull request from `main`, `release/*`, or `hotfix/*` into `stable`.
- Mark the PR ready for review.
- Confirm the Stable Release Gate workflow passes.
- Confirm the Stable Release Verification workflow passes.
- Confirm the normal CI workflow passes.
- Resolve all review comments and conversations.
- Confirm at least one approval is present.
- Confirm the PR has no unexpected file changes.

The Stable Release Verification workflow can also be run manually from GitHub
Actions when a release candidate needs another heavy verification pass. It is
the home for the slower checks: supported Python/MySQL matrix runs, repeated
focused suites, repeated rules imports, and migration idempotency checks.

## After Merge

- Pull the updated `stable` branch locally.
- Create the release tag, starting with `v0.1.0` for the first stable release.
- Push the tag to GitHub.
- Confirm production installs can see the upgrade on the configured `stable`
  branch.
- Run the in-app upgrade from `Settings -> Application Status`.
- Confirm the status page is green after the upgrade and restart.

Example tag commands:

```bash
git checkout stable
git pull --ff-only origin stable
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

## Rollback Notes

If a deployment must be rolled back, restore the database and environment
backup taken before upgrade, check out the previous stable tag, install
dependencies, run migrations as needed, collect static files, and restart the
app.
