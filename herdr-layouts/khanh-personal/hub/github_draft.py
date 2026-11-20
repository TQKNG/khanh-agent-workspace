"""Drafting a GitHub issue from a short idea, for the inbox's "File issue" dialog.

`issue_draft` (a fetch) reads the repository, then asks a coding agent for a draft: a title, a body, an issue type (or
labels, when the owner has no issue types) and the issues that already cover the same subject. The agent follows the
github-issues skill's templates when that skill is installed, else GitHub's issue best practice. It runs with no tools,
in an empty folder, so its answer is only text. Nothing is posted here: `file_issue` (github_inbox.py) does that once the
person has confirmed the draft in the dialog.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import github_start
from github_inbox import CREATE_NO_WINDOW, REPO_RE, GitHubError, gh

KINDS = ("issue_draft",)
ROOT = Path(__file__).resolve().parent
PROMPT = ROOT / "issue-draft-prompt.md"
FALLBACK = ROOT / "issue-draft-fallback.md"
# The agents that can draft, and how each answers a prompt on stdin with no tools. Codex writes its answer to a file.
DRAFTERS = {
    "claude": ["-p", "--tools", "", "--output-format", "text"],
    "codex": ["exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--output-last-message", "{answer}", "-"],
}
DRAFT_SECONDS = 300
MAX_IDEA = 4000
TITLE_MAX = 72
MAX_LABELS = 3
SIMILAR_LIMIT = 5
SEARCH_WORDS = 6
PLACEHOLDER = re.compile(r"\{(guidance|idea|repo|types|labels|similar)\}")


def skill_folder() -> Path:
    return Path.home() / ".agents" / "skills" / "github-issues"


def guidance() -> tuple[str, str]:
    """The guidance the agent follows and where it came from: the skill's templates when it is installed, else the fallback."""
    folder = skill_folder()
    try:
        (folder / "SKILL.md").read_text(encoding="utf-8")
        templates = (folder / "references" / "templates.md").read_text(encoding="utf-8")
    except OSError:
        return "github best practice", FALLBACK.read_text(encoding="utf-8")
    return "github-issues skill", "The github-issues skill is installed. Follow it for the title, the body and the type, using its templates:\n\n" + templates


def drafter(config: dict) -> dict:
    """The agent that drafts: the one the inbox starts with when it can draft, else the first installed one that can."""
    offered = [a for a in github_start.agents(config) if a["id"] in DRAFTERS]
    chosen = github_start.default_agent(config, offered)
    if chosen is None:
        raise GitHubError("No agent is installed to draft the issue. Install Claude or Codex, then try again.")
    return next(a for a in offered if a["id"] == chosen)


def similar_issues(repo: str, idea: str) -> list[dict]:
    """Open and closed issues in the repository that share words with the idea: the same subject, if any."""
    words = re.findall(r"[^\W_]+", idea)[:SEARCH_WORDS]  # letters and digits only: no search operators from the person's text
    if not words:
        return []
    listed = json.loads(
        gh(["issue", "list", "--repo", repo, "--state", "all", "--search", " ".join(words), "--limit", str(SIMILAR_LIMIT), "--json", "number,title,url,state"]) or "[]"
    )
    return [{"number": i["number"], "title": i["title"], "url": i["url"], "state": str(i.get("state", "")).lower()} for i in listed]


def issue_types(owner: str) -> list[str]:
    """The issue types an organization has configured; a personal account has none, so an empty list."""
    try:
        listed = json.loads(gh(["api", f"orgs/{owner}/issue-types"]) or "[]")
    except (GitHubError, json.JSONDecodeError):
        return []
    return [t["name"] for t in listed if isinstance(t, dict) and isinstance(t.get("name"), str)]


def repo_labels(repo: str) -> list[str]:
    listed = json.loads(gh(["label", "list", "--repo", repo, "--limit", "100", "--json", "name"]) or "[]")
    return [l["name"] for l in listed if isinstance(l, dict) and isinstance(l.get("name"), str)]


def untrusted(text: str) -> str:
    """Text from the person or from GitHub, kept inside its <data> block: it cannot close the block early."""
    return text.replace("</data", "<\\/data")


def build_prompt(values: dict[str, str], template: str) -> str:
    """Fills the prompt's placeholders in one pass, so a value that contains a placeholder is left as it is."""
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def run_agent(agent: dict, prompt: str) -> str:
    """Runs the agent once with no tools, in an empty folder, and returns its answer."""
    with tempfile.TemporaryDirectory(prefix="issue-draft-") as folder:
        answer = Path(folder) / "answer.txt"
        args = [a.replace("{answer}", str(answer)) for a in DRAFTERS[agent["id"]]]
        exe = shutil.which(agent["argv"][0]) or agent["argv"][0]
        try:
            done = subprocess.run(
                [exe, *args],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=DRAFT_SECONDS,
                cwd=folder,
                env={**os.environ, "NO_COLOR": "1"},
                creationflags=CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitHubError(f"{agent['label']} took too long to draft the issue.") from exc
        except OSError as exc:
            raise GitHubError(f"{agent['label']} could not start: {exc}") from exc
        if done.returncode != 0:
            lines = (done.stderr or done.stdout).strip().splitlines()
            raise GitHubError(f"{agent['label']} failed: {lines[-1][:300] if lines else f'exit code {done.returncode}'}")
        if agent["id"] == "codex":
            return answer.read_text(encoding="utf-8") if answer.is_file() else ""
        return done.stdout


def shorten(title: str) -> str:
    if len(title) <= TITLE_MAX:
        return title
    cut = title[:TITLE_MAX]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" .,:;-")


def parse_answer(text: str, types: list[str], labels: list[str]) -> dict:
    """The draft from the agent's answer. Only a type or labels the repository has are kept, and labels only without types."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise GitHubError("The agent did not answer with a draft.")
    try:
        value = json.loads(text[start : end + 1], strict=False)  # a body may carry a raw newline, which strict JSON refuses
    except json.JSONDecodeError as exc:
        raise GitHubError("The agent's draft was not valid JSON.") from exc
    if not isinstance(value, dict):
        raise GitHubError("The agent's draft was not a JSON object.")
    title = " ".join(str(value.get("title") or "").split())
    body = str(value.get("body") or "").strip()
    if not title:
        raise GitHubError("The agent's draft has no title.")
    if not body:
        raise GitHubError("The agent's draft has no body.")
    issue_type = value.get("type") if isinstance(value.get("type"), str) and value.get("type") in types else None
    chosen: list[str] = []
    if issue_type is None:
        for name in value.get("labels") if isinstance(value.get("labels"), list) else []:
            if isinstance(name, str) and name in labels and name not in chosen:
                chosen.append(name)
    return {"title": shorten(title), "body": body, "type": issue_type, "labels": chosen[:MAX_LABELS]}


def draft(spec: dict, run=None) -> dict:
    run = run or run_agent  # looked up at call time, so a test can stand in for the agent
    idea = str(spec.get("idea") or "").strip()
    repo = str(spec.get("repo") or "").strip()
    if not idea:
        raise GitHubError("Type an idea first.")
    if len(idea) > MAX_IDEA:
        raise GitHubError(f"The idea is longer than {MAX_IDEA} characters.")
    if not REPO_RE.match(repo):
        raise GitHubError("Type the repository as owner/name.")
    agent = drafter(github_start.settings())
    similar = similar_issues(repo, idea)
    types = issue_types(repo.split("/")[0])
    labels = [] if types else repo_labels(repo)
    source, text = guidance()
    prompt = build_prompt(
        {
            "guidance": text,
            "idea": untrusted(idea),
            "repo": untrusted(repo),
            "types": untrusted("\n".join(types)) or "(none: this owner has no issue types)",
            "labels": untrusted("\n".join(labels)) or "(none)",
            "similar": untrusted("\n".join(f"#{i['number']} ({i['state']}) {i['title']}" for i in similar)) or "(none)",
        },
        PROMPT.read_text(encoding="utf-8"),
    )
    result = parse_answer(run(agent, prompt), types, labels)
    return {**result, "repo": repo, "similar": similar, "types": types, "source": source, "agent": agent["label"]}


def fetch(kind: str, args: dict) -> dict:
    try:
        return draft(args or {})
    except (GitHubError, json.JSONDecodeError, KeyError, OSError) as exc:
        return {"error": str(exc) or "The issue could not be drafted."}
