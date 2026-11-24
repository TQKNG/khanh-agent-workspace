"""Fresh-home and repeat-install smoke check for Windows/macOS CI.

Run from the package directory with a disposable destination:
    python tests/smoke_install.py <herdr-home>
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent.parent


def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=PACKAGE, env=env, capture_output=True, text=True, timeout=180)


def fail(result: subprocess.CompletedProcess, label: str) -> None:
    if result.returncode == 0:
        return
    print(f"{label} failed with exit code {result.returncode}.")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    raise SystemExit(result.returncode)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tests/smoke_install.py <disposable-herdr-home>")
    home = Path(sys.argv[1]).resolve()
    if home.exists() and any(home.iterdir()):
        raise SystemExit(f"Refusing to use a non-empty smoke-test home: {home}")
    home.mkdir(parents=True, exist_ok=True)
    (home / "keys.json").write_text("{}\n", encoding="utf-8")
    (home / "settings.json").write_text("{}\n", encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key not in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"}}
    env["GH_CONFIG_DIR"] = str(home / ".gh-config")

    command = [sys.executable, "install.py", "--home", str(home)]
    first = run(command, env)
    fail(first, "Fresh install")
    backups = set((home / ".install-backups" / "khanh-personal").iterdir()) if (home / ".install-backups" / "khanh-personal").exists() else set()
    second = run(command, env)
    fail(second, "Repeat install")
    after = set((home / ".install-backups" / "khanh-personal").iterdir()) if (home / ".install-backups" / "khanh-personal").exists() else set()
    if after != backups:
        raise SystemExit("Repeat install created a backup; install is not idempotent.")

    layout = json.loads((home / "layouts" / "personal.json").read_text(encoding="utf-8"))
    if not layout or not all((home / "mods" / mod / "main.js").is_file() for mod in ("khanh-personal", "khanh-workspace-chrome")):
        raise SystemExit("Fresh install is missing its layout or a package mod.")
    config = json.loads((home / "khanh-personal.json").read_text(encoding="utf-8"))
    launcher = Path(config["bin"])
    health = run([str(launcher), "hub", "health"], env)
    fail(health, "Hub health")
    report = json.loads(health.stdout)
    if report.get("status") != "ok":
        raise SystemExit("Hub did not report healthy.")
    github_status = report.get("capabilities", {}).get("github", {}).get("status")
    if github_status not in {"missing_cli", "login_required"}:
        raise SystemExit(f"Unexpected GitHub capability status: {github_status}")
    herdr = shutil.which("herdr-app")
    herdr_version = "not-installed"
    if herdr:
        version = subprocess.run([herdr, "--version"], capture_output=True, text=True, timeout=10)
        herdr_version = (version.stdout or version.stderr).strip() or "unknown"
    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "herdr_app": herdr_version,
        "fresh_install": "passed",
        "repeat_install": "passed",
        "hub_health": "passed",
        "github_capability": github_status,
        "live_herdr_mod_checks": "passed" if herdr else "skipped-herdr-app-not-installed",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
