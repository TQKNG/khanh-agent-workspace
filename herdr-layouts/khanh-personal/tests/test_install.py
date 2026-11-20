"""Tests for install.py's file handling: python -m unittest discover -s tests"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import install  # noqa: E402


class Trees(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source, self.home = self.root / "source", self.root / "home"
        for folder in (self.source, self.home):
            folder.mkdir()
        (self.source / "main.js").write_text("one")

    def tearDown(self):
        self.tmp.cleanup()

    def installer(self):
        return install.Installer(self.home, dry_run=False)

    def test_generated_files_are_neither_copied_nor_a_difference(self):
        # `herdr-app check` and Python write these next to the sources.
        for name in ("gpui-kit.d.ts", "jsconfig.json", "main.js.error"):
            (self.source / name).write_text("generated")
        (self.source / "__pycache__").mkdir()
        (self.source / "__pycache__" / "x.pyc").write_text("bytecode")
        destination = self.home / "mods" / "personal"
        self.installer().copy_tree(self.source, destination)
        self.assertEqual(sorted(p.name for p in destination.iterdir()), ["main.js"])
        self.assertTrue(install.Installer.same_tree(self.source, destination))

    def test_a_real_difference_reinstalls_and_backs_up(self):
        destination = self.home / "mods" / "personal"
        installer = self.installer()
        installer.copy_tree(self.source, destination)
        (self.source / "main.js").write_text("two")
        self.assertFalse(install.Installer.same_tree(self.source, destination))
        installer.copy_tree(self.source, destination)
        self.assertEqual((destination / "main.js").read_text(), "two")
        self.assertEqual(next(installer.backup.rglob("main.js")).read_text(), "one")

    def test_an_extra_or_missing_file_is_a_difference(self):
        destination = self.home / "mods" / "personal"
        self.installer().copy_tree(self.source, destination)
        (self.source / "new.js").write_text("n")
        self.assertFalse(install.Installer.same_tree(self.source, destination))
        (destination / "new.js").write_text("n")
        (destination / "stray.js").write_text("s")
        self.assertFalse(install.Installer.same_tree(self.source, destination))


class Worktrees(unittest.TestCase):
    """The installer keeps worktrees in <home>/worktrees through Herdr's worktrees.directory, unless one is set."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "herdr-app"
        self.home.mkdir()
        self.settings = self.home / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_installer(self):
        installer = install.Installer(self.home, dry_run=False)
        installer.worktrees()
        return installer

    def test_sets_the_folder_and_keeps_the_rest(self):
        self.settings.write_text(json.dumps({"zoom": 1, "worktrees": {"other": True}}))
        installer = self.run_installer()
        got = json.loads(self.settings.read_text())
        self.assertEqual(got["zoom"], 1)
        self.assertEqual(got["worktrees"], {"other": True, "directory": (self.home / "worktrees").as_posix()})
        self.assertEqual(json.loads(next(installer.backup.rglob("settings.json")).read_text())["zoom"], 1)

    def test_a_folder_under_home_is_written_with_a_tilde(self):
        self.settings.write_text("{}")
        with mock.patch.object(Path, "home", return_value=Path(self.tmp.name)):
            self.run_installer()
        self.assertEqual(json.loads(self.settings.read_text())["worktrees"]["directory"], "~/herdr-app/worktrees")

    def test_keeps_a_folder_the_person_chose(self):
        chosen = json.dumps({"worktrees": {"directory": "~/my-trees"}})
        self.settings.write_text(chosen)
        installer = self.run_installer()
        self.assertEqual(self.settings.read_text(), chosen)
        self.assertFalse(installer.backup.exists(), "nothing changed, so nothing is backed up")

    def test_missing_or_broken_settings_are_left_alone(self):
        self.run_installer()
        self.assertFalse(self.settings.exists())
        self.settings.write_text("{not json")
        self.run_installer()
        self.assertEqual(self.settings.read_text(), "{not json")


class Keys(unittest.TestCase):
    """The layout's shortcuts: added when missing, and the ones an earlier version shipped for pages it no longer has fixed."""

    OLD = {"cmd-alt-0": "personal.go:dashboard", "cmd-alt-1": "personal.go:workqueue", "cmd-alt-2": "personal.go:calendar",
           "cmd-alt-3": "personal.go:work", "cmd-r": "personal.refresh"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.keys = self.home / "keys.json"
        self.wanted = json.loads((install.HERE / "keys.layout-personal.json").read_text())["layout:personal"]

    def tearDown(self):
        self.tmp.cleanup()

    def run_installer(self):
        installer = install.Installer(self.home, dry_run=False)
        installer.keys()
        return installer, json.loads(self.keys.read_text())

    def test_every_shipped_shortcut_opens_a_page_the_layout_has(self):
        layout = (install.HERE / "layouts" / "personal.json").read_text()
        for command in self.wanted.values():
            if command.startswith("personal.go:"):
                self.assertIn(f'"id": "{command.split(":", 1)[1]}"', layout, command)

    def test_a_fresh_keys_file_gets_the_section(self):
        self.keys.write_text(json.dumps({"global": {}}))
        _, got = self.run_installer()
        self.assertEqual(got["layout:personal"], self.wanted)

    def test_old_shortcuts_are_fixed_and_the_persons_own_kept(self):
        self.keys.write_text(json.dumps({"layout:personal": {**self.OLD, "cmd-alt-1": "my.own:thing"}}))
        installer, got = self.run_installer()
        binds = got["layout:personal"]
        self.assertEqual(binds["cmd-alt-0"], "personal.go:home")
        self.assertEqual(binds["cmd-alt-1"], "my.own:thing", "a shortcut the person changed is theirs")
        self.assertEqual(binds["cmd-alt-2"], "personal.go:agents", "the old calendar shortcut now opens Agents")
        self.assertEqual(binds["cmd-alt-3"], "personal.go:work")
        self.assertEqual(binds["cmd-alt-5"], "personal.go:monitor")
        self.assertEqual(json.loads(next(installer.backup.rglob("keys.json")).read_text())["layout:personal"]["cmd-alt-2"], "personal.go:calendar")

    def test_a_second_run_changes_nothing(self):
        self.keys.write_text(json.dumps({"layout:personal": dict(self.OLD)}))
        first, _ = self.run_installer()
        shutil.rmtree(first.backup.parent)  # both runs fall in the same second, so they would share a backup folder
        before = self.keys.read_text()
        installer, _ = self.run_installer()
        self.assertEqual(self.keys.read_text(), before)
        self.assertFalse(installer.backup.exists())


if __name__ == "__main__":
    unittest.main()
