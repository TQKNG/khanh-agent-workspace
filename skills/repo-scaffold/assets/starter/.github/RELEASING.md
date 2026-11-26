# Releasing {{PROJECT_NAME}}

{{PROJECT_NAME}} uses [release-please](https://github.com/googleapis/release-please) to version releases, generate `CHANGELOG.md`, create tags, and publish GitHub Releases.
Versions follow [Semantic Versioning](https://semver.org/) and tags use the `v<major>.<minor>.<patch>` format.

## Commit messages

Release notes are generated from the commits that land on `{{DEFAULT_BRANCH}}`.
Write those commits, or the pull request titles used for squash merges, as [Conventional Commits](https://www.conventionalcommits.org/).
`fix:` produces a patch release, `feat:` produces a minor release, and `!` or a `BREAKING CHANGE:` footer produces a major release.
Before version 1.0.0, a breaking change produces a minor release instead.
Other types such as `docs:`, `test:`, and `chore:` do not trigger a release on their own.

## First version

If the project has no earlier release and the manifest is `0.0.0`, the first release uses `initial-version` from `.github/release-please-config.json`, which defaults to `0.1.0`.
A releasable commit is still required before release-please opens the first release pull request.

## Review and publish a version

1. Merge changes to `{{DEFAULT_BRANCH}}` as usual.
2. The `Release` workflow opens or updates a release pull request that bumps the version and updates `CHANGELOG.md`.
3. Review the release pull request: confirm the proposed version, read the generated changelog, and check that the included changes are ready to ship.
4. Merge the release pull request when you want to publish.
5. The `Release` workflow then creates the `v<version>` tag and the GitHub Release with the same notes.
6. Confirm the tag and the GitHub Release exist, then run or monitor any deployment described below.

To force a specific version, add a `Release-As: <version>` footer to a commit on `{{DEFAULT_BRANCH}}`.
To correct the note for a merged squash commit, add a `BEGIN_COMMIT_OVERRIDE` and `END_COMMIT_OVERRIDE` block to that pull request's description before the release pull request is merged.
Do not edit `CHANGELOG.md` by hand; the next release pull request regenerates it.

## Deployment

{{DEPLOYMENT_NOTES}}

## Repository settings

Enable **Settings > Actions > General > Allow GitHub Actions to create and approve pull requests** so the workflow can open the release pull request.
The workflow uses the default `GITHUB_TOKEN` with `contents: write` and `pull-requests: write` only.
Tags and releases created with `GITHUB_TOKEN` do not trigger other workflows.
Workflow runs for a release pull request opened or updated with `GITHUB_TOKEN` wait for approval, so required checks do not pass until they run.
Someone with write access can start them by selecting **Approve workflows to run** on the pull request.
To run checks without approval, or to start a deployment from the release or tag event, pass a GitHub App token or fine-grained token to the action's `token` input instead.
