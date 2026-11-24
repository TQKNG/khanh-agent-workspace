#!/usr/bin/env python3
"""Installs the personal Herdr layout, its mods and its local hub into a Herdr app home.

    python install.py                 install into ~/.config/herdr-app (or $HERDR_APP_HOME)
    python install.py --activate      also switch the window to the layout
    python install.py --home DIR      install into another Herdr home
    python install.py --dry-run       print what would change and touch nothing
    python install.py --brand-name "Acme Workspace" --brand-logo logo.png
                                      set your own name and logo (also works with --only-brand)

Anything it replaces is backed up under <home>/.install-backups/khanh-personal/<time>/ first.
It keeps worktrees in <home>/worktrees by setting Herdr's worktrees.directory, unless one is already set.
It never touches credentials.json or data/ under the hub folder, and it leaves an
existing khanh-personal.json alone when that points at another cockpit (use --force-hub).
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
import tempfile
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
LAYOUT = "personal"
MODS = ["khanh-personal", "khanh-workspace-chrome"]
# Herdr's own mods the layout shows (tabs, files, changes) or opens (help, picker): they come with Herdr, not with this
# package, so the installer says which a Herdr version lacks rather than leaving a blank space in the window.
HERDR_MODS = ["tabs", "files", "changes", "help", "picker"]
HUB_FILES = ["cockpit_hub.py", "github_inbox.py", "github_pulls.py", "github_checks.py", "github_start.py", "github_draft.py", "issue_format.py", "agent_profiles.py", "agent_activity.py", "copilot_quota.py", "claude_status.py", "worker-prompt.md", "issue-draft-prompt.md", "issue-task-template.md", "cockpit-hub", "cockpit-hub.cmd"]
SCAFFOLD_FILES = ["SKILL.md", "assets/starter/.github/ISSUE_TEMPLATE/bug_report.md", "assets/starter/.github/ISSUE_TEMPLATE/feature_request.md", "assets/starter/.github/pull_request_template.md"]
HUB_VERSION = "0.3.0"
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
        self.backup = home / ".install-backups" / "khanh-personal" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.source_root = HERE
        self.scaffold_root = HERE.parents[1] / "skills" / "repo-scaffold"
        self.changes: dict[str, dict[str, bool]] = {}

    def say(self, message: str) -> None:
        print(("[dry-run] " if self.dry else "") + message)

    def stash(self, path: Path, keep: bool = False) -> None:
        """Puts an existing file or folder in the backup folder: moved out of the way, or copied when `keep` is set."""
        if not path.exists():
            return
        self.record_change(path)
        target = self.backup / path.relative_to(self.home)
        self.say(f"backing up {path.relative_to(self.home)} -> {target.relative_to(self.home)}")
        if self.dry:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if keep and path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            (shutil.copy2 if keep else shutil.move)(str(path), str(target))
        entry = self.changes.setdefault(path.relative_to(self.home).as_posix(), {"existed": True, "backed_up": False})
        entry["backed_up"] = True

    def record_change(self, path: Path) -> None:
        relative = path.relative_to(self.home).as_posix()
        self.changes.setdefault(relative, {"existed": path.exists(), "backed_up": False})

    def save_transaction(self) -> None:
        if self.dry or not self.changes:
            return
        self.backup.mkdir(parents=True, exist_ok=True)
        (self.backup / "manifest.json").write_text(
            json.dumps({"package": "khanh-personal", "changes": self.changes}, indent=2) + "\n",
            encoding="utf-8",
        )

    def rollback(self, backup: Path | None = None) -> bool:
        """Restore the latest package transaction without reverting user settings or runtime state."""
        root = self.home / ".install-backups" / "khanh-personal"
        candidates = [backup] if backup else sorted(
            (p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").is_file()), reverse=True
        ) if root.exists() else []
        source = next((p for p in candidates if p and (p / "manifest.json").is_file()), None)
        if source is None:
            print("No khanh-personal transaction is available to roll back.")
            return False
        try:
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"The rollback manifest is unreadable: {source}")
            return False
        preserved = {"brand.json"}
        rollback_snapshot = root / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-rollback")
        rollback_changes: dict[str, dict[str, bool]] = {}
        print(f"Rolling back {source.name}; preserving user settings, brand, credentials, caches and runtime state.")
        for relative, item in manifest.get("changes", {}).items():
            if relative in preserved:
                continue
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                print(f"Skipping unsafe rollback path: {relative}")
                continue
            target = (self.home / relative_path).resolve()
            saved = (source / relative_path).resolve()
            if not target.is_relative_to(self.home.resolve()) or not saved.is_relative_to(source.resolve()):
                print(f"Skipping rollback path outside its package directories: {relative}")
                continue
            if relative == "keys.json" and target.is_file() and saved.is_file():
                self.rollback_keys(target, saved)
                continue
            if relative == "settings.json" and target.is_file() and saved.is_file():
                self.rollback_worktree_setting(target, saved)
                continue
            existed_now = target.exists()
            if not item.get("existed"):
                self.say(f"removing {relative}")
                if not self.dry:
                    if target.is_dir():
                        current_target = rollback_snapshot / Path(relative)
                        current_target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(target), str(current_target))
                    elif target.exists():
                        current_target = rollback_snapshot / Path(relative)
                        current_target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(target), str(current_target))
                    rollback_changes[relative] = {"existed": existed_now, "backed_up": existed_now}
                continue
            if not item.get("backed_up") or not saved.exists():
                continue
            self.say(f"restoring {relative}")
            if self.dry:
                continue
            current_target = rollback_snapshot / Path(relative)
            current_target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_dir():
                shutil.move(str(target), str(current_target))
            elif target.exists():
                shutil.move(str(target), str(current_target))
            target.parent.mkdir(parents=True, exist_ok=True)
            if saved.is_dir():
                shutil.copytree(saved, target, dirs_exist_ok=True)
            else:
                shutil.copy2(saved, target)
            rollback_changes[relative] = {"existed": existed_now, "backed_up": existed_now}
        if not self.dry and rollback_changes:
            rollback_snapshot.mkdir(parents=True, exist_ok=True)
            (rollback_snapshot / "manifest.json").write_text(
                json.dumps({"package": "khanh-personal", "changes": rollback_changes}, indent=2) + "\n",
                encoding="utf-8",
            )
        return True

    def rollback_keys(self, current_path: Path, saved_path: Path) -> None:
        try:
            current = json.loads(current_path.read_text(encoding="utf-8"))
            previous = json.loads(saved_path.read_text(encoding="utf-8"))
            wanted = json.loads((HERE / "keys.layout-personal.json").read_text(encoding="utf-8"))["layout:personal"]
        except (OSError, json.JSONDecodeError, KeyError):
            return
        if not isinstance(current, dict) or not isinstance(previous, dict):
            return
        binds = current.get("layout:personal")
        old_binds = previous.get("layout:personal") if isinstance(previous.get("layout:personal"), dict) else {}
        if not isinstance(binds, dict):
            return
        changed = False
        for key, package_value in wanted.items():
            if binds.get(key) != package_value:
                continue
            if key in old_binds:
                binds[key] = old_binds[key]
            else:
                binds.pop(key, None)
            changed = True
        if changed:
            if not binds:
                current.pop("layout:personal", None)
            current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    def rollback_worktree_setting(self, current_path: Path, saved_path: Path) -> None:
        try:
            current = json.loads(current_path.read_text(encoding="utf-8"))
            previous = json.loads(saved_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(current, dict) or not isinstance(previous, dict):
            return
        current_worktrees = current.get("worktrees")
        previous_worktrees = previous.get("worktrees")
        if not isinstance(current_worktrees, dict) or current_worktrees.get("directory") != self.default_worktrees_directory():
            return
        if isinstance(previous_worktrees, dict) and "directory" in previous_worktrees:
            return
        current_worktrees.pop("directory", None)
        if not current_worktrees:
            current.pop("worktrees", None)
        current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

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
        self.record_change(destination)
        self.stash(destination)
        self.say(f"installing {destination.relative_to(self.home)}")
        if not self.dry:
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*GENERATED))

    def copy_file(self, source: Path, destination: Path) -> None:
        if destination.exists() and destination.read_bytes() == source.read_bytes():
            return
        self.record_change(destination)
        self.stash(destination)
        self.say(f"installing {destination.relative_to(self.home)}")
        if not self.dry:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    # ---------------------------------------------------------------------------------------------------------------
    def layout_and_mods(self) -> None:
        for name in (f"{LAYOUT}.json", f"{LAYOUT}.svg"):
            self.copy_file(self.source_root / "layouts" / name, self.home / "layouts" / name)
        for mod in MODS:
            self.copy_tree(self.source_root / "mods" / mod, self.home / "mods" / mod)

    def hub(self, force: bool) -> None:
        folder = self.home / "khanh-personal-hub"
        for name in HUB_FILES:
            source = self.source_root / "hub" / name
            if not source.exists():
                continue
            self.copy_file(source, folder / name)
            if not IS_WINDOWS and name == "cockpit-hub" and not self.dry:
                (folder / name).chmod(0o755)
        scaffold = self.scaffold_root
        for name in SCAFFOLD_FILES:
            self.copy_file(scaffold / name, folder / "repo-scaffold" / name)
        launcher = folder / ("cockpit-hub.cmd" if IS_WINDOWS else "cockpit-hub")
        config = {"bin": str(launcher), "home": str(folder), "cache": str(folder / "cache"), "version": HUB_VERSION}
        path = self.home / "khanh-personal.json"
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
        self.say("writing khanh-personal.json")
        if not self.dry:
            self.record_change(path)
            path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def keys(self) -> None:
        wanted = json.loads((self.source_root / "keys.layout-personal.json").read_text(encoding="utf-8"))
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
                elif binds[key] == value.replace("khanh-personal.", "personal."):
                    # Migrate only the package's previous command; preserve user edits.
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
        directory = self.default_worktrees_directory()
        self.stash(path, keep=True)
        self.say(f"setting worktrees.directory to {directory} in settings.json")
        if not self.dry:
            current["worktrees"] = {**(current.get("worktrees") or {}), "directory": directory}
            path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    def default_worktrees_directory(self) -> str:
        target = self.home / "worktrees"
        if os.name == "nt":
            return target.as_posix()
        try:
            return "~/" + target.relative_to(Path.home()).as_posix()
        except ValueError:
            return target.as_posix()

    def uninstall(self) -> None:
        """Remove unchanged package-owned files, leaving user edits and runtime state in place."""
        for name in (f"{LAYOUT}.json", f"{LAYOUT}.svg"):
            source, target = self.source_root / "layouts" / name, self.home / "layouts" / name
            if target.is_file() and source.is_file() and target.read_bytes() == source.read_bytes():
                self.record_change(target)
                self.stash(target, keep=True)
                self.say(f"removing {target.relative_to(self.home)}")
                if not self.dry:
                    target.unlink()
            elif target.exists():
                self.say(f"preserving locally changed {target.relative_to(self.home)}")
        for mod in MODS:
            source, target = self.source_root / "mods" / mod, self.home / "mods" / mod
            if self.same_tree(source, target) and not target.is_symlink():
                self.record_change(target)
                self.stash(target, keep=True)
                self.say(f"removing {target.relative_to(self.home)}")
                if not self.dry:
                    shutil.rmtree(target)
            elif target.exists():
                self.say(f"preserving locally changed {target.relative_to(self.home)}")
        hub = self.home / "khanh-personal-hub"
        for name in HUB_FILES:
            source, target = self.source_root / "hub" / name, hub / name
            if source.is_file() and target.is_file() and source.read_bytes() == target.read_bytes():
                self.record_change(target)
                self.stash(target, keep=True)
                self.say(f"removing {target.relative_to(self.home)}")
                if not self.dry:
                    target.unlink()
            elif target.exists():
                self.say(f"preserving locally changed {target.relative_to(self.home)}")
        for name in SCAFFOLD_FILES:
            source, target = self.scaffold_root / name, hub / "repo-scaffold" / name
            if source.is_file() and target.is_file() and source.read_bytes() == target.read_bytes():
                self.record_change(target)
                self.stash(target, keep=True)
                self.say(f"removing {target.relative_to(self.home)}")
                if not self.dry:
                    target.unlink()
        config = self.home / "khanh-personal.json"
        if config.is_file():
            try:
                value = json.loads(config.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                value = {}
            launcher = hub / ("cockpit-hub.cmd" if IS_WINDOWS else "cockpit-hub")
            if isinstance(value, dict) and Path(str(value.get("bin", ""))) == launcher:
                self.record_change(config)
                self.stash(config, keep=True)
                self.say("removing khanh-personal.json")
                if not self.dry:
                    config.unlink()
        self.uninstall_keys()
        self.uninstall_worktree_setting()

    def uninstall_keys(self) -> None:
        path = self.home / "keys.json"
        if not path.is_file():
            return
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            wanted = json.loads((self.source_root / "keys.layout-personal.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.say("preserving unreadable keys.json")
            return
        if not isinstance(current, dict):
            self.say("preserving keys.json with an unsupported structure")
            return
        section = wanted.get("layout:personal", {})
        binds = current.get("layout:personal")
        if not isinstance(binds, dict):
            return
        removed = [key for key, value in section.items() if binds.get(key) == value]
        if not removed:
            return
        self.record_change(path)
        self.stash(path, keep=True)
        for key in removed:
            del binds[key]
        if not binds:
            current.pop("layout:personal", None)
        self.say(f"removing unchanged package shortcuts: {', '.join(removed)}")
        if not self.dry:
            path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    def uninstall_worktree_setting(self) -> None:
        path = self.home / "settings.json"
        if not path.is_file():
            return
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            worktrees = current.get("worktrees")
        except (json.JSONDecodeError, AttributeError):
            return
        if not isinstance(worktrees, dict) or worktrees.get("directory") != self.default_worktrees_directory():
            return
        self.record_change(path)
        self.stash(path, keep=True)
        worktrees.pop("directory", None)
        if not worktrees:
            current.pop("worktrees", None)
        self.say("removing the default worktrees.directory added by this package")
        if not self.dry:
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
        sys.exit(f"Python 3.9 or newer is required; found {sys.version.split()[0]}. On Windows, try `py -3`.")
    if not shutil.which("git"):
        print("WARNING: Git was not found. Layout rendering can work, but repository and worktree features need Git on PATH.")
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


def verify(home: Path, activate: bool) -> list[str]:
    errors: list[str] = []
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
            passed = result.returncode == 0 and "check passed" in "\n".join((result.stdout, result.stderr)).lower()
            print(f"  herdr-app check {mod}: {line[0]}")
            if not passed:
                errors.append(f"Herdr mod check failed for {mod}.")
        if activate and not errors:
            result = run([herdr, "do", "layout.switch", json.dumps({"name": LAYOUT})], env=env)
            if result.returncode == 0:
                print("  layout switched")
            else:
                errors.append(f"Could not activate layout: {(result.stdout or result.stderr).strip()}")
                print(f"  could not switch the layout: {result.stdout or result.stderr}")
    else:
        print("  herdr-app is not on PATH: open the Herdr app and press ctrl-shift-l to pick the layout.")
    launcher = home / "khanh-personal-hub" / ("cockpit-hub.cmd" if IS_WINDOWS else "cockpit-hub")
    if launcher.exists() and (home / "khanh-personal.json").exists() and json.loads((home / "khanh-personal.json").read_text(encoding="utf-8")).get("bin") == str(launcher):
        result = run([str(launcher), "hub", "start"])
        try:
            port = json.loads(result.stdout)["port"]
            if result.returncode != 0 or not isinstance(port, int) or not 1 <= port <= 65535:
                raise ValueError("invalid hub response")
            print(f"  hub started on 127.0.0.1:{port}")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            detail = (result.stderr or result.stdout).strip() or "no valid port was returned"
            errors.append(f"Hub startup failed: {detail}")
            print(f"  hub did not start: {detail}")
        if not errors:
            checked = run([str(launcher), "hub", "health"])
            try:
                report = json.loads(checked.stdout)
                if checked.returncode != 0 or report.get("status") != "ok":
                    raise ValueError("the hub did not report healthy")
                print("  hub health: ok")
                for name, capability in report.get("capabilities", {}).items():
                    if isinstance(capability, dict) and capability.get("status") not in ("ready", "ok"):
                        print(f"  capability {name}: {capability.get('status')}")
                    elif name == "agents" and isinstance(capability, list) and not any(agent.get("available") for agent in capability):
                        print("  capability agents: no supported agent CLI found")
            except (json.JSONDecodeError, AttributeError, ValueError) as exc:
                detail = (checked.stderr or str(exc)).strip()
                errors.append(f"Hub health check failed: {detail}")
                print(f"  hub health check failed: {detail}")
    return errors


def validate_stage(stage: Path, home: Path) -> list[str]:
    """Validate package structure and both mods before touching the active installation."""
    errors: list[str] = []
    try:
        json.loads((stage / "layouts" / f"{LAYOUT}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Staged layout is missing or invalid: {exc}")
    for name in (f"{LAYOUT}.svg", "keys.layout-personal.json", *HUB_FILES):
        if not (stage / ("hub" if name in HUB_FILES else "layouts" if name.endswith(".svg") else "") / name).is_file():
            errors.append(f"Staged package file is missing: {name}")
    for mod in MODS:
        folder = stage / "mods" / mod
        if not (folder / "mod.json").is_file() or not (folder / "main.js").is_file():
            errors.append(f"Staged mod is incomplete: {mod}")
    scaffold = stage / "repository-resources" / "skills" / "repo-scaffold"
    for name in SCAFFOLD_FILES:
        if not (scaffold / name).is_file():
            errors.append(f"Staged repository resource is missing: {name}")
    if errors:
        return errors
    herdr = shutil.which("herdr-app")
    if not herdr:
        print("NOTE: herdr-app was not found on PATH; staged mod checks were skipped.")
        return errors
    env = {**os.environ, "HERDR_APP_HOME": str(home)}
    for mod in MODS:
        result = run([herdr, "check", str(stage / "mods" / mod)], env=env)
        output = "\n".join((result.stdout, result.stderr))
        if result.returncode != 0 or "check passed" not in output.lower():
            errors.append(f"Staged Herdr mod check failed for {mod}: {(result.stderr or result.stdout).strip()}")
        else:
            print(f"  staged mod check {mod}: passed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", default=os.environ.get("HERDR_APP_HOME") or str(Path.home() / ".config" / "herdr-app"))
    parser.add_argument("--activate", action="store_true", help="switch the window to the layout afterwards")
    parser.add_argument("--force-hub", action="store_true", help="replace this package's khanh-personal.json hub configuration")
    parser.add_argument("--dry-run", action="store_true", help="print the changes without making them")
    parser.add_argument("--brand-name", help="the workspace name shown in the sidebar header")
    parser.add_argument("--brand-logo", help="a png, jpg, webp or svg shown beside the name")
    parser.add_argument("--brand-shortcut-logo", help="the image on the top-right shortcuts button (default: the logo)")
    parser.add_argument("--only-brand", action="store_true", help="only set the brand; install nothing else")
    parser.add_argument("--rollback", action="store_true", help="restore the previous khanh-personal package transaction")
    parser.add_argument("--uninstall", action="store_true", help="remove unchanged package files and preserve user data")
    args = parser.parse_args()

    if args.rollback and args.uninstall:
        parser.error("--rollback and --uninstall cannot be used together")

    home = Path(args.home).expanduser().resolve()
    if not home.is_dir():
        sys.exit(f"{home} is not a Herdr app home. Start the Herdr app once so it creates it, or pass --home.")
    installer = Installer(home, args.dry_run)
    if args.rollback:
        return 0 if installer.rollback() else 1
    if args.uninstall:
        installer.uninstall()
        installer.save_transaction()
        if args.dry_run:
            print("Uninstall dry run complete; no files were changed.")
        elif installer.changes:
            print(f"Package-owned files removed; backups saved under {installer.backup}")
        if not args.dry_run:
            print("User settings, brand, credentials, hub runtime data, caches and repositories were preserved.")
        return 0
    if args.only_brand:
        if args.brand_name is None and args.brand_logo is None and args.brand_shortcut_logo is None:
            sys.exit("--only-brand needs --brand-name, --brand-logo or --brand-shortcut-logo.")
        installer.brand(args.brand_name, args.brand_logo, args.brand_shortcut_logo)
        return 0
    prerequisites()
    print(f"Staging the '{LAYOUT}' layout for {home}")
    with tempfile.TemporaryDirectory(prefix=".khanh-personal-stage-", dir=home) as temporary:
        stage = Path(temporary) / "package"
        shutil.copytree(
            HERE,
            stage,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.error", "*.d.ts", "jsconfig.json", "tests", "cache", ".venv", "credentials.json", "data"),
        )
        staged_scaffold = stage / "repository-resources" / "skills" / "repo-scaffold"
        shutil.copytree(HERE.parents[1] / "skills" / "repo-scaffold", staged_scaffold)
        errors = validate_stage(stage, home)
        if errors:
            print("Staged package validation failed; the active installation was not changed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        installer.source_root = stage
        installer.scaffold_root = staged_scaffold
        print(f"Activating validated package into {home}")
        try:
            installer.layout_and_mods()
            installer.hub(args.force_hub)
            installer.keys()
            installer.worktrees()
            installer.brand(args.brand_name, args.brand_logo, args.brand_shortcut_logo)
            installer.save_transaction()
        except Exception:
            installer.save_transaction()
            installer.rollback(installer.backup)
            raise
        if not args.dry_run:
            print("Checking the active install:")
            errors = verify(home, args.activate)
            if installer.backup.exists():
                print(f"Rollback backup: {installer.backup}")
            if errors:
                print("Post-install validation failed; restoring the previous package files.")
                installer.rollback(installer.backup)
                for error in errors:
                    print(f"  - {error}")
                return 1
    print("Done. The hub needs `gh auth login` for GitHub features.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
