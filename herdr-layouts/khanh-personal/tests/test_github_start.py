"""Tests for hub/github_start.py with a fake `gh` and real git repositories: python -m unittest discover -s tests"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import github_inbox  # noqa: E402
import github_start as start  # noqa: E402

URL = "https://github.com/o/r/issues/7"
# `sh` stands in for Claude and Codex (it is always installed); Copilot is missing unless a test says otherwise.
AGENTS = {"claude": ["sh"], "codex": ["sh", "-c"], "copilot": ["no-such-copilot", "-i"]}


def sh(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class FakeGh:
    """Answers the gh calls the module makes; remembers an assignment."""

    def __init__(self, state="open", assignees=(), me="bob", pull_request=False):
        self.issue = {"state": state, "title": "Fix the login page!", "assignees": [{"login": a} for a in assignees]}
        if pull_request:
            self.issue["pull_request"] = {}
        self.me = me
        self.assigned = None

    def __call__(self, args, timeout=60, stdin=None):
        if args[:2] == ["api", "user"]:
            return self.me + "\n"
        if args[:2] == ["api", "repos/o/r/issues/7"]:
            return json.dumps(self.issue)
        if args[:2] == ["api", "repos/o/r"]:
            return json.dumps({"default_branch": "main"})
        if args[:2] == ["issue", "edit"]:
            self.assigned = args[2:]
            return ""
        raise AssertionError(f"unexpected gh call {args}")


class Repos(unittest.TestCase):
    """A bare `origin` and a clone of it under a root folder, as the person's machine has them."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / "Repositories"
        origin = base / "origin.git"
        seed = base / "seed"
        sh(base, "init", "-q", "--bare", "-b", "main", str(origin))
        sh(base, "init", "-q", "-b", "main", str(seed))
        sh(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "first")
        sh(seed, "push", "-q", str(origin), "main")
        self.clone = self.root / "Personal" / "r"
        self.clone.parent.mkdir(parents=True)
        sh(base, "clone", "-q", str(origin), str(self.clone))
        # The clone's origin reads as GitHub's o/r, while insteadOf sends its fetches and pushes to the bare repository.
        sh(self.clone, "remote", "set-url", "origin", "git@github.com:o/r.git")
        sh(self.clone, "config", f"url.{origin}.insteadOf", "git@github.com:o/r.git")
        self.settings = base / "settings.json"
        self.settings.write_text(json.dumps({"roots": [str(self.root)], "agents": AGENTS}))
        self.trees = base / "herdr-worktrees"
        herdr = base / "herdr-settings.json"
        herdr.write_text(json.dumps({"worktrees": {"directory": str(self.trees)}}))
        self.tree = self.trees / "r" / "issue-7-fix-the-login-page"
        self.patches = [
            mock.patch.object(start, "SETTINGS", self.settings),
            mock.patch.object(start, "HERDR_SETTINGS", herdr),
            mock.patch.object(start, "CLONES", start.Clones()),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def plan(self, fake):
        with mock.patch.object(start, "gh", fake):
            return start.make_plan({"id": URL})


class TestHelpers(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(start.slug("Fix the login page!"), "fix-the-login-page")
        self.assertEqual(start.slug("???"), "work")
        self.assertLessEqual(len(start.slug("a" * 100)), 40)

    def test_remote_forms(self):
        for url in ("git@github.com:O/R.git", "https://github.com/O/R", "https://github.com/O/R.git", "ssh://git@github.com/O/R.git"):
            found = start.GITHUB_REMOTE_RE.search(url)
            self.assertEqual(f"{found.group(1)}/{found.group(2)}", "O/R", url)

    def test_only_issues(self):
        with self.assertRaises(github_inbox.GitHubError):
            start.issue_ref({"id": "https://github.com/o/r/pull/7"})


class TestPlan(Repos):
    def test_ready_plan(self):
        plan = self.plan(FakeGh())
        self.assertTrue(plan["ok"], plan["blockers"])
        ctx = plan["ctx"]
        self.assertEqual(Path(ctx["clone"]), self.clone)
        self.assertEqual(ctx["branch"], "issue-7-fix-the-login-page")
        self.assertEqual(Path(ctx["worktree"]), self.tree)
        self.assertTrue(any("Assign #7 to you" in s for s in plan["steps"]))

    def test_settings_repo_wins_over_scan(self):
        self.settings.write_text(json.dumps({"roots": ["/nowhere"], "repos": {"o/r": str(self.clone)}, "agents": AGENTS}))
        self.assertTrue(self.plan(FakeGh())["ok"])

    def test_blockers(self):
        self.assertIn("#7 is closed.", self.plan(FakeGh(state="closed"))["blockers"])
        self.assertIn("#7 is a pull request, not an issue.", self.plan(FakeGh(pull_request=True))["blockers"])
        # A worktree made for the issue under an older title still counts.
        (self.trees / "r" / "issue-7-old-title").mkdir(parents=True)
        self.assertTrue(any("issue-7-old-title already exists" in b for b in self.plan(FakeGh())["blockers"]))

    def test_no_clone(self):
        self.settings.write_text(json.dumps({"roots": [str(self.root / "elsewhere")], "agents": AGENTS}))
        plan = self.plan(FakeGh())
        self.assertFalse(plan["ok"])
        self.assertIn("No local clone of o/r", plan["blockers"][0])

    def test_missing_agent(self):
        none = {key: ["no-such-agent-cli"] for key in AGENTS}
        self.settings.write_text(json.dumps({"roots": [str(self.root)], "agents": none}))
        self.assertTrue(any("None of the agents" in b for b in self.plan(FakeGh())["blockers"]))

    def test_offers_every_agent_and_says_which_are_installed(self):
        plan = self.plan(FakeGh())
        self.assertEqual([a["id"] for a in plan["agents"]], ["claude", "codex", "copilot"])
        self.assertEqual([a["available"] for a in plan["agents"]], [True, True, False])
        self.assertEqual(plan["agent"], "claude")

    def test_default_agent(self):
        self.settings.write_text(json.dumps({"roots": [str(self.root)], "agents": AGENTS, "agent": "codex"}))
        self.assertEqual(self.plan(FakeGh())["agent"], "codex")
        # A default that is not installed falls back to Claude.
        self.settings.write_text(json.dumps({"roots": [str(self.root)], "agents": AGENTS, "agent": "copilot"}))
        self.assertEqual(self.plan(FakeGh())["agent"], "claude")

    def test_built_in_commands(self):
        commands = {a["id"]: a["argv"] for a in start.agents({})}
        self.assertEqual(commands, {"claude": ["claude"], "codex": ["codex"], "copilot": ["copilot", "-i"]})

    def test_already_assigned_is_not_assigned_again(self):
        plan = self.plan(FakeGh(assignees=["bob"]))
        self.assertFalse(plan["ctx"]["assign"])

    def test_fetch_never_raises(self):
        with mock.patch.object(start, "gh", FakeGh()):
            got = start.fetch("start_plan", {"target": {"id": "https://github.com/o/r/pull/1"}})
        self.assertEqual(got["ok"], False)
        self.assertNotIn("ctx", got)


class TestStart(Repos):
    def test_creates_worktree_assigns_and_launches(self):
        fake = FakeGh()
        with mock.patch.object(start, "gh", fake):
            got = start.start({"id": URL})
        tree = self.tree
        self.assertTrue((tree / ".git").is_file(), "a worktree, not a clone")
        branch = subprocess.run(["git", "-C", str(tree), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(branch, "issue-7-fix-the-login-page")
        self.assertEqual(fake.assigned, [URL, "--add-assignee", "@me"])
        launch = got["launch"]
        self.assertEqual(launch["name"], "issue-7")
        self.assertEqual(Path(launch["folder"]), tree)
        self.assertFalse(launch["focus"])
        self.assertEqual(launch["argv"][:-1], ["sh"], "Claude, the default")
        self.assertIn("Claude", got["note"])
        prompt = launch["argv"][-1]
        self.assertIn(URL, prompt)
        self.assertIn("untrusted", prompt)
        self.assertIn("Do not merge", prompt)
        self.assertNotIn("Fix the login page", prompt, "the issue's own text never goes into the prompt")
        self.assertNotIn("{", prompt)

    def test_picked_agent(self):
        with mock.patch.object(start, "gh", FakeGh()):
            got = start.start({"id": URL, "agent": "codex"})
        self.assertEqual(got["launch"]["argv"][:-1], ["sh", "-c"])
        self.assertIn("Codex", got["note"])

    def test_copilot_gets_its_task_after_i(self):
        installed = {**AGENTS, "copilot": ["sh", "-i"]}
        self.settings.write_text(json.dumps({"roots": [str(self.root)], "agents": installed}))
        with mock.patch.object(start, "gh", FakeGh()):
            argv = start.start({"id": URL, "agent": "copilot"})["launch"]["argv"]
        self.assertEqual(argv[:2], ["sh", "-i"])
        self.assertIn(URL, argv[2])

    def test_refuses_unknown_or_missing_agents(self):
        with mock.patch.object(start, "gh", FakeGh()):
            with self.assertRaisesRegex(github_inbox.GitHubError, "Unknown agent"):
                start.start({"id": URL, "agent": "rm -rf /"})
            with self.assertRaisesRegex(github_inbox.GitHubError, "not found on PATH"):
                start.start({"id": URL, "agent": "copilot"})
        self.assertFalse(self.tree.exists(), "nothing is made for an agent that cannot start")

    def test_refuses_a_second_start(self):
        with mock.patch.object(start, "gh", FakeGh()):
            start.start({"id": URL})
            with self.assertRaises(github_inbox.GitHubError):
                start.start({"id": URL})

    def test_refuses_when_origin_has_the_branch(self):
        sh(self.clone, "push", "-q", "origin", "HEAD:refs/heads/issue-7-fix-the-login-page")
        with mock.patch.object(start, "gh", FakeGh()), self.assertRaises(github_inbox.GitHubError):
            start.start({"id": URL})
        self.assertFalse(self.tree.exists())

    def test_worktree_prefix(self):
        self.assertEqual(start.worktree_prefix("o/r", 7), str(self.trees / "r" / "issue-7-"))
        self.assertTrue(str(self.tree).startswith(start.worktree_prefix("o/r", 7)))
        self.assertIsNone(start.worktree_prefix("o/other", 7))


class TestWorktreesRoot(unittest.TestCase):
    """Herdr's worktrees.directory, read as Herdr's worktree mod reads it."""

    def root_for(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            if content is not None:
                path.write_text(content)
            with mock.patch.object(start, "HERDR_SETTINGS", path):
                return start.worktrees_root()

    def test_default(self):
        default = Path("~/.herdr/worktrees").expanduser()
        self.assertEqual(self.root_for(None), default)
        self.assertEqual(self.root_for("{}"), default)
        self.assertEqual(self.root_for("not json"), default)
        self.assertEqual(self.root_for(json.dumps({"worktrees": {"directory": "relative/path"}})), default)

    def test_setting(self):
        self.assertEqual(self.root_for(json.dumps({"worktrees": {"directory": "~/trees"}})), Path("~/trees").expanduser())
        self.assertEqual(self.root_for(json.dumps({"worktrees": {"directory": "/srv/trees"}})), Path("/srv/trees"))


if __name__ == "__main__":
    unittest.main()
