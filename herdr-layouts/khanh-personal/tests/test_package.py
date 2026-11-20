"""The package as a whole, so it installs and draws on any machine: every asset it names is in it, every page it links to
is in the layout, every hub module is installed, and a fresh install is complete. python -m unittest discover -s tests"""

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import install  # noqa: E402

MODS = ROOT / "mods"
PERSONAL = MODS / "personal"
ICONS = {p.stem for p in (PERSONAL / "icons").glob("*.svg")}
JS = {p: p.read_text(encoding="utf-8") for p in MODS.rglob("*.js")}
HUB_PY = {p: p.read_text(encoding="utf-8") for p in (ROOT / "hub").glob("*.py")}
# Paths Herdr itself provides; the code that draws them has a fallback when a Herdr version lacks one (ui.js agentMark).
HERDR_PROVIDED = re.compile(r"^icons/")


def layout_ids() -> set:
    ids = set()

    def walk(node):
        if isinstance(node, dict):
            if "id" in node:
                ids.add(node["id"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads((ROOT / "layouts" / "personal.json").read_text(encoding="utf-8")))
    return ids


class TestAssets(unittest.TestCase):
    def test_every_icon_named_is_in_the_package(self):
        pattern = re.compile(r'(?:\bIcon\(\s*|\bicon(?:Right)?\s*[:=]\s*|"icon"\s*:\s*)(?:[^"\'`,)]*\?\s*)?["\'`]([a-z][a-z0-9-]*)["\'`](?:\s*:\s*["\'`]([a-z][a-z0-9-]*)["\'`])?')
        named = {}
        for path, text in list(JS.items()) + list(HUB_PY.items()):
            for match in pattern.finditer(text):
                for name in filter(None, match.groups()):
                    named.setdefault(name, set()).add(path.name)
        for path, text in JS.items():
            for block in re.findall(r"const (?:ICON|ICONS|KIND_ICON)\s*=\s*\{(.*?)\};", text, re.S):
                for name in re.findall(r':\s*"([a-z][a-z0-9-]*)"', block):
                    named.setdefault(name, set()).add(path.name)
        self.assertGreater(len(named), 50, "the scan found the icon names")
        missing = {name: sorted(files) for name, files in named.items() if name not in ICONS}
        self.assertEqual(missing, {}, "an icon that is not in mods/personal/icons draws nothing")

    def test_every_fixed_image_path_is_in_the_package(self):
        for path, text in JS.items():
            for match in re.finditer(r'\b(?:svg|image)\(\s*[`"]([^`"$]+)[`"]', text):
                target = match.group(1)
                if HERDR_PROVIDED.match(target):
                    continue
                self.assertTrue((ROOT / target).is_file(), f"{target} (named in {path.name})")

    def test_the_header_and_footer_icons(self):
        text = JS[MODS / "workspace-chrome-swiss" / "main.js"]
        for name in re.findall(r'row\("[\w-]+", "([\w-]+)"', text):
            self.assertTrue((MODS / "workspace-chrome-swiss" / f"{name}.svg").is_file(), name)

    def test_every_critter_has_its_four_pictures(self):
        text = JS[PERSONAL / "sidebar.js"]
        names = re.findall(r'"([a-z]+)"', text.split("const CRITTER_NAMES = [")[1].split("];")[0])
        art = PERSONAL / "critters" / "art"
        missing = [f"{n}-{s}" for n in names for s in ("working", "blocked", "done", "idle") if not (art / f"sprite-{n}-{s}.svg").is_file()]
        self.assertEqual(missing, [])


class TestWiring(unittest.TestCase):
    """Every way to reach a page lands on one the layout has, and every page in it has a view."""

    def setUp(self):
        self.ids = layout_ids()

    def test_every_page_in_the_layout_has_a_view(self):
        layout = (ROOT / "layouts" / "personal.json").read_text(encoding="utf-8")
        apps = set(re.findall(r'"app":\s*"([\w-]+)"', layout))
        views = JS[PERSONAL / "main.js"].split("const VIEWS = {")[1].split("};")[0]
        known = set(re.findall(r'(?:"([\w-]+)"|(\w+)):\s*\w+', views))
        known = {a or b for a, b in known}
        self.assertEqual(sorted(apps - known), [])

    def test_sidebar_palette_panels_and_shortcuts_reach_real_pages(self):
        sidebar = JS[PERSONAL / "sidebar.js"].split("const APPS = {")[1].split("};")[0]
        for key, child in re.findall(r'^\s+"?([\w-]+)"?: \{ (?:child: "([\w-]+)", )?label', sidebar, re.M):
            self.assertIn(child or key, self.ids, "sidebar")
        palette = JS[PERSONAL / "palette.js"].split("const APPS = [")[1].split("];")[0]
        for page in re.findall(r'\["([\w-]+)"', palette):
            self.assertIn(page, self.ids, "palette")
        panels = JS[PERSONAL / "status.js"].split("export const PANELS = {")[1].split("};")[0]
        for _, child in re.findall(r'(\w+): "([\w-]+)"', panels):
            self.assertIn(child, self.ids, "side panel")
        keys = json.loads((ROOT / "keys.layout-personal.json").read_text(encoding="utf-8"))["layout:personal"]
        for command in keys.values():
            if command.startswith("personal.go:"):
                self.assertIn(command.split(":", 1)[1], self.ids, "shortcut")


class TestInstall(unittest.TestCase):
    def test_every_hub_module_is_installed(self):
        modules = {f"{m}.py" for text in HUB_PY.values() for m in re.findall(r"^import (\w+)$", text, re.M) if (ROOT / "hub" / f"{m}.py").exists()}
        self.assertTrue(modules, "the hub imports its modules")
        self.assertEqual(sorted(modules - set(install.HUB_FILES)), [], "a hub module the installer does not copy breaks the hub")
        for name in install.HUB_FILES:
            self.assertTrue((ROOT / "hub" / name).is_file(), name)

    def test_a_fresh_install_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "keys.json").write_text("{}")
            (home / "settings.json").write_text("{}")
            for mod in install.HERDR_MODS:
                (home / "mods" / mod).mkdir(parents=True)
                (home / "mods" / mod / "main.js").write_text("")
            installer = install.Installer(home, dry_run=False)
            installer.layout_and_mods()
            installer.hub(force=False)
            installer.keys()
            installer.worktrees()

            for name in ("personal.json", "personal.svg"):
                self.assertTrue((home / "layouts" / name).is_file(), name)
            for mod in install.MODS:
                source = {p.relative_to(MODS / mod) for p in (MODS / mod).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
                copied = {p.relative_to(home / "mods" / mod) for p in (home / "mods" / mod).rglob("*") if p.is_file()}
                self.assertEqual(sorted(map(str, source - copied)), [], f"mods/{mod} is copied whole")
            for name in install.HUB_FILES:
                self.assertTrue((home / "cockpit-hub" / name).is_file(), name)
            config = json.loads((home / "cockpit.json").read_text())
            self.assertTrue(Path(config["bin"]).is_file())
            self.assertIn("layout:personal", json.loads((home / "keys.json").read_text()))
            self.assertEqual(json.loads((home / "settings.json").read_text())["worktrees"]["directory"], (home / "worktrees").as_posix())
            self.assertEqual(install.missing_herdr_mods(home), [])

            # A second run changes nothing and backs nothing up.
            shutil.rmtree(installer.backup.parent, ignore_errors=True)
            again = install.Installer(home, dry_run=False)
            again.layout_and_mods()
            again.hub(force=False)
            again.keys()
            again.worktrees()
            self.assertFalse(again.backup.exists())

    def test_a_herdr_without_its_mods_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(install.missing_herdr_mods(Path(tmp)), install.HERDR_MODS)


if __name__ == "__main__":
    unittest.main()
