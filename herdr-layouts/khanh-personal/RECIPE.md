# Khanh Personal Herdr Layout

This package adds Khanh's personal cockpit layout to Herdr.

## What it includes

- A `personal` layout with a cockpit sidebar, home board, agent view, work area, inbox, runbook, todo, meetings, monitor, routines, mail, and status areas.
- The `personal` mod and its local icons.
- The layout preview and source files needed to install the package.

## Install

Ask the Herdr agent:

> Read `~/.config/herdr-app/AGENTS.md`, then add this layout: `https://github.com/TQKNG/khanh-agent-workspace/tree/main/herdr-layouts/khanh-personal`

The layout is selected with `Ctrl+Shift+L` or `herdr-app do layout.switch '{"name":"personal"}'`.

## Local capabilities

The `personal` mod reads local configuration and project files to populate its views.

It can run local commands such as Git, editors, and Herdr commands through the app's trusted mod API.

It does not include Khanh's runtime state, project files, credentials, or connection settings.

## Package contents

```text
layouts/personal.json
layouts/personal.svg
mods/personal/
preview.png
```

## Validation

Run the following command after installing or changing the mod:

```powershell
herdr-app check "$env:USERPROFILE\.config\herdr-app\mods\personal"
```
