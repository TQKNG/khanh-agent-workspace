"""Focused checks for the template, naming, and tagging paths in Herdr's issue flow."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import github_draft
import github_inbox
import github_start
import issue_format


class IssueFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templates = {"repo-scaffold/feature_request.md": "## Problem\n\n## Outcome\n"}

    def test_draft_rejects_plain_text_and_wrong_sections(self) -> None:
        answer = {"template": "repo-scaffold/feature_request.md", "title": "feat(ui): add search", "body": "plain text", "type": None, "labels": []}
        with self.assertRaises(github_inbox.GitHubError):
            github_draft.parse_answer(json.dumps(answer), [], [], self.templates)
        answer["body"] = "## Outcome\n\nSearch works.\n\n## Problem\n\nUsers cannot find items."
        with self.assertRaises(github_inbox.GitHubError):
            github_draft.parse_answer(json.dumps(answer), [], [], self.templates)

    def test_draft_normalizes_title_and_keeps_type_with_existing_labels(self) -> None:
        answer = {
            "template": "repo-scaffold/feature_request.md",
            "title": "feature(ui): add search",
            "body": "## Problem\n\nUsers cannot find items.\n\n## Outcome\n\nItems can be found.",
            "type": "Feature",
            "labels": ["frontend", "not-in-repo"],
        }
        result = github_draft.parse_answer(json.dumps(answer), ["Feature"], ["frontend"], self.templates)
        self.assertEqual(result["title"], "feat(ui): add search")
        self.assertEqual(result["type"], "Feature")
        self.assertEqual(result["labels"], ["frontend"])
        self.assertTrue(result["body"].endswith("\n"))

    def test_title_rejects_empty_scope(self) -> None:
        with self.assertRaises(ValueError):
            issue_format.normalize_title("chore(): update tools")

    def test_guidance_contains_repo_and_reference_templates(self) -> None:
        own = [(".github/ISSUE_TEMPLATE/custom.md", "## Reason\n\n## Result\n")]
        with patch.object(github_draft, "repository_templates", return_value=own):
            source, guidance, templates = github_draft.guidance("owner/repo")
        self.assertEqual(source, "repository and repo-scaffold templates")
        self.assertIn("repo-scaffold/bug_report.md", templates)
        self.assertIn("repo-scaffold/feature_request.md", templates)
        self.assertIn("herdr/task.md", templates)
        self.assertIn(".github/ISSUE_TEMPLATE/custom.md", guidance)
        self.assertIn("<data name=\"repository-templates\">", guidance)

    def test_legacy_bug_title_infers_fix_branch_type(self) -> None:
        self.assertEqual(issue_format.issue_kind({"title": "[Bug] Search fails"}), "fix")
        self.assertEqual(issue_format.slug("[Bug] Search fails"), "search-fails")
        self.assertEqual(issue_format.issue_kind({"title": "Fix the login page!"}), "fix")

    def test_plan_uses_typed_branch_and_stable_issue_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def fake_gh(args):
                endpoint = args[-1]
                if endpoint.endswith("/issues/23"):
                    return json.dumps({"state": "open", "title": "feat(ui): add search", "assignees": [{"login": "khanh"}]})
                if endpoint.endswith("repos/owner/repo"):
                    return json.dumps({"default_branch": "main"})
                return "khanh"

            offered = [{"id": "codex", "label": "Codex", "argv": ["codex"], "available": True}]
            with patch.object(github_start, "gh", side_effect=fake_gh), patch.object(github_start, "agents", return_value=offered), patch.object(github_start, "settings", return_value={}), patch.object(github_start, "clones_root", return_value=root / "clones"), patch.object(github_start, "worktrees_root", return_value=root / "worktrees"), patch.object(github_start.CLONES, "find", return_value=None):
                plan = github_start.make_plan({"url": "https://github.com/owner/repo/issues/23"})
            self.assertTrue(plan["ok"])
            self.assertEqual(plan["ctx"]["branch"], "feat/23-add-search")
            self.assertTrue(plan["ctx"]["worktree"].endswith("/repo/issue-23-add-search"))

    def test_file_issue_validates_markdown_and_posts_type_with_labels(self) -> None:
        spec = {
            "team": "owner/repo",
            "template": "repo-scaffold/feature_request.md",
            "title": "feat(ui): add search",
            "description": "## Problem\n\nUsers cannot find items.\n\n## Outcome\n\nItems can be found.",
            "type": "Feature",
            "labels": ["frontend"],
        }
        calls = []

        def fake_gh(args, stdin=None):
            calls.append((args, stdin))
            return json.dumps({"html_url": "https://github.com/owner/repo/issues/23"})

        with patch.object(github_draft, "guidance", return_value=("repo-scaffold templates", "", self.templates)), patch.object(github_inbox, "gh", side_effect=fake_gh):
            result = github_inbox.file_issue(spec)
        self.assertIn("issues/23", result)
        payload = json.loads(calls[0][1])
        self.assertEqual(payload["type"], "Feature")
        self.assertEqual(payload["labels"], ["frontend"])
        self.assertTrue(payload["body"].startswith("## Problem\n"))

    def test_draft_reads_templates_and_never_posts(self) -> None:
        claude = {"id": "claude", "label": "Claude", "argv": ["claude"], "available": True}
        calls = []

        def fake_gh(args, timeout=60, stdin=None):
            calls.append(args)
            if args[:2] == ["issue", "list"]:
                return "[]"
            if args[:2] == ["api", "orgs/owner/issue-types"]:
                return '[{"name":"Feature"}]'
            if args[:2] == ["label", "list"]:
                return '[{"name":"frontend"}]'
            if args[0] == "api" and "/contents/" in args[1]:
                raise github_inbox.GitHubError("not found")
            raise AssertionError(args)

        template = (github_draft.SCAFFOLD / "assets/starter/.github/ISSUE_TEMPLATE/feature_request.md").read_text()
        headings = issue_format.headings_for_template(template)
        body = "\n\n".join(f"## {heading}\n\nTo confirm." for heading in headings)
        answer = json.dumps({"template": "repo-scaffold/feature_request.md", "title": "feat(ui): add search", "body": body, "type": "Feature", "labels": ["frontend"]})
        with patch.object(github_draft, "gh", side_effect=fake_gh), patch.object(github_start, "agents", return_value=[claude]), patch.object(github_start, "settings", return_value={}):
            result = github_draft.draft({"idea": "Add search", "repo": "owner/repo"}, run=lambda agent, prompt: answer)
        self.assertEqual(result["labels"], ["frontend"])
        self.assertEqual(result["available_labels"], ["frontend"])
        self.assertEqual(result["type"], "Feature")
        self.assertFalse(any("POST" in call or "create" in call for call in calls))

    def test_agent_receives_prompt_without_tools(self) -> None:
        seen = {}

        def fake_run(argv, **kwargs):
            seen.update(argv=argv, **kwargs)
            return subprocess.CompletedProcess(argv, 0, stdout="answer", stderr="")

        agent = {"id": "claude", "label": "Claude", "argv": ["claude"]}
        with patch.object(github_draft.subprocess, "run", side_effect=fake_run), patch.object(github_draft.shutil, "which", return_value="/bin/claude"):
            self.assertEqual(github_draft.run_agent(agent, "draft this"), "answer")
        self.assertEqual(seen["argv"], ["/bin/claude", "-p", "--tools", "", "--output-format", "text"])
        self.assertEqual(seen["input"], "draft this")


if __name__ == "__main__":
    unittest.main()
