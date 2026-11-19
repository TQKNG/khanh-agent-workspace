"""Tests for the workflow runs the inbox shows (hub/github_inbox.py): python -m unittest discover -s tests"""

import json
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import github_inbox as inbox  # noqa: E402


def stamp(days_ago=0.0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(id, branch="main", workflow=1, status="completed", conclusion="failure", days_ago=0.1):
    return {"id": id, "name": f"wf{workflow}", "workflow_id": workflow, "head_branch": branch, "status": status, "conclusion": conclusion,
            "updated_at": stamp(days_ago), "created_at": stamp(days_ago), "html_url": f"https://github.com/o/r/actions/runs/{id}", "run_number": id, "event": "push"}


class PickRuns(unittest.TestCase):
    def pick(self, runs, wanted=("main",)):
        return inbox.pick_runs("o/r", runs, set(wanted))

    def test_a_recent_failure_and_a_running_run_show(self):
        rows = self.pick([run(1), run(2, workflow=2, status="in_progress", conclusion=None)])
        self.assertEqual([(r["item"]["run_id"], r["item"]["state"]) for r in rows], [(1, "fail"), (2, "running")])
        self.assertEqual({r["repo"] for r in rows}, {"o/r"})

    def test_only_the_latest_run_of_a_workflow_on_a_branch_counts(self):
        # Newest first: the failure was fixed by a later success, so nothing shows; an older failure after a newer one is hidden too.
        self.assertEqual(self.pick([run(3, conclusion="success"), run(2), run(1)]), [])
        self.assertEqual([r["item"]["run_id"] for r in self.pick([run(3), run(2, conclusion="success"), run(1)])], [3])

    def test_workflows_and_branches_count_separately(self):
        rows = self.pick([run(1, workflow=1), run(2, workflow=2), run(3, branch="topic", workflow=1)], wanted=("main", "topic"))
        self.assertEqual(sorted(r["item"]["run_id"] for r in rows), [1, 2, 3])

    def test_only_branches_the_person_cares_about(self):
        self.assertEqual(self.pick([run(1, branch="someone-elses")]), [])

    def test_old_failures_and_non_failures_are_left_out(self):
        self.assertEqual(self.pick([run(1, days_ago=inbox.RUN_DAYS + 1)]), [])
        for conclusion in ("success", "cancelled", "skipped", "neutral"):
            self.assertEqual(self.pick([run(1, conclusion=conclusion)]), [], conclusion)
        for conclusion in ("failure", "timed_out", "startup_failure"):
            self.assertEqual(len(self.pick([run(1, conclusion=conclusion)])), 1, conclusion)

    def test_the_row(self):
        row = self.pick([run(7, workflow=3)])[0]
        self.assertEqual((row["kind"], row["section"], row["repo"], row["key"]), ("run", "Runs", "o/r", "https://github.com/o/r/actions/runs/7"))
        self.assertEqual(row["text"][1], {"text": "wf3", "bold": True})
        self.assertEqual(row["acts"][0]["call"]["fn"], "open_url")
        self.assertIn("failed", row["text"][-1]["text"])


class ReadRuns(unittest.TestCase):
    def test_reads_each_repo_and_survives_one_that_fails(self):
        def fake(args, timeout=60, stdin=None):
            if "o/bad" in args[1]:
                raise inbox.GitHubError("no access")
            return json.dumps({"workflow_runs": [run(1)]})

        with mock.patch.object(inbox, "gh", fake):
            rows = inbox.read_runs({"o/good": {"main"}, "o/bad": {"main"}})
        self.assertEqual([r["repo"] for r in rows], ["o/good"])

    def test_at_most_a_dozen_repos(self):
        calls = []

        def fake(args, timeout=60, stdin=None):
            calls.append(args[1])
            return json.dumps({"workflow_runs": []})

        with mock.patch.object(inbox, "gh", fake):
            inbox.read_runs({f"o/r{i}": {"main"} for i in range(inbox.MAX_RUN_REPOS + 5)})
        self.assertEqual(len(calls), inbox.MAX_RUN_REPOS)


class Rows(unittest.TestCase):
    def test_every_row_names_its_repo(self):
        pr = {"number": 2, "title": "t", "url": "https://github.com/o/r/pull/2", "headRefName": "b", "headRefOid": "a" * 40, "baseRefName": "main",
              "repository": {"nameWithOwner": "o/r"}, "author": {"login": "x"}, "updatedAt": stamp(), "commits": {"nodes": []}, "reviewRequests": {"nodes": []}}
        self.assertEqual(inbox.pr_row(pr, "work", "pr", "me")[0]["repo"], "o/r")
        issue = {"number": 3, "title": "t", "url": "https://github.com/o/r/issues/3", "updatedAt": stamp(), "repository": {"nameWithOwner": "o/r"}}
        self.assertEqual(inbox.issue_row(issue)[0]["repo"], "o/r")
        self.assertEqual(inbox.alert_row({"nameWithOwner": "o/r", "url": "https://github.com/o/r"})["repo"], "o/r")


if __name__ == "__main__":
    unittest.main()
