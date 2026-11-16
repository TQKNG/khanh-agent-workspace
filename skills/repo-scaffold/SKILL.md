---
name: repo-scaffold
description: Scaffold a new GitHub repository with core project documents, contribution templates, and basic CI, or review and safely add missing repository hygiene artifacts to an existing repository.
---

# Repository scaffold

Use this skill when asked to create a consistent GitHub repository starter or add its baseline artifacts to an existing repository.
DecisionLane is the reference for the artifact set: README, license, contribution guide, issue and pull request templates, and CI.
Adapt the content to the target repository rather than copying DecisionLane's product details or stack checks.
Use `~/.codex/AGENTS.md` as Khanh's single authoring source for shared agent rules.
Read it fresh on every invocation; do not rely on the skill's installation-time contents.
If it is unavailable on the current machine, ask for the current source before copying shared agent rules into a repository.

## Inspect first

Resolve the target directory and inspect Git status, tracked files, root documents, `.github/`, package manifests, test commands, default branch, and repository instructions.
Classify the target as a new empty repository or an existing repository with meaningful content or history.
Treat an existing repository as existing even when some baseline artifacts are absent.
Check for case-insensitive filename collisions and generated files.

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
Run the local equivalent of the CI check and inspect the final files for placeholders and broken relative links.

## Existing repository

Prepare a concrete inventory before writing: present artifacts, missing artifacts, proposed paths and contents, conflicting conventions, and likely effects on existing workflows or contributors.
Include `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` in this review when cross-agent consistency is requested.
Compare any existing root `AGENTS.md` with `~/.codex/AGENTS.md` and show differences before proposing a replacement or merge.
Show the user this inventory and explicitly ask whether to add the proposed artifacts.
Wait for their answer before editing the repository.
After approval, add only the agreed missing artifacts, preserve existing files and workflows, and integrate CI checks with the actual project commands.
Do not overwrite a license, contributor guide, templates, or CI workflow without separate, specific approval for that replacement.
Verify the resulting files and run the applicable local checks.

## Content standard

README: purpose, current status, setup, verification, repository layout, and links to contribution guidance, with claims grounded in the repo.
CONTRIBUTING: how to propose changes, set up, run checks, and submit a pull request.
Issue templates: reproducible bug reports and outcome focused feature requests.
Pull request template: summary, linked issue, verification, review notes, and sensitive data reminder.
License: complete chosen license text with correct holder and year.
CI: least privilege read access and a check that actually runs for the repository's current state.
Agent instructions: inspect the repository before generation or PR creation, follow the contribution and PR templates, run applicable checks, and report results honestly.
For stronger enforcement, recommend required CI status checks and branch protection after the workflow has run successfully; instructions alone do not guarantee agent compliance.
Keep each full sentence on its own physical line in long Markdown files.
