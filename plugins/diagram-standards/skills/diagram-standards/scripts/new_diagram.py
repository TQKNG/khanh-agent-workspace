#!/usr/bin/env python3
"""Copy an approved draw.io template and fill its title block.

usage: new_diagram.py <type-key> <doc-number> --title "<title>" --author "<name>"
         [--version 0.0.1] [--date YYYY.MM.DD] [--out-dir diagrams/src] [--force]
"""
import argparse, datetime, html, re, shutil, sys
from pathlib import Path

TPL = Path(__file__).resolve().parent.parent / "templates"
TYPES = {
    "sc":            ("system-context.drawio",  dict(title="t1",  number="t2",  version="t3", author="t4", date="t5")),
    "bc":            ("business-context.drawio", dict(title="v4", number="v6",  version="v7", author="v9", date="v10")),
    "l1-whitebox":   ("l1-whitebox.drawio",     dict(title="v4", number="v6",  version="v7", author="v9", date="v10")),
    "l1-deployment": ("l1-deployment.drawio",   dict(title="v224", number="v225", version="v226", author="v227", date="v228")),
    "l2-component":  ("l2-component.drawio",    dict(title="v4", number="v6",  version="v7", author="v9", date="v10")),
}

def set_text(xml, cell_id, new):
    """Replace the text after the first ': ' (or 'Label: ') in the cell's value, keeping markup."""
    m = re.search(r'(<mxCell id="%s"[^>]*? value=")([^"]*)(")' % re.escape(cell_id), xml)
    if not m:
        sys.exit(f"title-block cell '{cell_id}' not found in template")
    raw = m.group(2)
    esc = html.escape(new, quote=False)
    # the editable text is the last text node before the closing </span> (or end of value)
    if "&lt;/span&gt;" in raw:
        idx = raw.rfind("&lt;/span&gt;")
        head = raw[:idx]
        pos = head.rfind("&gt;") + 1
        old = head[pos:]
        prefix = old.split(": ", 1)[0] + ": " if ": " in old else ""
        out = head[:pos] + prefix + esc + raw[idx:]
    else:
        pos = raw.rfind("&gt;") + 1
        old = raw[pos:]
        prefix = old.split(": ", 1)[0] + ": " if ": " in old else ""
        out = raw[:pos] + prefix + esc
    return xml[:m.start(2)] + out + xml[m.end(2):]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("type", choices=TYPES)
    ap.add_argument("doc_number")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--version", default="0.0.1")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y.%m.%d"))
    ap.add_argument("--out-dir", default="diagrams/src")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    fname, ids = TYPES[a.type]
    out = Path(a.out_dir) / f"{a.doc_number}.drawio"
    if out.exists() and not a.force:
        sys.exit(f"{out} already exists (use --force to overwrite)")
    out.parent.mkdir(parents=True, exist_ok=True)
    xml = (TPL / fname).read_text(encoding="utf-8")
    for key, val in [("title", a.title), ("number", a.doc_number), ("version", a.version),
                     ("author", a.author), ("date", a.date)]:
        xml = set_text(xml, ids[key], val)
    out.write_text(xml, encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
