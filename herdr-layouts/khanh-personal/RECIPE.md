# Personal

A light "Swiss" workspace for the Herdr app.
A left sidebar lists spaces and agents, a slim top bar holds the tabs, and a center area switches between your terminals and pages such as the Inbox.
A status bar at the bottom counts agents by state.

![Personal](layouts/personal.svg)

## What you see

- Left, 268 px wide, background `chrome`: a 46 px brand block (the user's workspace name and logo from `brand.json`, search, sidebar toggle), the sidebar page (page icons, agents, spaces) and a 69 px footer (settings, add machine).
- Top, 42 px: the tab pills, a 52 px notification bell, and a 48 px shortcuts button.
- Center: a stack of pages inside rounded 6 px cards with a 1 px `border`: home, work (terminals), inbox, agents, monitor, routines and mail.
- Bottom, 34 px: the status bar.
- Right edge: a floating queue drawer that peeks 44 px and slides out on hover.
- Theme: `paper` in light mode and `graphite` in dark mode, accent `#D71920`, UI font Geist.

## How it behaves

- Agent statuses `working`, `blocked`, `done` and `idle` show as dots and counts in the sidebar, the bell and the status bar.
- The Inbox has three tabs, Pull requests (your PRs and review requests), Issues (assigned to you or opened by you) and Actions (failing or running runs, and repositories whose default branch CI fails), switched with a click or `1` to `3` and remembered.
  Enter opens the row on GitHub, `tab` toggles the details panel, `/` filters the tab, and `R` refreshes.
- Inside a tab the rows are grouped by repository: one unfolded heading per repo with a summary, repos that need you first.
  `w` switches to the arrangement by kind.
- Its text is a step larger than the kit's (14 px content, 13 px secondary, 12 px small labels), with rows of 38 px.
- `s` on an issue assigns it to an agent: a dialog shows the plan and an Agent dropdown (Claude, Codex, Copilot, with their marks from Herdr's `icons/`), then the hub makes a worktree from `origin/<default branch>` in Herdr's `worktrees.directory` and assigns the issue, and the Inbox opens the agent in a background tab with `tab.new`.
  The issue's row then shows the agent and its state.
- Hovering a PR shows its checks, reviewers, labels and unresolved review threads.
- `r` on a PR row opens a review window: the diff with line comments, a Conversation tab, a Checks tab, the verdicts approve (`a`), request changes (`x`) and comment (`m`), and merge (`M`).
  The Checks tab lists check runs and statuses, shows a failed Actions job's failing step, and re-runs the failed jobs after a confirmation.
  Each verdict and merge asks first, listing failing checks, unresolved threads and drafts, and is pinned to the commit that was read.
  Merge is offered only when GitHub says the pull request is ready, in the methods the repository allows.
- The Agents page draws a trading card per coding agent (Claude, Codex, Copilot): a frame in the agent's colour, a gradient artwork window with a diagonal foil and the agent's mark from Herdr's `icons/`, the skill count as its "HP", four "moves" (instructions, skills, plugins, MCP servers) and a footer with what needs a look.
  Under the picked card, tabs list its instructions, skills, plugins and MCP servers, from the hub's `agent_profiles`.
- Shortcuts in the layout: `cmd-alt-0` Home, `cmd-alt-1` Inbox, `cmd-alt-2` Agents, `cmd-alt-3` the terminals, `cmd-alt-5` to `cmd-alt-7` Monitor, Routines and Mail, and `cmd-r` refreshes.

## Built from

- `layouts/personal.json`: a root row with a `sidebar` column, then a `main-area` column holding the `topbar` row, the `center` stack and the `status` block.
- Mods of its own: `personal` (the pages and the sidebar, selected with `props.app`) and `workspace-chrome-swiss` (the brand block and footer).
- Herdr's shipped mods: `tabs`, `files`, `changes`, `menu`, `prompt` and `help`.
- A local hub, started by the mods with `<cockpit.json bin> hub start`, which prints `{port, token}` as JSON and keeps running.
  The mods talk to it over TCP on `127.0.0.1` with one JSON message per line.
- The hub serves the view `inbox`, answers `fetch` for `pr_merge`, `review_threads`, `ticket_card`, `pr_diff`, `pr_checks`, `check_log`, `start_plan`, `issue_draft` and `agent_profiles`, and handles the actions `request_refresh`, `file_issue`, `submit_review`, `merge`, `rerun_failed`, `start` and `open_url`.
  The inbox reads GitHub through `gh api graphql`.

## Watch out

- In the Windows build of the Herdr app, `Buffer#toString` returns an empty string.
  The mods' `hub.js` therefore decodes bytes by hand, and a fresh build that uses `Buffer` will fail with "Unexpected end of JSON input".
- Windows has no `env` program, so `hub.js` runs the launcher directly there.
- Page code must not be copied from the stock cockpit mod without these two changes.
- A review is posted with `commit_id` set to the head the window read, and a merge is sent with `sha` set to it.
  The hub refuses either when the pull request's head moved since, when it is not open, or when an approval is of the viewer's own PR, and refuses a merge of a draft.
  Never remove those checks: they are what stops a verdict or a merge on code that was not seen.
- A job's log is cut to its failing step (header to last error line), else its end, at 300 lines of 400 characters, because logs can be megabytes.
- A re-run is refused unless every workflow run belongs to the commit the person is looking at.
- Every inbox row carries its `repo`, because the grouping is done in the mod (`inbox-groups.js`, pure functions) from the hub's rows by kind.
- A workflow run is a row only when it needs a look (latest of its workflow on a branch that matters, failed within seven days or running), so the Inbox does not fill with green history.
- Every inbox PR row carries `head_sha`, because the inbox's merge dialog pins the merge to the commit the row showed.
- The diff view takes lines as `[kind, old number, new number, [[text]]]` with kind `" "`, `+`, `-`, `@` (hunk header) or `!` (a note), and a comment on a removed line is sent with side LEFT.
- The hub must print exactly one JSON line from `hub start` and then exit, leaving the server detached.
- On macOS and Linux the mods start the hub with `HOME` set to its own folder, so the hub must put back the account's home (from the password database) before running `gh` or `git`, or `gh` reports it is not signed in.
- Commands a mod sends to itself start with its own name (`personal.go:inbox`): Herdr delivers `<mod>.<command>` only to a mod of that name.
- `start` takes only an agent's id from the mod; the command is the hub's own, and the agent's task names the issue but never carries its text.
- `agent_profiles` keeps only an MCP server's name, transport, state and URL host: its environment, headers and arguments can hold keys.
- Pages for mail, monitor, routines, queue and home need hub views this hub does not serve.
- The sidebar's critter pictures are files named `sprite-<critter>-<status>.svg` in `mods/personal/critters/art`, and the folder must ship with the layout.
- The brand is read from `<herdr home>/brand.json` (`name`, `logo`, `shortcut_logo`) every four seconds, and logo paths must stay inside the Herdr home.
- Logo files carry a content hash in their name, because Herdr caches images by path and a replaced logo would otherwise not show.
- Without `brand.json` the header shows "Workspace" with an initial tile, and the shortcuts button shows a "?".
- Never ship a personal logo or name inside the mod.
- Never ship another product's logo either: the Agents page takes Herdr's (`icons/`), which the hub redraws sharp into its cache, and falls back to the kit's robot icon.
- The hub must import on Python 3.9 (macOS's own): anything newer, such as `tomllib`, is imported with a fallback.

## Done when

- `herdr-app check` passes for `personal` and `workspace-chrome-swiss`.
- `herdr-app status` reports no errors with the layout active.
- `cockpit-hub hub start` prints a JSON line with a port and exits, and a process stays running.
- The Inbox page shows your open PRs and issues within a few seconds, with no error text.
- Stopping the hub process makes the app start it again within about ten seconds.
- Running `python install.py` twice changes nothing the second time.
- Running `python install.py --only-brand --brand-name X` changes the header text within about ten seconds, with no restart.
- The sidebar shows critter pictures, not blank squares.
- `python -m unittest discover -s tests` and `node --test tests/*.test.mjs` pass, on Python 3.9 as well as the newest.
- `tests/test_package.py` passes: every icon and picture the mods name is in the package, every page the sidebar, palette, side panel and shortcuts reach is in the layout, every hub module is installed, and a fresh install is complete.
- Installed with no `gh`, no agent CLIs and no clones, the hub still starts: the Inbox says `gh` is missing, the Agents page shows three grey cards, and nothing raises.
- The Inbox's three tabs show their counts, `1` to `3` switch them, and each shows one heading per repository, failing ones first.
- `s` on an issue shows the plan with no blockers when its clone exists, and Cancel creates nothing.
- `r` on a PR row shows its diff, `x` and `M` ask before sending, and nothing is sent until the dialog is confirmed.
- A draft PR, or one with failing checks, offers no merge method and says why.
- The Checks tab shows a failing check's reason; a failed Actions job shows its failing step, and Re-run failed asks first.
