# arc42 Plugin Marketplace

This repository distributes the `arc42-gitbook-docs` plugin through a Git-backed Codex plugin marketplace.

The plugin creates a standard GitBook documentation structure and generates evidence-based arc42 architecture documentation with C4 views from GitHub repositories.

## Included plugin

- `arc42-gitbook-docs` version `0.2.2`

## Requirements

- Codex CLI or Codex in the ChatGPT desktop app.
- Git access to this repository.
- The GitHub plugin installed and connected.
- The GitBook plugin installed and connected.

## Install on another machine

Add this Git-backed marketplace:

```powershell
codex plugin marketplace add TQKNG/arc42-plugin-marketplace --ref v0.2.2
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
```

The marketplace catalog resolves the plugin path relative to this repository root.

Do not commit GitHub credentials, GitBook credentials, access tokens, or local connection settings.
