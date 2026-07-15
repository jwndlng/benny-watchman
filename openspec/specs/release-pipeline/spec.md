# release-pipeline Specification

## Purpose
TBD - created by syncing change release-process. Update Purpose after archive.
## Requirements
### Requirement: PR titles are validated against conventional-commit format
Every pull request SHALL have its title checked against the conventional-commit pattern (`type(scope)!: description`, where `type` is one of `feat`, `fix`, `chore`, `build`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`). The check SHALL run on PR open, reopen, edit, and synchronize, and SHALL fail the check if the title does not match.

#### Scenario: Conventional PR title
- **WHEN** a PR is opened with title `feat(docker): add release pipeline`
- **THEN** the title check passes

#### Scenario: Non-conventional PR title
- **WHEN** a PR is opened with title `add release pipeline` (no type prefix)
- **THEN** the title check fails and blocks the status check from passing

---

### Requirement: PRs are auto-labeled by conventional-commit type
On a passing title check, the PR SHALL be automatically labeled to match its conventional-commit type, so downstream release-note categorization and version resolution can key off labels without manual tagging.

#### Scenario: Feature PR opened
- **WHEN** a PR titled `feat: add draft release workflow` is opened
- **THEN** it is automatically labeled `feat`

---

### Requirement: Draft release is created and updated on every push to main
On every push to `main`, the CI system SHALL automatically create or update a GitHub draft release using Release Drafter. The draft SHALL aggregate all merged PRs since the last published release, grouped by label category.

#### Scenario: First push to main after a release
- **WHEN** a commit is pushed to `main` and no draft release exists
- **THEN** a new draft release is created with the next resolved version as the title and aggregated PR changes in the body

#### Scenario: Subsequent push to main
- **WHEN** a commit is pushed to `main` and a draft release already exists
- **THEN** the existing draft release is updated to include any newly merged PRs

---

### Requirement: Release version is resolved from PR labels
The draft release title and tag SHALL use semantic versioning (`vMAJOR.MINOR.PATCH`) resolved from the labels on merged PRs. The resolver SHALL apply the following precedence: `major` label → bump major, `minor`/`feat`/`feature`/`enhancement` label → bump minor, `patch`/`fix`/`bug`/`bugfix`/`chore`/`refactor`/`style`/`perf`/`test`/`ci`/`docs`/`doc`/`documentation` label or no label → bump patch.

#### Scenario: Feature-labeled PR merged
- **WHEN** a PR with the `feat` label is merged to main
- **THEN** the draft release tag increments the minor version (e.g., v1.0.3 → v1.1.0)

#### Scenario: No bump label on PR
- **WHEN** a merged PR has no major/minor/patch-mapped label
- **THEN** the draft release tag increments the patch version by default

---

### Requirement: Changelog entries are categorized by PR label
The draft release body SHALL group PR entries under human-readable category headings based on their labels: 🚀 Features (`feat`, `feature`, `enhancement`), 🐛 Bug Fixes (`fix`, `bug`, `bugfix`), 🛠 Maintenance (`chore`, `refactor`, `style`, `perf`, `test`, `ci`), 📚 Documentation (`docs`, `doc`, `documentation`).

#### Scenario: Feature PR merged
- **WHEN** a PR with the `feat` label is merged
- **THEN** it appears under the "🚀 Features" section in the draft release body

---

### Requirement: Docker image is built and pushed on merge and on release
On every push to `main` and on every `v*` tag push, CI SHALL build the application's Docker image and push it to GHCR at `ghcr.io/jwndlng/benny-watchman`. A push to `main` SHALL produce a `:latest` tag; a `v*` tag push SHALL additionally produce a version-matched tag (e.g., `:v1.2.0`).

#### Scenario: Push to main
- **WHEN** a commit is pushed directly to `main` (not via a version tag)
- **THEN** the image is built and pushed as `ghcr.io/jwndlng/benny-watchman:latest`

#### Scenario: Version tag pushed
- **WHEN** tag `v1.2.0` is pushed (e.g., because a draft release was published)
- **THEN** the image is built and pushed as both `ghcr.io/jwndlng/benny-watchman:latest` and `ghcr.io/jwndlng/benny-watchman:v1.2.0`

---

### Requirement: Built images carry resolvable version metadata
Each built image SHALL have its version resolved via `git describe --tags --always` and recorded as both an OCI `org.opencontainers.image.version` label and an `APP_VERSION` environment variable inside the image, so a running container's version can be determined without external metadata.

#### Scenario: Image built from a tagged commit
- **WHEN** the image is built at tag `v1.2.0`
- **THEN** the image's `org.opencontainers.image.version` label and `APP_VERSION` env var both read `v1.2.0`

---

### Requirement: Publishing a release triggers build provenance attestation
When a maintainer publishes a draft release, CI SHALL wait for the corresponding versioned Docker image to become available in GHCR, then attest build provenance for that image digest.

#### Scenario: Release published, image already available
- **WHEN** a release `v1.2.0` is published and `ghcr.io/jwndlng/benny-watchman:v1.2.0` already exists
- **THEN** the attestation step resolves the image digest and publishes a provenance attestation for it

#### Scenario: Release published, image not yet available
- **WHEN** a release `v1.2.0` is published before the corresponding Docker build has finished
- **THEN** CI polls for the image to appear (up to 3 minutes) before proceeding, and fails the workflow if the image never appears

---

### Requirement: Release notes include Docker pull instructions
After successful attestation, the release notes SHALL be updated to append ready-to-use `docker pull` commands for both the version tag and `:latest`.

#### Scenario: Attestation succeeds
- **WHEN** build provenance attestation succeeds for release `v1.2.0`
- **THEN** the release body is appended with a "Docker Image" section containing `docker pull ghcr.io/jwndlng/benny-watchman:v1.2.0` and `docker pull ghcr.io/jwndlng/benny-watchman:latest`
