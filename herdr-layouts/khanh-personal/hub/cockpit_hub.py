"""Local cockpit hub for the Herdr app: a GitHub inbox, and the profiles of the coding agents on this machine.

This service intentionally implements only the small Cockpit protocol surface
the Herdr cockpit mods use here: hub start, subscribe, view, fetch and act.
The inbox view reads GitHub through the signed-in `gh` CLI (see github_inbox.py).
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from socketserver import ThreadingMixIn, StreamRequestHandler, TCPServer

import agent_profiles
import github_inbox
import github_checks
import github_draft
import github_pulls
import github_start


ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
HUB_INFO = CACHE / "hub.json"


def load_json(path: Path) -> dict:
    """A JSON file's object, or {} when there is no file; invalid JSON raises ValueError."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


class Updates:
    """A counter every subscriber waits on, so a refresh wakes them all at once."""

    def __init__(self) -> None:
        self.cond = threading.Condition()
        self.version = 0

    def bump(self) -> None:
        with self.cond:
            self.version += 1
            self.cond.notify_all()

    def wait(self, seen: int, timeout: float) -> None:
        with self.cond:
            self.cond.wait_for(lambda: self.version != seen, timeout)


class HubServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


AGENTS_VIEW = {"tickets": []}
_HEALTH_LOCK = threading.Lock()
_HEALTH_VALUE: dict | None = None
_HEALTH_AT = 0.0


def first_dict(args: list) -> dict:
    return args[0] if args and isinstance(args[0], dict) else {}


def health_report() -> dict:
    """Return redacted dependency readiness without exposing command output or credentials."""
    global _HEALTH_VALUE, _HEALTH_AT
    with _HEALTH_LOCK:
        if _HEALTH_VALUE is not None and time.monotonic() - _HEALTH_AT < 15:
            return json.loads(json.dumps(_HEALTH_VALUE))
    gh = shutil.which("gh")
    authenticated = False
    auth_check = "not_checked"
    if gh:
        try:
            result = subprocess.run(
                [gh, "auth", "status"], capture_output=True, text=True,
                timeout=8, env={**os.environ, "GH_PROMPT_DISABLED": "1"},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            authenticated = result.returncode == 0
            auth_check = "authenticated" if authenticated else "login_required"
        except (OSError, subprocess.TimeoutExpired):
            auth_check = "check_failed"
    agents = github_start.agents(github_start.settings())
    herdr_home = Path(os.environ.get("HERDR_APP_HOME") or ROOT.parent)
    copilot_python = herdr_home / "khanh-personal-hub" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    copilot_sdk = "not_configured"
    if copilot_python.is_file():
        try:
            probe = subprocess.run(
                [str(copilot_python), "-c", "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('copilot') else 1)"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            copilot_sdk = "ready" if probe.returncode == 0 else "sdk_missing"
        except (OSError, subprocess.TimeoutExpired):
            copilot_sdk = "check_failed"
    claude_status = "not_configured"
    try:
        claude_settings = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
        command = str((claude_settings.get("statusLine") or {}).get("command") or "")
        if "claude_status.py" in command:
            claude_status = "ready"
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    report = {
        "status": "ok",
        "version": "0.3.0",
        "capabilities": {
            "github": {
                "status": "ready" if gh and authenticated else "missing_cli" if not gh else auth_check,
                "features": ["inbox", "issue filing", "reviews", "merge", "workflow reruns"],
            },
            "git": {
                "status": "ready" if shutil.which("git") else "missing_cli",
                "features": ["repository discovery", "worktrees", "agent assignment"],
            },
            "agents": [
                {"id": item["id"], "available": bool(item["available"])}
                for item in agents
            ],
            "codex_profile_switches": {
                "status": "ready" if agent_profiles.tomllib is not None else "missing_toml_reader",
            },
            "copilot_usage": {"status": copilot_sdk},
            "claude_usage": {"status": claude_status},
        },
    }
    with _HEALTH_LOCK:
        _HEALTH_VALUE = report
        _HEALTH_AT = time.monotonic()
    return json.loads(json.dumps(report))


# What the inbox's actions write (each returns the note to show, or a dict with the note and more for the mod), and who
# answers each `fetch` kind.
WRITES = {
    "file_issue": lambda args: github_inbox.file_issue(first_dict(args)),
    "submit_review": lambda args: github_pulls.submit_review(first_dict(args)),
    "merge": github_pulls.merge_pull_request,
    "rerun_failed": lambda args: github_checks.rerun_failed(first_dict(args)),
    "start": lambda args: github_start.start(first_dict(args)),
}
FETCHERS = {kind: module.fetch for module in (github_pulls, github_checks, github_start, github_draft, agent_profiles) for kind in module.KINDS}


def with_worktrees(model: dict) -> dict:
    """Gives each issue row the start of the folder an agent started on it works in, so the inbox can show that agent."""
    for section in model.get("sections") or []:
        for row in section.get("children") or []:
            item = row.get("item")
            if row.get("kind") == "ticket" and item and "worktree_prefix" not in item:
                item["worktree_prefix"] = github_start.worktree_prefix(item["repo"], item["number"])
    return model


def view_names(views: list) -> list[str]:
    """Subscriptions arrive as "inbox" or as {"name": "inbox", "args": {...}}."""
    names = []
    for view in views:
        name = view.get("name") if isinstance(view, dict) else view
        if isinstance(name, str) and name not in names:
            names.append(name)
    return names


class Client(StreamRequestHandler):
    def send(self, value: dict) -> None:
        self.wfile.write((json.dumps(value, ensure_ascii=False) + "\n").encode())
        self.wfile.flush()

    def handle(self) -> None:
        try:
            self._handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def view_value(self, name: str) -> dict | None:
        if name == "inbox":
            model = with_worktrees(self.server.inbox.get())
            model["capabilities"] = health_report()["capabilities"]
            return model
        if name == "agents":
            return AGENTS_VIEW
        return None

    def stream(self, names: list[str]) -> None:
        peer = self.client_address[1]
        print(f"{time.strftime('%H:%M:%S')} subscribe #{peer} {names}", flush=True)
        while True:
            seen = self.server.updates.version
            for name in names:
                try:
                    value = self.view_value(name)
                except github_inbox.GitHubError as exc:
                    # Alone, a failing view reports its error; among others it must not take them down with it.
                    if len(names) == 1:
                        raise
                    print(f"{time.strftime('%H:%M:%S')} {name}: {exc}", flush=True)
                    continue
                if value is not None:
                    self.send({"view": name, "value": value})
                    print(f"{time.strftime('%H:%M:%S')} sent {name} to #{peer}", flush=True)
            self.server.updates.wait(seen, 60)

    def act(self, request: dict) -> dict:
        app, action, args = request.get("app"), request.get("action"), request.get("args") or []
        if app == "agents":
            try:
                return {**agent_profiles.act(action, args), "pending": {}}
            except RuntimeError as exc:
                return {"error": str(exc), "pending": {}}
        if app != "inbox":
            return {"error": f"Unsupported cockpit app: {app}", "pending": {}}
        if action == "request_refresh":
            self.server.inbox.invalidate()
            self.server.updates.bump()
            return {"note": "Refreshing from GitHub", "pending": {}, "refreshing": {"inbox": True}}
        if action == "forget_result":
            return {"note": "", "pending": {}}
        write = WRITES.get(action)
        if write:
            result = write(args)
            note, extra = (result.get("note", ""), result) if isinstance(result, dict) else (result, {})
            item = first_dict(args)
            target = f" {item['repo']}#{item.get('number')}" if item.get("repo") else ""
            print(f"{time.strftime('%H:%M:%S')} {action}{target}", flush=True)
            self.server.inbox.invalidate()
            self.server.updates.bump()
            return {**extra, "note": note, "pending": {}, "refreshing": {"inbox": True}}
        return {"error": f"{action} is not supported by the local GitHub hub yet.", "pending": {}}

    def _handle(self) -> None:
        for raw in self.rfile:
            try:
                request = json.loads(raw.decode("utf-8"))
                if request.get("token") != self.server.hub_token:
                    self.send({"error": "Invalid cockpit hub token"})
                    return
                op = request.get("op")
                if op == "subscribe":
                    self.stream(view_names(request.get("views", [])))
                    return
                if op == "view":
                    value = self.view_value(str(request.get("name")))
                    self.send({"value": value} if value is not None else {"error": f"Unknown view: {request.get('name')}"})
                elif op == "fetch":
                    kind = str(request.get("kind"))
                    self.send(FETCHERS.get(kind, github_inbox.fetch)(kind, request.get("args") or {}))
                elif op == "act":
                    self.send(self.act(request))
                elif op == "search":
                    self.send({"entries": []})
                elif op == "events":
                    self.send({"events": []})
                elif op == "history":
                    self.send({"values": []})
                elif op == "health":
                    self.send(health_report())
                elif op == "go":
                    self.send({})
                else:
                    self.send({"error": f"Unsupported cockpit hub operation: {op}"})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return
            except github_inbox.GitHubError as exc:
                self.send({"error": str(exc)})
            except Exception as exc:  # Keep the local hub alive for the next request.
                self.send({"error": f"Cockpit hub error: {exc}"})


def write_hub_info(server: HubServer, token: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    save_json(HUB_INFO, {"port": server.server_address[1], "token": token})


def run_server() -> None:
    token = secrets.token_urlsafe(32)
    server = HubServer(("127.0.0.1", 0), Client)
    server.hub_token = token
    server.inbox = github_inbox.InboxSource()
    server.updates = Updates()
    threading.Thread(target=server.inbox.get, daemon=True).start()  # warm the inbox before the first view asks
    write_hub_info(server, token)
    print(f"Cockpit hub listening on 127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        HUB_INFO.unlink(missing_ok=True)


def live_hub_info() -> dict | None:
    """hub.json's { port, token } when a hub still answers on that port."""
    try:
        info = load_json(HUB_INFO)
        port = int(info["port"])
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return {"port": port, "token": info["token"]}
    except (KeyError, ValueError, TypeError, OSError):
        return None


def start_hub() -> int:
    """What the mods run to get a hub: start one in the background, print { port, token }, exit."""
    info = live_hub_info()
    if not info:
        CACHE.mkdir(parents=True, exist_ok=True)
        HUB_INFO.unlink(missing_ok=True)
        flags = 0
        if os.name == "nt":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        with open(CACHE / "hub.log", "ab") as log:
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "hub", "serve"],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                cwd=ROOT,
                creationflags=flags,
                start_new_session=os.name != "nt",
                close_fds=True,
            )
        deadline = time.time() + 15
        while time.time() < deadline and not info:
            time.sleep(0.2)
            info = live_hub_info()
    if not info:
        print("the cockpit hub did not start; see cockpit-hub/cache/hub.log", file=sys.stderr)
        return 1
    print(json.dumps(info))
    return 0


def check_health() -> int:
    """Ask the running hub for a health report; print only the redacted JSON response."""
    info = live_hub_info()
    if not info:
        print("hub is not running", file=sys.stderr)
        return 1
    try:
        with socket.create_connection(("127.0.0.1", int(info["port"])), timeout=5) as sock:
            sock.sendall((json.dumps({"op": "health", "token": info["token"]}) + "\n").encode())
            with sock.makefile("rb") as stream:
                result = json.loads(stream.readline().decode("utf-8"))
        if result.get("status") != "ok":
            raise ValueError("hub returned an invalid health response")
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"hub health check failed: {exc}", file=sys.stderr)
        return 1


def restore_home() -> None:
    """The mods start the hub with HOME set to the cockpit's own folder, so `gh` would miss its login and `git` its config.
    The hub keeps its files beside this script, so it puts back the account's real home for the programs it runs."""
    if os.name == "nt":
        return
    import pwd

    real = pwd.getpwuid(os.getuid()).pw_dir
    if real and os.environ.get("HOME") != real:
        os.environ["HOME"] = real


def main() -> int:
    restore_home()
    command = sys.argv[1:] or ["hub", "start"]
    if command[:2] == ["hub", "start"]:
        return start_hub()
    if command[:2] == ["hub", "serve"]:
        run_server()
        return 0
    if command[:2] == ["hub", "health"]:
        return check_health()
    print("Usage: cockpit-hub hub start | hub serve | hub health", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
