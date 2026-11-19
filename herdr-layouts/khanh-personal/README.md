# Personal layout for the Herdr app

A complete, self-contained setup for the [Herdr app](https://herdr.dev).
It contains the `personal` layout, the mods it needs, and a small local hub that connects its Inbox to GitHub and its Meetings page to Google Calendar.
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
6. Report what is not connected: Google Calendar (needs the steps below) and the pages listed under "What is and is not connected".

Do not edit files under `mods/` of the Herdr home by hand afterwards.
Change this package in the repository and run the installer again instead.

## What you get

- A sidebar with spaces and agents, a top bar with tabs, a status bar, and a center area that switches between your terminals and the Inbox, Meetings and other pages.
- An Inbox page backed by your GitHub account, grouped by repository: your PRs with CI and merge readiness, review requests, your open issues, failing or running workflow runs, and repositories whose default branch CI is failing.
- A review window opened from any PR row: read the diff, comment on lines, approve, request changes or comment, merge, and see why a check failed and re-run it, without leaving Herdr.
- A Meetings page backed by Google Calendar (read only).

## Requirements

- The Herdr app, started at least once (it creates `~/.config/herdr-app`).
- Python 3.9 or newer.
- The [GitHub CLI](https://cli.github.com), signed in with `gh auth login`.
  The hub reads GitHub through it, so no token is stored anywhere in this setup.

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
- runs `herdr-app check` on each mod and starts the hub once to prove it works.

Anything it replaces is moved to `<herdr home>/.install-backups/<time>/` first.
If your `cockpit.json` already points at another cockpit, the installer leaves it alone and says so.

The Herdr app starts the hub by itself when a page needs it.
This is tested on Windows.
On macOS and Linux the mods use the same mechanism as the original cockpit (`env <launcher> hub start`), but that path is not tested yet.
If a page says it cannot reach the hub, run `<herdr home>/cockpit-hub/cockpit-hub hub start` once.

## Herdr version

This setup was built and tested with herdr-app 0.1.16.
The installer prints a warning when your version is different.
It does not stop, because a newer version often works.

Herdr rewrites its shipped mods (`tabs`, `files`, `changes`, `menu`, `prompt`, `shortcut-help`) at every start.
The layout uses them, so a newer Herdr can change how the top bar, file panels or menus look.
If something looks wrong after an upgrade:

- Run `herdr-app check <herdr home>/mods/<mod>` for `personal` and `workspace-chrome-swiss`, and read any error.
- Compare `<herdr home>/AGENTS.md` with the mod code, since that file documents the mod API of your version.

The theme (`paper` and `graphite`) and the fonts (Geist for the UI) ship with Herdr itself, so nothing about them is bundled here.

## Upgrading from the previous package

The previous version of this package shipped a calendar-only hub in `calendar-cockpit/` and the mods `personal-swiss` and `herdr-critters`.
To move to this version:

1. Run `python install.py --activate --force-hub`.
   The installer would otherwise leave your existing `cockpit.json`, which points at the old hub, alone.
2. If you had set up Google Calendar, copy `calendar-cockpit/credentials.json` to `cockpit-hub/credentials.json` and `calendar-cockpit/data/token.json` to `cockpit-hub/data/token.json` in your Herdr home, or run `cockpit-hub auth` again.
3. Delete `calendar-cockpit/`, `mods/personal-swiss` and `mods/herdr-critters` from your Herdr home when you like.
   The installer does not delete anything it did not replace, and nothing uses them any more.

## Google Calendar (optional)

1. Enable the Google Calendar API in a Google Cloud project.
2. Create OAuth credentials of type "Desktop app".
3. Save the downloaded JSON as `<herdr home>/cockpit-hub/credentials.json`.
4. Run `<herdr home>/cockpit-hub/cockpit-hub auth` once (`cockpit-hub.cmd` on Windows).

The hub asks only for the read only `calendar.events.readonly` scope.
Your token is stored in `<herdr home>/cockpit-hub/data/token.json`.
Neither file is ever part of this repository.

## What is and is not connected

Only two pages have a real backend in the bundled hub.

| Page | Backend |
|---|---|
| Inbox | GitHub, through `gh` |
| Meetings | Google Calendar |

The layout also contains pages that belong to the full cockpit: the home dashboard, queue, todo, mail, monitor, routines and runbook.
The bundled hub does not implement their data, so they stay empty or on "Loading".
The status counts and agent lists that come from the hub are stubs for the same reason.

The Inbox writes to GitHub in four places: "File issue" (type the repository as `owner/name` in the team field), reviews, merges and re-runs of failed jobs.
Changing a ticket's status, auto-merge, the merge queue and starting work from a row are not implemented.

## How the Inbox is organized

By default the Inbox has one heading per repository, holding everything about it:

- a failing default-branch alert and failing or running workflow runs first, then review requests, then your PRs, then your tickets;
- a summary on the heading (`CI failing` in red, review requests in amber, then PR and ticket counts) so a folded repository still tells you what is in it;
- repositories that need you come first (failing CI, then review requests, then open PRs), the rest by how recently they were pushed;
- repositories with only tickets start folded, the others start open.

Press `w` to switch to the older arrangement by kind (alerts, reviews, your PRs, runs, tickets).
`/` filters by repository name as well as by title.

Workflow runs are shown only when they matter: the latest run of each workflow on the default branch and on the branches of your open PRs (and the PRs you are asked to review), if it failed in the last seven days or is still going.
They are read for up to twelve repositories at a time, and a repository whose runs cannot be read simply shows none.

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
The write path is covered by unit tests with a fake `gh` (`python -m unittest discover -s tests`), and the inbox's grouping by `node --test tests/`.

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
mods/personal                         the pages (Inbox, Meetings, Home and others), the PR review window and the sidebar
mods/personal/critters/art            the sidebar's critter pictures
mods/workspace-chrome-swiss           the header, shortcuts button and footer (reads your brand)
hub/                                  the local hub (Python) and its launchers
tests/                                unit tests: the hub's GitHub code (Python) and the inbox grouping (Node)
package.json                          marks the JavaScript as ES modules, so `node --test tests/` runs
keys.layout-personal.json             the layout's shortcuts
install.py                            the installer
RECIPE.md                             the brief to rebuild this layout from scratch
```

## Security

- The hub listens on `127.0.0.1` only and requires a random token that the mods read from a local file.
- GitHub access uses your existing `gh` login.
- Do not commit `credentials.json` or `data/token.json`.
  The included `.gitignore` already excludes them.
