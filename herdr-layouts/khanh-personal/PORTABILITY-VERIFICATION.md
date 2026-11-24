# Windows and macOS portability verification

Use this checklist on a clean Windows user profile or VM and a clean macOS user profile or VM.
Record results separately for each operating system.
Do not copy Herdr runtime state, credentials, or agent configuration from another computer.

## 1. Record the environment

Record the date, OS version, CPU architecture, Herdr version, Python version, Git version, Node version, and whether `gh` and agent CLIs are installed.
Record whether the test used an authenticated GitHub CLI account or the isolated unauthenticated smoke test.
Never include access tokens, credential files, private MCP headers, or full agent configuration in the report.

## 2. Run the isolated installer smoke check

From the package directory, choose an empty disposable Herdr home and run:

```sh
python tests/smoke_install.py <empty-herdr-home>
```

On Windows, use `py -3 tests/smoke_install.py <empty-herdr-home>` if `python` does not select Python 3.9 or newer.
The script installs twice, checks idempotence, starts the package hub, and calls its health endpoint.
It removes GitHub token variables and points `gh` at an empty configuration directory, so the check cannot use a personal GitHub login.
The JSON result reports the platform, interpreter versions, hub health, GitHub capability state, and whether Herdr mod checks ran.

## 3. Install into the clean Herdr profile

Install and open Herdr once so it creates its app home.
Clone the repository or download a reviewed package release.
From `herdr-layouts/khanh-personal`, run:

```sh
python install.py --activate
```

On Windows, `py -3 install.py --activate` is also supported.
Complete `gh auth login` only when testing authenticated GitHub features.
Do not reuse another user's Herdr home for this clean-profile check.

## 4. Verify the installed app

Run `herdr-app check` for `khanh-personal` and `khanh-workspace-chrome`.
Run `herdr-app status` and confirm the `personal` layout is active with no app errors.
Capture a screenshot with `herdr-app shot <evidence-path>` and inspect the sidebar, tabs, page icons, status bar, and layout at the normal display scale.
Open Home, Work, Inbox, Agents, Monitor, Routines, Mail, and the queue drawer.
Record which pages have live data and which are intentionally disconnected, as listed in the README.

## 5. Verify optional dependencies and GitHub behavior

With no authenticated `gh`, confirm the Inbox says how to install or sign in and that unrelated layout pages still open.
With Git and no supported agent CLIs, confirm repository worktree actions and agent assignment explain their missing prerequisites.
With one supported agent CLI installed, confirm it appears in the agent picker and the other unavailable agents remain unavailable.
With authenticated `gh`, confirm the Inbox loads pull requests, issues, and Actions without exposing credentials in the UI or logs.
For write actions, use a throwaway repository and throwaway pull request, and verify the confirmation and stale-commit protections before submitting any action.
Do not use a pull request or repository whose state matters for testing file issue, review, merge, or rerun actions.

## 6. Verify recovery and user-data preservation

Run the installer twice and confirm the second run reports no package changes or new backup.
Run `python install.py --rollback --dry-run`, then perform rollback only in the disposable profile.
Confirm rollback restores the previous package version while retaining the user's current settings, shortcuts, brand, credentials, caches, repositories, and worktrees.
Run `python install.py --uninstall --dry-run`, then uninstall only in the disposable profile.
Confirm locally edited package files are reported and preserved, user-modified shortcuts remain, and hub credentials, settings, caches, and virtual environments remain.

## 7. Record the result

| Platform | OS and architecture | Herdr | Python | Smoke check | Live mod checks | Visual and feature checks | Result |
|---|---|---|---|---|---|---|---|
| Windows isolated Herdr home | Windows 10 build 19045, x64 | 0.1.18 | 3.11.9 | Fresh install, repeat install, and hub health passed; GitHub status was `login_required` using an empty CLI config | Both package mods passed staged and installed `herdr-app check` | Not run | Partially verified on 2026-11-24; not a clean OS profile |
| macOS | Pending | Pending | Pending | Pending | Pending | Pending | Not yet verified |

Attach the smoke JSON and a screenshot with personal workspace content removed or obscured.
List each failed step, the exact non-sensitive error, and whether it blocks installation or only an optional feature.
Do not mark a platform verified until its clean-profile install, live mod checks, visual review, and required feature checks have passed.
