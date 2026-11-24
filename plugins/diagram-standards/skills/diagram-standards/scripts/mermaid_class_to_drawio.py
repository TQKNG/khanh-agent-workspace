#!/usr/bin/env python3
"""Convert a Mermaid classDiagram into a draw.io file that uses the standard frame,
title block and legend.

usage:
  mermaid_class_to_drawio.py <input.mmd | page.mdx> <out.drawio> --title T --number CLS-Product-001
        --author NAME [--version 0.0.1] [--date YYYY.MM.DD] [--block N]
  (for .mdx input, --block N picks the Nth ```mermaid classDiagram block, 1-based)

Supported Mermaid:
  class Name / class Name { ... } with members, <<interface>> and <<enumeration>> stereotypes,
  `Name : +member` lines, and these relationships with optional "cardinality" and `: label`:
  A <|-- B (inheritance), A <|.. B (realization), A *-- B (composition), A o-- B (aggregation),
  A --> B (association), A ..> B (dependency), A -- B (link), A --|> B, A ..|> B.
A member with "(" is an operation; every other member is an attribute (an enumeration value).
"""
import argparse, html, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uml_common import (BOX, FILL, FONT, FRAME_X, FRAME_W, LABEL, LINE, USABLE_W, CAPTION, Canvas,
                        add_common_args, assemble, layered, load_source)

REL = re.compile(r'^(\w+)\s*(?:"([^"]*)")?\s*(<\|--|<\|\.\.|\*--|o--|-->|\.\.>|--\|>|\.\.\|>|--)\s*(?:"([^"]*)")?\s*(\w+)\s*(?::\s*(.*))?$')
# relationship token -> (upper, lower) role: which side sits above, plus the draw.io edge style and direction
STYLES = {
    "<|--": ("a", "endArrow=block;endFill=0;endSize=14;", True),
    "<|..": ("a", "endArrow=block;endFill=0;endSize=14;dashed=1;", True),
    "--|>": ("b", "endArrow=block;endFill=0;endSize=14;", False),
    "..|>": ("b", "endArrow=block;endFill=0;endSize=14;dashed=1;", False),
    "*--": ("a", "startArrow=diamondThin;startFill=1;startSize=18;endArrow=none;", False),
    "o--": ("a", "startArrow=diamondThin;startFill=0;startSize=18;endArrow=none;", False),
    "-->": ("a", "endArrow=open;endSize=12;", False),
    "..>": ("a", "endArrow=open;endSize=12;dashed=1;", False),
    "--": ("a", "endArrow=none;", False),
}


def clean(text):
    return re.sub(r"~(\w+)~", r"<\1>", text.strip())


def parse(src):
    classes, order, rels = {}, [], []

    def cls(name):
        if name not in classes:
            classes[name] = {"stereo": None, "attrs": [], "ops": []}
            order.append(name)
        return classes[name]

    def member(c, text):
        text = clean(text)
        c["ops" if "(" in text else "attrs"].append(text)

    current = None
    for raw in src.splitlines():
        l = raw.strip()
        if not l or l == "classDiagram" or l.startswith("%%") or re.match(r"direction\s+\w+$", l):
            continue
        if current is not None:
            if l == "}":
                current = None
                continue
            m = re.match(r"<<(\w+)>>$", l)
            if m:
                classes[current]["stereo"] = m.group(1)
            else:
                member(classes[current], l)
            continue
        m = re.match(r"class\s+(\w+)(?:\s*<<(\w+)>>)?\s*(\{)?$", l)
        if m:
            c = cls(m.group(1))
            if m.group(2):
                c["stereo"] = m.group(2)
            if m.group(3):
                current = m.group(1)
            continue
        m = re.match(r"<<(\w+)>>\s+(\w+)$", l)
        if m:
            cls(m.group(2))["stereo"] = m.group(1)
            continue
        m = REL.match(l)
        if m:
            a, card_a, token, card_b, b, label = m.groups()
            if a == b:
                sys.exit(f"self-relationship on '{a}' is not supported")
            cls(a), cls(b)
            rels.append((a, b, token, card_a or "", card_b or "", (label or "").strip()))
            continue
        m = re.match(r"(\w+)\s*:\s*(.+)$", l)
        if m:
            member(cls(m.group(1)), m.group(2))
            continue
        sys.exit(f"unsupported Mermaid line: {l}")
    if current is not None:
        sys.exit(f"class '{current}' is not closed with }}")
    if not classes:
        sys.exit("no class found")
    return classes, order, rels


def rows_of(c):
    rows = []
    if c["attrs"]:
        rows.append(c["attrs"])
    if c["ops"]:
        rows.append(c["ops"])
    return rows or [[""]]


def size_of(name, c):
    longest = max([len(name) * 1.25] + [len(t) for rows in rows_of(c) for t in rows])
    w = min(560, max(280, longest * 7.8 + 32))
    head = 44 if c["stereo"] else 26
    h = head + sum(20 * len(r) + 8 for r in rows_of(c)) + 8 * (len(rows_of(c)) - 1)
    return w, h, head


def kind_of(c):
    return c["stereo"] if c["stereo"] in ("interface", "enumeration") else "class"


def build(classes, order, rels, a):
    cv = Canvas()
    sizes = {n: size_of(n, classes[n])[:2] for n in order}
    layering = []
    for x, y, token, *_ in rels:
        upper = STYLES[token][0]
        layering.append((x, y) if upper == "a" else (y, x))
    pos, width, height = layered(sizes, layering, rank_sep=110, node_sep=70)
    if width > USABLE_W:
        sys.exit(f"diagram is {width:.0f}px wide and the page holds {USABLE_W:.0f}px: split it into smaller diagrams")
    x0, y0 = FRAME_X + (FRAME_W - width) / 2, 40
    ids = {n: f"c_{k}" for k, n in enumerate(order)}
    for n in order:
        c = classes[n]
        w, h, head = size_of(n, c)
        x, y = x0 + pos[n][0], y0 + pos[n][1]
        title = f"«{c['stereo']}»<br>{html.escape(n)}" if c["stereo"] else html.escape(n)
        style = ("swimlane;fontStyle=1;align=center;verticalAlign=middle;childLayout=stackLayout;horizontal=1;"
                 f"startSize={head};horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;"
                 f"marginBottom=0;whiteSpace=wrap;html=1;fontSize=15;strokeWidth=1.5;{FILL[kind_of(c)]}{FONT}")
        cv.vx(style, title, x, y, w, h, ids[n])
        offset, rows = head, rows_of(c)
        for k, lines in enumerate(rows):
            rh = 20 * len(lines) + 8
            cv.vx("text;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=top;spacingLeft=6;spacingRight=4;"
                  "overflow=hidden;rotatable=0;whiteSpace=wrap;fontSize=13;" + FONT,
                  "<br>".join(html.escape(t) for t in lines), 0, offset, w, rh, parent=ids[n])
            offset += rh
            if k < len(rows) - 1:
                cv.vx("line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;rotatable=0;strokeColor=#000000;",
                      "", 0, offset, w, 8, parent=ids[n])
                offset += 8
    for x, y, token, card_x, card_y, label in rels:
        _, style, swap = STYLES[token]
        src, dst, cs, cd = (y, x, card_y, card_x) if swap else (x, y, card_x, card_y)
        cv.link("edgeStyle=orthogonalEdgeStyle;" + style + LINE, ids[src], ids[dst], label)
        for name, text, upper in ((src, cs, True), (dst, cd, False)):
            if not text:
                continue
            w, h, _ = size_of(name, classes[name])
            px, py = x0 + pos[name][0], y0 + pos[name][1]
            other = dst if name == src else src
            below = (y0 + pos[other][1]) > py
            ty = py + h + 2 if below else py - 24
            cv.vx(LABEL + "align=left;", text, px + w / 2 + 6, ty, 70, 22)
    return cv, y0 + height


def legend(c, ly):
    for cid, x, kind, label in (("l_cls", 77.8, "class", "Class"), ("l_if", 247.0, "interface", "Interface"),
                                ("l_en", 417.0, "enumeration", "Enumeration")):
        c.vx(BOX + FILL[kind], f'<span style="font-size:12px">name<br></span><span style="font-size:12px">[{label}]</span>',
             x, ly + 97, 140, 73.4, cid)
    for x, caption, style in (
            (640, "Composition", "startArrow=diamondThin;startFill=1;startSize=14;endArrow=none;"),
            (850, "Association", "endArrow=open;endSize=10;"),
            (1060, "Realization", "endArrow=block;endFill=0;endSize=12;dashed=1;"),
            (1270, "Dependency", "endArrow=open;endSize=10;dashed=1;")):
        c.vx(CAPTION, caption, x + 10, ly + 94, 160, 24)
        c.free_edge(style + "html=1;strokeWidth=2;strokeColor=#000000;", x, ly + 144, x + 180, ly + 144)


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    a = ap.parse_args()
    classes, order, rels = parse(load_source(a.input, a.block, "classDiagram"))
    cv, bottom = build(classes, order, rels, a)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(assemble(cv, bottom, legend, a), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
