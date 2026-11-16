# Khanh Agent Workspace

This repository contains reusable agent skills, instructions, prompts, Codex plugins, and Herdr workspace layouts.

The Codex marketplace distributes `arc42-gitbook-docs` and `session-token-audit`.

The repository is also a source for reusable agent guidance that can be included in future plugins or used as shared project resources.

The Herdr package distributes Khanh's personal cockpit layout and its custom mod.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and pull request guidance.

Repository: <https://github.com/TQKNG/khanh-agent-workspace>

## Contents

- Codex plugin marketplace: `.agents/plugins/marketplace.json`
- Codex plugin: `plugins/arc42-gitbook-docs/`
- Standalone skills: `skills/repo-scaffold/`, `skills/graphify/`, and `skills/technical-blog-writing/`
- Claude and Herdr issue skill: `.claude/skills/ticket/`
- Session audit plugin: `plugins/session-token-audit/`
- Agent skills and instructions: `plugins/*/skills/` and `plugins/*/references/`
- Agent prompts: `plugins/*/prompts/` when a plugin provides reusable prompts
- Herdr layout package: `herdr-layouts/khanh-personal/`

## Included plugin

- `arc42-gitbook-docs` version `0.3.0`
- `session-token-audit` version `0.1.0`

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
Read ~/.config/herdr-app/AGENTS.md, then add this layout:
https://github.com/TQKNG/khanh-agent-workspace/tree/main/herdr-layouts/khanh-personal
```

The package includes `layouts/personal.json`, `layouts/personal.svg`, the `personal` mod, `RECIPE.md`, and `preview.png`.

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
```

The marketplace catalog resolves the plugin path relative to this repository root.

The Herdr package is intentionally outside `plugins/` and is not listed in the Codex marketplace manifest.

It excludes Herdr runtime state such as `shared.json`, `view.json`, `data/`, `window.json`, and `windows.json`.

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
Bundled third-party materials retain their own terms, including the font licenses under `herdr-layouts/khanh-personal/mods/herdr-critters/fonts/`.
The `herdr-critters` upstream repository does not identify a license, so this MIT grant does not cover that imported mod.
