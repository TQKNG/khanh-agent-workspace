"""Tests for hub/agent_activity.py with fixture logs in a temporary home: python -m unittest discover -s tests"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import agent_activity as aa  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc).timestamp()
TODAY = "2026-11-20T10:00:00.000Z"
OLD = "2026-09-01T10:00:00.000Z"  # well before the 30-day window


def write_lines(path: Path, records: list, mtime: float = NOW) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    path.touch()
    os.utime(path, (mtime, mtime))
    return path


def claude_turn(stamp: str, *tools: str) -> dict:
    return {"type": "assistant", "timestamp": stamp, "message": {"content": [{"type": "tool_use", "name": n, "input": {}} for n in tools]}}


def codex_call(stamp: str, name: str, kind: str = "function_call") -> dict:
    return {"type": "response_item", "timestamp": stamp, "payload": {"type": kind, "name": name}}


def values(result: dict) -> dict:
    return {a["key"]: a["count"] for a in result["axes"]}


class Claude(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".claude"
        aa._cache.clear()

    def tearDown(self):
        self._tmp.cleanup()

    def test_counts_each_area_of_work_in_the_window(self):
        write_lines(
            self.root / "projects" / "p" / "a.jsonl",
            [
                claude_turn(TODAY, "Edit", "MultiEdit", "Write"),
                claude_turn(TODAY, "Read", "Grep", "Glob", "Bash", "PowerShell"),
                claude_turn(TODAY, "Skill", "Task", "Agent", "mcp__github__get_me", "mcp__github__list_commits"),
                {"type": "user", "timestamp": TODAY, "message": {"content": "not a call"}},
            ],
        )
        result = aa.claude(self.root, now=NOW)
        self.assertEqual(result["state"], "read")
        self.assertEqual(result["days"], aa.ACTIVITY_DAYS)
        self.assertEqual(
            values(result),
            {"edits": 3, "reads": 3, "shell": 2, "skills": 1, "mcp": 2, "subagents": 2},
        )
        self.assertEqual([a["label"] for a in result["axes"]], ["Edits", "Reads", "Shell", "Skills", "MCP", "Agents"])

    def test_calls_older_than_the_window_are_left_out(self):
        write_lines(self.root / "projects" / "p" / "old.jsonl", [claude_turn(OLD, "Edit", "Edit"), claude_turn(TODAY, "Read")], mtime=NOW)
        result = aa.claude(self.root, now=NOW)
        self.assertEqual(values(result)["edits"], 0)
        self.assertEqual(values(result)["reads"], 1)

    def test_a_log_not_touched_in_the_window_is_not_read(self):
        write_lines(self.root / "projects" / "p" / "stale.jsonl", [claude_turn(TODAY, "Edit")], mtime=NOW - 90 * 86400)
        result = aa.claude(self.root, now=NOW)
        self.assertEqual(result["state"], "not_enough")
        self.assertEqual(result["reason"], "No tool calls in the last 30 days.")

    def test_no_logs_is_not_an_error(self):
        result = aa.claude(self.root, now=NOW)
        self.assertEqual(result["state"], "not_enough")
        self.assertEqual(sum(values(result).values()), 0)

    def test_a_changed_log_is_read_again_and_an_unchanged_one_is_not(self):
        path = write_lines(self.root / "projects" / "p" / "a.jsonl", [claude_turn(TODAY, "Edit")])
        self.assertEqual(values(aa.claude(self.root, now=NOW))["edits"], 1)
        with mock_read(path) as reads:
            aa.claude(self.root, now=NOW)
            self.assertEqual(reads.count, 0, "an unchanged log is answered from the cache")
        write_lines(path, [claude_turn(TODAY, "Edit"), claude_turn(TODAY, "Edit")])
        self.assertEqual(values(aa.claude(self.root, now=NOW))["edits"], 2)

    def test_broken_lines_are_skipped(self):
        path = self.root / "projects" / "p" / "broken.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"type": "assistant", "timestamp": "' + TODAY + '", "message": \n' + json.dumps(claude_turn(TODAY, "Read")) + "\n", encoding="utf-8")
        self.assertEqual(values(aa.claude(self.root, now=NOW))["reads"], 1)


class mock_read:
    """Counts how many times a log file is opened, to see the cache answer instead."""

    def __init__(self, path: Path):
        self.path = path
        self.count = 0

    def __enter__(self):
        original = Path.open
        outer = self

        def counting(self_, *args, **kwargs):
            if self_ == outer.path:
                outer.count += 1
            return original(self_, *args, **kwargs)

        self._patch = unittest.mock.patch.object(Path, "open", counting)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class Codex(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".codex"
        aa._cache.clear()

    def tearDown(self):
        self._tmp.cleanup()

    def test_counts_shell_scripts_and_mcp_calls(self):
        write_lines(
            self.root / "sessions" / "2026" / "rollout.jsonl",
            [
                codex_call(TODAY, "exec", "custom_tool_call"),
                codex_call(TODAY, "exec", "custom_tool_call"),
                codex_call(TODAY, "js"),
                codex_call(TODAY, "mcp__repl__run"),
                codex_call(TODAY, "wait"),
                {"type": "event_msg", "timestamp": TODAY, "payload": {"type": "token_count"}},
            ],
        )
        result = aa.codex(self.root, now=NOW)
        self.assertEqual(result["state"], "read")
        self.assertEqual(values(result), {"shell": 2, "scripts": 1, "mcp": 1})

    def test_no_sessions_folder_is_not_an_error(self):
        self.assertEqual(aa.codex(self.root, now=NOW)["state"], "not_enough")


class Copilot(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".copilot"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_only_edits_are_countable_so_there_is_no_shape_to_draw(self):
        conn = sqlite3.connect(self.root / "session-store.db")
        conn.execute("CREATE TABLE session_files (id INTEGER, session_id TEXT, file_path TEXT, tool_name TEXT, turn_index INTEGER, first_seen_at TEXT)")
        conn.executemany(
            "INSERT INTO session_files (session_id, file_path, tool_name, first_seen_at) VALUES ('s', 'a', ?, ?)",
            [("apply_patch", "2026-11-12T20:03:17.527Z"), ("edit", "2026-11-12T18:36:29.836Z"), ("apply_patch", OLD)],
        )
        conn.commit()
        conn.close()
        result = aa.copilot(self.root, now=NOW)
        self.assertEqual(values(result), {"edits": 2})
        self.assertEqual(result["state"], "not_enough")
        self.assertIn("only the files it edits", result["reason"])

    def test_no_store_is_not_an_error(self):
        self.assertEqual(aa.copilot(self.root, now=NOW)["state"], "not_enough")


class Window(unittest.TestCase):
    def test_the_window_starts_on_the_day_thirty_days_back_counting_today(self):
        self.assertEqual(aa._since(NOW), "2026-10-22")


if __name__ == "__main__":
    unittest.main()
