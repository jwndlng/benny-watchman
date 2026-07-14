## Why

Benny has no release process today: merges to `main` produce no versioned artifact, and there's no repeatable way to build and publish a deployable image. We need a lightweight, automated pipeline — modeled on the proven process from `jwndlng/ai-app-radar` — so every merge is labeled, changelogs write themselves, and a tagged Docker image is the deployable unit.

## What Changes

- Add a **conventional-commit PR title check** that gates merges and auto-labels PRs by type (`feat`, `fix`, `chore`, etc.)
- Add a **draft release** workflow (Release Drafter) that maintains an always-up-to-date draft release on every push to `main`, auto-resolving the next semver from PR labels and grouping the changelog by category
- Add a **Docker publish** workflow that builds and pushes the image to GHCR (`ghcr.io/jwndlng/benny-watchman`) on push to `main` (`:latest`) and on version tags (`:vX.Y.Z`), passing the resolved version as a build arg
- Add a **release attestation** workflow that runs when a maintainer publishes the draft release: waits for the matching image tag, attests build provenance, and appends `docker pull` instructions to the release notes
- Update the existing `Dockerfile` to accept an `APP_VERSION` build arg and expose it as an OCI label/env var (currently hardcoded, no version metadata)

## Capabilities

### New Capabilities
- `release-pipeline`: CI/CD workflows that label PRs, draft versioned releases from merged PR history, and build/publish/attest a Docker image per release

### Modified Capabilities
(none — no existing runtime behavior changes; this only adds CI/CD and a build-arg to the Dockerfile)

## Impact

- **Affected code**: `Dockerfile` (add `APP_VERSION` build arg + label), new files under `.github/workflows/` and `.github/config/`
- **Dependencies**: GitHub Actions (`release-drafter/release-drafter`, `docker/build-push-action`, `docker/login-action`, `actions/attest-build-provenance`), GHCR as the image registry
- **No application code, API, or runtime behavior changes** — this is purely CI/CD and packaging
