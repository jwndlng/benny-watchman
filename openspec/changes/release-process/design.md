## Context

Benny has three CI workflows today (`test.yml`, `lint.yml`, `integration-test.yml`) but nothing that versions or publishes anything — merges to `main` just sit there. `jwndlng/ai-app-radar` already runs a working release pipeline (PR labeling → draft release → Docker publish → attestation) that we're porting with minimal changes: swap the image name/owner, and adapt the Docker build to this repo's `uv`-based Dockerfile (no Playwright/static assets to copy).

## Goals / Non-Goals

**Goals:**
- Every merged PR is labeled by conventional-commit type, feeding an always-current draft release
- Publishing that draft release is the single human trigger for a versioned Docker image
- The published image is provenance-attested and the release notes get a ready-to-use `docker pull` command
- Reuse the ai-app-radar config/action versions as-is — this is a proven process, not a redesign

**Non-Goals:**
- No auto-deploy of the image to any environment — this change stops at "image published to GHCR"
- No change to existing test/lint/integration-test workflows or branch protection rules (repo settings, not code — left as a follow-up)
- No multi-arch builds, SBOMs, or vulnerability scanning — out of scope for this pass

## Decisions

- **Reuse Release Drafter's category/version-resolver config verbatim** — the categories (`feat`/`fix`/`chore`.../`docs`) and resolver precedence (`major` > `minor` > `patch`, default `patch`) are already proven in ai-app-radar and match the conventional-commit types the PR-title check enforces. Alternative considered: hand-roll a changelog script — rejected, reinvents a solved problem.
- **Reuse `action-runner/conventional-labeler` (pinned SHA) for auto-labeling**, triggered off the same PR title regex check — keeps the label vocabulary in lockstep with the release-drafter config without a second source of truth.
- **Image name: `ghcr.io/jwndlng/benny-watchman`** — GHCR under the repo owner, matching the ai-app-radar pattern (`ghcr.io/<owner>/<repo>`).
- **Two build triggers, two tag sets**: push to `main` → `:latest`; push of a `v*` tag (created when the draft release is published) → `:latest` + `:vX.Y.Z`. Mirrors ai-app-radar exactly so `:latest` always tracks `main` and versioned tags only appear at release time.
- **`APP_VERSION` resolved via `git describe --tags --always`** and passed as a Docker build-arg, baked into an OCI label (`org.opencontainers.image.version`) and `ENV`. Alternative considered: derive version only from the release tag — rejected, because `:latest` builds off `main` (between releases) still need *some* identifiable version for debugging.
- **Attestation is a separate workflow gated on the `release: published` event**, not folded into `docker.yml` — it needs the *release* tag name (not just the git tag) and posts back to the release body via `gh release edit`, which only makes sense once a release object exists. Keeps `docker.yml` a pure build/push job with no GitHub-release side effects.
- **Poll-for-image loop (18 × 10s = 3 min) in the attestation workflow** rather than a workflow dependency (`needs:`) on `docker.yml` — the release-publish event and the tag-push event are two independent triggers with no guaranteed ordering or shared run ID, so polling the registry is the simplest reliable handoff. Same approach and timeout as ai-app-radar (proven in practice).
- **Dockerfile changes are additive only**: add `ARG APP_VERSION=dev`, an OCI label, and `ENV APP_VERSION`. No change to the existing two-stage `uv sync` layering (dependency layer cached separately from source).

## Risks / Trade-offs

- **[Risk]** Docker build takes longer than the 3-minute poll window in the attestation workflow → image never found, attestation fails. **Mitigation**: same timeout as the reference implementation, where it's held up in practice; revisit the retry count if Benny's image proves slower to build.
- **[Risk]** GHCR packages default to private visibility on personal accounts; a private image will fail to `docker pull` for anyone without registry access, silently breaking the "append pull instructions" step for external consumers. **Mitigation**: flagged as a one-time manual follow-up (see Open Questions) — not something a workflow file can set.
- **[Risk]** Nothing currently *requires* `test.yml`/`lint.yml` to pass before merge to `main`, so a red build could still get labeled, drafted, and eventually released. **Mitigation**: out of scope for this change (branch protection is a repo setting, not code) but called out as a recommended follow-up.
- **[Trade-off]** Auto-labeling trusts the PR title regex; a mislabeled or unlabeled PR silently resolves to a `patch` bump rather than failing loudly. Accepted because it matches ai-app-radar's behavior and a wrong patch bump is low-cost to correct (edit the draft before publishing).

## Migration Plan

1. Add `.github/workflows/{conventional-commits,draft-release,docker}.yml`, `.github/workflows/release.yml`, and `.github/config/draft-release-config.yml`.
2. Update `Dockerfile` with the `APP_VERSION` build arg/label.
3. Merge to `main` — Release Drafter creates the first draft release automatically; no manual step needed to bootstrap it.
4. Nothing is published until a maintainer manually publishes the draft release for the first time.

Rollback: revert the added workflow/config files; no state to migrate back since nothing outside GitHub Actions is touched.

## Open Questions

- Should the GHCR package (`ghcr.io/jwndlng/benny-watchman`) be flipped to public, and by whom — first-time manual step, not automatable from a workflow?
- Do we want to add branch protection requiring `test.yml`/`lint.yml` to pass before merge to `main`? Recommended, but it's a repo-settings change outside this change's scope.
