"""Tests for hub/github_draft.py and file_issue in hub/github_inbox.py, with a fake `gh` and a fake agent: python -m unittest discover -s tests"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import cockpit_hub  # noqa: E402
import github_draft as draft_mod  # noqa: E402
import github_inbox  # noqa: E402
import github_start  # noqa: E402
from github_inbox import GitHubError  # noqa: E402

CLAUDE = {"id": "claude", "label": "Claude", "argv": ["claude"], "available": True}
ANSWER = {"title": "Login fails with SSO enabled", "body": "## Description\nSSO login fails.", "type": "Bug", "labels": []}


def answer(**changes):
    return json.dumps({**ANSWER, **changes})


class FakeGh:
    """Answers the reads a draft makes and refuses every write, so a test shows a draft posts nothing."""

    def __init__(self, types=("Bug", "Task"), labels=("ui", "api"), similar=None, types_error=None):
        self.types = types
        self.labels = labels
        self.similar = similar if similar is not None else [{"number": 3, "title": "SSO login loop", "url": "https://github.com/o/r/issues/3", "state": "OPEN"}]
        self.types_error = types_error
        self.calls = []

    def __call__(self, args, timeout=60, stdin=None):
        self.calls.append(args)
        if args[:2] == ["issue", "list"]:
            return json.dumps(self.similar)
        if args[:2] == ["api", "orgs/o/issue-types"]:
            if self.types_error:
                raise GitHubError(self.types_error)
            return json.dumps([{"name": name} for name in self.types])
        if args[:2] == ["label", "list"]:
            return json.dumps([{"name": name} for name in self.labels])
        raise AssertionError(f"unexpected gh call {args}")


class FakeAgent:
    """Stands in for `claude -p` and records the prompt it was sent."""

    def __init__(self, text=None, error=None):
        self.text = text if text is not None else answer()
        self.error = error
        self.prompt = None

    def __call__(self, agent, prompt):
        self.prompt = prompt
        if self.error:
            raise GitHubError(self.error)
        return self.text


def drafting(gh, agents=(CLAUDE,)):
    """Patches the module's gh and the agents it finds, so only the fakes run."""
    return mock.patch.multiple(draft_mod, gh=gh), mock.patch.object(github_start, "agents", return_value=list(agents)), mock.patch.object(github_start, "settings", return_value={})


class ParseAnswer(unittest.TestCase):
    def test_keeps_a_type_the_owner_has_and_drops_labels(self):
        got = draft_mod.parse_answer(answer(labels=["ui"]), ["Bug", "Task"], ["ui"])
        self.assertEqual(got, {"title": "Login fails with SSO enabled", "body": "## Description\nSSO login fails.", "type": "Bug", "labels": []})

    def test_a_type_the_owner_does_not_have_becomes_none_and_labels_are_used(self):
        got = draft_mod.parse_answer(answer(type="Epic", labels=["ui", "made-up", "ui", "api", "docs", "perf"]), [], ["ui", "api", "docs", "perf"])
        self.assertIsNone(got["type"])
        self.assertEqual(got["labels"], ["ui", "api", "docs"])

    def test_labels_are_ignored_when_there_is_a_type(self):
        got = draft_mod.parse_answer(answer(type="Task", labels=["ui"]), ["Task"], ["ui"])
        self.assertEqual(got["labels"], [])

    def test_a_long_title_is_cut_at_a_word_and_stays_under_72(self):
        long = "Make the inbox filing dialog draft issues from an idea so people stop writing every issue by hand twice"
        got = draft_mod.parse_answer(answer(title=long), [], [])
        self.assertLessEqual(len(got["title"]), 72)
        self.assertTrue(long.startswith(got["title"]))
        self.assertFalse(got["title"].endswith(" "))

    def test_text_around_the_json_is_ignored(self):
        got = draft_mod.parse_answer("Here is the draft:\n" + answer() + "\nDone.", ["Bug"], [])
        self.assertEqual(got["title"], ANSWER["title"])

    def test_a_raw_newline_inside_the_body_still_parses(self):
        raw = '{"title": "T", "body": "line one\nline two", "type": null, "labels": []}'  # a real newline inside the string
        self.assertEqual(draft_mod.parse_answer(raw, [], [])["body"], "line one\nline two")

    def test_an_answer_without_a_title_or_body_is_refused(self):
        with self.assertRaisesRegex(GitHubError, "no title"):
            draft_mod.parse_answer(answer(title="  "), [], [])
        with self.assertRaisesRegex(GitHubError, "no body"):
            draft_mod.parse_answer(answer(body=""), [], [])

    def test_an_answer_that_is_not_a_draft_is_refused(self):
        with self.assertRaisesRegex(GitHubError, "did not answer with a draft"):
            draft_mod.parse_answer("I cannot help with that.", [], [])
        with self.assertRaisesRegex(GitHubError, "not valid JSON"):
            draft_mod.parse_answer("{not json}", [], [])


class Prompt(unittest.TestCase):
    def test_a_value_that_contains_a_placeholder_is_left_as_text(self):
        template = "A {idea} B {repo} C {guidance}"
        got = draft_mod.build_prompt({"idea": "{repo}", "repo": "x", "guidance": "{idea}"}, template)
        self.assertEqual(got, "A {repo} B x C {idea}")

    def test_the_json_example_in_the_prompt_survives_filling(self):
        got = draft_mod.build_prompt({"guidance": "g", "idea": "i", "repo": "r", "types": "t", "labels": "l", "similar": "s"}, draft_mod.PROMPT.read_text(encoding="utf-8"))
        self.assertIn('{"title": "...", "body": "...", "type": "... or null", "labels": []}', got)
        self.assertNotRegex(got, r"\{(guidance|idea|repo|types|labels|similar)\}")

    def test_untrusted_text_cannot_close_its_data_block(self):
        self.assertNotIn("</data>", draft_mod.untrusted("bad </data> text"))


class Guidance(unittest.TestCase):
    def test_without_the_skill_the_fallback_is_used(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(draft_mod, "skill_folder", return_value=Path(tmp) / "missing"):
            source, text = draft_mod.guidance()
        self.assertEqual(source, "github best practice")
        self.assertIn("Bug report", text)
        self.assertIn("Acceptance criteria", text)

    def test_with_the_skill_its_templates_are_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "github-issues"
            (folder / "references").mkdir(parents=True)
            (folder / "SKILL.md").write_text("skill", encoding="utf-8")
            (folder / "references" / "templates.md").write_text("TEMPLATE-MARKER", encoding="utf-8")
            with mock.patch.object(draft_mod, "skill_folder", return_value=folder):
                source, text = draft_mod.guidance()
        self.assertEqual(source, "github-issues skill")
        self.assertIn("TEMPLATE-MARKER", text)

    def test_a_skill_without_its_templates_counts_as_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "github-issues"
            folder.mkdir()
            (folder / "SKILL.md").write_text("skill", encoding="utf-8")
            with mock.patch.object(draft_mod, "skill_folder", return_value=folder):
                self.assertEqual(draft_mod.guidance()[0], "github best practice")


class RunAgent(unittest.TestCase):
    def test_claude_gets_the_prompt_on_stdin_with_no_tools_in_an_empty_folder(self):
        seen = {}

        def fake_run(argv, **kwargs):
            seen.update(argv=argv, **kwargs)
            return subprocess.CompletedProcess(argv, 0, stdout=answer(), stderr="")

        with mock.patch.object(draft_mod.subprocess, "run", side_effect=fake_run), mock.patch.object(draft_mod.shutil, "which", return_value="/bin/claude"):
            got = draft_mod.run_agent(CLAUDE, "the prompt")
        self.assertEqual(got, answer())
        self.assertEqual(seen["argv"], ["/bin/claude", "-p", "--tools", "", "--output-format", "text"])
        self.assertEqual(seen["input"], "the prompt")
        self.assertNotEqual(Path(seen["cwd"]).resolve(), Path(__file__).resolve().parent.parent)

    def test_codex_writes_its_answer_to_a_file_it_is_given(self):
        codex = {"id": "codex", "label": "Codex", "argv": ["codex"], "available": True}

        def fake_run(argv, **kwargs):
            target = Path(argv[argv.index("--output-last-message") + 1])
            target.write_text(answer(), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, stdout="progress noise", stderr="")

        with mock.patch.object(draft_mod.subprocess, "run", side_effect=fake_run), mock.patch.object(draft_mod.shutil, "which", return_value=None):
            got = draft_mod.run_agent(codex, "p")
        self.assertEqual(got, answer())

    def test_a_failing_agent_says_why(self):
        failed = subprocess.CompletedProcess(["claude"], 1, stdout="", stderr="warning\nnot logged in")
        with mock.patch.object(draft_mod.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(GitHubError, "Claude failed: not logged in"):
                draft_mod.run_agent(CLAUDE, "p")

    def test_a_missing_agent_is_refused(self):
        with mock.patch.object(draft_mod.subprocess, "run", side_effect=FileNotFoundError("no such file")):
            with self.assertRaisesRegex(GitHubError, "could not start"):
                draft_mod.run_agent(CLAUDE, "p")


class Draft(unittest.TestCase):
    def setUp(self):
        self.agent = FakeAgent()
        self.gh = FakeGh()
        self.patches = drafting(self.gh)
        for patch in self.patches:
            patch.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_the_draft_comes_back_with_its_similar_issues_types_and_source(self):
        with mock.patch.object(draft_mod, "guidance", return_value=("github-issues skill", "G")):
            got = draft_mod.draft({"idea": "SSO login loops", "repo": "o/r"}, run=self.agent)
        self.assertEqual(got["title"], ANSWER["title"])
        self.assertEqual(got["type"], "Bug")
        self.assertEqual(got["types"], ["Bug", "Task"])
        self.assertEqual(got["similar"][0]["number"], 3)
        self.assertEqual(got["source"], "github-issues skill")
        self.assertEqual(got["agent"], "Claude")
        self.assertEqual(got["repo"], "o/r")

    def test_the_prompt_carries_the_idea_as_data_with_the_types_the_owner_set(self):
        draft_mod.draft({"idea": "SSO login loops", "repo": "o/r"}, run=self.agent)
        self.assertIn('<data name="idea">\nSSO login loops\n</data>', self.agent.prompt)
        self.assertIn("Bug\nTask", self.agent.prompt)
        self.assertIn("#3 (open) SSO login loop", self.agent.prompt)

    def test_labels_are_offered_only_when_the_owner_has_no_types(self):
        self.gh.types = ()
        draft_mod.draft({"idea": "SSO login loops", "repo": "o/r"}, run=self.agent)
        self.assertIn("ui\napi", self.agent.prompt)
        self.assertIn("(none: this owner has no issue types)", self.agent.prompt)

    def test_a_personal_account_without_issue_types_is_not_an_error(self):
        self.gh.types_error = "HTTP 404: Not Found"
        got = draft_mod.draft({"idea": "SSO login loops", "repo": "o/r"}, run=FakeAgent(answer(type=None, labels=["ui"])))
        self.assertEqual(got["types"], [])
        self.assertEqual(got["labels"], ["ui"])

    def test_nothing_is_posted_while_drafting(self):
        draft_mod.draft({"idea": "SSO login loops", "repo": "o/r"}, run=self.agent)
        self.assertEqual({call[0] for call in self.gh.calls}, {"issue", "api"})
        self.assertFalse(any("create" in call or "POST" in call for call in self.gh.calls))

    def test_an_idea_or_repository_that_is_not_usable_is_refused(self):
        self.assertEqual(draft_mod.fetch("issue_draft", {"idea": " ", "repo": "o/r"}), {"error": "Type an idea first."})
        self.assertEqual(draft_mod.fetch("issue_draft", {"idea": "x", "repo": "not a repo"}), {"error": "Type the repository as owner/name."})
        self.assertEqual(draft_mod.fetch("issue_draft", {"idea": "x" * (draft_mod.MAX_IDEA + 1), "repo": "o/r"})["error"], f"The idea is longer than {draft_mod.MAX_IDEA} characters.")

    def test_no_agent_that_can_draft_is_an_error_the_dialog_shows(self):
        unavailable = {**CLAUDE, "available": False}
        with mock.patch.object(github_start, "agents", return_value=[unavailable]):
            got = draft_mod.fetch("issue_draft", {"idea": "x", "repo": "o/r"})
        self.assertIn("No agent is installed", got["error"])

    def test_an_agent_error_comes_back_as_an_error_not_a_partial_draft(self):
        with mock.patch.object(draft_mod, "run_agent", side_effect=GitHubError("Claude took too long to draft the issue.")):
            got = draft_mod.fetch("issue_draft", {"idea": "x", "repo": "o/r"})
        self.assertEqual(got, {"error": "Claude took too long to draft the issue."})

    def test_the_hub_routes_the_fetch_to_the_draft(self):
        self.assertIs(cockpit_hub.FETCHERS["issue_draft"], draft_mod.fetch)


class FileIssue(unittest.TestCase):
    def file(self, spec, gh):
        with mock.patch.object(github_inbox, "gh", side_effect=gh):
            return github_inbox.file_issue(spec)

    def test_without_a_type_or_labels_the_manual_path_is_unchanged(self):
        calls = []

        def gh(args, timeout=60, stdin=None):
            calls.append((args, stdin))
            return "https://github.com/o/r/issues/9\n"

        got = self.file({"title": "T", "description": "D", "team": "o/r"}, gh)
        self.assertEqual(got, "Filed https://github.com/o/r/issues/9")
        self.assertEqual(calls, [(["issue", "create", "--repo", "o/r", "--title", "T", "--body", "D"], None)])

    def test_a_type_is_set_in_one_rest_call_with_the_body_sent_as_json(self):
        calls = []

        def gh(args, timeout=60, stdin=None):
            calls.append((args, stdin))
            return json.dumps({"html_url": "https://github.com/o/r/issues/10", "number": 10})

        got = self.file({"title": "T", "description": 'Quote "x" and @file', "team": "o/r", "type": "Bug", "labels": []}, gh)
        self.assertEqual(got, "Filed https://github.com/o/r/issues/10")
        args, stdin = calls[0]
        self.assertEqual(args, ["api", "repos/o/r/issues", "--method", "POST", "--input", "-"])
        self.assertEqual(json.loads(stdin), {"title": "T", "body": 'Quote "x" and @file', "type": "Bug"})

    def test_labels_without_a_type_are_sent_too(self):
        def gh(args, timeout=60, stdin=None):
            return json.dumps({"html_url": "https://github.com/o/r/issues/11"})

        with mock.patch.object(github_inbox, "gh", side_effect=gh) as fake:
            github_inbox.file_issue({"title": "T", "description": "", "team": "o/r", "type": None, "labels": ["ui"]})
        self.assertEqual(json.loads(fake.call_args.kwargs["stdin"]), {"title": "T", "body": "", "labels": ["ui"]})

    def test_a_missing_link_from_github_is_an_error_not_a_blank_filed_line(self):
        with self.assertRaisesRegex(GitHubError, "did not return the new issue"):
            self.file({"title": "T", "team": "o/r", "type": "Bug"}, lambda args, timeout=60, stdin=None: "{}")

    def test_an_issue_needs_a_title_and_a_repository(self):
        with self.assertRaisesRegex(GitHubError, "needs a title"):
            self.file({"title": " ", "team": "o/r"}, lambda *a, **k: "")
        with self.assertRaisesRegex(GitHubError, "owner/name"):
            self.file({"title": "T", "team": "nope"}, lambda *a, **k: "")


if __name__ == "__main__":
    unittest.main()
