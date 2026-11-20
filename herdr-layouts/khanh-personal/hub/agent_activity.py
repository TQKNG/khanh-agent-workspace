"""How much each coding agent on this machine is used, for the radar on its card: the tool calls its own logs record in
the last ACTIVITY_DAYS days, counted in areas of work (edits, reads, shell, skills, MCP servers, subagents).

Each agent keeps its logs in its own format, so each reader maps the tool names it finds to areas and ignores the rest.
Only the day and the area of each call are kept, never a prompt or an output. A log file is parsed once and kept by its
size and time of change, so a later read that finds the same files is quick.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple

ACTIVITY_DAYS = 30
# A radar needs at least this many areas; an agent whose logs show fewer is drawn as "not enough usage data".
MIN_AREAS = 3
# The areas each agent is drawn with, in the radar's order: (key, label).
AREAS = {
    "claude": [("edits", "Edits"), ("reads", "Reads"), ("shell", "Shell"), ("skills", "Skills"), ("mcp", "MCP"), ("subagents", "Agents")],
    "codex": [("shell", "Shell"), ("scripts", "Scripts"), ("mcp", "MCP")],
    "copilot": [("edits", "Edits")],
}
# The tool names each agent's logs record, and the area each one counts toward. `mcp__<server>__<tool>` names count as MCP.
CLAUDE_TOOLS = {
    "Edit": "edits",
    "MultiEdit": "edits",
    "Write": "edits",
    "NotebookEdit": "edits",
    "Read": "reads",
    "Grep": "reads",
    "Glob": "reads",
    "Bash": "shell",
    "PowerShell": "shell",
    "Skill": "skills",
    "Task": "subagents",
    "Agent": "subagents",
}
CODEX_TOOLS = {"exec": "shell", "js": "scripts"}
COPILOT_TOOLS = {"apply_patch": "edits", "edit": "edits"}
# Why an agent's logs cannot draw a shape, when its areas alone say so.
REASONS = {"copilot": "Copilot's logs record only the files it edits, too few kinds of work to draw a shape."}

_cache: dict = {}  # log file -> (mtime, size, Counter of (day, area) -> calls)
_lock = threading.Lock()


def _area(name: str, table: dict) -> Optional[str]:
    if isinstance(name, str) and name.startswith("mcp__"):
        return "mcp"
    return table.get(name)


def _claude_calls(record: dict) -> Iterable[Tuple[str, str]]:
    """(timestamp, tool name) of each tool call in one Claude Code transcript line."""
    content = (record.get("message") or {}).get("content") if record.get("type") == "assistant" else None
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield record.get("timestamp"), block.get("name")


def _codex_calls(record: dict) -> Iterable[Tuple[str, str]]:
    """(timestamp, tool name) of each call in one Codex rollout line."""
    payload = record.get("payload") if record.get("type") == "response_item" else None
    if isinstance(payload, dict) and payload.get("type") in ("function_call", "custom_tool_call"):
        yield record.get("timestamp"), payload.get("name")


def _log_counts(path: Path, calls: Callable, table: dict) -> Counter:
    """(day, area) -> calls in one log file, read once per change to the file."""
    try:
        st = path.stat()
    except OSError:
        return Counter()
    key = str(path)
    with _lock:
        hit = _cache.get(key)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    counts = Counter()
    try:
        with path.open(encoding="utf-8", errors="replace") as lines:
            for line in lines:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                for stamp, name in calls(record):
                    area = _area(name, table)
                    if area and isinstance(stamp, str) and len(stamp) >= 10:
                        counts[(stamp[:10], area)] += 1
    except OSError:
        return Counter()
    with _lock:
        _cache[key] = (st.st_mtime, st.st_size, counts)
    return counts


def _result(agent: str, counts: Counter, now: float) -> dict:
    """The radar's figures: each area's calls over the window, or why there is no shape to draw."""
    axes = [{"key": key, "label": label, "count": counts.get(key, 0)} for key, label in AREAS[agent]]
    total = sum(axis["count"] for axis in axes)
    base = {"days": ACTIVITY_DAYS, "axes": axes, "since": _since(now)}
    if len(axes) < MIN_AREAS:
        return {**base, "state": "not_enough", "reason": REASONS.get(agent, "Too few kinds of work to draw a shape.")}
    if total == 0:
        return {**base, "state": "not_enough", "reason": f"No tool calls in the last {ACTIVITY_DAYS} days."}
    return {**base, "state": "read"}


def _since(now: float) -> str:
    """The first day counted: today and the ACTIVITY_DAYS - 1 days before it, in UTC like the logs' timestamps."""
    return (datetime.fromtimestamp(now, timezone.utc) - timedelta(days=ACTIVITY_DAYS - 1)).strftime("%Y-%m-%d")


def _logs(agent: str, folder: Path, pattern: str, calls: Callable, table: dict, now: float) -> dict:
    """Sums the calls of every log under `folder` changed in the window; a log not touched since the window began is skipped."""
    since = _since(now)
    oldest = now - (ACTIVITY_DAYS + 1) * 86400
    total = Counter()
    if folder.is_dir():
        for path in folder.rglob(pattern):
            try:
                if path.stat().st_mtime < oldest:
                    continue
            except OSError:
                continue
            for (day, area), n in _log_counts(path, calls, table).items():
                if day >= since:
                    total[area] += n
    return _result(agent, total, now)


def claude(root: Path, now: Optional[float] = None) -> dict:
    """Claude Code's transcripts under `<root>/projects`."""
    return _logs("claude", root / "projects", "*.jsonl", _claude_calls, CLAUDE_TOOLS, time.time() if now is None else now)


def codex(root: Path, now: Optional[float] = None) -> dict:
    """Codex's rollout logs under `<root>/sessions`."""
    return _logs("codex", root / "sessions", "*.jsonl", _codex_calls, CODEX_TOOLS, time.time() if now is None else now)


def copilot(root: Path, now: Optional[float] = None) -> dict:
    """Copilot's session store: the files each session edited, with the day each was first seen."""
    now = time.time() if now is None else now
    db = root / "session-store.db"
    total = Counter()
    if db.is_file():
        with closing(sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)) as conn:
            rows = conn.execute(
                "SELECT tool_name, substr(first_seen_at, 1, 10), COUNT(*) FROM session_files WHERE first_seen_at >= ? GROUP BY 1, 2",
                (_since(now),),
            ).fetchall()
        for tool, day, n in rows:
            area = COPILOT_TOOLS.get(tool)
            if area and day:
                total[area] += n
    return _result("copilot", total, now)
