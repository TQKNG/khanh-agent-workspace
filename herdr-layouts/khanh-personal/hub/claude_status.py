"""Capture Claude Code's documented status-line usage payload for Herdr."""
import json
import sys
import time
from pathlib import Path


def main():
    data = json.load(sys.stdin)
    limits = data.get("rate_limits") or {}
    if limits:
        target = Path.home() / ".config" / "herdr-app" / "cockpit-hub" / "claude-usage.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"observed_at": time.time(), "rate_limits": limits}), encoding="utf-8")
        temporary.replace(target)
    parts = []
    for key, name in (("five_hour", "5h"), ("seven_day", "7d")):
        used = (limits.get(key) or {}).get("used_percentage")
        if isinstance(used, (int, float)):
            parts.append(f"{name}: {used:.0f}%")
    print("Claude " + "  ".join(parts) if parts else "Claude")


if __name__ == "__main__":
    main()
