"""Tests for hub/github_checks.py with a fake `gh`: python -m unittest discover -s tests"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import github_checks as checks  # noqa: E402
import github_inbox  # noqa: E402

SHA = "a" * 40
NEWER = "b" * 40


def run(name, status="completed", conclusion="success", app="github-actions", id=1, run_id=900):
    return {"id": id, "name": name, "status": status, "conclusion": conclusion, "app": {"slug": app},
            "started_at": "2026-01-01T10:00:00Z", "completed_at": "2026-01-01T10:01:05Z",
            "details_url": f"https://github.com/o/r/actions/runs/{run_id}/job/{id}", "html_url": f"https://github.com/o/r/runs/{id}"}


class Entries(unittest.TestCase):
    def test_states(self):
        self.assertEqual(checks.check_entry(run("a"))["state"], "pass")
        for conclusion in ("failure", "cancelled", "timed_out", "action_required", None):
            self.assertEqual(checks.check_entry(run("a", conclusion=conclusion))["state"], "fail", conclusion)
        for conclusion in ("skipped", "neutral"):
            self.assertEqual(checks.check_entry(run("a", conclusion=conclusion))["state"], "skip")
        self.assertEqual(checks.check_entry(run("a", status="in_progress", conclusion=None))["state"], "running")
        for status in ("queued", "waiting", "pending"):
            self.assertEqual(checks.check_entry(run("a", status=status, conclusion=None))["state"], "queued")

    def test_actions_jobs_carry_their_ids_and_other_apps_do_not(self):
        job = checks.check_entry(run("build", id=77, run_id=555))
        self.assertEqual((job["job_id"], job["run_id"], job["seconds"]), (77, 555, 65))
        other = checks.check_entry(run("preview", app="vercel", id=78))
        self.assertEqual((other["job_id"], other["run_id"]), (None, None))
        self.assertIsNone(checks.check_entry({**run("x"), "started_at": None})["seconds"])

    def test_commit_statuses(self):
        self.assertEqual([checks.status_entry({"context": "ci", "state": s})["state"] for s in ("success", "pending", "failure", "error")], ["pass", "running", "fail", "fail"])
        self.assertEqual(checks.status_entry({"context": "Vercel", "state": "failure", "description": "no access"})["note"], "no access")


class FakeGh:
    def __init__(self, heads=(SHA,), state="open", run_heads=None):
        self.heads = list(heads)
        self.state = state
        self.run_heads = run_heads or {}
        self.posts = []

    def __call__(self, args, timeout=60, stdin=None):
        path = args[-1]
        if args[:3] == ["api", "-X", "POST"]:
            self.posts.append(path)
            return ""
        if path.endswith("/pulls/7"):
            sha = self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]
            return json.dumps({"state": self.state, "merged": False, "head": {"sha": sha}})
        if "/check-runs" in path:
            return json.dumps({"check_runs": [run("lint", id=2), run("test", conclusion="failure", id=3, run_id=901), run("slow", status="in_progress", conclusion=None, id=4)]})
        if path.endswith("/status"):
            return json.dumps({"statuses": [{"context": "Vercel", "state": "failure", "target_url": "https://v"}]})
        if "/actions/runs/" in path:
            number = int(path.rsplit("/", 1)[1])
            return json.dumps({"head_sha": self.run_heads.get(number, SHA)})
        raise AssertionError(f"unexpected gh call {args}")


class List(unittest.TestCase):
    def test_failing_first_then_running_then_the_rest(self):
        with mock.patch.object(checks, "gh", FakeGh()), mock.patch("github_pulls.gh", FakeGh()):
            got = checks.fetch("pr_checks", {"repo": "o/r", "number": 7})
        self.assertEqual([(c["state"], c["name"]) for c in got["checks"]], [("fail", "test"), ("fail", "Vercel"), ("running", "slow"), ("pass", "lint")])
        self.assertEqual(got["head_sha"], SHA)

    def test_bad_reference_is_an_error_answer(self):
        self.assertIn("error", checks.fetch("pr_checks", {"repo": "a b", "number": 7}))


LOG = "\n".join([
    "﻿2026-01-01T10:00:00.1Z setup line",
    "2026-01-01T10:00:01.0Z ##[group]Run tests",
    "2026-01-01T10:00:02.0Z \x1b[31mFAILED test_a\x1b[0m",
    "2026-01-01T10:00:03.0Z ##[error]Process completed with exit code 1.",
    "2026-01-01T10:00:04.0Z ##[endgroup]",
    "2026-01-01T10:00:05.0Z cleanup 1", "2026-01-01T10:00:06.0Z cleanup 2", "2026-01-01T10:00:07.0Z cleanup 3",
    "2026-01-01T10:00:08.0Z cleanup 4", "2026-01-01T10:00:09.0Z cleanup 5", "2026-01-01T10:00:10.0Z cleanup 6", "",
])


class Log(unittest.TestCase):
    def test_a_failed_job_shows_its_failing_step(self):
        got = checks.clean_log(LOG)
        self.assertEqual(got["focus"], "failure")
        self.assertEqual(got["lines"][0], ["Run tests", "group"])
        self.assertEqual(got["lines"][1], ["FAILED test_a", ""])
        self.assertEqual(got["lines"][2], ["Process completed with exit code 1.", "error"])
        self.assertEqual((got["before"], len(got["lines"]), got["after"]), (1, 3 + checks.AFTER_ERROR, 6 - checks.AFTER_ERROR))

    def test_a_job_without_errors_shows_the_end(self):
        text = "\n".join(f"2026-01-01T10:00:00Z line {i}" for i in range(checks.MAX_LOG_LINES + 20))
        got = checks.clean_log(text)
        self.assertEqual((got["focus"], len(got["lines"]), got["before"], got["after"]), ("end", checks.MAX_LOG_LINES, 20, 0))
        self.assertEqual(got["lines"][-1][0], f"line {checks.MAX_LOG_LINES + 19}")

    def test_long_failures_keep_the_part_nearest_the_error_and_long_lines_are_cut(self):
        text = "##[group]step\n" + "\n".join("x" * 1000 for _ in range(checks.MAX_LOG_LINES + 50)) + "\n##[error]boom"
        got = checks.clean_log(text)
        self.assertEqual(len(got["lines"]), checks.MAX_LOG_LINES)
        self.assertEqual(got["lines"][-1], ["boom", "error"])
        self.assertTrue(all(len(t) <= checks.MAX_LOG_CHARS for t, _k in got["lines"]))

    def test_validation(self):
        for bad in ({"repo": "a b", "job_id": 5}, {"repo": "o/r", "job_id": 0}, {"repo": "o/r"}, {"repo": "o/r", "job_id": "x"}):
            self.assertIn("error", checks.fetch("check_log", bad))
        with mock.patch.object(checks, "gh", return_value=LOG) as fake:
            checks.fetch("check_log", {"repo": "o/r", "job_id": "42"})
        fake.assert_called_once()
        self.assertEqual(fake.call_args[0][0], ["api", "repos/o/r/actions/jobs/42/logs"])


class Rerun(unittest.TestCase):
    def spec(self, **extra):
        return {"repo": "o/r", "number": 7, "head_sha": SHA, "run_ids": [901], **extra}

    def run_with(self, fake, spec):
        with mock.patch.object(checks, "gh", fake), mock.patch("github_pulls.gh", fake):
            return checks.rerun_failed(spec)

    def test_reruns_the_failed_jobs_of_each_run(self):
        fake = FakeGh()
        self.assertEqual(self.run_with(fake, self.spec(run_ids=[901, 902])), "Re-running the failed jobs of 2 workflow runs on o/r#7")
        self.assertEqual(fake.posts, ["repos/o/r/actions/runs/901/rerun-failed-jobs", "repos/o/r/actions/runs/902/rerun-failed-jobs"])

    def test_refusals_rerun_nothing(self):
        cases = (
            (FakeGh(heads=(NEWER,)), self.spec(), "New commits were pushed"),
            (FakeGh(state="closed"), self.spec(), "is closed"),
            (FakeGh(run_heads={902: NEWER}), self.spec(run_ids=[901, 902]), "Run 902 is not of the commit"),
            (FakeGh(), self.spec(head_sha=None), "not pinned"),
            (FakeGh(), self.spec(run_ids=[]), "Pick between"),
            (FakeGh(), self.spec(run_ids=["9"]), "Pick between"),
            (FakeGh(), self.spec(run_ids=[True]), "Pick between"),
            (FakeGh(), self.spec(run_ids=list(range(1, checks.MAX_RUNS + 2))), "Pick between"),
            (FakeGh(), {"repo": "x y", "number": 7, "head_sha": SHA, "run_ids": [1]}, "no repository"),
        )
        for fake, spec, message in cases:
            with self.assertRaisesRegex(github_inbox.GitHubError, message):
                self.run_with(fake, spec)
            self.assertEqual(fake.posts, [], message)


if __name__ == "__main__":
    unittest.main()
