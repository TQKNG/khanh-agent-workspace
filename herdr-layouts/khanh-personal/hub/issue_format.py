"""Shared issue title, Markdown, and branch conventions for the Cockpit GitHub flow."""

from __future__ import annotations

import re
from pathlib import Path

TITLE_MAX = 72
TITLE_RE = re.compile(r"^(?P<kind>feat|fix|chore|docs|refactor|test|perf|ci|build)(?:\((?P<scope>[a-z0-9][a-z0-9._/-]*)\))?: (?P<summary>\S.*)$")
LEGACY_RE = re.compile(r"^\[(?:bug|feature|enhancement|task)\]\s*", re.I)
HEADING_RE = re.compile(r"(?m)^## ([^\n]+)\s*$")
TYPE_ALIASES = {"feature": "feat", "enhancement": "feat", "bug": "fix", "defect": "fix", "task": "chore", "maintenance": "chore"}


def repo_scaffold_path(hub_root: Path) -> Path:
    """Use the installed reference, the source repository, or the user's installed skill."""
    candidates = (
        hub_root / "repo-scaffold",
        hub_root.parents[2] / "skills" / "repo-scaffold",
        Path.home() / ".agents" / "skills" / "repo-scaffold",
    )
    return next((path for path in candidates if (path / "SKILL.md").is_file()), candidates[0])


def normalize_title(title: str) -> str:
    """Validate a concise conventional title and canonicalize common type aliases."""
    value = " ".join(title.split())
    value = re.sub(r"^(feature|bug)(?=\(|:)", lambda match: TYPE_ALIASES[match.group(1).lower()], value, flags=re.I)
    if len(value) > TITLE_MAX:
        raise ValueError(f"The title must be {TITLE_MAX} characters or fewer.")
    if not TITLE_RE.fullmatch(value):
        raise ValueError("Use a title such as 'feat(area): add search', 'fix(area): correct search', or 'chore: update tooling'. The scope is optional but cannot be empty.")
    return value


def issue_kind(issue: dict) -> str:
    """Infer a branch type from a conventional title, then GitHub issue type and labels."""
    title = str(issue.get("title") or "").strip()
    match = TITLE_RE.match(title)
    if match:
        return match.group("kind")
    legacy = re.match(r"^\[(bug|feature|enhancement|task)\]", title, re.I)
    if legacy:
        return TYPE_ALIASES[legacy.group(1).lower()]
    prefix = title.split(":", 1)[0].split("(", 1)[0].strip("[] ").lower()
    if prefix in TYPE_ALIASES:
        return TYPE_ALIASES[prefix]
    if re.match(r"^(fix|repair|correct|resolve)\b", title, re.I):
        return "fix"
    if re.match(r"^(add|create|implement|support)\b", title, re.I):
        return "feat"
    issue_type = issue.get("type")
    names = [issue_type.get("name", "") if isinstance(issue_type, dict) else str(issue_type or "")]
    names.extend(label.get("name", "") if isinstance(label, dict) else str(label) for label in issue.get("labels") or [])
    for name in names:
        kind = TYPE_ALIASES.get(name.strip().lower())
        if kind:
            return kind
    return "chore"


def slug(text: str, size: int = 40) -> str:
    value = LEGACY_RE.sub("", text.strip())
    match = TITLE_RE.match(value)
    if match:
        value = match.group("summary")
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:size].rstrip("-") or "work"


def headings_for_template(content: str) -> list[str]:
    """Extract ordered Markdown headings, or field labels from a GitHub YAML issue form."""
    headings = [heading.strip() for heading in HEADING_RE.findall(content)]
    if not headings:
        headings = [label.strip().strip("\"'") for label in re.findall(r"(?m)^\s+label:\s*(.+)$", content)]
    return headings or ["Summary", "Details", "Acceptance criteria"]


def normalize_markdown(body: str, headings: list[str]) -> str:
    """Require exactly the selected template's section structure and nonempty Markdown content."""
    value = body.replace("\r\n", "\n").strip()
    found = [heading.strip() for heading in HEADING_RE.findall(value)]
    if found != headings:
        raise ValueError(f"The issue body must use these Markdown headings in order: {', '.join(headings)}.")
    if not value.startswith(f"## {headings[0]}\n"):
        raise ValueError("The issue body must start with its first Markdown section.")
    parts = HEADING_RE.split(value)[2::2]
    if any(not part.strip() for part in parts):
        raise ValueError("Every issue section needs content. Mark unknown details as 'To confirm'.")
    return value + "\n"
