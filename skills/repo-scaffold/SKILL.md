---
name: repo-scaffold
description: Scaffold a new GitHub repository or update missing hygiene in an existing one with project documents, contribution templates, CI, and a release process.
---

# Scaffold a new GitHub Repository Workflow

Use this skill when asked to create a GitHub repository starter or add missing repository hygiene to an existing repository.


## Step 1: Project name and General Configuration

- Prompt the user for [project name] and [Owner/Repository].
- Prompt the user for [local location path].
- For a new repository, ask for the repository visibility [public/private].
- Prompt the user for any bot configuration that affects repository access.
- Prompt the user for these GitHub settings:
  - Branch protection: [Yes/No].
  - If enabled, ask which branch protection rules to configure.
- Suggest relevant optional settings such as `CODEOWNERS`, Dependabot, required CI checks, and branch protection.
- Show a summary in table format and require user confirmation before applying repository settings.
- If the user declines, ask what to change and repeat the summary until they confirm.

## Step 2: Local Repo Setup

Dependencies: Step 1
- Resolve the path in user response and create a new project folder locally
- Scaffold below folders and files structure with empty content:

```text
.
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── AGENTS.md
├── CLAUDE.md
├── infra/
│   ├── main.bicep
│   ├── modules/
│   └── main.bicepparam
├── .github/
│   ├── copilot-instructions.md
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   └── workflows/
│       ├── ci.yml
│       ├── deploy.yml
│       └── release.yml
└── .gitignore
```

## Inspect first

Resolve the target directory and inspect Git status, tracked files, root documents, `.github/`, package manifests, test commands, default branch, and repository instructions.
Classify the target as a new empty repository or an existing repository with meaningful content or history.
Treat an existing repository as existing even when some baseline artifacts are absent.
Check for case-insensitive filename collisions and generated files.
Inspect the release state described in [Release setup](#release-setup) before proposing any change.

## New repository

Create a small, usable baseline using [assets/starter](assets/starter): `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/pull_request_template.md`, issue templates, and `.github/workflows/ci.yml`.
Copy the current contents of `~/.codex/AGENTS.md` into the new repository's root `AGENTS.md` so agents in GitHub or other machines can read the rules.
Do not replace its rules with a separately maintained skill template.
Use `CLAUDE.md` as Claude Code's import, and Copilot's repository instructions as a pointer to the repository copy.
The repository copy is a portable snapshot, not a live link; report this limitation and refresh it from the authoring source when asked to update shared rules.
Keep each tool's entrypoint short and avoid conflicting duplicate rules.
Replace every placeholder with verified project information; ask for essential missing identity or license details rather than guessing.
DecisionLane uses MIT, but only select MIT when the user chooses it or an existing project convention establishes it.
If the project has no implementation yet, use a CI check that validates the baseline files and template metadata.
If code already exists, use the project's real install, lint, and test commands, and avoid claiming checks that do not run.
Keep permissions minimal and use the repository's actual default branch, or branch agnostic push and pull request triggers when it is unknown.
Include a practical `.gitignore` only when its entries match the selected stack.
Recommend the release starter from [assets/release](assets/release) and add it when the user accepts it, as described in [Release setup](#release-setup).
Run the local equivalent of the CI check and inspect the final files for placeholders and broken relative links.

## Existing repository

Prepare a concrete inventory before writing: present artifacts, missing artifacts, proposed paths and contents, conflicting conventions, and likely effects on existing workflows or contributors.
Include `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` in this review when cross-agent consistency is requested.
Compare any existing root `AGENTS.md` with `~/.codex/AGENTS.md` and show differences before proposing a replacement or merge.
Include the release inventory from [Release setup](#release-setup): current versions, tags, releases, changelogs, release and deployment workflows, and the proposed release additions.
Show the user this inventory and explicitly ask whether to add the proposed artifacts.
Wait for their answer before editing the repository.
After approval, add only the agreed missing artifacts, preserve existing files and workflows, and integrate CI checks with the actual project commands.
Do not overwrite a license, contributor guide, templates, or CI workflow without separate, specific approval for that replacement.
Verify the resulting files and run the applicable local checks.

## Release setup

Inspect the current release state before recommending anything:

- Versions: version fields in manifests such as `package.json`, `pyproject.toml`, `Cargo.toml`, `*.csproj`, `go.mod` module paths, or `VERSION` files, and whether they agree.
- Tags: `git tag --sort=-v:refname` and the tag format in use, such as `v1.2.3` or `name-v1.2.3`.
- Releases: `gh release list` when the GitHub CLI is available, and whether release notes are generated or hand written.
- Changelogs: `CHANGELOG.md`, `HISTORY.md`, or `NEWS` files, their format, and whether a tool generates them.
- Release tooling: existing workflows or configuration for release-please, semantic-release, Changesets, GoReleaser, `cargo-release`, or tag-triggered publishing.
- Deployment: workflows triggered by `release`, tag `push`, `workflow_run`, or `workflow_dispatch`, and any publish targets such as npm, PyPI, container registries, or hosting.
- Conventions: recent commit messages and pull request titles, merge strategy, and whether they follow Conventional Commits.

Prefer the release tooling the repository already uses and only fill its gaps.
When there is none, recommend the starter in [assets/release](assets/release), which uses release-please through a release pull request.
Set `release-type` in `release-please-config.json` to match the stack, such as `node`, `python`, `rust`, `go`, or `simple` for repositories without a supported manifest.
Set `.release-please-manifest.json` to the latest released version from tags or manifests, or to `0.0.0` when nothing has been released so the first release is `0.1.0`.
Keep the existing tag format; the starter produces `v1.2.3` tags and must be adjusted when the repository uses another format.
Adapt `RELEASING.md`, describe real deployment steps or state that there is no deployment, and link it from `README.md` and `CONTRIBUTING.md`.
Add a Conventional Commits note to `CONTRIBUTING.md`, because the changelog and version bumps are generated from commit messages.
Never hand write or edit `CHANGELOG.md`; the release tool generates it.
release-please adds new entries above an existing changelog, so report how existing history will be kept and ask before moving or renaming it.

For a new repository, include the release starter in the baseline when the user accepts the recommendation.
For an existing repository, list the release additions in the inventory with their paths and contents, and follow the same approval rules as other artifacts.
Do not modify, replace, or remove an existing release or deployment workflow unless the user specifically approves that replacement.
When a deployment listens for `release` or tag events, explain that releases created with `GITHUB_TOKEN` do not trigger other workflows, and propose a GitHub App or fine-grained token or a direct call from the release workflow instead of silently breaking deployment.

Generated release workflows set `permissions: {}` at the top level and grant only `contents: write` and `pull-requests: write` to the release job.
Add publishing permissions, such as `id-token: write` for trusted publishing, only to a separate job that needs them.
Trigger the release workflow on pushes to the repository's actual default branch only.
Tell the user to enable "Allow GitHub Actions to create and approve pull requests" in the repository settings, because the release pull request cannot be opened otherwise.

## Content standard

README: follow `assets/starter/README.md` for the centered project title and badges, concise product summary, overview, core features, local quick start, actual repository tree, how-it-works flow, contribution link, and license link.
Keep the centered product summary to ten words and feature names to two to four words.
Replace every placeholder with verified project information or remove the optional section when it does not apply.
Use the actual CI and release workflow filenames in badge URLs; include the release badge only when a release workflow exists.
Use a GitHub releases version badge rather than an Actions status badge for the version.
Use a real demo image and screenshots when available; remove image placeholders rather than shipping broken image links.
Use a simple Mermaid flow with four or five real steps when it helps explain the project; do not retain generic sample nodes.
The project tree must match the files actually created and must not list documentation or tooling that is not in the target repository.
CONTRIBUTING: how to propose changes, set up, run checks, and submit a pull request.
Issue templates: reproducible bug reports and outcome focused feature requests.
Pull request template: summary, linked issue, verification, review notes, and sensitive data reminder.
License: complete chosen license text with correct holder and year.
CI: least privilege read access and a check that actually runs for the repository's current state.
Release guide: how versions are chosen, how maintainers review and publish a release, where the changelog comes from, and how deployment follows a release.
Agent instructions: inspect the repository before generation or PR creation, follow the contribution and PR templates, run applicable checks, and report results honestly.
For stronger enforcement, recommend required CI status checks and branch protection after the workflow has run successfully; instructions alone do not guarantee agent compliance.
Keep each full sentence on its own physical line in long Markdown files.
