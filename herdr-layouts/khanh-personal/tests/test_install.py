"""Tests for install.py's file handling: python -m unittest discover -s tests"""

import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
