"""Tests for hub/github_pulls.py with a fake `gh`: python -m unittest discover -s tests"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import github_inbox  # noqa: E402
import github_pulls as pulls  # noqa: E402

SHA = "a" * 40
NEWER = "b" * 40
PATCH = "@@ -1,3 +1,3 @@ def f():\n keep\n-old\n+new\n+added\n\\ No newline at end of file"


def pull(sha=SHA, state="open", author="alice", merged=False):
    return {"state": state, "merged": merged, "user": {"login": author}, "head": {"sha": sha, "ref": "topic"}, "base": {"ref": "main"},
            "html_url": "https://github.com/o/r/pull/7", "title": "T", "body": "B", "draft": False, "additions": 2, "deletions": 1}


class FakeGh:
    """Answers the few gh calls the module makes; remembers the review it was asked to post."""

    def __init__(self, heads=(SHA,), me="bob", author="alice", state="open", files=None, draft=False):
        self.heads = list(heads)
        self.me, self.author, self.state, self.draft = me, author, state, draft
        self.files = files if files is not None else [{"filename": "a.py", "status": "modified", "additions": 2, "deletions": 1, "patch": PATCH}]
        self.posted = None
        self.merged = None

    def __call__(self, args, timeout=60, stdin=None):
        if args[:2] == ["api", "user"]:
            return self.me + "\n"
        if args[:3] == ["api", "-X", "POST"]:
            self.posted = (args[3], json.loads(stdin))
            return "{}"
        if args[:3] == ["api", "-X", "PUT"]:
            self.merged = (args[3], json.loads(stdin))
            return "{}"
        path = args[1]
        if path.endswith("/pulls/7"):
            sha = self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]
            return json.dumps({**pull(sha, self.state, self.author), "draft": self.draft})
        if "/pulls/7/files" in path:
            return json.dumps(self.files if "page=1" in path else [])
        raise AssertionError(f"unexpected gh call {args}")


class ParsePatch(unittest.TestCase):
    def test_numbers_lines_on_both_sides(self):
        lines = pulls.parse_patch(PATCH)
        self.assertEqual([l[:3] for l in lines], [["@", None, None], [" ", 1, 1], ["-", 2, None], ["+", None, 2], ["+", None, 3], ["!", None, None]])
        self.assertEqual(lines[0][3], [["@@ -1,3 +1,3 @@ def f():"]])
        self.assertEqual(lines[-1][3], [["No newline at end of file"]])

    def test_second_hunk_restarts_numbering(self):
        lines = pulls.parse_patch("@@ -1 +1 @@\n-a\n+b\n@@ -10,2 +10,2 @@\n x\n-y\n+z")
        self.assertEqual([l[:3] for l in lines[4:]], [[" ", 10, 10], ["-", 11, None], ["+", None, 11]])

    def test_file_entry_caps_and_notes(self):
        big = "@@ -1,2000 +1,2000 @@\n" + "\n".join(f"+l{i}" for i in range(2000))
        entry = pulls.file_entry({"filename": "big.txt", "additions": 2000, "deletions": 0, "patch": big}, pulls.MAX_TOTAL_LINES)
        self.assertEqual((len(entry["lines"]), entry["more"]), (pulls.MAX_FILE_LINES, 2001 - pulls.MAX_FILE_LINES))
        binary = pulls.file_entry({"filename": "x.png", "status": "added", "additions": 0, "deletions": 0}, 100)
        self.assertEqual(binary["lines"][0][0], "!")
        spent = pulls.file_entry({"filename": "late.py", "additions": 1, "deletions": 0, "patch": "@@ -0,0 +1 @@\n+x"}, 0)
        self.assertIn("too large", spent["lines"][0][3][0][0])
        renamed = pulls.file_entry({"filename": "n.py", "previous_filename": "o.py", "additions": 0, "deletions": 0, "patch": ""}, 100)
        self.assertIn("Renamed from o.py", renamed["lines"][0][3][0][0])


class Validation(unittest.TestCase):
    def test_comments(self):
        ok = pulls.clean_comments([{"path": "a.py", "line": 3, "old": True, "text": " hi "}, {"path": "a.py", "line": 4, "text": "x"}])
        self.assertEqual([(c["side"], c["body"]) for c in ok], [("LEFT", "hi"), ("RIGHT", "x")])
        for bad in ([{"path": "", "line": 1, "text": "x"}], [{"path": "a", "line": 0, "text": "x"}], [{"path": "a", "line": True, "text": "x"}],
                    [{"path": "a", "line": 1, "text": " "}], ["x"], "x", [{"path": "a", "line": 1, "text": "x"}] * (pulls.MAX_COMMENTS + 1)):
            with self.assertRaises(github_inbox.GitHubError):
                pulls.clean_comments(bad)

    def test_reference(self):
        self.assertEqual(pulls.reference({"repo": "o/r", "number": "7"}), ("o/r", 7))
        for bad in ({"repo": "o r", "number": 1}, {"repo": "o/r", "number": 0}, {"repo": "o/r"}, {"repo": "../x/y;rm", "number": 1}):
            with self.assertRaises(github_inbox.GitHubError):
                pulls.reference(bad)


class Submit(unittest.TestCase):
    def spec(self, **extra):
        return {"repo": "o/r", "number": 7, "head_sha": SHA, "event": "APPROVE", **extra}

    def run_with(self, fake, spec):
        with mock.patch.object(pulls, "gh", fake):
            return pulls.submit_review(spec)

    def test_posts_one_review_pinned_to_the_commit(self):
        fake = FakeGh()
        note = self.run_with(fake, self.spec(body=" lgtm ", comments=[{"path": "a.py", "line": 2, "old": False, "text": "nit"}]))
        self.assertEqual(note, "Approved o/r#7")
        path, payload = fake.posted
        self.assertEqual(path, "repos/o/r/pulls/7/reviews")
        self.assertEqual(payload, {"commit_id": SHA, "event": "APPROVE", "body": "lgtm", "comments": [{"path": "a.py", "line": 2, "side": "RIGHT", "body": "nit"}]})

    def test_refuses_when_the_head_moved(self):
        fake = FakeGh(heads=(NEWER,))
        with self.assertRaisesRegex(github_inbox.GitHubError, "New commits were pushed"):
            self.run_with(fake, self.spec())
        self.assertIsNone(fake.posted)

    def test_refuses_a_closed_pull_request_and_own_approval(self):
        for fake, message in ((FakeGh(state="closed"), "is closed"), (FakeGh(me="alice"), "your own")):
            with self.assertRaisesRegex(github_inbox.GitHubError, message):
                self.run_with(fake, self.spec())
            self.assertIsNone(fake.posted)

    def test_a_comment_by_the_author_on_their_own_pull_request_is_allowed(self):
        fake = FakeGh(me="alice")
        self.assertEqual(self.run_with(fake, self.spec(event="COMMENT", body="note")), "Commented on o/r#7")

    def test_event_rules(self):
        for spec in (self.spec(event="MERGE"), self.spec(head_sha="abc"), self.spec(head_sha=SHA.upper()), self.spec(event="REQUEST_CHANGES"),
                     self.spec(event="COMMENT"), self.spec(body="x" * (pulls.MAX_TEXT + 1))):
            fake = FakeGh()
            with self.assertRaises(github_inbox.GitHubError):
                self.run_with(fake, spec)
            self.assertIsNone(fake.posted)


class FetchDiff(unittest.TestCase):
    def detail(self):
        return {"latestReviews": {"nodes": [{"state": "APPROVED", "author": {"login": "bob"}, "commit": {"oid": NEWER}}]},
                "reviewThreads": {"nodes": [{"isResolved": False, "comments": {"nodes": [{"author": {"login": "c"}, "path": "a.py", "line": 2, "body": "q"}]}},
                                            {"isResolved": True, "comments": {"nodes": [{}]}}]},
                "detail": {"nodes": []}}

    def run_with(self, fake):
        offered = ([{"do": "merge", "method": "squash", "label": "Squash and merge"}], "")
        with mock.patch.object(pulls, "gh", fake), mock.patch.object(pulls, "pull_request", return_value=self.detail()),                 mock.patch.object(pulls, "merge_choices", return_value=offered):
            return pulls.fetch("pr_diff", {"repo": "o/r", "number": 7})

    def test_the_model(self):
        got = self.run_with(FakeGh())
        self.assertEqual((got["head_sha"], got["own"], got["state"], got["base"]), (SHA, False, "open", "main"))
        self.assertEqual(got["files"][0]["lines"][1][:3], [" ", 1, 1])
        self.assertEqual([t["body"] for t in got["threads"]], ["q"])
        self.assertEqual(got["mine"], {"login": "bob", "state": "APPROVED", "sha": NEWER})
        self.assertEqual([c["method"] for c in got["merge"]["choices"]], ["squash"])

    def test_nothing_to_merge_on_a_closed_pull_request(self):
        got = self.run_with(FakeGh(state="closed"))
        self.assertEqual((got["merge"]["choices"], got["merge"]["why"]), ([], "This pull request is closed."))

    def test_a_head_that_moves_while_reading_is_read_again_then_given_up(self):
        # get_pull is called twice per read: a head that changes between the two forces another read.
        self.assertEqual(self.run_with(FakeGh(heads=(SHA, NEWER, NEWER)))["head_sha"], NEWER)
        self.assertIn("pushing new commits", self.run_with(FakeGh(heads=(SHA, NEWER, SHA, NEWER)))["error"])

    def test_errors_become_an_error_answer(self):
        with mock.patch.object(pulls, "gh", side_effect=github_inbox.GitHubError("boom")):
            self.assertEqual(pulls.fetch("pr_diff", {"repo": "o/r", "number": 7}), {"error": "boom"})


class Merge(unittest.TestCase):
    def item(self, **extra):
        return {"repo": "o/r", "number": 7, "head_sha": SHA, **extra}

    def run_with(self, fake, args):
        with mock.patch.object(pulls, "gh", fake):
            return pulls.merge_pull_request(args)

    def test_merges_pinned_to_the_head_that_was_seen(self):
        fake = FakeGh()
        self.assertEqual(self.run_with(fake, [self.item(), "squash"]), "Merged o/r#7")
        self.assertEqual(fake.merged, ("repos/o/r/pulls/7/merge", {"merge_method": "squash", "sha": SHA}))

    def test_refusals_send_nothing(self):
        cases = (
            (FakeGh(heads=(NEWER,)), [self.item(), "squash"], "New commits were pushed"),
            (FakeGh(state="closed"), [self.item(), "squash"], "is closed"),
            (FakeGh(draft=True), [self.item(), "squash"], "draft"),
            (FakeGh(), [self.item(), "fast-forward"], "Pick how to merge"),
            (FakeGh(), [self.item(), None], "Pick how to merge"),
            (FakeGh(), [self.item(head_sha=None), "merge"], "not pinned"),
            (FakeGh(), [{"repo": "x y", "number": 1, "head_sha": SHA}, "merge"], "no repository"),
            (FakeGh(), [], "no repository"),
        )
        for fake, args, message in cases:
            with self.assertRaisesRegex(github_inbox.GitHubError, message):
                self.run_with(fake, args)
            self.assertIsNone(fake.merged, message)


class MergeChoices(unittest.TestCase):
    READY = {"state": "ready", "text": "Ready to merge", "tone": "good"}

    def choices(self, ready, repo):
        with mock.patch.object(github_inbox, "gh", return_value=json.dumps(repo)):
            return github_inbox.merge_choices("o/r", ready)

    def test_offered_only_when_ready_and_allowed(self):
        repo = {"permissions": {"push": True}, "allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": True}
        choices, why = self.choices(self.READY, repo)
        self.assertEqual(([c["method"] for c in choices], why), (["squash", "rebase"], ""))
        self.assertEqual(choices[0], {"do": "merge", "method": "squash", "label": "Squash and merge"})
        for ready in ({"state": "waiting", "text": "Checks running"}, {"state": "blocked", "text": "Checks are failing"}, {"state": "draft", "text": "Draft"}):
            self.assertEqual(self.choices(ready, repo)[0], [])
        self.assertIn("write access", self.choices(self.READY, {**repo, "permissions": {"push": False}})[1])
        self.assertIn("no merge method", self.choices(self.READY, {"permissions": {"push": True}})[1])


if __name__ == "__main__":
    unittest.main()
