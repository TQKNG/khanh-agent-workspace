# Khanh Agent Workspace

Khanh Agent Workspace is a collection of reusable agent skills, instructions, prompts, Codex plugins and Herdr workspace layouts.
They help with writing GitBook and arc42 documentation, auditing Codex session token use, scaffolding and releasing GitHub repositories, writing technical blog posts, taking GitHub issues through to pull requests, and running a Herdr cockpit with a GitHub inbox and an agents page.

## What is in each folder

- `.agents/`: the Codex plugin marketplace file, `.agents/plugins/marketplace.json`.
- `.claude-plugin/`: the Claude Code plugin marketplace file, `.claude-plugin/marketplace.json`.
- `.claude/skills/`: the `ticket` skill, which takes a GitHub issue through an isolated implementation and pull request in its own Herdr tab.
- `.github/`: issue and pull request templates, Copilot instructions and the CI workflows.
- `docs/`: the reference site analysis and the verification report for the `arc42-gitbook-docs` plugin.
- `herdr-layouts/`: the Herdr layout package `khanh-personal`, with its layout, mods, local hub and installer.
- `plugins/`: the plugins `arc42-gitbook-docs` (GitBook and arc42 documentation), `arc42-mintlify-docs` (Mintlify arc42 documentation), `diagram-standards` (approved draw.io diagram templates) and `session-token-audit` (Codex session token audit).
- `skills/`: the standalone skills `graphify`, `repo-scaffold` and `technical-blog-writing`.
- `tests/`: the repository's Python tests, run with `python -m unittest discover -s tests -v`.

The install steps for the plugins, standalone skills and Herdr layout follow below.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and pull request guidance.

Repository: <https://github.com/TQKNG/khanh-agent-workspace>

## Included plugin

- `arc42-gitbook-docs` version `0.3.0`
- `session-token-audit` version `0.1.0`
- `diagram-standards` version `0.2.0`

## Requirements

- Codex CLI or Codex in the ChatGPT desktop app.
- Git access to this repository.
- The GitHub plugin installed and connected for repository inputs.
- The GitBook plugin installed and connected.

## Install the Codex plugin

Add this Git-backed marketplace:

```powershell
codex plugin marketplace add TQKNG/khanh-agent-workspace --ref main
```

Verify the marketplace registration:

```powershell
codex plugin marketplace list
```

Restart the ChatGPT desktop app.

Open the Plugins directory, select `Khanh Plugins`, and install the plugins you need.

In Codex CLI, run `/plugins`, select the `Khanh Plugins` source, and install the plugin.

Start a new chat after installation.

Installing the Codex plugin also makes its bundled skills, instructions, references, and prompts available to Codex according to the plugin manifest.

The `session-token-audit` plugin reads local Codex session logs and needs access to the configured Notion workspace before it can record results.
Its pricing reference is an estimate that must be refreshed against official rates before use.

## Install the Claude Code plugin

The `arc42-mintlify-docs` and `diagram-standards` plugins are also listed in `.claude-plugin/marketplace.json` for Claude Code.

Add this marketplace and install the plugin:

```bash
claude plugin marketplace add TQKNG/khanh-agent-workspace
claude plugin install arc42-mintlify-docs@khanh-plugins
```

In a Claude Code session, run `/reload-plugins` or start a new session to load it.

The plugin uses the `diagram-standards` plugin for architecture diagrams, so install that one too:

```bash
claude plugin install diagram-standards@khanh-plugins
```

The `diagram-standards` plugin needs Python 3.
PNG export needs the draw.io desktop CLI, or the bundled `export-diagrams.yml` GitHub Action in the documentation repository.

## Use the standalone skills

The three folders under `skills/` are the maintained repository copies of reusable skills.
To use one in Codex, copy its complete folder to `~/.codex/skills/`.
To use one in Claude Code, copy its complete folder to `~/.claude/skills/` or the target repository's `.claude/skills/` directory.
These files are not installed by the Codex plugin marketplace.
The `graphify` skill requires the Graphify CLI; semantic extraction can use an available host agent when no model key is configured.

The `ticket` skill lives in `.claude/skills/ticket/` because it uses Claude's issue argument and requires a Herdr-managed session.
Copy that folder to a target repository's `.claude/skills/` or to `~/.claude/skills/` to use it elsewhere.

The standalone skills and plugins are reviewable distribution snapshots of local sources: `~/.codex/skills/repo-scaffold`, `~/.codex/skills/graphify`, `~/.codex/skills/technical-blog-writing`, `~/.claude/skills/ticket`, and `~/plugins/session-token-audit`.
Refresh the repository copies through a pull request when a local source changes.

Standalone resources that are not part of a plugin should be documented with their intended installation path and scope before they are added to this repository.

## Install the Herdr layout

Ask the Herdr agent:

```text
Read ~/.config/herdr-app/AGENTS.md, then set up this layout by following the agent steps in its README:
https://github.com/TQKNG/khanh-agent-workspace/tree/main/herdr-layouts/khanh-personal
```

Or run the installer yourself:

```sh
git clone https://github.com/TQKNG/khanh-agent-workspace
cd khanh-agent-workspace/herdr-layouts/khanh-personal
python install.py --activate
```

The package includes `layouts/personal.json` and `layouts/personal.svg`, the `personal` mod (the pages, the PR review window and the sidebar) and the `workspace-chrome-swiss` mod, the local hub in `hub/`, `install.py`, `RECIPE.md`, `ARCHITECTURE.md` and tests.

The Inbox shows your GitHub pull requests, issues and Actions in three tabs grouped by repository; a PR can be reviewed, approved, merged and have its failed checks inspected and re-run from a review window, and an issue can be assigned to Claude, Codex or Copilot in its own worktree and tab.
The Agents page shows each coding agent's instructions, skills, plugins and MCP servers, to edit and turn on or off.
It needs Python 3.9 or newer and the GitHub CLI signed in with `gh auth login`; the agent CLIs are optional.

Set your own workspace name and logo with `python install.py --only-brand --brand-name "<name>" --brand-logo <file>`.
If you installed the previous version of this package, follow "Upgrading from the previous package" in its README.

It does not include Herdr runtime state, project files, credentials, or connection settings.

## Test

Try this prompt:

```text
@arc42 GitBook Docs Create a new GitBook documentation site.
```

For repository-driven documentation, try:

```text
@arc42 GitBook Docs Inspect TQKNG/automation and generate arc42 architecture documentation in GitBook.
```

## Upgrade

Each release has its notes on the repository's [Releases](https://github.com/TQKNG/khanh-agent-workspace/releases) page and in `CHANGELOG.md`; see [RELEASING.md](RELEASING.md) for how versions are made.

Refresh the marketplace after a new version is published:

```powershell
codex plugin marketplace upgrade khanh-plugins
```

Restart the ChatGPT desktop app and verify the installed plugin version.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/arc42-gitbook-docs/plugin.json
plugins/arc42-gitbook-docs/.codex-plugin/plugin.json
plugins/arc42-gitbook-docs/skills/
plugins/arc42-gitbook-docs/references/
plugins/arc42-gitbook-docs/prompts/
skills/repo-scaffold/
skills/graphify/
skills/technical-blog-writing/
.claude/skills/ticket/
plugins/session-token-audit/skills/
herdr-layouts/khanh-personal/layouts/personal.json
herdr-layouts/khanh-personal/mods/personal/
herdr-layouts/khanh-personal/mods/workspace-chrome-swiss/
herdr-layouts/khanh-personal/hub/
herdr-layouts/khanh-personal/install.py
```

The marketplace catalog resolves the plugin path relative to this repository root.

The Herdr package is intentionally outside `plugins/` and is not listed in the Codex marketplace manifest.

It excludes Herdr runtime state such as `shared.json`, `view.json`, `data/`, `window.json`, and `windows.json`.

The layout package has its own tests: `python -m unittest discover -s herdr-layouts/khanh-personal/tests -v` and `node --test herdr-layouts/khanh-personal/tests/*.test.mjs`.

Do not commit GitHub credentials, GitBook credentials, access tokens, or local connection settings.

Review all skills, instructions, and prompts before distribution.

Document any required connectors, permissions, filesystem access, network access, commands, or external services.

## Version 0.3 workflow

Input may be a GitHub repository, plan or idea.
The plugin always asks questions and receives answers before constructing documentation.
Missing required details block writes until resolved or explicitly omitted by the user.
The final output is a six-space GitBook site with reviewable changes and a verification report.

See [site analysis](docs/site-analysis.md), [page contracts](plugins/arc42-gitbook-docs/references/site-blueprint.json), and [test report](docs/test-report.md).

Run the local checks with `python3 -m unittest discover -s tests -v`.
The readiness validator is invoked with `python3 plugins/arc42-gitbook-docs/scripts/validate_session.py session.json --phase write`.
Merge additionally requires approval of the exact reviewed revision.

## License

Original material authored by Khanh Nguyen is available under the [MIT License](LICENSE).
Bundled third-party materials retain their own terms.
The critter pictures under `herdr-layouts/khanh-personal/mods/personal/critters/art/` come from the `herdr-critters` mod.
Its upstream repository does not identify a license, so this MIT grant does not cover them.
The font files and font licenses that shipped with that imported mod are no longer part of this repository.
