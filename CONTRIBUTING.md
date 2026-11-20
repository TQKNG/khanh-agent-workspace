# Contributing to Khanh Agent Workspace

Check existing issues and pull requests before proposing a change.
Keep changes to the Codex plugin, standalone agent resources, and Herdr layout package clearly scoped.
Explain which resource is affected and how a user installs or updates it.

## Work on the plugin

Read [README.md](README.md) for marketplace installation and upgrade instructions.
Run the repository test suite from the root:

```sh
python -m unittest discover -s tests -v
```

When changing a skill, plugin manifest, prompt, or reference, check its paths and describe the behavior you verified.
Do not publish credentials, access tokens, private connection settings, or customer data.

## Work on the Herdr layout

Read [the layout recipe](herdr-layouts/khanh-personal/RECIPE.md) and the Herdr app instructions before changing a packaged layout or mod.
Keep machine-specific runtime state and credentials out of the share package.
For mod changes, run `herdr-app check` on the affected mod and inspect the layout in the app when available.
Run the layout's tests from the root:

```sh
python -m unittest discover -s herdr-layouts/khanh-personal/tests -v
node --test herdr-layouts/khanh-personal/tests/*.test.mjs
```

Do not test write actions (reviews, merges, re-runs) against a pull request you care about.
Use a throwaway pull request, or the fake `gh` the tests use.
State any visual or runtime checks that could not be performed.

## Submit a pull request

Write commit messages, or the pull request title for a squash merge, as [Conventional Commits](https://www.conventionalcommits.org/) such as `feat: …`, `fix: …` or `docs: …`.
Versions and `CHANGELOG.md` are generated from them; see [RELEASING.md](RELEASING.md).

Describe the problem, the affected package, and any related issue.
List automated and manual checks with results.
Include a preview or screenshots for visible Herdr layout changes.
Call out connector, permission, installation, or compatibility changes for reviewers.
