# Personal layout for the Herdr app

A complete, self-contained setup for the [Herdr app](https://herdr.dev).
It contains the `personal` layout, the mods it needs, and a small local hub that connects its Inbox to GitHub.
Nothing in it depends on the author's machine.

## For an AI agent: set this up on a new machine

Follow these steps in order.
Stop and report if a step fails, instead of working around it.

1. Make sure the Herdr app is installed and has been started once, so `~/.config/herdr-app` exists.
   Read `~/.config/herdr-app/AGENTS.md` if you need to understand the app's files.
2. Check the prerequisites:
   - `python --version` reports 3.9 or newer (on Windows `py -3 --version` also works).
   - `herdr-app --version` works, and `gh --version` works.
   - `gh auth status` shows a signed-in account. If not, ask the user to run `gh auth login`, because it is interactive.
3. Clone `https://github.com/TQKNG/khanh-agent-workspace`, go to `herdr-layouts/khanh-personal` and run `python install.py --activate`.
4. Ask the user for their workspace name and logo, then run:
   `python install.py --only-brand --brand-name "<name>" --brand-logo <path>`
   If they have none, skip this step. The header then shows "Workspace".
5. Verify:
   - The installer's `herdr-app check` lines for both mods show no errors.
   - `herdr-app status` shows `"layout": "personal"` and `"errors": []`.
   - The installer printed `hub started on 127.0.0.1:<port>`.
   - Open the Inbox page from the page icons at the top of the sidebar and confirm it lists the user's GitHub PRs and issues without error text.
6. Report what is not connected: the pages listed under "What is and is not connected".

Do not edit files under `mods/` of the Herdr home by hand afterwards.
Change this package in the repository and run the installer again instead.

## What you get

- A sidebar with spaces and agents, a top bar with tabs, a status bar, and a center area that switches between your terminals, the Inbox and the other pages.
- An Inbox page backed by your GitHub account, with a tab each for pull requests, issues and Actions, each grouped by repository: your PRs with CI and merge readiness, review requests, your open issues, failing or running workflow runs, and repositories whose default branch CI is failing.
- A review window opened from any PR row: read the diff, comment on lines, approve, request changes or comment, merge, and see why a check failed and re-run it, without leaving Herdr.
- An Agents page: a trading card each for Claude, Codex and Copilot, and under the picked one its instructions, skills, plugins and MCP servers, read from this machine.
- "Assign to agent" on any issue: a fresh worktree and a Claude, Codex or Copilot session in its own tab, working towards a pull request.

## Requirements

- The Herdr app, started at least once (it creates `~/.config/herdr-app`).
- Python 3.9 or newer (the one macOS ships works).
  Turning Codex's skills, plugins and MCP servers on and off also needs Python 3.11 or the `tomli` package; without either the Agents page still shows Codex, with its switches off and a note saying why.
- The [GitHub CLI](https://cli.github.com), signed in with `gh auth login`.
  The hub reads GitHub through it, so no token is stored anywhere in this setup.
  Without it the Inbox says so and the rest of the layout works.
- Optional: Claude Code, Codex and GitHub Copilot CLI, for the Agents page and for "Assign to agent".
  One that is not installed shows as a grey card, and is left out of the agent picker.

### Agent card usage readings

Codex usage is read from local session logs.
Claude usage is captured from Claude Code's documented status-line JSON after a session receives its first API response.
To enable it, add `"statusLine": {"type": "command", "command": "python3 <herdr home>/cockpit-hub/claude_status.py"}` to `~/.claude/settings.json`, replacing `<herdr home>` with the installed Herdr home.
If a status line is already configured, incorporate the capture script into that command so the existing display is preserved.
Copilot usage requires the optional official Python SDK: create `<herdr home>/cockpit-hub/.venv` and install `github-copilot-sdk` in it.
The reader uses the signed-in Copilot CLI account and shows a bar only when the SDK returns a current finite quota.
When a provider has no current reading, the card shows an empty track with an explanation instead of treating missing data as zero remaining.

## Install

```sh
git clone https://github.com/TQKNG/khanh-agent-workspace
cd khanh-agent-workspace/herdr-layouts/khanh-personal
python install.py --activate
```

On Windows, use `python install.py --activate` as well.
Use `--home DIR` for a different Herdr home, `--dry-run` to preview, and `--force-hub` to replace an existing `cockpit.json`.

The installer:

- copies the layout and the mods `personal` and `workspace-chrome-swiss`,
- installs the hub into `<herdr home>/cockpit-hub` and writes `cockpit.json` so the mods find it,
- adds the layout's shortcuts to `keys.json` without replacing any key you already have,
- keeps worktrees in `<herdr home>/worktrees` by setting Herdr's `worktrees.directory` in `settings.json`, unless you already chose a folder,
- runs `herdr-app check` on each mod and starts the hub once to prove it works.

Anything it replaces is moved to `<herdr home>/.install-backups/<time>/` first.
If your `cockpit.json` already points at another cockpit, the installer leaves it alone and says so.

The Herdr app starts the hub by itself when a page needs it.
This is tested on Windows and macOS.
On macOS and Linux the mods start it with `HOME` set to the hub's folder; the hub puts back the account's real home, so `gh` finds its login and `git` its config.
If a page says it cannot reach the hub, run `<herdr home>/cockpit-hub/cockpit-hub hub start` once.

## Herdr version

This setup was built and tested with herdr-app 0.1.16.
The installer prints a warning when your version is different.
It does not stop, because a newer version often works.

Herdr rewrites its shipped mods at every start.
The layout shows `tabs`, `files` and `changes` and opens `help` and `picker`, so a newer Herdr can change how the top bar, file panels or menus look.
The installer names any of them a Herdr version lacks, and that part of the window then stays empty rather than failing.
The agents' logos on the Agents page are Herdr's too (`icons/claude.svg`, `codex.svg`, `copilot.svg`); a Herdr without one shows a robot icon in its place.
If something looks wrong after an upgrade:

- Run `herdr-app check <herdr home>/mods/<mod>` for `personal` and `workspace-chrome-swiss`, and read any error.
- Compare `<herdr home>/AGENTS.md` with the mod code, since that file documents the mod API of your version.

The theme (`paper` and `graphite`) and the fonts (Geist for the UI) ship with Herdr itself, so nothing about them is bundled here.

## Upgrading from the previous package

Earlier versions of this package shipped a calendar-only hub in `calendar-cockpit/`, the mods `personal-swiss` and `herdr-critters`, and the To-do, Runbook and Meetings pages (with Google Calendar in the hub).
To move to this version:

1. Run `python install.py --activate --force-hub`.
   The installer would otherwise leave your existing `cockpit.json`, which points at the old hub, alone.
   It also fixes the layout's old shortcuts that pointed at pages it does not have, and keeps any shortcut you changed.
2. Delete `calendar-cockpit/`, `mods/personal-swiss` and `mods/herdr-critters` from your Herdr home when you like, and `cockpit-hub/credentials.json` and `cockpit-hub/data/` if you had set up Google Calendar.
   The installer does not delete anything it did not replace, and nothing uses them any more.

## What is and is not connected

Only the Inbox has a real backend in the bundled hub: GitHub, through `gh`.

The layout also contains pages that belong to the full cockpit: the home dashboard, queue, mail, monitor and routines.
The bundled hub does not implement their data, so they stay empty or on "Loading".
The status counts and agent lists that come from the hub are stubs for the same reason.

The Inbox writes to GitHub in five places: "File issue" (type the repository as `owner/name`), reviews, merges, re-runs of failed jobs, and assigning an issue to you when you give it to an agent.
"File issue" can also draft the issue from a short idea: an agent (Claude or Codex) writes the title, body and type, using the `github-issues` skill when it is installed in `~/.agents/skills/github-issues`.
The draft is shown for editing, and nothing is posted until you click "File it".
Changing an issue's status, auto-merge and the merge queue are not implemented.

## How the Inbox is organized

The Inbox has three tabs, each with its count; click one or press `1`, `2` or `3`, and the Inbox remembers the last one:

- **Pull requests**: your open PRs and the ones you are asked to review;
- **Issues**: open issues assigned to you or opened by you;
- **Actions**: failing or running workflow runs, and repositories whose default branch CI is failing.

Inside a tab there is one heading per repository, all unfolded:

- what is wrong first (a failing default branch, failing runs), then review requests, then your PRs;
- a summary on the heading (`CI failing` in red, review requests in amber, then PR and issue counts);
- repositories that need you come first (failing CI, then review requests, then open PRs), the rest by how recently they were pushed.

Press `w` to switch to the older arrangement by kind within the tab.
`/` filters the tab by repository name as well as by title.

Workflow runs are shown only when they matter: the latest run of each workflow on the default branch and on the branches of your open PRs (and the PRs you are asked to review), if it failed in the last seven days or is still going.
They are read for up to twelve repositories at a time, and a repository whose runs cannot be read simply shows none.

## The Agents page

`cmd-alt-2` (or the bot icon in the sidebar) shows a card for each coding agent: its version, how many skills, plugins and MCP servers it has, and what needs a look (MCP servers waiting for a sign-in, anything that could not be read).
Click a card or press `1` to `3` to pick an agent, and `i`, `s`, `p` or `m` to show its instructions, skills, plugins or MCP servers; `R` reads everything again.

| | Instructions | Skills | Plugins and MCP servers |
|---|---|---|---|
| Claude | `~/.claude/CLAUDE.md` | `~/.claude/skills` (yours and synced from claude.ai) and its plugins' skills | `claude plugin list`, `claude mcp list` |
| Codex | `~/.codex/AGENTS.md` | `~/.codex/skills` and `~/.agents/skills`, marked off when `config.toml` turns them off | `codex plugin list`, `codex mcp list` |
| Copilot | `~/.copilot/copilot-instructions.md` | `copilot skill list` | `copilot plugin list`, `copilot mcp list` |

It also changes them:

- **Instructions and skills**: `e` (or Edit) opens the instructions file in Herdr's editor on the page, and the pencil on a skill opens its `SKILL.md`; `⌘S` saves, `esc` closes (twice with unsaved edits).
  A save is refused when the file changed on disk since it was opened, so an agent's own edit is never overwritten; a missing instructions file can be created.
- **On and off**: skills, plugins and MCP servers all show the same enabled or disabled badge (an MCP server also its connection state), enabled first, with a switch wherever the agent can turn the item on or off:

  | | Skills | Plugins | MCP servers |
  |---|---|---|---|
  | Claude | no switch (Claude has none for one skill) | `claude plugin enable\|disable` | no switch (`claude mcp` has none) |
  | Codex | `config.toml` | `config.toml` | `config.toml`, for servers it defines (a plugin's server follows its plugin) |
  | Copilot | `copilot skill enable\|disable` | `copilot plugin enable\|disable` | `copilot mcp enable\|disable` |

  Codex has no such commands, so the hub changes the one `enabled` value in `~/.codex/config.toml`, after a daily backup (`config.toml.bak-cockpit-<date>`), and only when the file still parses to what it was with just that value changed.
- Changes apply to sessions started afterwards; an agent already running keeps what it loaded.

An MCP server shows its name, transport, state and the host of its URL, never its environment, headers, arguments or tokens.
`claude mcp list` checks every server, so the hub keeps the result five minutes.
The cards' logos are Herdr's own (`icons/`), redrawn by the hub at 256 px into `cockpit-hub/cache/marks/`, because Herdr's files are sized for 16 px and blur when scaled up.

## Assigning an issue to an agent

Select an issue and press `s` (or click its bot icon), pick the agent, and confirm:

1. A dialog shows the plan first: the local clone, the branch `issue-<n>-<title>` from `origin/<default branch>`, the new worktree, assigning the issue to you, and the tab that opens.
   It says what stops it instead (no local clone, the worktree or branch already exists, the issue is closed, no agent installed) and keeps Start disabled.
2. The **Agent** dropdown offers Claude, Codex and Copilot, with their marks; `1`, `2` and `3` pick one, and the next dialog opens on the last one picked.
   One that is not installed is left out and named.
3. On Start the hub fetches the repository, creates the branch and the worktree, and assigns the issue to you on GitHub; the Inbox opens the tab `issue-<n>` in the background with the agent and its task.
4. The issue's row then shows that agent and its state (working, blocked, done); a click goes to it, and `s` on that issue goes to it instead of starting a second one.

The worktree goes where Herdr's own worktree feature puts them, `<worktrees.directory>/<clone folder>/<branch>` (the installer sets `worktrees.directory` to `<herdr home>/worktrees`), so Herdr lists it too.
The local clone is found by its `origin`, under `~/Documents/Development/Repositories`, `~/Developer`, `~/code`, `~/src`, `~/projects`, `~/repos` and `~/git`.

The agent's task is `hub/worker-prompt.md`: the issue's address and the rules, never the issue's own text.
It reads the issue itself and treats it as untrusted, follows the repository's own instructions, tests, commits, opens a pull request that closes the issue, and never merges.

`<herdr home>/cockpit-hub/settings.json` (optional, never overwritten) changes the defaults:

```json
{ "repos": { "owner/name": "~/path/to/clone" }, "roots": ["~/work"], "agent": "codex", "agents": { "claude": ["claude", "--model", "opus"] } }
```

## Reviewing a pull request

Select a PR row and press `r` (or click the eye icon).
On a row under Reviews, `enter` opens it too.

- **Files** tab: the diff, with `j`/`k` to move, `c` to comment on a line, `s` for side by side and `z` to fold.
- **Conversation** tab: the description, who reviewed, and the unresolved threads (click one to jump to its file).
- **Checks** tab: every check run and commit status of the PR's head, failing ones first (`j`/`k` to move).
  The first failing job opens by itself.
- `1`, `2` and `3` switch tabs.
- `a` approves, `x` requests changes, `m` leaves a comment review, `M` (shift-m) merges, `r` reads the pull request again, `o` opens it on GitHub, `esc` closes the window.

Two rules keep a verdict honest:

- Every verdict asks first.
  The dialog lists what GitHub says about the PR (failing or running checks, unresolved threads, a draft, an older review of yours) and takes an optional summary.
  A request for changes needs a summary.
- The verdict is pinned to the commit you read.
  The hub reads the PR's head again when you send it and refuses if the author pushed in between.
  The window then offers to read the new commits, and your line comments stay on the lines that still exist.

You cannot approve your own PR or review one that is closed or merged, and those buttons say why.
Your `gh` login needs permission to review on that repository.

## Checks and re-running

The Checks tab lists the PR's check runs (GitHub Actions jobs and other apps) and commit statuses (what services such as Vercel report), with their state and duration.
It reads again every ten seconds while something is still running.

- Selecting a GitHub Actions job shows its log.
  For a failed job the log starts at the failing step's header and runs to the last error line, with the error lines in red, so the reason is on screen.
  A job without errors shows the end of its log, or all of it when it is short.
  Only the last 300 lines are drawn, and the pane says how many are not shown.
- Other checks have no log here: their note and an Open button take you to the service's page.
- **Re-run failed** restarts the failed jobs of the workflow runs that failed (not the ones that passed).
  It asks first, lists the jobs, and is pinned to the commit you are looking at: the hub refuses when the author pushed since, or when a run belongs to another commit.
  It is disabled when no GitHub Actions job failed, with the reason.
- Your `gh` login needs permission to re-run workflows on that repository.

## Merging a pull request

Press `M` in the review window, or `M` on a row in the Inbox, then pick a method and confirm.

- Merging is offered only when GitHub says the PR is ready: not a draft, checks passing, no changes requested, no conflicts, and the branch rules satisfied.
  Otherwise the button is disabled and says what is missing (for example "Waiting for review").
- The methods are the ones the repository allows: squash, merge commit and rebase.
  You need write access to the repository.
- The merge is pinned to the commit you saw, like a review.
  The hub refuses it when the branch moved, and GitHub is sent the commit as well (`sha`), so a push right after the check is refused too.
- Admin overrides of branch rules, auto-merge and the merge queue are not offered.
  On a repository that requires a review, someone other than the author has to approve first, because you cannot approve your own PR.
The write path is covered by unit tests with a fake `gh` (`python -m unittest discover -s tests`), and the inbox's grouping by `node --test tests/*.test.mjs`.

## Your own name and logo

The sidebar header shows a workspace name and a logo, and the top-right button shows a second image.
They come from your Herdr home, not from this repository, so each user sets their own:

```sh
python install.py --only-brand --brand-name "Acme Workspace" --brand-logo path/to/logo.png
```

- `--brand-logo` accepts png, jpg, webp or svg.
- `--brand-shortcut-logo` sets the image on the top-right button.
  Without it the button uses the logo.
- You can also pass these flags on the full install.
- Without any brand, the header shows "Workspace" with an initial tile, and the button shows a "?".

The installer copies the logo to `<herdr home>/brand/` and writes `<herdr home>/brand.json`:

```json
{ "name": "Acme Workspace", "logo": "brand/logo-1a2b3c4d.png", "shortcut_logo": "brand/shortcut-logo-5e6f7a8b.png" }
```

You can edit that file by hand as well.
The app picks up a change within a few seconds, with no restart.
Logo paths are relative to the Herdr home, and the name is cut at 40 characters.
Reinstalling never overwrites your brand unless you pass brand flags.

## Critter pictures

The sidebar draws small critter pictures from `mods/personal/critters/art`.
That folder is included, so the layout is complete on a fresh install.
Replace the files there to change them, keeping the same file names.
The pictures come from the herdr-critters mod, whose upstream repository does not identify a license, so the repository's MIT license does not cover them.

## Layout of this package

```
layouts/personal.json, personal.svg   the layout and its settings preview
mods/personal                         the pages (Inbox, Agents, Home and others), the PR review window and the sidebar
mods/personal/critters/art            the sidebar's critter pictures
mods/workspace-chrome-swiss           the header, shortcuts button and footer (reads your brand)
hub/                                  the local hub (Python), its launchers, and the agent's task (worker-prompt.md)
tests/                                unit tests: the hub's GitHub code, the issue start, the agent profiles and the installer, and the package itself
                                      (every asset it names is in it, every page it links to exists, a fresh install is complete) (Python);
                                      the inbox's tabs and grouping (Node)
package.json                          marks the JavaScript as ES modules, so `node --test tests/*.test.mjs` runs
keys.layout-personal.json             the layout's shortcuts
install.py                            the installer
RECIPE.md                             the brief to rebuild this layout from scratch
```

## Security

- The hub listens on `127.0.0.1` only and requires a random token that the mods read from a local file.
- GitHub access uses your existing `gh` login.
- An agent started from the Inbox gets the issue's address, never its text, and is told to treat what it reads there as untrusted.
  The hub accepts only an agent's name from the Inbox, never a command.
- An earlier version kept a Google token in `cockpit-hub/data/`; the included `.gitignore` still excludes `credentials.json` and `data/`.
