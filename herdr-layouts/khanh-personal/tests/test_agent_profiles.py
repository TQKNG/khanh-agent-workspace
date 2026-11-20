"""Tests for hub/agent_profiles.py with fake agent CLIs and a temporary home: python -m unittest discover -s tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import agent_profiles as ap  # noqa: E402

SECRET = "sk-test-SECRET-123"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def skill_md(name: str, description: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"


class Home(unittest.TestCase):
    """A home folder holding the three agents' files, and fake CLIs answering as the real ones do."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        write(self.home / ".claude" / "CLAUDE.md", "@ ~/.codex/AGENTS.md\n")
        write(self.home / ".claude" / "skills" / "ticket" / "SKILL.md", skill_md("ticket", "Take an issue to a PR."))
        write(self.home / ".claude" / "skills" / "synced" / "bucket" / "pdf" / "SKILL.md", skill_md("pdf", "PDF things."))
        self.plugin = self.home / "plugins" / "design"
        write(self.plugin / "skills" / "critique" / "SKILL.md", skill_md("critique", "Design feedback."))
        write(self.home / ".codex" / "AGENTS.md", "line one\nline two\n")
        write(self.home / ".codex" / "skills" / "audit" / "SKILL.md", skill_md("audit", "Audit a session."))
        self.off = write(self.home / ".agents" / "skills" / "herdr" / "SKILL.md", skill_md("herdr", "Control Herdr."))
        write(self.home / ".codex" / "config.toml", f'model = "gpt-5"\n\n[[skills.config]]\npath = "{self.off}"\nenabled = false\n\n[mcp_servers.repl]\ncommand = "node"\nenabled = false\n\n[mcp_servers.repl.env]\nAPI_KEY = "{SECRET}"\n')
        write(self.home / ".copilot" / "settings.json", '// managed\n{ "disabledMcpServers": ["off-server"] }\n')
        write(self.home / ".copilot" / "copilot-instructions.md", "Be brief.\n")
        self.answers = {
            ("claude", "plugin"): json.dumps([{"id": "design@synced", "version": "1.2.0", "scope": "synced", "enabled": True, "installPath": str(self.plugin)}]),
            ("claude", "mcp"): (
                "Checking MCP server health…\n\n"
                f"claude.ai Gmail: https://gmailmcp.googleapis.com/mcp/v1?key={SECRET} - ✔ Connected\n"
                "plugin:design:figma: https://mcp.figma.com/mcp (HTTP) - ! Needs authentication\n"
                "local-tool: /usr/local/bin/tool --flag - ✗ Failed to connect\n"
            ),
            ("codex", "plugin"): json.dumps({"installed": [{"name": "github", "version": "1.0", "enabled": True, "marketplaceName": "openai-curated"}], "available": []}),
            ("codex", "mcp"): json.dumps([
                {"name": "docs", "enabled": True, "auth_status": "unsupported", "transport": {"type": "streamable_http", "url": f"https://learn.example.com/api/mcp?token={SECRET}", "http_headers": {"Authorization": SECRET}}},
                {"name": "repl", "enabled": False, "auth_status": "unsupported", "disabled_reason": None, "transport": {"type": "stdio", "command": "node", "args": ["--key", SECRET], "env": {"API_KEY": SECRET}}},
            ]),
            ("copilot", "skill"): json.dumps([{"name": "grill-me", "description": "An interview.", "enabled": True, "path": str(self.home / ".agents" / "skills" / "grill-me" / "SKILL.md"), "source": "personal"}]),
            ("copilot", "plugin"): json.dumps([{"name": "computer-use", "marketplace": "", "version": "0.1", "enabled": False, "source": "builtin"}]),
            ("copilot", "mcp"): json.dumps({"mcpServers": {"github-mcp-server": {"type": "http", "url": "https://api.githubcopilot.com/mcp/", "headers": {"Authorization": SECRET}, "source": "builtin"}, "off-server": {"type": "stdio", "command": "x"}}}),
        }
        self.patches = [
            mock.patch.object(ap, "home", return_value=self.home),
            mock.patch.object(ap, "run", side_effect=self.fake_run),
            mock.patch.object(ap.shutil, "which", side_effect=lambda c: f"/bin/{c}" if c in ("claude", "codex", "copilot") else None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def fake_run(self, argv, timeout=ap.CLI_TIMEOUT):
        if argv[1:] == ["--version"]:
            return f"{argv[0]} 1.2.3\n"
        answer = self.answers.get((argv[0], argv[1]))
        if answer is None:
            raise RuntimeError(f"{argv[0]} {argv[1]} failed")
        return answer

    def profiles(self):
        return {p["id"]: p for p in ap.Profiles().get()["agents"]}


class TestFrontmatter(unittest.TestCase):
    def test_plain_quoted_and_folded(self):
        self.assertEqual(ap.frontmatter('---\nname: "pdf"\ndescription: Read PDFs.\n---\nbody'), {"name": "pdf", "description": "Read PDFs."})
        folded = ap.frontmatter("---\nname: x\ndescription: >\n  First line\n  second line.\nlicense: MIT\n---\n")
        self.assertEqual(folded["description"], "First line second line.")
        self.assertEqual(folded["license"], "MIT")

    def test_quoted_values_lose_their_escapes(self):
        got = ap.frontmatter('---\ndescription: "the pane (\\"your own browser\\")"\nname: \'it\'\'s\'\n---\n')
        self.assertEqual(got, {"description": 'the pane ("your own browser")', "name": "it's"})

    def test_no_frontmatter(self):
        self.assertEqual(ap.frontmatter("# Just a heading"), {})
        self.assertEqual(ap.frontmatter("---\nname: unterminated"), {})


class TestProfiles(Home):
    def test_claude(self):
        claude = self.profiles()["claude"]
        self.assertTrue(claude["installed"])
        self.assertEqual(claude["version"], "1.2.3")
        self.assertEqual(claude["instructions"]["imports"], ["~/.codex/AGENTS.md"])
        self.assertEqual(sorted((s["name"], s["source"]) for s in claude["skills"]), [("critique", "plugin design"), ("pdf", "claude.ai"), ("ticket", "personal")])
        self.assertEqual(claude["plugins"], [{"name": "design", "key": "design@synced", "version": "1.2.0", "enabled": True, "source": "synced", "toggle": True}])
        self.assertFalse(any(s["toggle"] for s in claude["skills"]), "Claude has no switch for a skill")
        mcp = {m["name"]: m for m in claude["mcp"]}
        self.assertEqual(sorted(mcp), ["Gmail", "figma", "local-tool"])
        self.assertFalse(any(m["toggle"] for m in claude["mcp"]), "`claude mcp` has no switch")
        self.assertEqual((mcp["Gmail"]["host"], mcp["Gmail"]["status"], mcp["Gmail"]["source"]), ("gmailmcp.googleapis.com", "Connected", "claude.ai"))
        self.assertEqual((mcp["figma"]["transport"], mcp["figma"]["status"], mcp["figma"]["source"]), ("http", "Needs authentication", "design"))
        self.assertEqual((mcp["local-tool"]["transport"], mcp["local-tool"]["host"]), ("stdio", None))
        self.assertEqual(claude["errors"], [])

    def test_without_a_toml_reader_codex_still_shows_and_switches_stay_off(self):
        with mock.patch.object(ap, "tomllib", None):
            codex = self.profiles()["codex"]
            with self.assertRaisesRegex(RuntimeError, "Python 3.11"):
                ap.change_codex("plugin", "github@openai-curated", False)
        self.assertEqual(codex["errors"], [ap.NO_TOML])
        self.assertTrue(codex["skills"] and codex["plugins"] and codex["mcp"], "everything else is still read")
        self.assertFalse(any(i["toggle"] for i in codex["skills"] + codex["plugins"] + codex["mcp"]))

    @unittest.skipIf(ap.tomllib is None, "needs Python 3.11 or tomli")
    def test_codex_marks_skills_turned_off_in_its_config(self):
        codex = self.profiles()["codex"]
        self.assertEqual(codex["instructions"]["lines"], 2)
        skills = {s["name"]: s for s in codex["skills"]}
        self.assertTrue(skills["audit"]["enabled"])
        self.assertFalse(skills["herdr"]["enabled"])
        self.assertEqual(skills["herdr"]["source"], "~/.agents")
        mcp = {m["name"]: m for m in codex["mcp"]}
        self.assertEqual((mcp["docs"]["transport"], mcp["docs"]["host"]), ("http", "learn.example.com"))
        self.assertFalse(mcp["repl"]["enabled"])
        self.assertEqual((mcp["repl"]["toggle"], mcp["repl"]["source"]), (True, "config"), "a server config.toml defines switches there")
        self.assertEqual((mcp["docs"]["toggle"], mcp["docs"]["source"]), (False, "plugin"), "one a plugin brings follows its plugin")
        self.assertIsNone(mcp["repl"]["status"], "no connection state to report beyond enabled or disabled")

    def test_copilot(self):
        copilot = self.profiles()["copilot"]
        self.assertEqual([s["name"] for s in copilot["skills"]], ["grill-me"])
        self.assertTrue(copilot["skills"][0]["path"].startswith("~/"), "paths are shown from ~")
        mcp = {m["name"]: m for m in copilot["mcp"]}
        self.assertTrue(mcp["github-mcp-server"]["enabled"])
        self.assertFalse(mcp["off-server"]["enabled"], "settings.json lists what Copilot turned off")
        self.assertTrue(all(m["toggle"] for m in copilot["mcp"]))

    def test_never_carries_a_secret(self):
        blob = json.dumps(ap.Profiles().get())
        self.assertNotIn(SECRET, blob, "an MCP server's URL query, headers, arguments and environment stay out")
        self.assertNotIn("Authorization", blob)

    def test_a_missing_agent_and_a_failing_cli(self):
        del self.answers[("codex", "mcp")]
        with mock.patch.object(ap.shutil, "which", side_effect=lambda c: None if c == "copilot" else f"/bin/{c}"):
            got = self.profiles()
        self.assertFalse(got["copilot"]["installed"])
        self.assertEqual((got["copilot"]["skills"], got["copilot"]["mcp"]), ([], []))
        self.assertEqual(got["codex"]["mcp"], [])
        self.assertTrue(any(e.startswith("MCP:") for e in got["codex"]["errors"]))
        self.assertTrue(got["claude"]["skills"], "one agent's failure does not hide the others")

    def test_cached_until_refreshed(self):
        profiles = ap.Profiles()
        first = profiles.get()
        self.answers[("claude", "plugin")] = "[]"
        self.assertIs(profiles.get(), first)
        self.assertEqual(next(a for a in profiles.get(refresh=True)["agents"] if a["id"] == "claude")["plugins"], [])


CODEX = """model = "gpt-5"

[plugins."github@openai-curated"]
enabled = true

[plugins."gmail@openai-curated"]
enabled = false

[[skills.config]]
path = "/home/me/.agents/skills/herdr/SKILL.md"
enabled = false

[tui]
theme = "dark"
"""


@unittest.skipIf(ap.tomllib is None, "needs Python 3.11 or tomli")
class TestCodexConfig(unittest.TestCase):
    """config.toml changed in one value: the rest of the file, comments and order included, stays as it was."""

    def test_plugin_on_and_off(self):
        off = ap.set_codex_plugin(CODEX, "github@openai-curated", False)
        self.assertEqual(off, CODEX.replace('[plugins."github@openai-curated"]\nenabled = true', '[plugins."github@openai-curated"]\nenabled = false'))
        self.assertEqual(ap.set_codex_plugin(off, "github@openai-curated", True), CODEX)

    def test_a_missing_plugin_table_is_added(self):
        got = ap.set_codex_plugin(CODEX, "new@market", True)
        self.assertTrue(got.startswith(CODEX))
        self.assertEqual(ap.tomllib.loads(got)["plugins"]["new@market"], {"enabled": True})

    def test_skill_entries(self):
        path = "/home/me/.agents/skills/herdr/SKILL.md"
        on = ap.set_codex_skill(CODEX, path, True)
        self.assertEqual(ap.tomllib.loads(on)["skills"]["config"], [{"path": path, "enabled": True}])
        self.assertEqual(on.count("\n"), CODEX.count("\n"), "only the value line changed")
        other = "/home/me/.codex/skills/audit/SKILL.md"
        self.assertEqual(ap.set_codex_skill(CODEX, other, True), CODEX, "no entry already means on")
        added = ap.set_codex_skill(CODEX, other, False)
        self.assertEqual(ap.tomllib.loads(added)["skills"]["config"][-1], {"path": other, "enabled": False})
        self.assertEqual(ap.tomllib.loads(added)["tui"], {"theme": "dark"}, "the table after it is untouched")


@unittest.skipIf(ap.tomllib is None, "needs Python 3.11 or tomli")
class TestToggle(Home):
    def setUp(self):
        super().setUp()
        self.calls = []
        real = self.fake_run

        def recording(argv, timeout=ap.CLI_TIMEOUT):
            if argv[1] in ("plugin", "skill", "mcp") and argv[2] in ("enable", "disable"):
                self.calls.append(argv)
                return ""
            return real(argv, timeout)

        self.patches.append(mock.patch.object(ap, "run", side_effect=recording))
        self.patches[-1].start()
        self.patches.append(mock.patch.object(ap, "PROFILES", ap.Profiles()))
        self.patches[-1].start()
        self.config = self.home / ".codex" / "config.toml"

    def test_claude_and_copilot_go_through_their_cli(self):
        self.assertIn("turned off", ap.toggle({"agent": "claude", "kind": "plugin", "key": "design@synced", "enabled": False}))
        ap.toggle({"agent": "copilot", "kind": "skill", "key": "grill-me", "enabled": False})
        ap.toggle({"agent": "copilot", "kind": "plugin", "key": "computer-use", "enabled": True})
        self.assertEqual(self.calls, [["claude", "plugin", "disable", "design@synced"], ["copilot", "skill", "disable", "grill-me"], ["copilot", "plugin", "enable", "computer-use"]])

    def test_mcp_servers(self):
        ap.toggle({"agent": "copilot", "kind": "mcp", "key": "off-server", "enabled": True})
        self.assertEqual(self.calls, [["copilot", "mcp", "enable", "off-server"]])
        ap.toggle({"agent": "codex", "kind": "mcp", "key": "repl", "enabled": True})
        after = ap.tomllib.loads(self.config.read_text())
        self.assertTrue(after["mcp_servers"]["repl"]["enabled"])
        self.assertEqual(after["mcp_servers"]["repl"]["env"], {"API_KEY": SECRET}, "the server's sub-table is untouched")

    def test_codex_changes_its_config_with_a_backup(self):
        before = self.config.read_text()
        ap.toggle({"agent": "codex", "kind": "skill", "key": str(self.off), "enabled": True})
        after = ap.tomllib.loads(self.config.read_text())
        self.assertEqual(after["skills"]["config"], [{"path": str(self.off), "enabled": True}])
        backups = list(self.config.parent.glob("config.toml.bak-cockpit-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), before)
        self.assertEqual(self.calls, [], "Codex has no CLI for it")
        skills = {s["name"]: s for s in next(a for a in ap.PROFILES.get()["agents"] if a["id"] == "codex")["skills"]}
        self.assertTrue(skills["herdr"]["enabled"], "the profile is read again after the change")

    def test_refuses_what_it_did_not_list_or_cannot_switch(self):
        cases = [
            ({"agent": "claude", "kind": "plugin", "key": "not-installed@x", "enabled": False}, "has no plugin"),
            ({"agent": "claude", "kind": "skill", "key": str(self.home / ".claude" / "skills" / "ticket" / "SKILL.md"), "enabled": False}, "cannot turn"),
            ({"agent": "claude", "kind": "mcp", "key": "local-tool", "enabled": False}, "cannot turn its MCP server"),
            ({"agent": "codex", "kind": "mcp", "key": "docs", "enabled": False}, "cannot turn its MCP server"),
            ({"agent": "claude", "kind": "hook", "key": "x", "enabled": False}, "Only plugins, skills and MCP servers"),
            ({"agent": "gemini", "kind": "plugin", "key": "x", "enabled": False}, "Unknown agent"),
        ]
        for spec, message in cases:
            with self.assertRaisesRegex(RuntimeError, message):
                ap.toggle(spec)
        self.assertEqual(self.calls, [])

    def test_a_form_it_does_not_edit_is_refused_not_ignored(self):
        inline = f'[skills]\nconfig = [{{ path = "{self.off}", enabled = false }}]\n'
        self.config.write_text(inline)
        with self.assertRaisesRegex(RuntimeError, "form the page does not edit"):
            ap.toggle({"agent": "codex", "kind": "skill", "key": str(self.off), "enabled": True})
        self.assertEqual(self.config.read_text(), inline)

    def test_a_config_that_would_change_more_is_left_alone(self):
        before = self.config.read_text()
        with mock.patch.object(ap, "set_codex_skill", return_value=before + "\n[tui]\ntheme = 'x'\n"):
            with self.assertRaisesRegex(RuntimeError, "more of config.toml"):
                ap.toggle({"agent": "codex", "kind": "skill", "key": str(self.off), "enabled": True})
        self.assertEqual(self.config.read_text(), before)


class TestMark(unittest.TestCase):
    def test_sharp_copy_without_a_white_backdrop(self):
        with tempfile.TemporaryDirectory() as tmp:
            herdr = Path(tmp)
            write(herdr / "icons" / "codex.svg", '<svg height="1em" style="flex:none" viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h24v24H0z" fill="#fff"></path><path d="M1 1" fill="currentColor"/></svg>')
            with mock.patch.object(ap, "herdr_home", return_value=herdr), mock.patch.object(ap, "ROOT", herdr / "cockpit-hub"):
                path = ap.mark("codex")
                self.assertIsNone(ap.mark("nobody"))
            self.assertEqual(path, "cockpit-hub/cache/marks/codex.svg")
            svg = (herdr / path).read_text()
            self.assertIn('width="256" height="256"', svg)
            self.assertNotIn("1em", svg)
            self.assertNotIn('fill="#fff"', svg)
            self.assertIn('fill="#1F2328"', svg)


if __name__ == "__main__":
    unittest.main()
