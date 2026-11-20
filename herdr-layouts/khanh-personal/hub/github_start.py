"""Assigning a GitHub issue to an agent from the inbox: a fresh worktree for it and an agent in its own Herdr tab.

`start_plan` (a fetch) says what starting would do and what stops it, without changing anything.
`start` (an act, sent only after the person confirmed that plan) checks it all again, fetches the
repository, creates the branch and worktree from origin/<default branch>, assigns the issue to the
person, and returns the tab the mod opens with `tab.new`. The hub never merges, pushes or deletes.

The local clone of a repository is found in cockpit-hub/settings.json (`repos`), else by looking for a
clone whose origin is that repository under the usual folders (`roots`) and the clones folder (`clones`,
default <herdr home>/repos). When there is none, the start clones it with gh into the clones folder, so
no clone has to be placed by hand. Worktrees go where Herdr's own
worktree feature puts them, so it lists them too: <worktrees.directory>/<clone folder>/<branch>, with
worktrees.directory from the Herdr app's settings.json (default ~/.herdr/worktrees). The agent's
instructions come from worker-prompt.md beside this file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from github_inbox import CREATE_NO_WINDOW, ISSUE_URL_RE, GitHubError, gh

KINDS = ("start_plan",)
ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "settings.json"
# The hub is installed in the Herdr app's home, whose settings.json holds Herdr's worktrees.directory.
HERDR_SETTINGS = Path(os.environ.get("HERDR_APP_HOME") or ROOT.parent) / "settings.json"
DEFAULT_WORKTREES = "~/.herdr/worktrees"
PROMPT = ROOT / "worker-prompt.md"
DEFAULT_ROOTS = ["~/Documents/Development/Repositories", "~/Developer", "~/code", "~/src", "~/projects", "~/repos", "~/git"]
# The agents the inbox offers, in the dialog's order: how each starts with its first message (appended as the last
# argument). The mod sends back only an id from this list, never a command. settings.json `agents` replaces an agent's
# command (say, to add flags) and `agent` names the one picked first.
AGENTS = {
    "claude": {"label": "Claude", "argv": ["claude"]},
    "codex": {"label": "Codex", "argv": ["codex"]},
    # -i keeps Copilot interactive with the task as its first message; -p would run unattended and deny its tools.
    "copilot": {"label": "Copilot", "argv": ["copilot", "-i"]},
}
DEFAULT_AGENT = "claude"
SCAN_DEPTH = 3
SCAN_SECONDS = 300
SKIP_DIRS = {"node_modules", ".venv", "venv", "vendor", "dist", "build", "target", "__pycache__"}
ORIGIN_RE = re.compile(r'\[remote "origin"\][^\[]*?\burl\s*=\s*(\S+)', re.S)
GITHUB_REMOTE_RE = re.compile(r"github\.com[:/]+([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


# ---------------------------------------------------------------------------------------------------------------------
# Settings and clones


def settings() -> dict:
    try:
        value = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def roots(config: dict) -> list[Path]:
    listed = config.get("roots")
    names = listed if isinstance(listed, list) and listed else DEFAULT_ROOTS
    return [Path(str(name)).expanduser() for name in names]


def clones_root(config: dict) -> Path:
    """Where the hub clones a repository it does not have yet: settings.json `clones`, else <herdr home>/repos/<owner>/<name>."""
    listed = config.get("clones")
    if isinstance(listed, str) and listed.strip():
        return Path(listed.strip()).expanduser()
    return Path(os.environ.get("HERDR_APP_HOME") or ROOT.parent) / "repos"


def agents(config: dict) -> list[dict]:
    """Every agent the dialog offers, with its command and whether that command is installed."""
    custom = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    out = []
    for key, agent in AGENTS.items():
        argv = custom.get(key)
        argv = [str(a) for a in argv] if isinstance(argv, list) and argv else list(agent["argv"])
        out.append({"id": key, "label": agent["label"], "argv": argv, "available": bool(shutil.which(argv[0]))})
    return out


def default_agent(config: dict, offered: list[dict]) -> str | None:
    """The agent picked first: settings.json `agent` when installed, else Claude, else the first installed one."""
    ready = [a["id"] for a in offered if a["available"]]
    for wanted in (config.get("agent"), DEFAULT_AGENT):
        if wanted in ready:
            return wanted
    return ready[0] if ready else None


def worktrees_root() -> Path:
    """Herdr's worktrees.directory, as its worktree mod reads it: an absolute path or one under ~."""
    try:
        directory = (json.loads(HERDR_SETTINGS.read_text(encoding="utf-8")).get("worktrees") or {}).get("directory")
    except (OSError, json.JSONDecodeError, AttributeError):
        directory = None
    path = Path(str(directory).strip() if isinstance(directory, str) and directory.strip() else DEFAULT_WORKTREES).expanduser()
    return path if path.is_absolute() else Path(DEFAULT_WORKTREES).expanduser()


def project_dir(clone: Path) -> Path:
    """Where a clone's worktrees live: one folder per project, named after the clone's folder, as Herdr names it."""
    return worktrees_root() / clone.name


def issue_worktrees(clone: Path, number: int) -> list[Path]:
    """Worktrees already made for an issue: any folder `issue-<n>-…` of its project, whatever the title was then."""
    folder = project_dir(clone)
    try:
        return sorted(p for p in folder.iterdir() if p.name.startswith(f"issue-{number}-"))
    except OSError:
        return []


def origin_repo(clone: Path) -> str | None:
    """The `owner/name` a clone's origin points at on GitHub, lowercased, from its .git/config."""
    try:
        text = (clone / ".git" / "config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    url = ORIGIN_RE.search(text)
    found = GITHUB_REMOTE_RE.search(url.group(1)) if url else None
    return f"{found.group(1)}/{found.group(2)}".lower() if found else None


def scan(folders: list[Path], depth: int = SCAN_DEPTH) -> dict[str, Path]:
    """Every main clone (a folder with a .git directory, so not a worktree) under the folders, by its origin repository."""
    found: dict[str, Path] = {}

    def walk(folder: Path, left: int) -> None:
        if (folder / ".git").is_dir():
            repo = origin_repo(folder)
            if repo and repo not in found:
                found[repo] = folder
            return
        if left <= 0:
            return
        try:
            children = sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS)
        except OSError:
            return
        for child in children:
            walk(child, left - 1)

    for folder in folders:
        if folder.is_dir():
            walk(folder, depth)
    return found


class Clones:
    """The scan, kept a few minutes: the plan and the start both ask, and walking the folders is not free."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.found: dict[str, Path] = {}
        self.at = 0.0
        self.key: tuple = ()

    def find(self, repo: str, config: dict, fresh: bool = False) -> Path | None:
        """`fresh` scans again when the repository is not known yet (a clone made a minute ago); the inbox does not ask for it."""
        listed = (config.get("repos") or {}).get(repo) if isinstance(config.get("repos"), dict) else None
        if listed:
            path = Path(str(listed)).expanduser()
            return path if (path / ".git").exists() else None
        folders = [*roots(config), clones_root(config)]
        with self.lock:
            key = tuple(str(f) for f in folders)
            if key != self.key or time.time() - self.at > SCAN_SECONDS or (fresh and repo.lower() not in self.found):
                self.found, self.at, self.key = scan(folders), time.time(), key
            return self.found.get(repo.lower())


CLONES = Clones()


# ---------------------------------------------------------------------------------------------------------------------
# git


def git(clone: Path, args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.run(
            ["git", "-C", str(clone), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise GitHubError("git was not found on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitHubError(f"git {args[0]} did not finish in time.") from exc


def git_ok(clone: Path, args: list[str], timeout: int = 60) -> str:
    done = git(clone, args, timeout)
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()
        raise GitHubError(f"git {args[0]} failed: {detail.splitlines()[-1][:300] if detail else done.returncode}")
    return done.stdout


def has_ref(clone: Path, ref: str) -> bool:
    return git(clone, ["rev-parse", "--verify", "--quiet", ref]).returncode == 0


# ---------------------------------------------------------------------------------------------------------------------
# The plan


def short_path(path: Path) -> str:
    """A path as the dialog shows it: the home folder as ~."""
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home):] if text == home or text.startswith(home + os.sep) else text


def slug(title: str, size: int = 40) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return text[:size].rstrip("-") or "work"


def issue_ref(target: dict) -> tuple[str, str, int, str]:
    url = str((target or {}).get("id") or (target or {}).get("url") or "")
    match = ISSUE_URL_RE.match(url)
    if not match:
        raise GitHubError("Only GitHub issues can be assigned to an agent.")
    owner, name, number = match.groups()
    return owner, name, int(number), url


def make_plan(target: dict) -> dict:
    """What starting would do, and what stops it. `ctx` carries the facts the start acts on."""
    owner, name, number, url = issue_ref(target)
    repo = f"{owner}/{name}"
    config = settings()
    issue = json.loads(gh(["api", f"repos/{repo}/issues/{number}"]))
    info = json.loads(gh(["api", f"repos/{repo}"]))
    viewer = gh(["api", "user", "--jq", ".login"]).strip()
    base = info.get("default_branch") or "main"
    branch = f"issue-{number}-{slug(issue.get('title') or '')}"
    offered = agents(config)
    found = CLONES.find(repo, config, fresh=True)
    # No clone yet: the plan names where one will be made, and the start makes it, so opening the dialog changes nothing.
    clone = found or clones_root(config) / owner / name
    will_clone = found is None
    worktree = project_dir(clone) / branch
    assignees = [a.get("login") for a in issue.get("assignees") or []]

    blockers = []
    if "pull_request" in issue:
        blockers.append(f"#{number} is a pull request, not an issue.")
    if issue.get("state") != "open":
        blockers.append(f"#{number} is closed.")
    if will_clone and clone.exists():
        blockers.append(f"{short_path(clone)} exists but is not a clone of {repo}. Move or remove it, or add the clone to cockpit-hub/settings.json under \"repos\".")
    if not will_clone:
        for existing in issue_worktrees(clone, number) or ([worktree] if worktree.exists() else []):
            blockers.append(f"{short_path(existing)} already exists, so an agent may already be on it. Open that tab, or remove the worktree first.")
        if has_ref(clone, f"refs/heads/{branch}"):
            blockers.append(f"The branch {branch} already exists in {clone}.")
    if not any(a["available"] for a in offered):
        blockers.append(f"None of the agents ({', '.join(a['argv'][0] for a in offered)}) was found on PATH.")

    steps = [
        f"Clone {repo} into {short_path(clone)} with gh" if will_clone else f"Fetch origin in {short_path(clone)}",
        f"Create the branch {branch} from origin/{base}",
        f"Check it out in the new worktree {short_path(worktree)}",
    ]
    if viewer not in assignees:
        steps.append(f"Assign #{number} to you ({viewer}) on GitHub")
    steps.append(f"Open the tab issue-{number} with the agent you pick: it reads the issue, implements it, tests, and opens a PR that closes #{number}")
    steps.append("You review and merge the PR here; the agent never merges")
    return {
        "ok": not blockers,
        "steps": steps,
        "blockers": blockers,
        "agents": [{key: a[key] for key in ("id", "label", "available")} for a in offered],
        "agent": default_agent(config, offered),
        "ctx": {
            "repo": repo,
            "number": number,
            "url": url,
            "base": base,
            "branch": branch,
            "clone": str(clone),
            "clone_repo": repo if will_clone else None,
            "worktree": str(worktree),
            "agents": offered,
            "assign": viewer not in assignees,
        },
    }


def fetch(kind: str, args: dict) -> dict:
    try:
        plan = make_plan((args or {}).get("target") or {})
        return {key: plan[key] for key in ("ok", "steps", "blockers", "agents", "agent")}
    except (GitHubError, json.JSONDecodeError, KeyError) as exc:
        return {"ok": False, "steps": [], "blockers": [str(exc) or "The plan could not be made."]}


# ---------------------------------------------------------------------------------------------------------------------
# Starting


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def worker_prompt(ctx: dict) -> str:
    """The agent's first message: the issue's address and the rules, never the issue's own text."""
    template = PROMPT.read_text(encoding="utf-8")
    return template.format_map(SafeDict(ctx)).strip()


def start(spec: dict) -> dict:
    plan = make_plan(spec)
    if not plan["ok"]:
        raise GitHubError(plan["blockers"][0])
    ctx = plan["ctx"]
    # Only an id comes from the mod: the command is the hub's own, for an agent that is installed.
    wanted = spec.get("agent") or plan["agent"]
    agent = next((a for a in ctx["agents"] if a["id"] == wanted), None)
    if not agent:
        raise GitHubError(f"Unknown agent: {wanted}")
    if not agent["available"]:
        raise GitHubError(f"{agent['label']} (`{agent['argv'][0]}`) was not found on PATH.")
    clone, branch, base = Path(ctx["clone"]), ctx["branch"], ctx["base"]
    if ctx.get("clone_repo") and not (clone / ".git").exists():
        clone.parent.mkdir(parents=True, exist_ok=True)
        gh(["repo", "clone", ctx["clone_repo"], str(clone)], timeout=600)
        CLONES.at = 0.0  # the next scan sees the new clone
    git_ok(clone, ["fetch", "--prune", "origin"], timeout=180)
    if has_ref(clone, f"refs/remotes/origin/{branch}"):
        raise GitHubError(f"origin already has a branch {branch}: someone may be on this issue.")
    git_ok(clone, ["worktree", "add", "-b", branch, ctx["worktree"], f"origin/{base}"], timeout=120)
    note = f"Started {agent['label']} on {ctx['repo']}#{ctx['number']} ({branch})"
    if ctx["assign"]:
        try:
            gh(["issue", "edit", ctx["url"], "--add-assignee", "@me"])
        except GitHubError as exc:
            note += f" (not assigned on GitHub: {exc})"
    return {
        "note": note,
        "launch": {
            "name": f"issue-{ctx['number']}",
            "folder": ctx["worktree"],
            "argv": [*agent["argv"], worker_prompt(ctx)],
            "focus": False,
        },
    }


def worktree_prefix(repo: str, number: int) -> str | None:
    """The start of the folder an agent started on this issue works in, when the clone is known: the inbox finds that agent by
    it. A prefix, not the whole path, so a title changed since the start still finds it."""
    clone = CLONES.find(repo, settings())
    return str(project_dir(clone) / f"issue-{number}-") if clone else None
