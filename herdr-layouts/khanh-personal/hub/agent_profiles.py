"""What each coding agent on this machine is set up with, for the cockpit's Agents page: its version, its instructions file,
its skills, its plugins and its MCP servers, and turning a skill, a plugin or an MCP server on or off.

Instructions and skills come from the agents' own files; plugins and MCP servers from each agent's CLI
(`<agent> plugin list`, `<agent> mcp list`), so they match what the agent itself sees. An MCP server's environment,
headers, arguments and tokens are never read into the profile: only its name, transport, state and the host of its URL.
`claude mcp list` checks every server's health and takes seconds, so profiles are kept a few minutes.

A toggle goes through the agent's own CLI where it has one (Claude's plugins, Copilot's plugins and skills). Codex has
none, so its `config.toml` is changed in exactly one value, after a daily backup, and checked to parse to what it was
with only that value changed. Only an item the profile listed can be toggled. The page edits instructions and SKILL.md
files itself, through Herdr's conflict-checked file writes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib  # Python 3.11 and newer
except ModuleNotFoundError:  # older Pythons (macOS ships 3.9): the tomli package if it is there, else Codex's config.toml is not read
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

NO_TOML = "Reading Codex's config.toml needs Python 3.11 or the tomli package, so its on and off states are not shown and its switches are off."

KINDS = ("agent_profiles",)
ROOT = Path(__file__).resolve().parent
CACHE_SECONDS = 300
CLI_TIMEOUT = 45
MAX_INSTRUCTIONS = 20_000  # characters of an instructions file the page shows
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def home() -> Path:
    return Path.home()


def short(path: Path | str) -> str:
    text, root = str(path), str(home())
    return "~" + text[len(root):] if text == root or text.startswith(root + os.sep) else text


def run(argv: list[str], timeout: int = CLI_TIMEOUT) -> str:
    """A CLI's output; raises RuntimeError with its first error line when it fails. The command is looked up first, so a
    Windows `.cmd` shim (how npm installs the agents there) runs too."""
    argv = [shutil.which(argv[0]) or argv[0], *argv[1:]]
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            stdin=subprocess.DEVNULL, env={**os.environ, "NO_COLOR": "1"}, creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"{Path(argv[0]).stem} is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"`{' '.join(argv[:3])}` did not answer in {timeout} s") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip().splitlines()
        raise RuntimeError(detail[0][:200] if detail else f"`{' '.join(argv[:3])}` exited with {done.returncode}")
    return done.stdout


def host(url: str | None) -> str | None:
    """Only the host of a server's URL: its path and query can carry keys."""
    if not url:
        return None
    try:
        return urlparse(url).hostname or None
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# Files: instructions and skills


def instructions(path: Path) -> dict:
    """An instructions file: where, how long, and its text (cut at MAX_INSTRUCTIONS). @imports are listed, not followed."""
    out = {"path": short(path), "file": str(path), "exists": path.is_file(), "lines": 0, "text": "", "imports": [], "cut": False}
    if not out["exists"]:
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    out["lines"] = len(text.splitlines())
    out["imports"] = re.findall(r"^\s*@\s*(\S+)", text, re.M)
    out["cut"] = len(text) > MAX_INSTRUCTIONS
    out["text"] = text[:MAX_INSTRUCTIONS]
    return out


def unquote(value: str) -> str:
    """A YAML scalar without its quotes: in double quotes \\" and \\\\ are escapes, in single quotes '' is a quote."""
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def frontmatter(text: str) -> dict[str, str]:
    """The `key: value` pairs of a SKILL.md's YAML front matter, enough of YAML for name and description: plain, quoted,
    and folded (`>`) or literal (`|`) values."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: dict[str, str] = {}
    key, block = None, []
    for line in text[3:end].splitlines():
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if top:
            if key and block:
                out[key] = " ".join(block)
            key, value = top.group(1), top.group(2).strip()
            block = []
            if value in (">", "|", ">-", "|-", ">+", "|+"):
                continue
            out[key] = unquote(value)
            key = None if value else key
        elif key and line.strip():
            block.append(line.strip())
    if key and block:
        out[key] = " ".join(block)
    return out


def skill(path: Path, source: str, enabled: bool = True, toggle: bool = False) -> dict:
    meta = frontmatter(path.read_text(encoding="utf-8", errors="replace")[:8000])
    return {
        "name": meta.get("name") or path.parent.name,
        "key": str(path),
        "description": meta.get("description", ""),
        "source": source,
        "enabled": enabled,
        "toggle": toggle,
        "path": short(path),
        "file": str(path),
    }


def skills_in(folder: Path, source: str, disabled: set[str] = frozenset(), nested: bool = False, toggle: bool = False) -> list[dict]:
    """The skills directly in a folder (<folder>/<skill>/SKILL.md); `nested` also looks one folder deeper, for
    bucket folders such as ~/.claude/skills/synced/<bucket>/<skill>."""
    if not folder.is_dir():
        return []
    found = []
    for entry in sorted(folder.iterdir()):
        if not entry.is_dir():
            continue
        file = entry / "SKILL.md"
        if file.is_file():
            found.append(skill(file, source, str(file) not in disabled, toggle))
        elif nested:
            found += skills_in(entry, source, disabled, toggle=toggle)
    return found


# ---------------------------------------------------------------------------------------------------------------------
# Each agent


def claude() -> dict:
    root = home() / ".claude"
    plugins, skills, errors = [], [], []
    skills += skills_in(root / "skills", "personal")
    skills += skills_in(root / "skills" / "synced", "claude.ai", nested=True)
    try:
        for p in json.loads(run(["claude", "plugin", "list", "--json"])):
            name, _, scope = str(p.get("id", "")).partition("@")
            plugins.append({"name": name, "key": p.get("id"), "version": p.get("version"), "enabled": bool(p.get("enabled")), "source": scope or p.get("scope"), "toggle": True})
            if p.get("installPath"):
                skills += skills_in(Path(p["installPath"]) / "skills", f"plugin {name}", nested=False)
    except (RuntimeError, json.JSONDecodeError) as exc:
        errors.append(f"plugins: {exc}")
    mcp = []
    try:
        mcp = claude_mcp(run(["claude", "mcp", "list"]))
    except RuntimeError as exc:
        errors.append(f"MCP: {exc}")
    skills = [s for s in skills if s["name"] != "synced"]
    return {"instructions": instructions(root / "CLAUDE.md"), "skills": skills, "plugins": plugins, "mcp": mcp, "errors": errors}


def claude_mcp(text: str) -> list[dict]:
    """`claude mcp list`'s lines, `<name>: <url or command> [(HTTP)] - <status>`: name, transport, state, host."""
    out = []
    for line in text.splitlines():
        match = re.match(r"^(.+?): (.*?) - (.+)$", line.strip())
        if not match:
            continue
        name, target, state = match.groups()
        transport = "http" if "(HTTP)" in target or target.startswith("http") else "sse" if "(SSE)" in target else "stdio"
        url = re.search(r"https?://\S+", target)
        source = "claude.ai" if name.startswith("claude.ai ") else name.split(":")[1] if name.startswith("plugin:") else "user"
        short_name = name.removeprefix("claude.ai ").split(":")[-1] if name.startswith(("claude.ai ", "plugin:")) else name
        out.append({
            "name": short_name,
            "key": name,
            "transport": transport,
            "host": host(url.group(0)) if url else None,
            "source": source,
            "enabled": "Not configured" not in state and "disabled" not in state.lower(),
            "toggle": False,  # `claude mcp` has no enable or disable
            "status": re.sub(r"^[^A-Za-z]+", "", state).strip(),
        })
    return out


def codex() -> dict:
    root = home() / ".codex"
    errors = [] if tomllib else [NO_TOML]
    config = {}
    if tomllib:
        try:
            config = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            pass
    switches = tomllib is not None
    disabled = {str(e.get("path")) for e in (config.get("skills") or {}).get("config") or [] if e.get("enabled") is False}
    skills = skills_in(root / "skills", "personal", disabled, toggle=switches) + skills_in(root / "skills" / ".system", "built in", disabled, toggle=switches)
    skills += skills_in(home() / ".agents" / "skills", "~/.agents", disabled, toggle=switches)
    plugins = []
    try:
        for p in json.loads(run(["codex", "plugin", "list", "--json"])).get("installed") or []:
            key = p.get("pluginId") or f"{p.get('name')}@{p.get('marketplaceName')}"
            plugins.append({"name": p.get("name"), "key": key, "version": p.get("version"), "enabled": bool(p.get("enabled")), "source": p.get("marketplaceName"), "toggle": switches})
    except (RuntimeError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"plugins: {exc}")
    mcp = []
    configured = set((config.get("mcp_servers") or {}).keys())
    try:
        for s in json.loads(run(["codex", "mcp", "list", "--json"])):
            transport = (s.get("transport") or {})
            mine = s.get("name") in configured
            mcp.append({
                "name": s.get("name"),
                "key": s.get("name"),
                "transport": "http" if "http" in str(transport.get("type")) else str(transport.get("type") or "stdio"),
                "host": host(transport.get("url")),
                "source": "config" if mine else "plugin",
                "enabled": bool(s.get("enabled")),
                "toggle": mine and switches,
                "status": {"o_auth": "Signed in with OAuth", "not_logged_in": "Needs authentication"}.get(s.get("auth_status")),
            })
    except (RuntimeError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"MCP: {exc}")
    return {"instructions": instructions(root / "AGENTS.md"), "skills": skills, "plugins": plugins, "mcp": mcp, "errors": errors}


def copilot_settings() -> dict:
    """~/.copilot/settings.json, which may carry // comments; {} when it cannot be read."""
    try:
        text = (home() / ".copilot" / "settings.json").read_text(encoding="utf-8")
        value = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def copilot() -> dict:
    root = home() / ".copilot"
    errors, skills, plugins, mcp = [], [], [], []
    try:
        for s in json.loads(run(["copilot", "skill", "list", "--json"])):
            skills.append({"name": s.get("name"), "key": s.get("name"), "description": s.get("description") or "", "source": s.get("source") or "", "enabled": bool(s.get("enabled", True)), "toggle": s.get("source") != "builtin", "path": short(s.get("path") or ""), "file": s.get("path") or ""})
    except (RuntimeError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"skills: {exc}")
    try:
        for p in json.loads(run(["copilot", "plugin", "list", "--json"])):
            plugins.append({"name": p.get("name"), "key": p.get("name"), "version": p.get("version"), "enabled": bool(p.get("enabled")), "source": p.get("marketplace") or p.get("source"), "toggle": True})
    except (RuntimeError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"plugins: {exc}")
    off = copilot_settings().get("disabledMcpServers") or []
    try:
        servers = json.loads(run(["copilot", "mcp", "list", "--json"])).get("mcpServers") or {}
        for name, s in servers.items():
            mcp.append({
                "name": name,
                "key": name,
                "transport": "http" if s.get("type") in ("http", "sse") or s.get("url") else "stdio",
                "host": host(s.get("url")),
                "source": s.get("sourcePlugin") or s.get("source") or "config",
                "enabled": not s.get("disabled", False) and name not in off,
                "toggle": True,
                "status": None,
            })
    except (RuntimeError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"MCP: {exc}")
    return {"instructions": instructions(root / "copilot-instructions.md"), "skills": skills, "plugins": plugins, "mcp": mcp, "errors": errors}


# The agents the page shows, in its order: their command, their maker, and how to read their set-up.
AGENTS = [
    {"id": "claude", "label": "Claude", "command": "claude", "maker": "Anthropic", "read": claude},
    {"id": "codex", "label": "Codex", "command": "codex", "maker": "OpenAI", "read": codex},
    {"id": "copilot", "label": "Copilot", "command": "copilot", "maker": "GitHub", "read": copilot},
]


def herdr_home() -> Path:
    """The Herdr app's home: the hub is installed in it."""
    return Path(os.environ.get("HERDR_APP_HOME") or ROOT.parent)


def mark(agent_id: str) -> str | None:
    """The agent's logo for the card, as a path in the Herdr home. Herdr's own (icons/<agent>.svg) declare a size of 1em, so
    they are drawn at 16 px and blur when scaled up: the copy declares 256 px, keeps the colours, draws `currentColor` dark,
    and drops a white backdrop (the card puts the mark on a white disc). Made once, in the hub's cache."""
    source = herdr_home() / "icons" / f"{agent_id}.svg"
    target = ROOT / "cache" / "marks" / f"{agent_id}.svg"
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        return None
    text = re.sub(r'\s(width|height)="[^"]*"', "", text, count=2)
    text = re.sub(r'\sstyle="[^"]*"', "", text, count=1).replace("<svg", '<svg width="256" height="256"', 1)
    text = re.sub(r'<path\b[^>]*\bfill="#fff(?:fff)?"[^>]*?(?:/>|>\s*</path>)', "", text, flags=re.I)
    text = text.replace("currentColor", "#1F2328")
    try:
        if not target.is_file() or target.read_text(encoding="utf-8") != text:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        return target.relative_to(herdr_home()).as_posix()
    except (OSError, ValueError):
        return None


def version(command: str) -> str | None:
    try:
        found = re.search(r"\d+(?:\.\d+)+", run([command, "--version"], timeout=15))
        return found.group(0) if found else None
    except RuntimeError:
        return None


def profile(agent: dict) -> dict:
    base = {**{key: agent[key] for key in ("id", "label", "command", "maker")}, "mark": mark(agent["id"])}
    if not shutil.which(agent["command"]):
        return {**base, "installed": False, "version": None, "instructions": instructions(Path("/nonexistent")), "skills": [], "plugins": [], "mcp": [], "errors": []}
    try:
        found = agent["read"]()
    except Exception as exc:  # One agent's broken set-up must not hide the others.
        found = {"instructions": instructions(Path("/nonexistent")), "skills": [], "plugins": [], "mcp": [], "errors": [str(exc)]}
    return {**base, "installed": True, "version": version(agent["command"]), **found}


class Profiles:
    """All agents' profiles, read side by side and kept CACHE_SECONDS."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.value: dict | None = None
        self.at = 0.0

    def get(self, refresh: bool = False) -> dict:
        with self.lock:
            if self.value and not refresh and time.time() - self.at < CACHE_SECONDS:
                return self.value
            with ThreadPoolExecutor(max_workers=len(AGENTS)) as pool:
                agents = list(pool.map(profile, AGENTS))
            self.value, self.at = {"agents": agents, "updated": time.strftime("%H:%M")}, time.time()
            return self.value

    def reread(self, agent_id: str) -> None:
        """Reads one agent again after a change to it, keeping the others as they were."""
        with self.lock:
            if not self.value:
                return
            fresh = profile(next(a for a in AGENTS if a["id"] == agent_id))
            self.value = {**self.value, "agents": [fresh if a["id"] == agent_id else a for a in self.value["agents"]], "updated": time.strftime("%H:%M")}


PROFILES = Profiles()


def fetch(kind: str, args: dict) -> dict:
    """All profiles; `refresh` reads every agent again, `agent` only that one (after the page saved one of its files)."""
    args = args or {}
    if args.get("agent") in {a["id"] for a in AGENTS}:
        PROFILES.get()
        PROFILES.reread(args["agent"])
    return PROFILES.get(refresh=bool(args.get("refresh")))


# ---------------------------------------------------------------------------------------------------------------------
# Turning a plugin or a skill on or off


def codex_config() -> Path:
    return home() / ".codex" / "config.toml"


def toml_string(value: str) -> str:
    """A TOML basic string: JSON's escaping is TOML's for the characters a path or a plugin id holds."""
    return json.dumps(value)


def set_enabled(text: str, headers: set[str], enabled: bool) -> str | None:
    """config.toml with `enabled` set in the table one of `headers` opens (its own lines, not its sub-tables); None when
    there is no such table."""
    lines = text.splitlines(keepends=True)
    value = f"enabled = {'true' if enabled else 'false'}\n"
    for i, line in enumerate(lines):
        if line.strip() not in headers:
            continue
        for j in range(i + 1, len(lines)):
            if lines[j].lstrip().startswith("["):
                break
            if re.match(r"^\s*enabled\s*=", lines[j]):
                lines[j] = value
                return "".join(lines)
        lines.insert(i + 1, value)
        return "".join(lines)
    return None


def set_codex_plugin(text: str, plugin_id: str, enabled: bool) -> str:
    """config.toml with `[plugins."<id>"] enabled` set, the table added at the end when it is missing."""
    header = f"[plugins.{toml_string(plugin_id)}]"
    changed = set_enabled(text, {header}, enabled)
    if changed is not None:
        return changed
    return text + ("" if text.endswith("\n") or not text else "\n") + f"\n{header}\nenabled = {'true' if enabled else 'false'}\n"


def set_codex_mcp(text: str, name: str, enabled: bool) -> str:
    """config.toml with `[mcp_servers.<name>] enabled` set; the table must be there (a plugin's server has none)."""
    changed = set_enabled(text, {f"[mcp_servers.{name}]", f"[mcp_servers.{toml_string(name)}]"}, enabled)
    return text if changed is None else changed


def set_codex_skill(text: str, path: str, enabled: bool) -> str:
    """config.toml with the `[[skills.config]]` entry for a SKILL.md set on or off, one added at the end when it is missing."""
    lines = text.splitlines(keepends=True)
    value = f"enabled = {'true' if enabled else 'false'}\n"
    wanted = f"path = {toml_string(path)}"
    for i, line in enumerate(lines):
        if line.strip() != "[[skills.config]]":
            continue
        end = next((j for j in range(i + 1, len(lines)) if lines[j].lstrip().startswith("[")), len(lines))
        block = range(i + 1, end)
        if not any(lines[j].strip() == wanted for j in block):
            continue
        for j in block:
            if re.match(r"^\s*enabled\s*=", lines[j]):
                lines[j] = value
                return "".join(lines)
        lines.insert(i + 1, value)
        return "".join(lines)
    if enabled:
        return text  # no entry means on
    return text + ("" if text.endswith("\n") or not text else "\n") + f"\n[[skills.config]]\n{wanted}\n{value}"


def expected_codex(before: dict, kind: str, key: str, enabled: bool) -> dict:
    """What config.toml must parse to after the change: what it was, with only that value changed."""
    want = deepcopy(before)
    if kind == "plugin":
        want.setdefault("plugins", {}).setdefault(key, {})["enabled"] = enabled
        return want
    if kind == "mcp":
        if key in (want.get("mcp_servers") or {}):
            want["mcp_servers"][key]["enabled"] = enabled
        return want
    entries = want.setdefault("skills", {}).setdefault("config", [])
    entry = next((e for e in entries if e.get("path") == key), None)
    if entry is not None:
        entry["enabled"] = enabled
    elif not enabled:
        entries.append({"path": key, "enabled": False})
    if not entries:
        want["skills"].pop("config")
        if not want["skills"]:
            want.pop("skills")
    return want


def change_codex(kind: str, key: str, enabled: bool) -> None:
    if tomllib is None:
        raise RuntimeError(NO_TOML)
    path = codex_config()
    text = path.read_text(encoding="utf-8")
    before = tomllib.loads(text)
    want = expected_codex(before, kind, key, enabled)
    if before == want:
        return
    after_text = {"plugin": set_codex_plugin, "skill": set_codex_skill, "mcp": set_codex_mcp}[kind](text, key, enabled)
    try:
        after = tomllib.loads(after_text)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"the change would break config.toml ({exc}), so it was not made") from exc
    if after_text == text:
        # The value is written in a form this edits line by line does not cover (an inline table or array, say).
        raise RuntimeError(f"config.toml writes its {kind}s in a form the page does not edit; change it there, or with Codex")
    if after != want:
        raise RuntimeError("the change would touch more of config.toml than that one value, so it was not made")
    backup = path.with_name(f"{path.name}.bak-cockpit-{time.strftime('%Y%m%d')}")
    if not backup.exists():
        shutil.copy2(path, backup)
    temp = path.with_name(f".{path.name}.cockpit-{os.getpid()}")
    temp.write_text(after_text, encoding="utf-8")
    os.replace(temp, path)


def toggle(spec: dict) -> str:
    """Turns one plugin or skill an agent's profile listed on or off; the note says what changed."""
    agent_id, kind, key, enabled = spec.get("agent"), spec.get("kind"), spec.get("key"), bool(spec.get("enabled"))
    if kind not in ("plugin", "skill", "mcp"):
        raise RuntimeError(f"Only plugins, skills and MCP servers can be turned on or off, not {kind}.")
    current = next((a for a in PROFILES.get()["agents"] if a["id"] == agent_id), None)
    if not current:
        raise RuntimeError(f"Unknown agent: {agent_id}")
    item = next((i for i in current[{"plugin": "plugins", "skill": "skills", "mcp": "mcp"}[kind]] if i.get("key") == key), None)
    what = "MCP server" if kind == "mcp" else kind
    if not item:
        raise RuntimeError(f"{current['label']} has no {what} {key}: read the agents again.")
    if not item.get("toggle"):
        raise RuntimeError(f"{current['label']} cannot turn its {what} {item['name']} on or off.")
    verb = "enable" if enabled else "disable"
    if agent_id == "claude":
        run(["claude", "plugin", verb, key])
    elif agent_id == "copilot":
        run(["copilot", kind, verb, key])
    else:
        change_codex(kind, key, enabled)
    PROFILES.reread(agent_id)
    return f"{current['label']}: {item['name']} turned {'on' if enabled else 'off'}"


def act(action: str, args: list) -> dict:
    spec = args[0] if args and isinstance(args[0], dict) else {}
    if action != "toggle":
        raise RuntimeError(f"{action} is not something the Agents page does.")
    return {"note": toggle(spec)}
