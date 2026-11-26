---
name: repo-scaffold
description: Scaffold a new GitHub repository or add missing repository hygiene to an existing one, including project documents, contribution templates, CI, and release setup.
---

# Repository Scaffolding Workflow

Use this skill when the user asks to create a GitHub repository starter or improve repository hygiene in an existing repository.

Follow the workflow in order.
Use the new-repository path for an empty repository or a project that has not been created yet.
Use the existing-repository path whenever meaningful files or history already exist, even when baseline artifacts are missing.

## 1. Shared intake and inspection

### Step 1: Gather project details with fixed choices

- Inspect the supplied project path and repository context first, then ask only for information that remains unknown.
- Ask exactly one question per turn and wait for the user's answer before asking the next question.
- Never combine several missing fields into one message, checklist, or free-text form.
- Ask every question in this workflow with the current agent's built-in question tool, including intake, project-specific text values, follow-up questions, release setup, proposed changes, and final confirmation, subject to higher-priority tool restrictions.
- Use `request_user_input` in Codex CLI.
- Use `AskUserQuestion` in Claude Code CLI.
- Use `ask_user` in GitHub Copilot CLI, or `vscode/askQuestions` in GitHub Copilot in VS Code.
- "The question tool" below means the tool listed for the current agent.
- If a question has more choices than the tool allows, show the most relevant choices and name the others in the question so the user can enter one as a custom value.
- Each call must contain exactly one question; wait for the user's answer before asking the next question.
- For finite choices, provide concise selectable options using the tool's supported schema.
- For project-specific text values such as project name or GitHub owner/repository, ask through the same tool and use its free-text response support.
- When the tool requires selectable options for a text question, offer a verified suggestion when available and explain that the user can enter a custom value; do not invent a project identity to fill an option.
- In Codex, the default-mode choice popup requires `features.default_mode_request_user_input = true` in `~/.codex/config.toml`.
- Do not substitute a chat question or another input tool for the current agent's question tool.
- If the question tool is unavailable or cannot represent the required question, report the limitation and pause the dependent workflow instead of silently falling back to chat.
- If a question is canceled or receives no answer, do not treat that as a choice or confirmation; preserve the pending question until the user resumes or changes the task.
- Infer the local path from the user's supplied target instead of asking them to repeat it.
- For a new repository, ask for missing values in this order: project name, GitHub owner/repository, project type, implementation stack, then license.
- Offer these project type choices: application/service, library/package, CLI/tool, infrastructure, documentation, or other.
- Infer implementation stack from files when possible; otherwise offer only relevant stack choices plus `Other`.
- Offer these license choices: `MIT`, `Apache-2.0`, `GPL-3.0`, `BSD-3-Clause`, `Proprietary/no license`, and `Other`.
- Never select a license on the user's behalf.
- If the user selects `Other`, ask one follow-up question for the specific value.

For GitHub configuration, ask about each unresolved setting separately, using a one-question choice prompt and the recommended production option as the default selection:

| Setting | Choices | Recommended default |
| --- | --- | --- |
| Visibility | Public / Private | User decides based on intended audience and source sensitivity. |
| Default branch | `main` / Existing repository convention | `main` for a new repository. |
| Merge method | Squash / Merge commit / Rebase | Squash, unless the project has a documented convention. |
| Pull request review | Required, with 1 approval / Required, with 2 approvals / Required, no approval count | Require a PR; choose an approval count supported by the team. |
| Required checks | CI checks / None until CI succeeds | Require the named CI checks only after they have run successfully. |
| Branch rules | Production baseline / Strict / None | Production baseline. |
| Security automation | Dependabot alerts and updates / Alerts only / Off | Alerts and updates, when available and compatible with the project. |
| Secret protection | Enable available secret scanning and push protection / Alerts only / Off | Enable available protection; explain plan or visibility limitations. |
| GitHub Actions permissions | Read-only by default / Existing organization policy | Read-only by default, with write permissions limited to jobs that need them. |
| Bot access | None / Dependabot only / Release automation / Existing bot | None unless automation is requested or required by an accepted workflow. |
| Optional repository features | Issues / Discussions / Projects, each on or off | Enable only features the project will use. |

- Use these choices instead of open-ended prompts for standard settings.
- Keep `Other` available when the project genuinely needs a nonstandard value, and ask only for that specific value.
- For an existing repository, infer choices from its current configuration and ask one choice question at a time only for proposed changes.
- Skip questions whose answers are already established by the user, repository, or organization policy.
- Do not show a combined list of questions and ask the user to type all answers at once.

### Step 2: Inspect the target

- Resolve and verify the target directory before reading or changing files.
- Inspect Git status, tracked files, root documents, `.github/`, manifests, test commands, default branch, and repository instructions.
- Check for case-insensitive path collisions and generated files.
- Classify the target as a new empty repository or an existing repository with meaningful content or history.
- Inspect its release state using [Release setup](#4-release-setup).

- For an existing repository, compare root `AGENTS.md` with `assets/starter/AGENTS.md` when shared agent rules are in scope.
- Show differences before proposing a replacement or merge.

## 2. New repository workflow

### Step 1: Confirm configuration

- Prepare a summary table of the project choices and every GitHub setting, including the selected production baseline and any limitations imposed by the account plan.
- Use explicit values rather than phrases such as "secure defaults" or "standard setup".
- After gathering individual choices, use the question tool for one final confirmation question with choices such as `Apply these settings` or `Edit a setting`.
- Do not create or configure the remote repository until the user selects confirmation.
- If the user selects `Edit a setting`, ask which setting to change, then ask only that setting's choice question and show the revised summary for confirmation.

### Step 2: Create the local baseline

- Create the project folder at the confirmed local path.
- Use `assets/starter/` as the source for reusable files.
- Create only files that fit the project's verified stack and requested scope.

The starter file map is:

- `assets/starter/README.md` -> `README.md`.
- `assets/starter/LICENSE` -> `LICENSE`, only when MIT is selected by the user or established by an existing project convention.
- For any other license, for now generate the `LICENSE` text from your own knowledge of the selected license, and tell the user it was generated this way and should be checked against the official text.
- For `Proprietary/no license`, do not create an open source license; ask before adding any proprietary notice, and adjust the README, CI file list, and other license references to match.
- `assets/starter/CONTRIBUTING.md` -> `CONTRIBUTING.md`.
- `assets/starter/AGENTS.md` -> root `AGENTS.md`.
- `assets/starter/CLAUDE.md` -> `CLAUDE.md`.
- `assets/starter/.github/copilot-instructions.md` -> `.github/copilot-instructions.md`.
- `assets/starter/.github/pull_request_template.md` -> `.github/pull_request_template.md`.
- `assets/starter/.github/ISSUE_TEMPLATE/bug_report.md` -> `.github/ISSUE_TEMPLATE/bug_report.md`.
- `assets/starter/.github/ISSUE_TEMPLATE/feature_request.md` -> `.github/ISSUE_TEMPLATE/feature_request.md`.
- `assets/starter/.github/workflows/ci.yml` -> `.github/workflows/ci.yml`.

- The root `AGENTS.md` is the single source of shared repository instructions.
- Keep `CLAUDE.md` and `.github/copilot-instructions.md` as short entrypoints that point to the root `AGENTS.md`.
- Do not duplicate or independently maintain the same shared rules in those entrypoints.
- The starter `AGENTS.md` is a baseline template; adapt it to verified repository conventions without copying machine-specific global instructions.

- Replace every placeholder with verified project information.
- Create `AGENTS.md` from `assets/starter/AGENTS.md`; do not write it from scratch or copy it from another repository.
- Keep the template's layout: the same headings, section order, lines, and placeholder positions.
- In `AGENTS.md`, replace each `{{UPPER_SNAKE_CASE}}` placeholder with a value from repository evidence or confirmed user choices, and use the exact runnable command for each supported check.
- When no value exists for an `AGENTS.md` placeholder, use `Not configured` with a short reason; do not remove its line or section.
- In other files, remove optional sections that do not apply.
- Keep all convention slots in `AGENTS.md`; fill only verified conventions and mark the others `Not configured` instead of inventing them.
- Keep the generated `AGENTS.md` between 200 and 300 lines, as specified by the starter template.
- Ask for essential identity or license details rather than guessing.
- DecisionLane uses MIT, but select MIT only when the user chooses it or the project's existing convention establishes it.

- If the project has no implementation yet, use a CI check that validates the baseline files and template metadata.
- If code already exists, configure CI with the project's real install, lint, and test commands.
- Do not claim checks that cannot run.
- Use least-privilege permissions and the repository's actual default branch, or branch-agnostic push and pull-request triggers when it is unknown.
- Add a `.gitignore` only when its entries match the selected stack.
- Add `infra/` or other product-specific directories only when the project requires them; do not create empty sample infrastructure by default.

#### Pull request and CI file references

- The pull request form comes from `assets/starter/.github/pull_request_template.md` and is installed at `.github/pull_request_template.md`.
- The CI workflow comes from `assets/starter/.github/workflows/ci.yml` and is installed at `.github/workflows/ci.yml`.
- The starter CI job named `repository-baseline` verifies the baseline files and checks for unresolved scaffold placeholders.
- When configuring branch protection, use the exact status check name reported by a successful CI run; do not guess the check name from the workflow filename.
- When the project has code, extend or replace the baseline CI steps only with the project's real install, lint, test, build, or security commands.

### Step 3: Decide on release setup

- Inspect release state as described in [Release setup](#4-release-setup).
- When no release tooling exists, recommend the release starter and ask whether to include it in the baseline.
- Add release files only when the user accepts the recommendation.

### Step 4: Apply GitHub settings

- After the user confirms the settings summary, create or configure the GitHub repository as requested.
- Use the confirmed visibility, default branch, bot configuration, and branch-protection rules.
- Do not silently enable optional settings that the user has not accepted.

- For the production baseline, protect the default branch with pull requests, passing CI status checks, resolved review conversations, and disabled force-push and branch deletion.
- Require one approval when another qualified reviewer is available; for a solo-maintained repository, require the pull request but do not set an impossible approval requirement.
- Dismiss stale approvals when new commits change the reviewed diff, unless the repository's review process requires a different policy.
- Enable dependency graph and Dependabot alerts, and enable Dependabot security updates where supported.
- Enable secret scanning and push protection where available, and state clearly when plan or repository visibility prevents a setting.
- Set GitHub Actions' default token permissions to read-only, then grant narrowly scoped permissions to individual jobs that need writes.
- Require CI status checks only after their exact check names exist and have completed successfully.
- Do not enable advanced gates such as signed commits, code scanning merge blocks, deployment gates, or merge queues unless the project has the tooling and workflow to satisfy them.
- Prefer repository rulesets when available for consistent branch policies; use branch protection rules when rulesets are unavailable or incompatible with the account plan.
- Review GitHub's current feature availability before promising a setting.

### Step 5: Validate the baseline

- Run the local equivalent of the CI check.
- Inspect the created files for unresolved placeholders, broken relative links, incorrect paths, and mismatches between the README project tree and actual files.
- Confirm `AGENTS.md` exists at the project root and both `CLAUDE.md` and `.github/copilot-instructions.md` reference it.
- Confirm `.github/pull_request_template.md` and `.github/workflows/ci.yml` are present and the CI job checks all required baseline files.
- Report the results and any unavailable checks honestly.

## 3. Existing repository workflow

### Step 1: Build a concrete inventory

- Before editing, identify present artifacts, missing artifacts, proposed paths and contents, conflicting conventions, and likely effects on workflows or contributors.
- Include `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` when cross-agent consistency is requested.
- Include the PR template at `.github/pull_request_template.md` and CI workflow at `.github/workflows/ci.yml` in the inventory when those files are in scope.
- Include the full release inventory from [Release setup](#4-release-setup).

### Step 2: Present the proposal and get approval

- Show the inventory and explicitly ask whether to add the proposed artifacts.
- For each proposed file, explain whether it is new, an integration into an existing file, or a replacement.
- Wait for the user's answer before editing.

- Do not overwrite a license, contributor guide, template, or CI workflow without separate, specific approval for that replacement.
- Do not modify, replace, or remove an existing release or deployment workflow unless the user specifically approves that replacement.

### Step 3: Apply only the approved changes

- Add only the agreed missing artifacts and preserve existing files and workflows.
- Use `assets/starter/` as a source for reusable content, adapting it to verified project facts and conventions.
- Integrate CI checks with the project's actual commands and current state.
- When shared agent instructions are in scope, propose `assets/starter/AGENTS.md` as the root instruction template and update `CLAUDE.md` and Copilot instructions to reference that same file.
- Never replace root agent rules with an independently maintained skill template.

### Step 4: Validate the changes

- Verify the resulting files, relative links, placeholders, and any README project tree affected by the change.
- Confirm agent entrypoints reference the root `AGENTS.md` when cross-agent consistency is in scope.
- Confirm the PR template and CI workflow paths and their links or checks are correct when those files changed.
- Run the applicable local checks and report their results honestly.

## 4. Release setup

Inspect the current release state before recommending release files.
Include this inventory for both new and existing repositories:

- Versions in manifests such as `package.json`, `pyproject.toml`, `Cargo.toml`, `*.csproj`, Go module paths, and `VERSION` files, including whether they agree.
- Tags from `git tag --sort=-v:refname` and the tag format in use, such as `v1.2.3` or `name-v1.2.3`.
- GitHub releases from `gh release list` when the GitHub CLI is available, including whether notes are generated or hand-written.
- Changelogs such as `CHANGELOG.md`, `HISTORY.md`, or `NEWS`, including their format and whether a tool generates them.
- Release tools such as release-please, semantic-release, Changesets, GoReleaser, `cargo-release`, or tag-triggered publishing.
- Deployment workflows triggered by `release`, tag `push`, `workflow_run`, or `workflow_dispatch`, and publish targets such as npm, PyPI, container registries, or hosting.
- Recent commit messages and pull-request titles, merge strategy, and whether they follow Conventional Commits.

Prefer existing release tooling and fill only its gaps.
When there is no release tooling, recommend these files from `assets/starter/.github/`:

- `workflows/release.yml`.
- `release-please-config.json`.
- `.release-please-manifest.json`.
- `RELEASING.md`.

Copy these files to the same relative paths under the target repository's `.github/` directory.
Set `release-type` in `.github/release-please-config.json` to the project's stack, such as `node`, `python`, `rust`, `go`, or `simple` when there is no supported manifest.
Set `.github/.release-please-manifest.json` to the latest released version from tags or manifests, or `0.0.0` when nothing has been released.
Keep `initial-version` set to `0.1.0` in `.github/release-please-config.json` so an unreleased project starts at `0.1.0`; without it, release-please starts at `1.0.0` because a `0.0.0` manifest does not count as an earlier release.
Change `initial-version` only when the user chooses a different first version.
Preserve the existing tag format; the starter produces `v1.2.3` tags and must be adjusted when the repository uses another format.
Adapt `.github/RELEASING.md` to describe real deployment steps or state that there is no deployment.
Link the release guide from `README.md` and `CONTRIBUTING.md` when those files are part of the approved change.
Add a Conventional Commits note to `CONTRIBUTING.md` because release notes and version bumps are generated from commit messages.
Never hand-write or edit `CHANGELOG.md`; the release tool generates it.
If release-please would add entries above an existing changelog, explain how existing history will be kept and ask before moving or renaming it.

When a deployment listens for `release` or tag events, explain that releases created with `GITHUB_TOKEN` do not trigger other workflows.
Propose a GitHub App or fine-grained token, or a direct call from the release workflow, instead of silently breaking deployment.
Generated release workflows must set top-level `permissions: {}` and grant only `contents: write` and `pull-requests: write` to the release job.
Add publishing permissions such as `id-token: write` only to a separate job that needs them.
Trigger the release workflow on pushes to the repository's actual default branch only.
Tell the user to enable "Allow GitHub Actions to create and approve pull requests" because release-please cannot open its release pull request otherwise.

## 5. Content and quality standards

### README

Follow `assets/starter/README.md` for a centered project title and badges, a concise product summary, overview, core features, local quick start, actual repository tree, how-it-works flow, contribution link, and license link.
Keep the centered product summary to ten words and feature names to two to four words.
Replace every placeholder with verified project information or remove optional sections that do not apply.
Use the actual CI and release workflow filenames in badge URLs.
Include a release badge only when a release workflow exists, and use a GitHub releases version badge rather than an Actions status badge for the version.
Use real demo images and screenshots when available, and remove image placeholders rather than shipping broken links.
Use a simple Mermaid flow with four or five real steps when it helps explain the project.
Ensure the README project tree matches files actually present and omits documentation or tooling that is not in the target repository.

### Other files

- Use `assets/starter/AGENTS.md` as the single root instruction template for repository agents.
- Keep `assets/starter/CLAUDE.md` and `assets/starter/.github/copilot-instructions.md` as concise references to the root `AGENTS.md`.
- Use `assets/starter/CONTRIBUTING.md` for guidance on proposing changes, local setup, checks, and pull requests.
- Use the issue templates in `assets/starter/.github/ISSUE_TEMPLATE/` for reproducible bug reports and outcome-focused feature requests.
- Use `assets/starter/.github/pull_request_template.md` for summary, linked issue, verification, review notes, and sensitive-data reminders.
- Use `assets/starter/.github/workflows/ci.yml` as a starting point only; adapt it to least privilege and checks that actually run for the repository.
- The starter CI workflow verifies required baseline files and unresolved placeholders; add project-specific checks when implementation code exists.
- Use the exact successful check name from the CI run when configuring a required status check.
- Use `assets/starter/LICENSE` only for MIT, after the correct holder and year are established.
- Follow the license rules in the new repository workflow for any other choice.
- Agent instructions should direct agents to inspect the repository before generation or pull-request creation, follow contribution and pull-request templates, run applicable checks, and report results honestly.
- Recommend required CI status checks and branch protection after the workflow has run successfully; instructions alone do not enforce agent compliance.
- In long Markdown files, put each full sentence on its own physical line.

- For current GitHub capabilities, consult [available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), and [security and analysis settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository).
