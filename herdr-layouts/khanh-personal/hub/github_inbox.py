"""GitHub data for the Herdr cockpit inbox, read through the signed-in `gh` CLI.

Builds the `inbox` view model the cockpit inbox mod expects (sections of PR, review,
ticket and alert rows) plus the on-demand details it fetches (merge readiness,
review threads, an issue's card). No tokens are stored here: `gh` owns the login.

Reads only, apart from `file_issue` (the inbox's "File issue" dialog), the reviews and
merges github_pulls.py sends, and the assignment github_start.py makes when an issue is
given to an agent; each is triggered by the user.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ISSUE_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)$")
MAX_REPOS = 30
CACHE_SECONDS = 55
ERROR_RETRY_SECONDS = 30
RUN_DAYS = 7  # a failed run older than this is history, not news
MAX_RUN_REPOS = 12
RUN_WORKERS = 6
FAILED_RUNS = {"failure", "timed_out", "startup_failure"}
MERGE_METHODS = (
    ("squash", "allow_squash_merge", "Squash and merge"),
    ("merge", "allow_merge_commit", "Create a merge commit"),
    ("rebase", "allow_rebase_merge", "Rebase and merge"),
)


class GitHubError(RuntimeError):
    pass


# ---------------------------------------------------------------------------------------------------------------------
# gh


def gh(args: list[str], timeout: int = 60, stdin: str | None = None) -> str:
    """Runs gh and returns its output; `stdin` is sent to it (a JSON body for `gh api --input -`)."""
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1"}
    try:
        done = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            input=stdin,
            stdin=None if stdin is not None else subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise GitHubError("The GitHub CLI (gh) was not found on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitHubError("GitHub did not answer in time.") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()
        if "gh auth login" in detail or "not logged in" in detail.lower():
            raise GitHubError("gh is not signed in. Run `gh auth login`, then refresh.")
        raise GitHubError(detail.splitlines()[0][:300] if detail else f"gh exited with {done.returncode}")
    return done.stdout


def graphql(query: str, strings: dict[str, str] | None = None, numbers: dict[str, int] | None = None) -> dict:
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in (strings or {}).items():
        args += ["-f", f"{key}={value}"]
    for key, value in (numbers or {}).items():
        args += ["-F", f"{key}={value}"]
    payload = json.loads(gh(args))
    if payload.get("errors") and not payload.get("data"):
        raise GitHubError(payload["errors"][0].get("message", "GitHub returned an error"))
    return payload.get("data") or {}


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers


def age(iso: str | None) -> str:
    if not iso:
        return ""
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    seconds = max(0, (datetime.now(timezone.utc) - then).total_seconds())
    for size, unit in ((365 * 86400, "y"), (30 * 86400, "mo"), (7 * 86400, "w"), (86400, "d"), (3600, "h"), (60, "m")):
        if seconds >= size:
            return f"{int(seconds // size)}{unit}"
    return "now"


def rollup(node: dict) -> str | None:
    commits = (node.get("commits") or {}).get("nodes") or []
    if not commits:
        return None
    return ((commits[0].get("commit") or {}).get("statusCheckRollup") or {}).get("state")


def person(user: dict | None) -> tuple[str, str]:
    user = user or {}
    login = user.get("login") or "ghost"
    return login, user.get("name") or login


def pr_ready(node: dict, ci: str | None) -> dict:
    review = node.get("reviewDecision")
    if node.get("isDraft"):
        return {"state": "draft", "text": "Draft", "tone": "dim"}
    if ci in ("FAILURE", "ERROR"):
        return {"state": "blocked", "text": "Checks are failing", "tone": "bad"}
    if review == "CHANGES_REQUESTED":
        return {"state": "blocked", "text": "Changes requested", "tone": "bad"}
    if node.get("mergeable") == "CONFLICTING":
        return {"state": "blocked", "text": "Merge conflicts", "tone": "bad"}
    if ci in ("PENDING", "EXPECTED"):
        return {"state": "waiting", "text": "Checks running", "tone": "warn"}
    if review == "REVIEW_REQUIRED":
        return {"state": "waiting", "text": "Waiting for review", "tone": "warn"}
    if node.get("mergeStateStatus") == "BLOCKED":
        return {"state": "waiting", "text": "Blocked by branch rules", "tone": "warn"}
    return {"state": "ready", "text": "Ready to merge", "tone": "good"}


def open_act(url: str, label: str = "open", main: bool = True) -> dict:
    return {"label": label, "key": "o", "main": main, "call": {"fn": "open_url", "args": [url]}}


def start_act(url: str) -> dict:
    """Assigns the issue to an agent: the mod asks for the plan (start_plan) and starts only once the person confirms."""
    return {"label": "assign to agent", "key": "s", "main": False, "call": {"fn": "start", "args": [{"id": url}]}}


def review_act(url: str, main: bool) -> dict:
    """Opens the cockpit's review window on the pull request: the mod handles it itself, the hub is not called."""
    return {"label": "review", "key": "r", "main": main, "call": {"fn": "review_pr", "args": [url]}}


def row(kind: str, key: str, path: str, name: str, section: str, **extra) -> dict:
    base = {
        "key": key,
        "path": path,
        "kind": kind,
        "name": name,
        "title": name,
        "section": section,
        "acts": [],
        "text": [],
        "children": [],
        "expand": False,
        "info": [],
    }
    base.update(extra)
    return base


def heading(key: str, title: str, icon: str, children: list[dict], extra: str = "") -> dict:
    return row("plain", key, f"/{key}", title, title, icon=icon, extra=extra, expand=True, children=children)


# ---------------------------------------------------------------------------------------------------------------------
# The inbox view

PR_FIELDS = """
  number title url isDraft updatedAt createdAt headRefName headRefOid baseRefName reviewDecision mergeable mergeStateStatus
  author { login ... on User { name } }
  repository { nameWithOwner }
  commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
  reviewRequests(first: 10) { nodes { requestedReviewer { ... on User { login } ... on Team { name } } } }
"""

ISSUE_FIELDS = """
  number title url updatedAt
  repository { nameWithOwner }
  labels(first: 4) { nodes { name } }
  assignees(first: 3) { nodes { login } }
"""

INBOX_QUERY = (
    """
query($mine: String!, $review: String!, $assigned: String!, $authored: String!, $repos: Int!) {
  viewer {
    login
    repositories(first: $repos, orderBy: {field: PUSHED_AT, direction: DESC}, isArchived: false, isFork: false,
                 ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
      nodes {
        nameWithOwner url
        defaultBranchRef { name target { ... on Commit { statusCheckRollup { state } } } }
      }
    }
  }
  mine: search(type: ISSUE, query: $mine, first: 50) { nodes { ... on PullRequest {"""
    + PR_FIELDS
    + """} } }
  review: search(type: ISSUE, query: $review, first: 50) { nodes { ... on PullRequest {"""
    + PR_FIELDS
    + """} } }
  assigned: search(type: ISSUE, query: $assigned, first: 40) { nodes { ... on Issue {"""
    + ISSUE_FIELDS
    + """} } }
  authored: search(type: ISSUE, query: $authored, first: 40) { nodes { ... on Issue {"""
    + ISSUE_FIELDS
    + """} } }
}
"""
)


def pr_row(node: dict, section: str, kind: str, viewer: str) -> tuple[dict, dict]:
    repo = node["repository"]["nameWithOwner"]
    owner, short = repo.split("/")
    number = node["number"]
    ci = rollup(node)
    review = node.get("reviewDecision")
    ready = pr_ready(node, ci)
    login, display = person(node.get("author"))
    reviewers = [
        (r.get("requestedReviewer") or {}).get("login")
        for r in (node.get("reviewRequests") or {}).get("nodes") or []
    ]
    lead = []
    if node.get("isDraft"):
        lead.append({"icon": "git-pull-request-draft", "tone": "dim"})
    else:
        tone = {"APPROVED": "good", "CHANGES_REQUESTED": "bad"}.get(review)
        lead.append({"icon": "git-pull-request", "tone": tone})
    if ci == "SUCCESS":
        lead.append({"icon": "circle-check", "tone": "good"})
    elif ci in ("FAILURE", "ERROR"):
        lead.append({"icon": "circle-x", "tone": "bad"})
    elif ci in ("PENDING", "EXPECTED"):
        lead.append({"icon": "clock", "tone": "warn"})
    url = node["url"]
    when = age(node.get("updatedAt"))
    pr = row(
        kind,
        url,
        f"/{section}/{owner}.{short}.{number}",
        f"{short}#{number} {node['title']}",
        "Reviews" if kind == "review" else "Your PRs",
        repo=repo,
        cells={
            "ref": f"{short}#{number}",
            "title": node["title"],
            "notes": ready["text"],
            "notes_tone": ready["tone"],
            "title_tone": "dim" if node.get("isDraft") else None,
            "age": when,
            "lead": lead,
        },
        item={
            "url": url,
            "repo": repo,
            "number": number,
            "title": node["title"],
            "branch": node.get("headRefName"),
            "head_sha": node.get("headRefOid"),
            "base": node.get("baseRefName"),
            "author": login,
            "authorName": display,
            "ci": ci,
            "review": review,
            "isDraft": bool(node.get("isDraft")),
            "updatedAt": node.get("updatedAt"),
            "isDirect": viewer in reviewers,
        },
        acts=[review_act(url, main=kind == "review"), open_act(url, main=kind != "review")],
        info=[
            [{"text": repo, "tone": "dim"}],
            [{"text": f"{node.get('headRefName')} into {node.get('baseRefName')}"}],
            [{"text": f"Opened by {login}, updated {when} ago", "tone": "dim"}],
        ],
    )
    return pr, {"url": url, "ready": ready}


def issue_row(node: dict) -> tuple[dict, dict]:
    repo = node["repository"]["nameWithOwner"]
    owner, short = repo.split("/")
    number = node["number"]
    url = node["url"]
    labels = [label["name"] for label in (node.get("labels") or {}).get("nodes") or []]
    status = labels[0] if labels else ""
    ref = f"{short}#{number}" + (f" {status}" if status else "")
    issue = row(
        "ticket",
        url,
        f"/work/{owner}.{short}.{number}",
        f"{short}#{number} {node['title']}",
        "Tickets",
        repo=repo,
        cells={"ref": ref, "title": node["title"], "notes": status, "lead": [{"icon": "circle-dot", "tone": "good"}], "age": age(node.get("updatedAt"))},
        item={"url": url, "repo": repo, "number": number, "title": node["title"]},
        acts=[open_act(url), start_act(url)],
        info=[[{"text": repo, "tone": "dim"}], [{"text": f"Updated {age(node.get('updatedAt'))} ago", "tone": "dim"}]],
    )
    return issue, {"id": url, "url": url, "status": status or "open", "project": repo, "secs": 0, "cost": 0}


def alert_row(repo: dict) -> dict:
    name = repo["nameWithOwner"]
    branch = (repo.get("defaultBranchRef") or {}).get("name") or "default branch"
    actions = f"{repo['url']}/actions"
    return row(
        "alert",
        f"alert:{name}",
        f"/alerts/{name.replace('/', '.')}",
        f"{name}: CI is failing on {branch}",
        "Alerts",
        repo=name,
        text=[
            {"icon": "triangle-alert", "tone": "bad"},
            {"text": name, "bold": True},
            {"text": f"CI is failing on {branch}", "tone": "bad"},
        ],
        acts=[open_act(actions, "open")],
        info=[[{"text": f"The latest commit on {branch} has failing checks."}], [{"text": actions, "tone": "dim"}]],
    )


def run_row(repo: str, run: dict, state: str) -> dict:
    """A workflow run that needs a look: failed, or still going. `state` is "fail" or "running"."""
    owner, short = repo.split("/")
    url = run["html_url"]
    workflow = run.get("name") or "workflow"
    branch = run.get("head_branch") or ""
    when = age(run.get("updated_at") or run.get("created_at"))
    if state == "fail":
        lead, tail = {"icon": "circle-x", "tone": "bad"}, {"text": f"failed {when} ago", "tone": "bad"}
    else:
        lead, tail = {"icon": "clock", "tone": "warn"}, {"text": "running", "tone": "warn"}
    return row(
        "run",
        url,
        f"/runs/{owner}.{short}.{run['id']}",
        f"{short}: {workflow} on {branch}",
        "Runs",
        repo=repo,
        item={"url": url, "repo": repo, "run_id": run["id"], "branch": branch, "state": state},
        text=[lead, {"text": workflow, "bold": True}, {"text": f"{short} · {branch}", "tone": "dim"}, tail],
        acts=[open_act(url)],
        info=[[{"text": repo, "tone": "dim"}], [{"text": f"Run #{run.get('run_number')} · {run.get('event')} · {branch}", "tone": "dim"}]],
    )


def pick_runs(repo: str, runs: list[dict], wanted: set[str]) -> list[dict]:
    """Of a repository's recent runs (newest first), the rows worth showing: the latest run of each workflow on each branch
    the person cares about (the default branch and their open PRs' branches), if it failed recently or is still going."""
    rows, seen = [], set()
    now = time.time()
    for run in runs:
        branch = run.get("head_branch")
        key = (run.get("workflow_id"), branch)
        if branch not in wanted or key in seen:
            continue
        seen.add(key)
        if run.get("status") != "completed":
            rows.append(run_row(repo, run, "running"))
        elif run.get("conclusion") in FAILED_RUNS and now - parse_time(run.get("updated_at") or run.get("created_at")) < RUN_DAYS * 86400:
            rows.append(run_row(repo, run, "fail"))
    return rows


def parse_time(iso: str | None) -> float:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return 0.0


def read_runs(branches: dict[str, set[str]]) -> list[dict]:
    """The runs that need a look in each repository, read side by side. Best effort: a repository whose runs cannot be
    read (no Actions, no access) simply shows none."""

    def one(repo: str) -> list[dict]:
        try:
            runs = json.loads(gh(["api", f"repos/{repo}/actions/runs?per_page=15"], timeout=30)).get("workflow_runs") or []
        except (GitHubError, json.JSONDecodeError):
            return []
        return pick_runs(repo, runs, branches[repo])

    repos = list(branches)[:MAX_RUN_REPOS]
    with ThreadPoolExecutor(max_workers=RUN_WORKERS) as pool:
        return [r for rows in pool.map(one, repos) for r in rows]


def build_inbox() -> dict:
    data = graphql(
        INBOX_QUERY,
        strings={
            "mine": "is:pr is:open author:@me archived:false sort:updated-desc",
            "review": "is:pr is:open review-requested:@me archived:false sort:updated-desc",
            "assigned": "is:issue is:open assignee:@me archived:false sort:updated-desc",
            "authored": "is:issue is:open author:@me archived:false sort:updated-desc",
        },
        numbers={"repos": MAX_REPOS},
    )
    viewer = data["viewer"]["login"]
    prs, ready_by_url, review_rows, work_rows = [], [], [], []
    seen: set[str] = set()

    def pull(nodes: list[dict], section: str, kind: str, into: list[dict]) -> None:
        for node in nodes:
            if not node or "url" not in node or node["url"] in seen:
                continue
            seen.add(node["url"])
            built, ready = pr_row(node, section, kind, viewer)
            into.append(built)
            ready_by_url.append(ready)

    pull(data["review"]["nodes"], "review", "review", review_rows)
    pull(data["mine"]["nodes"], "work", "pr", work_rows)

    tickets = []
    for node in data["assigned"]["nodes"] + data["authored"]["nodes"]:
        if not node or "url" not in node or node["url"] in seen:
            continue
        seen.add(node["url"])
        built, ticket = issue_row(node)
        work_rows.append(built)
        tickets.append(ticket)

    failing = [
        alert_row(repo)
        for repo in data["viewer"]["repositories"]["nodes"]
        if ((((repo.get("defaultBranchRef") or {}).get("target") or {}).get("statusCheckRollup") or {}).get("state")) in ("FAILURE", "ERROR")
    ]

    # Runs are read for the repositories the person has something in, on the branches they care about.
    default_branch = {r["nameWithOwner"]: (r.get("defaultBranchRef") or {}).get("name") for r in data["viewer"]["repositories"]["nodes"]}
    branches: dict[str, set[str]] = {}
    for built in review_rows + work_rows:
        repo = built["repo"]
        branches.setdefault(repo, {default_branch.get(repo)} - {None})
        if built["kind"] in ("pr", "review") and built["item"].get("branch"):
            branches[repo].add(built["item"]["branch"])
    for alert in failing:
        branches.setdefault(alert["repo"], {default_branch.get(alert["repo"])} - {None})
    runs = read_runs(branches)
    runs.sort(key=lambda r: (r["item"]["state"] != "fail", r["repo"]))

    sections = []
    if failing:
        sections.append(heading("alerts", "Alerts", "triangle-alert", failing, "default branch CI is failing"))
    if review_rows:
        sections.append(heading("review", "Reviews", "eye", review_rows, "waiting on you"))
    if work_rows:
        sections.append(heading("work", "Work", "git-pull-request", work_rows))
    if runs:
        sections.append(heading("runs", "Runs", "play", runs, "failing or running"))
    return {
        "state": "ok",
        "updated": datetime.now().strftime("%H:%M"),
        "sections": sections,
        "repos": [r["nameWithOwner"] for r in data["viewer"]["repositories"]["nodes"]],
        "prs": ready_by_url,
        "tickets": tickets,
        "worktrees": [],
        "results": {},
        "errors": [],
    }


def empty_model(message: str) -> dict:
    return {"state": "empty", "message": message, "sections": [], "prs": [], "tickets": [], "worktrees": [], "results": {}, "errors": []}


class InboxSource:
    """The inbox model, rebuilt at most once a minute however many views ask."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.model: dict | None = None
        self.built_at = 0.0
        self.failed_at = 0.0
        self.failure = ""

    def invalidate(self) -> None:
        with self.lock:
            self.built_at = 0.0
            self.failed_at = 0.0

    def get(self) -> dict:
        with self.lock:
            now = time.time()
            if self.model is not None and now - self.built_at < CACHE_SECONDS:
                return self.model
            if self.failure and now - self.failed_at < ERROR_RETRY_SECONDS:
                return empty_model(self.failure)
            try:
                self.model = build_inbox()
                self.built_at = now
                self.failure = ""
            except (GitHubError, json.JSONDecodeError, KeyError) as exc:
                self.failure = str(exc) or "GitHub data could not be read."
                self.failed_at = now
                if self.model is not None:
                    return {**self.model, "errors": [self.failure]}
                return empty_model(self.failure)
            return self.model


# ---------------------------------------------------------------------------------------------------------------------
# Details fetched on demand

PR_DETAIL_QUERY = (
    """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {"""
    + PR_FIELDS
    + """
      additions deletions changedFiles body
      labels(first: 10) { nodes { name color } }
      latestReviews(first: 10) { nodes { state author { login } commit { oid } } }
      autoMergeRequest { mergeMethod }
      reviewThreads(first: 50) { nodes { isResolved comments(first: 1) { nodes { author { login } body path line } } } }
      detail: commits(last: 1) { nodes { commit { statusCheckRollup { state contexts(first: 100) { nodes {
        __typename
        ... on CheckRun { status conclusion }
        ... on StatusContext { state }
      } } } } } }
    }
  }
}
"""
)


def pull_request(args: dict) -> dict:
    repo = str(args.get("repo") or "")
    if not REPO_RE.match(repo):
        raise GitHubError("That PR has no repository.")
    try:
        number = int(args.get("number"))
    except (TypeError, ValueError) as exc:
        raise GitHubError("That PR has no number.") from exc
    owner, name = repo.split("/")
    data = graphql(PR_DETAIL_QUERY, strings={"owner": owner, "name": name}, numbers={"number": number})
    pr = (data.get("repository") or {}).get("pullRequest")
    if not pr:
        raise GitHubError(f"{repo}#{number} was not found.")
    return pr


def check_counts(pr: dict) -> dict:
    counts = {"pass": 0, "fail": 0, "pending": 0, "skip": 0}
    commits = (pr.get("detail") or {}).get("nodes") or []
    contexts = (((commits[0].get("commit") or {}).get("statusCheckRollup") or {}).get("contexts") or {}).get("nodes") if commits else []
    for ctx in contexts or []:
        if ctx.get("__typename") == "CheckRun":
            if ctx.get("status") != "COMPLETED":
                counts["pending"] += 1
            elif ctx.get("conclusion") == "SUCCESS":
                counts["pass"] += 1
            elif ctx.get("conclusion") in ("SKIPPED", "NEUTRAL"):
                counts["skip"] += 1
            else:
                counts["fail"] += 1
        else:
            state = ctx.get("state")
            counts["pass" if state == "SUCCESS" else "pending" if state in ("PENDING", "EXPECTED") else "fail"] += 1
    return counts


def merge_choices(repo: str, ready: dict) -> tuple[list[dict], str]:
    """The ways a pull request can be merged right now, and why none when it cannot: only once GitHub says it is ready."""
    if ready["state"] != "ready":
        return [], f"{ready['text']}: merging is offered once GitHub says the pull request is ready."
    info = json.loads(gh(["api", f"repos/{repo}"]))
    if not (info.get("permissions") or {}).get("push"):
        return [], "You need write access to this repository to merge."
    choices = [{"do": "merge", "method": method, "label": label} for method, flag, label in MERGE_METHODS if info.get(flag)]
    return choices, "" if choices else "This repository allows no merge method."


def fetch_pr_merge(args: dict) -> dict:
    pr = pull_request(args)
    ready = pr_ready(pr, rollup(pr))
    choices, why = merge_choices(str(args["repo"]), ready)
    return {
        "ready": ready,
        "base": pr.get("baseRefName"),
        "choices": choices,
        "why": why,
        "auto": (pr.get("autoMergeRequest") or {}).get("mergeMethod"),
        "card": {
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "files": pr.get("changedFiles", 0),
            "body": pr.get("body") or "",
            "checks": check_counts(pr),
            "reviewers": [
                {"login": (r.get("author") or {}).get("login", "?"), "state": r.get("state")}
                for r in (pr.get("latestReviews") or {}).get("nodes") or []
            ],
            "labels": [{"name": l["name"], "color": l.get("color")} for l in (pr.get("labels") or {}).get("nodes") or []],
        },
    }


def fetch_review_threads(args: dict) -> dict:
    pr = pull_request(args)
    threads = []
    for thread in (pr.get("reviewThreads") or {}).get("nodes") or []:
        if thread.get("isResolved"):
            continue
        comment = ((thread.get("comments") or {}).get("nodes") or [{}])[0]
        threads.append(
            {
                "author": (comment.get("author") or {}).get("login", ""),
                "path": comment.get("path") or "",
                "line": comment.get("line"),
                "body": comment.get("body") or "",
            }
        )
    return {"threads": threads}


def fetch_ticket_card(args: dict) -> dict:
    match = ISSUE_URL_RE.match(str(args.get("id") or ""))
    if not match:
        raise GitHubError("That ticket is not a GitHub issue.")
    owner, name, number = match.groups()
    issue = json.loads(gh(["api", f"repos/{owner}/{name}/issues/{number}"]))
    viewer = gh(["api", "user", "--jq", ".login"]).strip()
    assignees = [a["login"] for a in issue.get("assignees") or []]
    return {
        "state": {"name": "Closed" if issue.get("state") == "closed" else "Open"},
        "states": [],
        "assignee": assignees[0] if assignees else None,
        "mine": viewer in assignees,
        "priority": None,
        "branch": None,
        "labels": [{"name": l["name"], "color": f"#{l.get('color', '888888')}"} for l in issue.get("labels") or []],
        "description": issue.get("body") or "",
    }


def fetch(kind: str, args: dict) -> dict:
    handlers = {"pr_merge": fetch_pr_merge, "review_threads": fetch_review_threads, "ticket_card": fetch_ticket_card}
    try:
        if kind in handlers:
            return handlers[kind](args or {})
        if kind == "failed_tests":
            return {"tests": []}
        if kind == "ci_log":
            return {"lines": [], "message": "Open the PR on GitHub to read the failing job's log."}
        return {"error": f"{kind} is not available from the local GitHub hub."}
    except (GitHubError, json.JSONDecodeError, KeyError) as exc:
        return {"error": str(exc) or f"{kind} failed."}


def file_issue(spec: dict) -> str:
    """Files the issue the dialog shows. An issue type or labels (from a draft) go in one REST call, since `gh issue create` has no
    flag for a type; without them the call is the same as before."""
    title = str(spec.get("title") or "").strip()
    repo = str(spec.get("team") or "").strip()
    body = str(spec.get("description") or "")
    issue_type = str(spec.get("type") or "").strip()
    labels = [str(name).strip() for name in spec.get("labels") or [] if str(name).strip()]
    if not title:
        raise GitHubError("An issue needs a title.")
    if not REPO_RE.match(repo):
        raise GitHubError("Type the repository as owner/name in the Repository field.")
    if issue_type or labels:
        payload = {"title": title, "body": body, **({"type": issue_type} if issue_type else {}), **({"labels": labels} if labels else {})}
        created = json.loads(gh(["api", f"repos/{repo}/issues", "--method", "POST", "--input", "-"], stdin=json.dumps(payload)))
        url = str(created.get("html_url") or "").strip()
        if not url:
            raise GitHubError("GitHub did not return the new issue.")
    else:
        url = gh(["issue", "create", "--repo", repo, "--title", title, "--body", body]).strip()
    return f"Filed {url}"
