## 1. PR title check + auto-labeling

- [x] 1.1 Add `.github/workflows/conventional-commits.yml`: validate PR title against conventional-commit regex on `opened`/`reopened`/`edited`/`synchronize`, failing the check on mismatch
- [x] 1.2 In the same workflow, auto-label the PR by conventional-commit type using `action-runner/conventional-labeler` (pinned SHA)

## 2. Draft release automation

- [x] 2.1 Add `.github/config/draft-release-config.yml` with the categories (Features/Bug Fixes/Maintenance/Documentation) and version-resolver precedence (major/minor/patch, default patch)
- [x] 2.2 Add `.github/workflows/draft-release.yml`: run `release-drafter/release-drafter` (pinned SHA) on push to `main`, pointing at the config from 2.1

## 3. Dockerfile version metadata

- [x] 3.1 Add `ARG APP_VERSION=dev` to `Dockerfile`, set `LABEL org.opencontainers.image.version=$APP_VERSION` and `ENV APP_VERSION=$APP_VERSION`

## 4. Docker build & publish

- [x] 4.1 Add `.github/workflows/docker.yml`: trigger on push to `main` and on `v*` tags
- [x] 4.2 Resolve `APP_VERSION` via `git describe --tags --always` and compute the tag set (`:latest` always; `:vX.Y.Z` added when triggered by a version tag)
- [x] 4.3 Log in to GHCR, set up Buildx, and build/push the image to `ghcr.io/jwndlng/benny-watchman` with the resolved tags and `APP_VERSION` build-arg, using GHA layer caching

## 5. Release attestation

- [x] 5.1 Add `.github/workflows/release.yml`: trigger on `release: published`
- [x] 5.2 Log in to GHCR and poll (`docker pull`, up to 18×10s) for the image tag matching the release until it becomes available, failing the workflow on timeout
- [x] 5.3 Extract the image digest and run `actions/attest-build-provenance` against `ghcr.io/jwndlng/benny-watchman`
- [x] 5.4 Append a "Docker Image" section with `docker pull` commands (version tag + `:latest`) to the release notes via `gh release edit`

## 6. Verification

- [ ] 6.1 Open a test PR with a non-conventional title and confirm the title check fails
- [ ] 6.2 Open a test PR with a conventional title (e.g., `chore: ...`) and confirm it's auto-labeled and the check passes
- [ ] 6.3 Merge to `main` and confirm a draft release is created/updated with correctly categorized changelog entries
- [ ] 6.4 Confirm `ghcr.io/jwndlng/benny-watchman:latest` is built and pushed on the `main` push
- [ ] 6.5 Publish the draft release and confirm: version-tagged image is pushed, provenance attestation succeeds, and release notes get the `docker pull` section
- [ ] 6.6 Manually verify (and if needed, flip) GHCR package visibility for `benny-watchman` — first-time setting, not automatable
