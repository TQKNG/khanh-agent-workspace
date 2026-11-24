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
        destination = self.home / "mods" / "khanh-personal"
        self.installer().copy_tree(self.source, destination)
        self.assertEqual(sorted(p.name for p in destination.iterdir()), ["main.js"])
        self.assertTrue(install.Installer.same_tree(self.source, destination))

    def test_a_real_difference_reinstalls_and_backs_up(self):
        destination = self.home / "mods" / "khanh-personal"
        installer = self.installer()
        installer.copy_tree(self.source, destination)
        (self.source / "main.js").write_text("two")
        self.assertFalse(install.Installer.same_tree(self.source, destination))
        installer.copy_tree(self.source, destination)
        self.assertEqual((destination / "main.js").read_text(), "two")
        self.assertEqual(next(installer.backup.rglob("main.js")).read_text(), "one")

    def test_an_extra_or_missing_file_is_a_difference(self):
        destination = self.home / "mods" / "khanh-personal"
        self.installer().copy_tree(self.source, destination)
        (self.source / "new.js").write_text("n")
        self.assertFalse(install.Installer.same_tree(self.source, destination))
        (destination / "new.js").write_text("n")
        (destination / "stray.js").write_text("s")
        self.assertFalse(install.Installer.same_tree(self.source, destination))


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "herdr-app"
        self.home.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rollback_restores_package_files_and_keeps_user_settings(self):
        target = self.home / "layouts" / "personal.json"
        target.parent.mkdir()
        target.write_text("old package")
        (self.home / "settings.json").write_text('{"zoom": 1}')
        installer = install.Installer(self.home, dry_run=False)
        installer.record_change(target)
        installer.stash(target)
        target.write_text("new package")
        installer.record_change(self.home / "new-file")
        (self.home / "new-file").write_text("new")
        installer.changes["settings.json"] = {"existed": True, "backed_up": True}
        installer.save_transaction()

        self.assertTrue(install.Installer(self.home, dry_run=False).rollback())
        self.assertEqual(target.read_text(), "old package")
        self.assertFalse((self.home / "new-file").exists())
        self.assertEqual((self.home / "settings.json").read_text(), '{"zoom": 1}')

    def test_dry_run_rollback_does_not_change_files(self):
        target = self.home / "layout.json"
        target.write_text("new")
        backup = self.home / ".install-backups" / "khanh-personal" / "transaction"
        saved = backup / "layout.json"
        saved.parent.mkdir(parents=True)
        saved.write_text("old")
        (backup / "manifest.json").write_text(json.dumps({"changes": {"layout.json": {"existed": True, "backed_up": True}}}))
        self.assertTrue(install.Installer(self.home, dry_run=True).rollback(backup))
        self.assertEqual(target.read_text(), "new")

    def test_rollback_reverts_package_shortcuts_but_keeps_other_user_changes(self):
        keys = self.home / "keys.json"
        keys.write_text(json.dumps({"layout:personal": {"cmd-alt-0": "personal.go:home", "cmd-alt-1": "custom.command"}}))
        settings = self.home / "settings.json"
        settings.write_text(json.dumps({"zoom": 1}))
        installer = install.Installer(self.home, dry_run=False)
        installer.stash(keys, keep=True)
        installer.stash(settings, keep=True)
        keys.write_text(json.dumps({"layout:personal": {"cmd-alt-0": "khanh-personal.go:home", "cmd-alt-1": "custom.command", "cmd-alt-2": "khanh-personal.go:agents"}}))
        settings.write_text(json.dumps({"zoom": 2, "worktrees": {"other": True, "directory": installer.default_worktrees_directory()}}))
        installer.save_transaction()

        self.assertTrue(install.Installer(self.home, dry_run=False).rollback())
        self.assertEqual(json.loads(keys.read_text())["layout:personal"], {"cmd-alt-0": "personal.go:home", "cmd-alt-1": "custom.command"})
        got = json.loads(settings.read_text())
        self.assertEqual(got["zoom"], 2)
        self.assertEqual(got["worktrees"], {"other": True})

    def test_uninstall_removes_package_files_and_preserves_user_runtime_data(self):
        source = Path(self.tmp.name) / "source"
        (source / "layouts").mkdir(parents=True)
        (source / "mods" / "khanh-personal").mkdir(parents=True)
        (source / "mods" / "khanh-workspace-chrome").mkdir(parents=True)
        (source / "hub").mkdir()
        shutil.copy2(install.HERE / "keys.layout-personal.json", source / "keys.layout-personal.json")
        scaffold = Path(self.tmp.name) / "scaffold"
        for name in install.SCAFFOLD_FILES:
            path = scaffold / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("template")
        for name in ("personal.json", "personal.svg"):
            (source / "layouts" / name).write_text(name)
            target = self.home / "layouts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(name)
        for mod in install.MODS:
            for name in ("mod.json", "main.js"):
                (source / "mods" / mod / name).write_text(name)
            target = self.home / "mods" / mod
            shutil.copytree(source / "mods" / mod, target)
        for name in install.HUB_FILES:
            (source / "hub" / name).write_text(name)
            target = self.home / "khanh-personal-hub" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(name)
        for name in install.SCAFFOLD_FILES:
            target = self.home / "khanh-personal-hub" / "repo-scaffold" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("template")
        hub = self.home / "khanh-personal-hub"
        (hub / ".venv").mkdir()
        (hub / ".venv" / "keep.txt").write_text("runtime")
        (hub / "cache").mkdir()
        (hub / "cache" / "keep.json").write_text("{}")
        config = {"bin": str(hub / ("cockpit-hub.cmd" if install.IS_WINDOWS else "cockpit-hub"))}
        (self.home / "khanh-personal.json").write_text(json.dumps(config))
        (self.home / "brand.json").write_text('{"name":"Keep me"}')
        (self.home / "keys.json").write_text(json.dumps({"layout:personal": {"cmd-alt-0": "khanh-personal.go:home", "cmd-alt-1": "custom.command"}}))
        (self.home / "settings.json").write_text(json.dumps({"zoom": 1, "worktrees": {"directory": install.Installer(self.home, False).default_worktrees_directory()}}))
        installer = install.Installer(self.home, dry_run=False)
        installer.source_root = source
        installer.scaffold_root = scaffold

        installer.uninstall()
        installer.save_transaction()

        self.assertFalse((self.home / "layouts" / "personal.json").exists())
        self.assertFalse((self.home / "mods" / "khanh-personal").exists())
        self.assertFalse((self.home / "khanh-personal.json").exists())
        self.assertTrue((hub / ".venv" / "keep.txt").is_file())
        self.assertTrue((hub / "cache" / "keep.json").is_file())
        self.assertEqual(json.loads((self.home / "brand.json").read_text())["name"], "Keep me")
        self.assertEqual(json.loads((self.home / "keys.json").read_text())["layout:personal"], {"cmd-alt-1": "custom.command"})
        settings = json.loads((self.home / "settings.json").read_text())
        self.assertEqual(settings["zoom"], 1)
        self.assertNotIn("worktrees", settings)


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
        expected = ((self.home / "worktrees").as_posix() if install.os.name == "nt" else "~/herdr-app/worktrees")
        self.assertEqual(json.loads(self.settings.read_text())["worktrees"]["directory"], expected)

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
           "cmd-alt-3": "personal.go:work", "cmd-alt-5": "personal.go:monitor", "cmd-alt-6": "personal.go:routines",
           "cmd-alt-7": "personal.go:mail", "cmd-r": "personal.refresh"}

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
            if command.startswith("khanh-personal.go:"):
                self.assertIn(f'"id": "{command.split(":", 1)[1]}"', layout, command)

    def test_a_fresh_keys_file_gets_the_section(self):
        self.keys.write_text(json.dumps({"global": {}}))
        _, got = self.run_installer()
        self.assertEqual(got["layout:personal"], self.wanted)

    def test_old_shortcuts_are_fixed_and_the_persons_own_kept(self):
        self.keys.write_text(json.dumps({"layout:personal": {**self.OLD, "cmd-alt-1": "my.own:thing"}}))
        installer, got = self.run_installer()
        binds = got["layout:personal"]
        self.assertEqual(binds["cmd-alt-0"], "khanh-personal.go:home")
        self.assertEqual(binds["cmd-alt-1"], "my.own:thing", "a shortcut the person changed is theirs")
        self.assertEqual(binds["cmd-alt-2"], "khanh-personal.go:agents", "the old calendar shortcut now opens Agents")
        self.assertEqual(binds["cmd-alt-3"], "khanh-personal.go:work")
        self.assertEqual(binds["cmd-alt-5"], "khanh-personal.go:monitor")
        self.assertEqual(json.loads(next(installer.backup.rglob("keys.json")).read_text())["layout:personal"]["cmd-alt-2"], "personal.go:calendar")

    def test_legacy_commands_are_migrated_but_custom_commands_are_preserved(self):
        self.keys.write_text(json.dumps({"layout:personal": {**self.OLD, "cmd-alt-1": "my.own:thing"}}))
        _, got = self.run_installer()
        binds = got["layout:personal"]
        self.assertEqual(binds["cmd-alt-0"], "khanh-personal.go:home")
        self.assertEqual(binds["cmd-alt-1"], "my.own:thing")
        self.assertEqual(binds["cmd-alt-3"], "khanh-personal.go:work")
        self.assertEqual(binds["cmd-alt-7"], "khanh-personal.go:mail")
        self.assertEqual(binds["cmd-r"], "khanh-personal.refresh")

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
