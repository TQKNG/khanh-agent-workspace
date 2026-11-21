"""Reading a pull request's changes, reviewing it and merging it, through the signed-in `gh` CLI.

The inbox's review window asks for `pr_diff`: the changes shaped as the cockpit diff view draws them, pinned to the
commit they were read at. It then sends one `submit_review`: a verdict (approve, request changes or comment) with line
comments. A review or a merge is refused when the pull request's head moved since the person read it, so neither is
ever done on code that was not seen. GitHub is told the commit too (`commit_id` for a review, `sha` for a merge).
"""

from __future__ import annotations

import json
import re
import threading

from github_inbox import MERGE_METHODS, REPO_RE, GitHubError, check_counts, gh, merge_choices, pr_ready, pull_request, rollup

KINDS = ("pr_diff",)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
EVENTS = {"APPROVE": "Approved", "REQUEST_CHANGES": "Requested changes on", "COMMENT": "Commented on"}
METHODS = {method for method, _flag, _label in MERGE_METHODS}
FILES_PER_PAGE = 100
MAX_PAGES = 30  # GitHub lists at most 3000 files of a pull request
MAX_FILE_LINES = 1500
MAX_TOTAL_LINES = 12000
MAX_COMMENTS = 100
MAX_TEXT = 60000

# One review or merge at a time, so a double click cannot send it twice.
submit_lock = threading.Lock()


def reference(args: dict) -> tuple[str, int]:
    repo = str(args.get("repo") or "")
    if not REPO_RE.match(repo):
        raise GitHubError("That PR has no repository.")
    try:
        number = int(args.get("number"))
    except (TypeError, ValueError):
        number = 0
    if number < 1:
        raise GitHubError("That PR has no number.")
    return repo, number


def get_pull(repo: str, number: int) -> dict:
    return json.loads(gh(["api", f"repos/{repo}/pulls/{number}"]))


def viewer() -> str:
    return gh(["api", "user", "--jq", ".login"]).strip()


def pinned_sha(value: object) -> str:
    sha = str(value or "")
    if not SHA_RE.match(sha):
        raise GitHubError("This is not pinned to a commit. Reload it and try again.")
    return sha


def require_open_at(pr: dict, repo: str, number: int, sha: str) -> None:
    """A review or a merge goes ahead only on an open pull request that still has the commit the person read."""
    if pr["state"] != "open":
        raise GitHubError(f"{repo}#{number} is {'merged' if pr.get('merged') else pr['state']}.")
    if pr["head"]["sha"] != sha:
        raise GitHubError(f"New commits were pushed ({sha[:7]} to {pr['head']['sha'][:7]}). Reload it, then look again.")


# ---------------------------------------------------------------------------------------------------------------------
# The changes


def parse_patch(patch: str) -> list[list]:
    """A file's patch as the diff view's lines: [kind, old number, new number, [[text]]], kind one of " ", "+", "-", "@" (a
    hunk header) and "!" (a note such as "No newline at end of file")."""
    lines: list[list] = []
    old = new = 0
    for text in patch.split("\n"):
        hunk = HUNK_RE.match(text)
        if hunk:
            old, new = int(hunk[1]), int(hunk[2])
            lines.append(["@", None, None, [[text]]])
        elif text.startswith("+"):
            lines.append(["+", None, new, [[text[1:]]]])
            new += 1
        elif text.startswith("-"):
            lines.append(["-", old, None, [[text[1:]]]])
            old += 1
        elif text.startswith("\\"):
            lines.append(["!", None, None, [[text.lstrip("\\ ")]]])
        elif text.startswith(" "):
            lines.append([" ", old, new, [[text[1:]]]])
            old += 1
            new += 1
    return lines


def note(text: str) -> list:
    return ["!", None, None, [[text]]]


def file_entry(item: dict, budget: int) -> dict:
    """One changed file; `budget` is how many lines may still be drawn in all."""
    patch = item.get("patch")
    lines = parse_patch(patch) if patch else []
    shown = lines[: max(0, min(MAX_FILE_LINES, budget))]
    head = []
    if item.get("previous_filename"):
        head.append(note(f"Renamed from {item['previous_filename']}"))
    if not patch:
        head.append(note("No text to show here (a binary or empty file, or too large). Open the pull request on GitHub to see it."))
    elif not shown:
        head.append(note("Not shown: this pull request is too large to draw in full here."))
    return {
        "path": item["filename"],
        "status": item.get("status"),
        "added": item.get("additions", 0),
        "removed": item.get("deletions", 0),
        "lines": head + shown,
        "more": len(lines) - len(shown),
    }


def read_files(repo: str, number: int) -> list[dict]:
    files: list[dict] = []
    budget = MAX_TOTAL_LINES
    for page in range(1, MAX_PAGES + 1):
        items = json.loads(gh(["api", f"repos/{repo}/pulls/{number}/files?per_page={FILES_PER_PAGE}&page={page}"]))
        for item in items:
            entry = file_entry(item, budget)
            budget -= len(entry["lines"])
            files.append(entry)
        if len(items) < FILES_PER_PAGE:
            break
    return files


def fetch_pr_diff(args: dict) -> dict:
    repo, number = reference(args)
    # The head can move while the files are listed: the answer counts only when it did not.
    for _ in range(2):
        pr = get_pull(repo, number)
        files = read_files(repo, number)
        if get_pull(repo, number)["head"]["sha"] == pr["head"]["sha"]:
            break
    else:
        raise GitHubError("The author is pushing new commits. Try again in a moment.")
    detail = pull_request({"repo": repo, "number": number})
    ready = pr_ready(detail, rollup(detail))
    if pr["state"] == "open":
        choices, why = merge_choices(repo, ready)
    else:
        choices, why = [], f"This pull request is {'merged' if pr.get('merged') else pr['state']}."
    login = viewer()
    author = (pr.get("user") or {}).get("login", "")
    reviews = [
        {"login": (r.get("author") or {}).get("login", "?"), "state": r.get("state"), "sha": (r.get("commit") or {}).get("oid")}
        for r in (detail.get("latestReviews") or {}).get("nodes") or []
    ]
    threads = []
    for thread in (detail.get("reviewThreads") or {}).get("nodes") or []:
        comment = ((thread.get("comments") or {}).get("nodes") or [{}])[0]
        if not thread.get("isResolved"):
            threads.append(
                {
                    "author": (comment.get("author") or {}).get("login", ""),
                    "path": comment.get("path") or "",
                    "line": comment.get("line"),
                    "body": (comment.get("body") or "")[:600],
                }
            )
    return {
        "repo": repo,
        "number": number,
        "url": pr["html_url"],
        "title": pr["title"],
        "body": pr.get("body") or "",
        "author": author,
        "draft": bool(pr.get("draft")),
        "state": "merged" if pr.get("merged") else pr["state"],
        "base": pr["base"]["ref"],
        "branch": pr["head"]["ref"],
        "head_sha": pr["head"]["sha"],
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "viewer": login,
        "own": login == author,
        "checks": check_counts(detail),
        "merge": {"ready": ready, "choices": choices, "why": why},
        "reviews": reviews,
        "mine": next((r for r in reviews if r["login"] == login), None),
        "threads": threads,
        "files": files,
    }


def fetch(kind: str, args: dict) -> dict:
    try:
        return fetch_pr_diff(args)
    except (GitHubError, json.JSONDecodeError, KeyError) as exc:
        return {"error": str(exc) or f"{kind} failed."}


# ---------------------------------------------------------------------------------------------------------------------
# The verdict


def clean_comments(raw: object) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > MAX_COMMENTS:
        raise GitHubError(f"A review takes at most {MAX_COMMENTS} line comments.")
    comments = []
    for item in raw:
        path = str(item.get("path") or "") if isinstance(item, dict) else ""
        text = str(item.get("text") or "").strip() if isinstance(item, dict) else ""
        line = item.get("line") if isinstance(item, dict) else None
        if not path or not text or not isinstance(line, int) or isinstance(line, bool) or line < 1 or len(text) > MAX_TEXT:
            raise GitHubError("A line comment needs a file, a line and a text.")
        comments.append({"path": path, "line": line, "side": "LEFT" if item.get("old") else "RIGHT", "body": text})
    return comments


def submit_review(spec: dict) -> str:
    """Posts one review; the pull request must still be open and at the commit the reviewer read."""
    repo, number = reference(spec)
    sha = pinned_sha(spec.get("head_sha"))
    event = spec.get("event")
    if event not in EVENTS:
        raise GitHubError("A review is an approval, a request for changes or a comment.")
    body = str(spec.get("body") or "").strip()
    if len(body) > MAX_TEXT:
        raise GitHubError("The review text is too long.")
    comments = clean_comments(spec.get("comments", []))
    if event == "REQUEST_CHANGES" and not body:
        raise GitHubError("Say what has to change: a request for changes needs a text.")
    if event == "COMMENT" and not body and not comments:
        raise GitHubError("A comment review needs a text or a line comment.")
    with submit_lock:
        pr = get_pull(repo, number)
        require_open_at(pr, repo, number, sha)
        if event in {"APPROVE", "REQUEST_CHANGES"} and (pr.get("user") or {}).get("login", "").lower() == viewer().lower():
            action = "approve" if event == "APPROVE" else "request changes on"
            raise GitHubError(f"You cannot {action} your own pull request. Use Comment to leave feedback instead.")
        payload = {"commit_id": sha, "event": event, "body": body, "comments": comments}
        gh(["api", "-X", "POST", f"repos/{repo}/pulls/{number}/reviews", "--input", "-"], stdin=json.dumps(payload))
    return f"{EVENTS[event]} {repo}#{number}"


# ---------------------------------------------------------------------------------------------------------------------
# The merge


def merge_pull_request(args: list) -> str:
    """Merges the pull request the inbox shows: `args` is [the row's item, the method]. Pinned to the head the person saw:
    this refuses when it moved, and GitHub refuses it too (`sha`), in case it moves right after the check."""
    item = args[0] if args and isinstance(args[0], dict) else {}
    method = args[1] if len(args) > 1 else None
    repo, number = reference(item)
    sha = pinned_sha(item.get("head_sha"))
    if method not in METHODS:
        raise GitHubError("Pick how to merge: squash, a merge commit or a rebase.")
    with submit_lock:
        pr = get_pull(repo, number)
        require_open_at(pr, repo, number, sha)
        if pr.get("draft"):
            raise GitHubError("It is a draft. Mark it ready for review first.")
        gh(["api", "-X", "PUT", f"repos/{repo}/pulls/{number}/merge", "--input", "-"], stdin=json.dumps({"merge_method": method, "sha": sha}))
    return f"Merged {repo}#{number}"
