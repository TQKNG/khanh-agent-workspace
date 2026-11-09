# Codex Plugin Marketplace

This repository distributes reusable Codex plugins through a Git-backed marketplace.

The first included plugin creates a standard GitBook documentation structure and generates evidence-based arc42 architecture documentation with C4 views from GitHub repositories.

## Included plugin

- `arc42-gitbook-docs` version `0.3.0`

## Requirements

- Codex CLI or Codex in the ChatGPT desktop app.
- Git access to this repository.
- The GitHub plugin installed and connected for repository inputs.
- The GitBook plugin installed and connected.

## Install on another machine

Add this Git-backed marketplace:

```powershell
codex plugin marketplace add TQKNG/khanh-agent-workspace --ref main
```

Verify the marketplace registration:

```powershell
codex plugin marketplace list
```

Restart the ChatGPT desktop app.

Open the Plugins directory, select `Khanh Plugins`, and install `arc42 GitBook Docs`.

In Codex CLI, run `/plugins`, select the `Khanh Plugins` source, and install the plugin.

Start a new chat after installation.

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
herdr-layouts/khanh-personal/layouts/personal.json
herdr-layouts/khanh-personal/mods/personal/
```

The marketplace catalog resolves the plugin path relative to this repository root.

## Herdr layout

This repository also contains Khanh's personal Herdr layout.

The Herdr package is intentionally outside `plugins/` and is not listed in the Codex marketplace manifest.

Share or install it from the layout folder:

```text
https://github.com/TQKNG/khanh-agent-workspace/tree/main/herdr-layouts/khanh-personal
```

The package includes the layout, its custom mod, a recipe, and a preview image.

It excludes Herdr runtime state such as `shared.json`, `view.json`, `data/`, `window.json`, and `windows.json`.

Do not commit GitHub credentials, GitBook credentials, access tokens, or local connection settings.

## Version 0.3 workflow

Input may be a GitHub repository, plan or idea.
The plugin always asks questions and receives answers before constructing documentation.
Missing required details block writes until resolved or explicitly omitted by the user.
The final output is a six-space GitBook site with reviewable changes and a verification report.

See [site analysis](docs/site-analysis.md), [page contracts](plugins/arc42-gitbook-docs/references/site-blueprint.json), and [test report](docs/test-report.md).

Run the local checks with `python3 -m unittest discover -s tests -v`.
The readiness validator is invoked with `python3 plugins/arc42-gitbook-docs/scripts/validate_session.py session.json --phase write`.
Merge additionally requires approval of the exact reviewed revision.
