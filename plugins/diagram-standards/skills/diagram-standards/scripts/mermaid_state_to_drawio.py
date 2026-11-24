#!/usr/bin/env python3
"""Convert a Mermaid stateDiagram-v2 into a draw.io file that uses the standard frame,
title block and legend.

usage:
  mermaid_state_to_drawio.py <input.mmd | page.mdx> <out.drawio> --title T --number STM-Product-001
        --author NAME [--version 0.0.1] [--date YYYY.MM.DD] [--block N]
  (for .mdx input, --block N picks the Nth ```mermaid stateDiagram block, 1-based)

Supported Mermaid:
  direction TB|LR (default TB, set per composite state inside its block), A --> B, A --> B: event [guard] / action, [*] --> A, A --> [*],
  state "Long name" as id, state id <<choice>>, and one level of composite state:
  state id { ... } with its own [*] markers.
Transitions between a composite state's inner states and states outside it are not supported:
draw the transition to the composite state itself.
"""
import argparse, html, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uml_common import (BOX, FILL, FRAME_X, FRAME_W, LINE, USABLE_W, CAPTION, Canvas, add_common_args,
                        assemble, layered, load_source)

STATE = BOX + FILL["class"] + "fontSize=16;fontStyle=1;arcSize=30;"
COMPOSITE = ("rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#3d81c3;strokeWidth=2;"
             "verticalAlign=top;align=left;spacingLeft=14;spacingTop=8;fontSize=16;fontStyle=1;fontFamily=Roboto;")
INITIAL = "ellipse;html=1;fillColor=#000000;strokeColor=#000000;"
FINAL = "ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;strokeWidth=2;"
CHOICE = "rhombus;html=1;fillColor=#ffffff;strokeColor=#000000;strokeWidth=2;"
TRANSITION = "endArrow=block;endFill=1;endSize=10;edgeStyle=orthogonalEdgeStyle;" + LINE
PAD_X, PAD_TOP, PAD_BOTTOM = 30, 48, 30
ENDPOINT = r"(\[\*\]|\w+)"


def parse(src):
    nodes, labels, scopes, owner = {}, {}, {"": {"nodes": [], "edges": [], "direction": "TB"}}, {}
    stack = [""]

    def touch(name, kind="state"):
        scope = stack[-1]
        if name in owner and owner[name] != scope:
            sys.exit(f"'{name}' is used inside and outside a composite state; draw the transition to the composite state instead")
        if name not in owner:
            owner[name] = scope
            nodes[name] = kind
            scopes[scope]["nodes"].append(name)
        elif kind != "state":
            nodes[name] = kind
        return name

    def endpoint(token, source):
        if token != "[*]":
            return touch(token)
        node = f"{'init' if source else 'final'}@{stack[-1]}"
        if node not in nodes:
            nodes[node] = "initial" if source else "final"
            scopes[stack[-1]]["nodes"].append(node)
            owner[node] = stack[-1]
        return node

    for raw in src.splitlines():
        l = raw.strip()
        if not l or l.startswith("stateDiagram") or l.startswith("%%"):
            continue
        m = re.match(r"direction\s+(TB|LR)$", l)
        if m:
            scopes[stack[-1]]["direction"] = m.group(1)
            continue
        if l == "}":
            if len(stack) == 1:
                sys.exit("unexpected }")
            stack.pop()
            continue
        m = re.match(r'state\s+"([^"]+)"\s+as\s+(\w+)$', l)
        if m:
            labels[touch(m.group(2))] = m.group(1)
            continue
        m = re.match(r"state\s+(\w+)\s*<<choice>>$", l)
        if m:
            touch(m.group(1), "choice")
            continue
        m = re.match(r"state\s+(\w+)\s*\{$", l)
        if m:
            if len(stack) > 1:
                sys.exit("composite states nested more than one level are not supported")
            name = touch(m.group(1), "composite")
            scopes[name] = {"nodes": [], "edges": [], "direction": "TB"}
            stack.append(name)
            continue
        m = re.match(ENDPOINT + r"\s*-->\s*" + ENDPOINT + r"\s*(?::\s*(.*))?$", l)
        if m:
            a, b, label = m.groups()
            if a == b and a != "[*]":
                sys.exit(f"self-transition on '{a}' is not supported")
            u, v = endpoint(a, True), endpoint(b, False)
            scopes[stack[-1]]["edges"].append((u, v, (label or "").strip()))
            continue
        sys.exit(f"unsupported Mermaid line: {l}")
    if len(stack) > 1:
        sys.exit(f"composite state '{stack[-1]}' is not closed with }}")
    if not scopes[""]["nodes"]:
        sys.exit("no state found")
    return nodes, labels, scopes


def node_size(name, kind, labels):
    if kind == "initial":
        return 30, 30
    if kind == "final":
        return 40, 40
    if kind == "choice":
        return 50, 50
    return min(340, max(160, len(labels.get(name, name)) * 9.5 + 40)), 70


def build(nodes, labels, scopes, a):
    cv = Canvas()
    def sep(scope):
        horizontal = scope["direction"] == "LR"
        return horizontal, dict(rank_sep=130 if horizontal else 90, node_sep=70)

    inner = {}
    sizes = {}
    for name in scopes[""]["nodes"]:
        if nodes[name] == "composite":
            scope = scopes[name]
            inner_sizes = {n: node_size(n, nodes[n], labels) for n in scope["nodes"]}
            horizontal, spacing = sep(scope)
            pos, w, h = layered(inner_sizes, [(u, v) for u, v, _ in scope["edges"]], horizontal, **spacing)
            inner[name] = (pos, inner_sizes)
            title_w = len(labels.get(name, name)) * 10 + 60
            sizes[name] = (max(w + 2 * PAD_X, title_w), h + PAD_TOP + PAD_BOTTOM)
        else:
            sizes[name] = node_size(name, nodes[name], labels)
    horizontal, spacing = sep(scopes[""])
    pos, width, height = layered(sizes, [(u, v) for u, v, _ in scopes[""]["edges"]], horizontal, **spacing)
    if width > USABLE_W:
        advice = "use 'direction TB'" if horizontal else "add 'direction LR'"
        sys.exit(f"diagram is {width:.0f}px wide and the page holds {USABLE_W:.0f}px: {advice} or split it")
    x0, y0 = FRAME_X + (FRAME_W - width) / 2, 40
    ids = {n: f"s_{k}" for k, n in enumerate(nodes)}

    def draw(name, x, y, w, h):
        kind = nodes[name]
        text = html.escape(labels.get(name, name))
        if kind == "state":
            cv.vx(STATE, text, x, y, w, h, ids[name])
        elif kind == "composite":
            cv.vx(COMPOSITE, text, x, y, w, h, ids[name])
        else:
            cv.vx({"initial": INITIAL, "final": FINAL, "choice": CHOICE}[kind], "", x, y, w, h, ids[name])

    for name in scopes[""]["nodes"]:
        x, y = x0 + pos[name][0], y0 + pos[name][1]
        draw(name, x, y, *sizes[name])
        if name in inner:
            ipos, isizes = inner[name]
            w, h = sizes[name]
            iw = max(p[0] + isizes[n][0] for n, p in ipos.items())
            ox = x + (w - iw) / 2
            for n, (px, py) in ipos.items():
                draw(n, ox + px, y + PAD_TOP + py, *isizes[n])
    for scope in scopes.values():
        for u, v, label in scope["edges"]:
            cv.link(TRANSITION, ids[u], ids[v], label)
    return cv, y0 + height


def legend(c, ly):
    c.vx(INITIAL, "", 100, ly + 122, 30, 30)
    c.vx(CAPTION, "Initial state", 55, ly + 158, 120, 24)
    c.vx(STATE + "fontSize=12;", '<span style="font-size:12px">name</span>', 215, ly + 104, 120, 50)
    c.vx(CAPTION, "State", 215, ly + 158, 120, 24)
    c.vx("rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#3d81c3;strokeWidth=2;verticalAlign=top;"
         "align=left;spacingLeft=8;fontStyle=1;fontFamily=Roboto;", '<span style="font-size:12px">name</span>', 380, ly + 94, 160, 60)
    c.vx(CAPTION, "Composite state", 380, ly + 158, 160, 24)
    c.vx(CHOICE, "", 600, ly + 114, 40, 40)
    c.vx(CAPTION, "Choice", 580, ly + 158, 80, 24)
    c.vx(FINAL, "", 725, ly + 117, 36, 36)
    c.vx(CAPTION, "Final state", 690, ly + 158, 100, 24)
    c.vx(CAPTION, "event [guard] / action", 870, ly + 94, 200, 24)
    c.free_edge("endArrow=block;endFill=1;endSize=10;html=1;strokeWidth=2;strokeColor=#000000;", 860, ly + 144, 1080, ly + 144)
    c.vx(CAPTION, "Transition", 910, ly + 158, 120, 24)


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    a = ap.parse_args()
    nodes, labels, scopes = parse(load_source(a.input, a.block, "stateDiagram"))
    cv, bottom = build(nodes, labels, scopes, a)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(assemble(cv, bottom, legend, a), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
