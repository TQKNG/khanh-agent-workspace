#!/usr/bin/env python3
"""PostToolUse check: an .mdx page that embeds /images/diagrams/<name>.png needs
diagrams/src/<name>.drawio, and a .drawio file must still carry the template title block.
Exit 2 with a message on stderr so Claude sees the problem and fixes it. Silent otherwise."""
import json, re, sys
from pathlib import Path

try:
    data = json.load(sys.stdin)
    path = Path((data.get("tool_input") or {}).get("file_path", ""))
except Exception:
    sys.exit(0)

def repo_root(p):
    for d in [p.parent, *p.parent.parents]:
        if (d / "docs.json").exists() or (d / "mint.json").exists():
            return d
    return None

problems = []
if path.suffix == ".mdx" and path.exists():
    root = repo_root(path)
    if root:
        for name in set(re.findall(r"/images/diagrams/([\w.\-]+?)\.png", path.read_text(encoding="utf-8", errors="ignore"))):
            if not (root / "diagrams" / "src" / f"{name}.drawio").exists():
                problems.append(f"{path.name} embeds {name}.png but diagrams/src/{name}.drawio is missing. "
                                f"Create it from a template (/new-diagram) instead of drawing from scratch.")
            ci = (root / ".github" / "workflows" / "export-diagrams.yml").exists()
            if not ci and not (root / "images" / "diagrams" / f"{name}.png").exists():
                problems.append(f"{path.name} embeds {name}.png but images/diagrams/{name}.png does not exist. Export it.")
elif path.suffix == ".drawio" and path.exists():
    t = path.read_text(encoding="utf-8", errors="ignore")
    for needle in ("Document Title", "Document Number", "Version Number", "Prepared By", "Legend"):
        if needle not in t:
            problems.append(f"{path.name} is missing '{needle}'. Diagrams must keep the template title block and legend.")
if problems:
    print("diagram-standards: " + " | ".join(problems), file=sys.stderr)
    sys.exit(2)
