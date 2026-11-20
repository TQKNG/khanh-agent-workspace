#!/usr/bin/env python3
"""Installs the personal Herdr layout, its mods and its local hub into a Herdr app home.

    python install.py                 install into ~/.config/herdr-app (or $HERDR_APP_HOME)
    python install.py --activate      also switch the window to the layout
    python install.py --home DIR      install into another Herdr home
    python install.py --dry-run       print what would change and touch nothing
    python install.py --brand-name "Acme Workspace" --brand-logo logo.png
                                      set your own name and logo (also works with --only-brand)

Anything it would replace is moved to <home>/.install-backups/<time>/ first.
It keeps worktrees in <home>/worktrees by setting Herdr's worktrees.directory, unless one is already set.
It never touches credentials.json or data/ under the hub folder, and it leaves an
existing cockpit.json alone when that points at another cockpit (use --force-hub).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYOUT = "personal"
MODS = ["personal", "workspace-chrome-swiss"]
# Herdr's own mods the layout shows (tabs, files, changes) or opens (help, picker): they come with Herdr, not with this
# package, so the installer says which a Herdr version lacks rather than leaving a blank space in the window.
HERDR_MODS = ["tabs", "files", "changes", "help", "picker"]
HUB_FILES = ["cockpit_hub.py", "github_inbox.py", "github_pulls.py", "github_checks.py", "github_start.py", "github_draft.py", "agent_profiles.py", "worker-prompt.md", "issue-draft-prompt.md", "issue-draft-fallback.md", "cockpit-hub", "cockpit-hub.cmd"]
HUB_VERSION = "0.2.0"
# The Herdr app version this setup was built and tested against (`herdr-app --version`).
TESTED_HERDR = "0.1.16"
# Shortcuts earlier versions of this package shipped that point at pages it no longer has (or never had): replaced or
# dropped when keys.json still holds exactly these values, so a shortcut the person changed is kept.
STALE_KEYS = {
    "layout:personal": {
        "cmd-alt-0": "personal.go:dashboard",
        "cmd-alt-1": "personal.go:workqueue",
        "cmd-alt-2": "personal.go:calendar",
    },
}
LOGO_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
IS_WINDOWS = os.name == "nt"
# Files the Herdr app and Python generate next to the sources: never copied, and never a reason to reinstall.
GENERATED = ("*.d.ts", "jsconfig.json", "*.error", "__pycache__")


class Installer:
    def __init__(self, home: Path, dry_run: bool) -> None:
        self.home = home
        self.dry = dry_run
        self.backup = home / ".install-backups" / time.strftime("%Y%m%d-%H%M%S")

    def say(self, message: str) -> None:
        print(("[dry-run] " if self.dry else "") + message)

    def stash(self, path: Path, keep: bool = False) -> None:
        """Puts an existing file or folder in the backup folder: moved out of the way, or copied when `keep` is set."""
        if not path.exists():
            return
        target = self.backup / path.relative_to(self.home)
        self.say(f"backing up {path.relative_to(self.home)} -> {target.relative_to(self.home)}")
        if self.dry:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copy2 if keep else shutil.move)(str(path), str(target))

    @staticmethod
    def same_tree(a: Path, b: Path) -> bool:
        if not (a.is_dir() and b.is_dir()):
            return False

        def files(root: Path) -> set[Path]:
            return {
                p.relative_to(root)
                for p in root.rglob("*")
                if p.is_file() and not any(fnmatch.fnmatch(part, pattern) for part in p.relative_to(root).parts for pattern in GENERATED)
            }

        files_a = files(a)
        return files_a == files(b) and all((a / f).read_bytes() == (b / f).read_bytes() for f in files_a)

    def copy_tree(self, source: Path, destination: Path) -> None:
        if self.same_tree(source, destination):
            return
        self.stash(destination)
        self.say(f"installing {destination.relative_to(self.home)}")
        if not self.dry:
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*GENERATED))

    def copy_file(self, source: Path, destination: Path) -> None:
        if destination.exists() and destination.read_bytes() == source.read_bytes():
            return
        self.stash(destination)
        self.say(f"installing {destination.relative_to(self.home)}")
        if not self.dry:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    # ---------------------------------------------------------------------------------------------------------------
    def layout_and_mods(self) -> None:
        for name in (f"{LAYOUT}.json", f"{LAYOUT}.svg"):
            self.copy_file(HERE / "layouts" / name, self.home / "layouts" / name)
        for mod in MODS:
            self.copy_tree(HERE / "mods" / mod, self.home / "mods" / mod)

    def hub(self, force: bool) -> None:
        folder = self.home / "cockpit-hub"
        for name in HUB_FILES:
            source = HERE / "hub" / name
            if not source.exists():
                continue
            self.copy_file(source, folder / name)
            if not IS_WINDOWS and name == "cockpit-hub" and not self.dry:
                (folder / name).chmod(0o755)
        launcher = folder / ("cockpit-hub.cmd" if IS_WINDOWS else "cockpit-hub")
        config = {"bin": str(launcher), "home": str(folder), "cache": str(folder / "cache"), "version": HUB_VERSION}
        path = self.home / "cockpit.json"
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {}
            if Path(str(current.get("bin", ""))) == launcher:
                return
            if not force:
                print(
                    f"NOTE: {path} already points at another cockpit ({current.get('bin')}).\n"
                    "      Leaving it alone, so the inbox keeps using that one.\n"
                    "      Re-run with --force-hub to use the bundled GitHub hub instead."
                )
                return
            self.stash(path)
        self.say("writing cockpit.json")
        if not self.dry:
            path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def keys(self) -> None:
        wanted = json.loads((HERE / "keys.layout-personal.json").read_text(encoding="utf-8"))
        path = self.home / "keys.json"
        if not path.exists():
            print(
                "NOTE: keys.json does not exist yet, so the layout's shortcuts were not added.\n"
                "      Start the Herdr app once, then run this installer again."
            )
            return
        current = json.loads(path.read_text(encoding="utf-8"))
        added = {section: binds for section, binds in wanted.items() if section not in current}
        fixed = []
        for section, stale in STALE_KEYS.items():
            binds = current.get(section)
            if section in added or not isinstance(binds, dict):
                continue
            for key, old in stale.items():
                if binds.get(key) != old:
                    continue
                if key in wanted.get(section, {}):
                    binds[key] = wanted[section][key]
                else:
                    del binds[key]
                fixed.append(f"{section} {key}")
            # Shortcuts this version adds to a section the person already has, where the key is still free.
            for key, value in wanted.get(section, {}).items():
                if key not in binds:
                    binds[key] = value
                    fixed.append(f"{section} {key}")
        if not added and not fixed:
            return
        self.stash(path, keep=True)
        current.update(added)
        if added:
            self.say(f"adding shortcut section(s) {', '.join(added)} to keys.json")
        if fixed:
            self.say(f"updating shortcut(s) {', '.join(fixed)} in keys.json")
        if not self.dry:
            path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    def worktrees(self) -> None:
        """Keeps worktrees beside the rest of the Herdr setup, in <home>/worktrees: sets Herdr's worktrees.directory, which
        both its own worktree feature and the inbox's "assign to agent" use. A directory the person already chose is kept."""
        path = self.home / "settings.json"
        if not path.exists():
            print(
                "NOTE: settings.json does not exist yet, so worktrees stay in Herdr's default folder.\n"
                "      Start the Herdr app once, then run this installer again."
            )
            return
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("NOTE: settings.json is not valid JSON, so the worktrees folder was not set.")
            return
        if not isinstance(current, dict) or (current.get("worktrees") or {}).get("directory"):
            return
        target = self.home / "worktrees"
        try:
            directory = "~/" + target.relative_to(Path.home()).as_posix()
        except ValueError:
            directory = target.as_posix()
        self.stash(path, keep=True)
        self.say(f"setting worktrees.directory to {directory} in settings.json")
        if not self.dry:
            current["worktrees"] = {**(current.get("worktrees") or {}), "directory": directory}
            path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    def brand(self, name: str | None, logo: str | None, shortcut_logo: str | None) -> None:
        """Writes brand.json (the sidebar's workspace name and logos) and copies the logo files into <home>/brand/."""
        if name is None and logo is None and shortcut_logo is None:
            return
        path = self.home / "brand.json"
        try:
            brand = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except json.JSONDecodeError:
            brand = {}
        folder = self.home / "brand"
        if name is not None:
            if not name.strip():
                sys.exit("--brand-name must not be empty.")
            brand["name"] = name.strip()[:40]
        superseded: list[str] = []
        for key, source in (("logo", logo), ("shortcut_logo", shortcut_logo)):
            if source is None:
                continue
            if isinstance(brand.get(key), str):
                superseded.append(brand[key])
            file = Path(source).expanduser()
            if not file.is_file():
                sys.exit(f"{source} is not a file.")
            if file.suffix.lower() not in LOGO_TYPES:
                sys.exit(f"{source}: logos must be one of {', '.join(sorted(LOGO_TYPES))}.")
            data = file.read_bytes()
            # The name carries a content hash, so a replaced logo is never served from an image cache.
            target = folder / f"{key.replace('_', '-')}-{hashlib.sha256(data).hexdigest()[:8]}{file.suffix.lower()}"
            self.say(f"installing {target.relative_to(self.home)}")
            if not self.dry:
                folder.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            brand[key] = target.relative_to(self.home).as_posix()
        self.say(f"writing brand.json ({', '.join(sorted(brand))})")
        if self.dry:
            return
        path.write_text(json.dumps(brand, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Remove only the files this run replaced, and only if the new brand no longer uses them.
        used = {brand.get("logo"), brand.get("shortcut_logo")}
        for old in superseded:
            leftover = self.home / old
            if old not in used and leftover.parent == folder and leftover.is_file():
                leftover.unlink()


def run(command: list[str], env: dict[str, str] | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)


def prerequisites() -> None:
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9 or newer is required (the hub runs on it).")
    herdr = shutil.which("herdr-app")
    if herdr:
        found = re.search(r"\d+(?:\.\d+)+", run([herdr, "--version"]).stdout or "")
        if not found:
            print("WARNING: could not read the Herdr app version.")
        elif found.group(0) != TESTED_HERDR:
            print(
                f"WARNING: this setup was tested with herdr-app {TESTED_HERDR}, you have {found.group(0)}.\n"
                "         Herdr rewrites its shipped mods (tabs, files, changes, menu, prompt, help) at every start,\n"
                "         so the look may differ. If a mod fails `herdr-app check`, see the README section on versions."
            )
    gh = shutil.which("gh")
    if not gh:
        print("WARNING: the GitHub CLI (gh) was not found. The inbox needs it: https://cli.github.com, then `gh auth login`.")
    elif run([gh, "auth", "status"]).returncode != 0:
        print("WARNING: gh is not signed in. Run `gh auth login` for the GitHub inbox to show data.")


def missing_herdr_mods(home: Path) -> list[str]:
    return [mod for mod in HERDR_MODS if not (home / "mods" / mod / "main.js").is_file()]


def verify(home: Path, activate: bool) -> None:
    env = {**os.environ, "HERDR_APP_HOME": str(home)}
    missing = missing_herdr_mods(home)
    if missing:
        print(
            f"WARNING: this Herdr has no {', '.join(missing)} mod, which the layout uses; that part of the window stays empty.\n"
            "         Start the Herdr app once so it writes its mods, or update it (`herdr-app --version`; tested with "
            f"{TESTED_HERDR})."
        )
    herdr = shutil.which("herdr-app")
    if herdr:
        for mod in MODS:
            result = run([herdr, "check", str(home / "mods" / mod)], env=env)
            line = (result.stdout or result.stderr).strip().splitlines()[-1:] or ["(no output)"]
            print(f"  herdr-app check {mod}: {line[0]}")
        if activate:
            result = run([herdr, "do", "layout.switch", json.dumps({"name": LAYOUT})], env=env)
            print("  layout switched" if result.returncode == 0 else f"  could not switch the layout: {result.stdout or result.stderr}")
    else:
        print("  herdr-app is not on PATH: open the Herdr app and press ctrl-shift-l to pick the layout.")
    launcher = home / "cockpit-hub" / ("cockpit-hub.cmd" if IS_WINDOWS else "cockpit-hub")
    if launcher.exists() and (home / "cockpit.json").exists() and json.loads((home / "cockpit.json").read_text(encoding="utf-8")).get("bin") == str(launcher):
        result = run([str(launcher), "hub", "start"])
        try:
            port = json.loads(result.stdout)["port"]
            print(f"  hub started on 127.0.0.1:{port}")
        except (json.JSONDecodeError, KeyError):
            print(f"  hub did not start: {(result.stderr or result.stdout).strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", default=os.environ.get("HERDR_APP_HOME") or str(Path.home() / ".config" / "herdr-app"))
    parser.add_argument("--activate", action="store_true", help="switch the window to the layout afterwards")
    parser.add_argument("--force-hub", action="store_true", help="replace an existing cockpit.json with the bundled hub")
    parser.add_argument("--dry-run", action="store_true", help="print the changes without making them")
    parser.add_argument("--brand-name", help="the workspace name shown in the sidebar header")
    parser.add_argument("--brand-logo", help="a png, jpg, webp or svg shown beside the name")
    parser.add_argument("--brand-shortcut-logo", help="the image on the top-right shortcuts button (default: the logo)")
    parser.add_argument("--only-brand", action="store_true", help="only set the brand; install nothing else")
    args = parser.parse_args()

    home = Path(args.home).expanduser().resolve()
    if not home.is_dir():
        sys.exit(f"{home} is not a Herdr app home. Start the Herdr app once so it creates it, or pass --home.")
    installer = Installer(home, args.dry_run)
    if args.only_brand:
        if args.brand_name is None and args.brand_logo is None and args.brand_shortcut_logo is None:
            sys.exit("--only-brand needs --brand-name, --brand-logo or --brand-shortcut-logo.")
        installer.brand(args.brand_name, args.brand_logo, args.brand_shortcut_logo)
        return 0
    prerequisites()
    print(f"Installing the '{LAYOUT}' layout into {home}")
    installer.layout_and_mods()
    installer.hub(args.force_hub)
    installer.keys()
    installer.worktrees()
    installer.brand(args.brand_name, args.brand_logo, args.brand_shortcut_logo)
    if not args.dry_run:
        print("Checking the install:")
        verify(home, args.activate)
        if installer.backup.exists():
            print(f"Replaced files were backed up under {installer.backup}")
    print("Done. The hub needs `gh auth login`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
