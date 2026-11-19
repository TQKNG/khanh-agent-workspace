"""A pull request's checks: the list, a failed job's log, and re-running the failed jobs, through the signed-in `gh` CLI.

The inbox's review window asks for `pr_checks` (every check run and commit status of the pull request's head, failing
ones first) and `check_log` (the tail of a GitHub Actions job's log). `rerun_failed` re-runs the failed jobs of
workflow runs, only of the commit the person is looking at, like a review or a merge.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from github_inbox import REPO_RE, GitHubError, gh
from github_pulls import get_pull, pinned_sha, reference, require_open_at, submit_lock

KINDS = ("pr_checks", "check_log")
RUN_RE = re.compile(r"/actions/runs/(\d+)")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
STAMP_RE = re.compile(r"^﻿?\d{4}-\d\d-\d\dT[\d:.]+Z ?")
MAX_PAGES = 5
MAX_RUNS = 10
MAX_LOG_LINES = 300
MAX_LOG_CHARS = 400
LOOK_BACK = 150  # how far before the first error a failing step's header is looked for
AFTER_ERROR = 4  # lines kept after the last error
CONCLUSIONS = {"success": "pass", "neutral": "skip", "skipped": "skip"}  # anything else that finished is a failure
STATUSES = {"success": "pass", "pending": "running", "expected": "running"}  # a commit status: anything else failed
WAITING = {"queued", "waiting", "pending", "requested"}
ORDER = {"fail": 0, "running": 1, "queued": 2, "pass": 3, "skip": 4}


def seconds_between(start: str | None, end: str | None) -> int | None:
    try:
        return round((datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds())
    except (AttributeError, ValueError):
        return None


def check_entry(run: dict) -> dict:
    """A check run: the state is pass, fail, skip, running or queued; a GitHub Actions job also has its run and job ids."""
    if run.get("status") in WAITING:
        state = "queued"
    elif run.get("status") != "completed":
        state = "running"
    else:
        state = CONCLUSIONS.get(run.get("conclusion"), "fail")
    actions = (run.get("app") or {}).get("slug") == "github-actions"
    match = RUN_RE.search(run.get("details_url") or "")
    return {
        "name": run.get("name") or "check",
        "state": state,
        "seconds": seconds_between(run.get("started_at"), run.get("completed_at")),
        "url": run.get("html_url") or run.get("details_url"),
        "job_id": run["id"] if actions else None,
        "run_id": int(match[1]) if actions and match else None,
        "note": (run.get("output") or {}).get("title") or "",
    }


def status_entry(status: dict) -> dict:
    """A commit status (what some services report instead of a check run)."""
    return {
        "name": status.get("context") or "status",
        "state": STATUSES.get(status.get("state"), "fail"),
        "seconds": None,
        "url": status.get("target_url"),
        "job_id": None,
        "run_id": None,
        "note": status.get("description") or "",
    }


def fetch_pr_checks(args: dict) -> dict:
    repo, number = reference(args)
    sha = get_pull(repo, number)["head"]["sha"]
    checks: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        data = json.loads(gh(["api", f"repos/{repo}/commits/{sha}/check-runs?per_page=100&page={page}"]))
        checks += [check_entry(run) for run in data.get("check_runs") or []]
        if len(data.get("check_runs") or []) < 100:
            break
    statuses = json.loads(gh(["api", f"repos/{repo}/commits/{sha}/status"])).get("statuses") or []
    checks += [status_entry(s) for s in statuses]
    checks.sort(key=lambda c: (ORDER[c["state"]], c["name"].lower()))
    return {"head_sha": sha, "checks": checks}


# ---------------------------------------------------------------------------------------------------------------------
# A job's log


def clean_log(text: str) -> dict:
    """The part of a job's log worth reading: timestamps and colour codes dropped, groups, warnings and errors marked by
    kind. A failed job shows its failing step (from the step's header to the last error); a job with no error shows the end."""
    lines: list[list[str]] = []
    for raw in text.replace("\r", "").split("\n"):
        line = ANSI_RE.sub("", STAMP_RE.sub("", raw))
        if line.startswith("##[endgroup]"):
            continue
        kind = ""
        for marker, name in (("##[error]", "error"), ("##[group]", "group"), ("##[warning]", "warning")):
            if line.startswith(marker):
                kind, line = name, line[len(marker) :]
        lines.append([line[:MAX_LOG_CHARS], kind])
    while lines and not lines[-1][0].strip():
        lines.pop()
    errors = [i for i, (_text, kind) in enumerate(lines) if kind == "error"]
    if not errors:
        start, end, focus = max(0, len(lines) - MAX_LOG_LINES), len(lines), "end"
    else:
        end = min(len(lines), errors[-1] + 1 + AFTER_ERROR)
        # The failing step's header when it is near; else as much as fits before the last error.
        header = next((i for i in range(errors[0], max(-1, errors[0] - LOOK_BACK), -1) if lines[i][1] == "group"), 0)
        start, focus = max(header, end - MAX_LOG_LINES), "failure"
    return {"lines": lines[start:end], "before": start, "after": len(lines) - end, "focus": focus}


def fetch_check_log(args: dict) -> dict:
    repo = str(args.get("repo") or "")
    if not REPO_RE.match(repo):
        raise GitHubError("That check has no repository.")
    try:
        job = int(args.get("job_id"))
    except (TypeError, ValueError):
        job = 0
    if job < 1:
        raise GitHubError("That check has no job log: it is not a GitHub Actions job.")
    return clean_log(gh(["api", f"repos/{repo}/actions/jobs/{job}/logs"], timeout=90))


def fetch(kind: str, args: dict) -> dict:
    try:
        return fetch_pr_checks(args) if kind == "pr_checks" else fetch_check_log(args)
    except (GitHubError, json.JSONDecodeError, KeyError) as exc:
        return {"error": str(exc) or f"{kind} failed."}


# ---------------------------------------------------------------------------------------------------------------------
# Re-running


def rerun_failed(spec: dict) -> str:
    """Re-runs the failed jobs of workflow runs, all of the commit the person is looking at, on a pull request still open."""
    repo, number = reference(spec)
    sha = pinned_sha(spec.get("head_sha"))
    runs = spec.get("run_ids")
    if not isinstance(runs, list) or not 0 < len(runs) <= MAX_RUNS or not all(isinstance(r, int) and not isinstance(r, bool) and r > 0 for r in runs):
        raise GitHubError(f"Pick between 1 and {MAX_RUNS} workflow runs to re-run.")
    with submit_lock:
        require_open_at(get_pull(repo, number), repo, number, sha)
        for run in runs:
            if json.loads(gh(["api", f"repos/{repo}/actions/runs/{run}"])).get("head_sha") != sha:
                raise GitHubError(f"Run {run} is not of the commit you are looking at.")
        for run in runs:
            gh(["api", "-X", "POST", f"repos/{repo}/actions/runs/{run}/rerun-failed-jobs"])
    return f"Re-running the failed jobs of {len(runs)} workflow run{'' if len(runs) == 1 else 's'} on {repo}#{number}"
