#!/usr/bin/env python3
"""Parse Codex session JSONL files into a per-thread usage audit."""
from __future__ import annotations
import argparse, json, os
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

def iso(value):
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception: return None

def parse_file(path):
    meta = None; records = []; models = set(); warnings = []; first = last = None
    try:
        with path.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                try: obj = json.loads(line)
                except json.JSONDecodeError: warnings.append(f"malformed JSON line {line_no}"); continue
                stamp = iso(obj.get("timestamp", ""))
                if stamp and (first is None or stamp < first): first = stamp
                if stamp and (last is None or stamp > last): last = stamp
                payload = obj.get("payload", {}) or {}
                if obj.get("type") == "session_meta":
                    candidate_id = payload.get("id")
                    candidate_session = payload.get("session_id")
                    if meta is None or (candidate_id and candidate_session and candidate_id != candidate_session and meta.get("id") == meta.get("session_id")):
                        meta = payload
                if obj.get("type") == "token_usage_record": records.append(payload)
                if obj.get("type") == "response_item":
                    model = payload.get("model") or (payload.get("response", {}) or {}).get("model")
                    if model: models.add(model)
                for model in (payload.get("model"), (payload.get("collaboration_mode", {}) or {}).get("settings", {}).get("model")):
                    if model: models.add(model)
    except OSError as error: return None, [str(error)]
    if not meta: warnings.append("missing session_meta")
    metadata_stamp = iso((meta or {}).get("timestamp", ""))
    if metadata_stamp and (first is None or metadata_stamp < first): first = metadata_stamp
    usage = defaultdict(int); seen = set(); requests = 0
    for record in records:
        response_id = record.get("response_id")
        if response_id and response_id in seen: continue
        if response_id: seen.add(response_id)
        values = record.get("usage", {}) or {}; requests += 1
        for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens"):
            usage[key] += int(values.get(key) or 0)
    if not records: warnings.append("no token usage records")
    session_id = (meta or {}).get("id") or (meta or {}).get("session_id")
    duration = (last - first).total_seconds() if first and last else None
    return {"id": session_id, "parent_thread_id": (meta or {}).get("parent_thread_id"), "path": str(path), "models": sorted(models), "usage": dict(usage), "model_requests": requests, "start": first.isoformat() if first else None, "end": last.isoformat() if last else None, "duration_seconds": duration, "warnings": warnings}, []

def audit(root, thread_id):
    entries = []
    for path in Path(root).rglob("*.jsonl"):
        item, _ = parse_file(path)
        if item and item.get("id"): entries.append(item)
    by_id = {item["id"]: item for item in entries}; children = defaultdict(list)
    for item in entries:
        if item.get("parent_thread_id"): children[item["parent_thread_id"]].append(item["id"])
    found = []; queue = deque([thread_id]); visited = set()
    while queue:
        current = queue.popleft()
        if current in visited: continue
        visited.add(current)
        if current in by_id:
            found.append(by_id[current]); queue.extend(children[current])
    return {"root_thread_id": thread_id, "sessions": found, "missing": sorted(visited - set(by_id))}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("thread_id"); parser.add_argument("--root", default=os.path.expanduser("~/.codex/sessions")); parser.add_argument("--pretty", action="store_true"); args = parser.parse_args()
    print(json.dumps(audit(args.root, args.thread_id), indent=2 if args.pretty else None))

if __name__ == "__main__": main()
