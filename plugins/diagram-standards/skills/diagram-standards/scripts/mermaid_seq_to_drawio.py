#!/usr/bin/env python3
"""Convert a Mermaid sequenceDiagram into a draw.io file that uses the standard frame,
title block and legend.

usage:
  mermaid_seq_to_drawio.py <input.mmd | page.mdx> <out.drawio> --title T --number SEQ-Product-001
        --author NAME [--version 0.0.1] [--date YYYY.MM.DD] [--block N]
  (for .mdx input, --block N picks the Nth ```mermaid sequenceDiagram block, 1-based)

Supported Mermaid: autonumber, actor, participant X as Label, ->> -->> -> -->, loop/alt/opt/else/end.
Element kinds come from a Mermaid comment (ignored by Mermaid itself):
  %% kind Customer=person API=container Claims=component Stripe=system
Defaults: actor -> person, participant -> container.
"""
import argparse, datetime, html, re, sys
from pathlib import Path

KINDS = {  # fill, stroke, label
    "person":    ("#08427b", "#073b6f", "Person"),
    "container": ("#438dd5", "#3d81c3", "Container"),
    "component": ("#85bbf0", "#78a8d8", "Component"),
    "system":    ("#1168bd", "#1864ad", "External System"),
}
FRAME_X, FRAME_W = 9.4, 1797.1
PERSON_PTS = "points=[[0.5,0,0],[1,0.5,0],[1,0.75,0],[0.75,1,0],[0.5,1,0],[0.25,1,0],[0,0.75,0],[0,0.5,0],[0,0.25,0],[1,0.25,0]];"
TXT = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=18;fontFamily=Roboto;spacingLeft=0;spacingTop=0;"
esc = lambda s: html.escape(s, quote=True)

def load_source(path, block):
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".mdx") or path.endswith(".md"):
        blocks = [b for b in re.findall(r"```mermaid\n(.*?)```", text, re.S) if b.lstrip().startswith("sequenceDiagram")]
        if not blocks: sys.exit("no sequenceDiagram block found")
        if not 1 <= block <= len(blocks): sys.exit(f"--block must be 1..{len(blocks)}")
        return blocks[block - 1]
    return text

def parse(src):
    parts, order, msgs, kinds, auto = {}, [], [], {}, False
    ops = []
    def add(i, label=None, actor=False):
        if i not in parts:
            parts[i] = {"label": label or i, "actor": actor}; order.append(i)
        else:
            if label: parts[i]["label"] = label
            if actor: parts[i]["actor"] = True
    for raw in src.splitlines():
        l = raw.strip()
        if not l or l == "sequenceDiagram": continue
        if l.startswith("%%"):
            m = re.match(r"%%\s*kind\s+(.*)", l)
            if m:
                for kv in m.group(1).split():
                    k, v = kv.split("=")
                    if v not in KINDS: sys.exit(f"unknown kind '{v}' (use {', '.join(KINDS)})")
                    kinds[k] = v
            continue
        if l == "autonumber": auto = True; continue
        m = re.match(r"(actor|participant)\s+(\w+)(?:\s+as\s+(.+))?$", l)
        if m: add(m.group(2), (m.group(3) or m.group(2)).strip(), m.group(1) == "actor"); continue
        m = re.match(r"(loop|alt|opt)\s*(.*)$", l)
        if m: ops.append(("open", m.group(1), m.group(2))); continue
        m = re.match(r"else\s*(.*)$", l)
        if m: ops.append(("else", m.group(1))); continue
        if l == "end": ops.append(("end",)); continue
        m = re.match(r"(\w+)\s*(-->>|->>|-->|->)\s*[+-]?(\w+)\s*:\s*(.*)$", l)
        if m:
            a, arrow, b, text = m.groups(); add(a); add(b)
            if a == b: sys.exit(f"self-message on '{a}' is not supported")
            ops.append(("msg", a, b, arrow.startswith("--"), text.strip())); continue
        sys.exit(f"unsupported Mermaid line: {l}")
    return order, parts, kinds, auto, ops

def build(order, parts, kinds, auto, ops, a):
    cells, nid = [], [0]
    def cid(p="c"): nid[0] += 1; return f"{p}{nid[0]}"
    def vx(style, value, x, y, w, h, i=None):
        i = i or cid("v")
        cells.append(f'<mxCell id="{i}" parent="1" style="{style}" value="{esc(value)}" vertex="1"><mxGeometry height="{h:.1f}" width="{w:.1f}" x="{x:.1f}" y="{y:.1f}" as="geometry" /></mxCell>')
    def ed(style, x1, y1, x2, y2, value=""):
        cells.append(f'<mxCell id="{cid("e")}" edge="1" parent="1" style="{style}" value="{esc(value)}"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1:.1f}" y="{y1:.1f}" as="sourcePoint" /><mxPoint x="{x2:.1f}" y="{y2:.1f}" as="targetPoint" /></mxGeometry></mxCell>')
    n, BW = len(order), 240
    gap = min(380, (FRAME_W - 80 - BW) / max(n - 1, 1)) if n > 1 else 0
    start = FRAME_X + FRAME_W / 2 - gap * (n - 1) / 2
    cx = {p: start + i * gap for i, p in enumerate(order)}
    HEAD_BOTTOM = 150
    for p in order:
        kind = kinds.get(p, "person" if parts[p]["actor"] else "container")
        fill, stroke, kl = KINDS[kind]
        label = f'<b><span style="font-size:16px">{html.escape(parts[p]["label"])}<br></span></b><span style="font-size:12px">[{kl}]</span>'
        if kind == "person":
            st = f"html=1;dashed=0;whiteSpace=wrap;fillColor={fill};strokeColor={stroke};fontColor=#ffffff;shape=mxgraph.c4.person2;align=center;metaEdit=1;{PERSON_PTS}resizable=0;fontFamily=Roboto;"
            vx(st, label, cx[p] - 75, 30, 150, 120)
        else:
            st = f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor=#ffffff;align=center;metaEdit=1;fontFamily=Roboto;"
            vx(st, label, cx[p] - BW / 2, 70, BW, 80)
    y, num, stack, body, lines = HEAD_BOTTOM + 40, 0, [], [], []
    for op in ops:
        if op[0] == "open":
            stack.append({"kind": op[1], "label": op[2], "top": y, "xs": set(), "divs": []}); y += 46
        elif op[0] == "else":
            f = stack[-1]; y += 14; f["divs"].append((y, op[1])); y += 38
        elif op[0] == "end":
            f = stack.pop(); y += 16
            xs = f["xs"] or {start}
            x1, x2 = min(xs) - 70, max(xs) + 70
            if x2 - x1 < 340: mid = (x1 + x2) / 2; x1, x2 = mid - 170, mid + 170
            lines.append(("frame", f, x1, x2, y))
            if stack: stack[-1]["xs"] |= {x1 + 70, x2 - 70}
            y += 24
        else:
            _, s, t, ret, text = op
            num += 1
            if auto: text = f"{num}. {text}"
            ay = y + 34
            for f in stack: f["xs"] |= {cx[s], cx[t]}
            body.append((s, t, ret, text, ay)); y += 66
    # frames first (so messages draw above), then lifelines, then messages
    for _, f, x1, x2, bottom in lines:
        tab = {"loop": 70, "alt": 56, "opt": 56}[f["kind"]]
        vx(f"shape=umlFrame;whiteSpace=wrap;html=1;pointerEvents=0;recursiveResize=0;container=0;collapsible=0;width={tab};height=30;fillColor=none;strokeColor=#000000;strokeWidth=1.5;fontFamily=Roboto;fontSize=14;fontStyle=1;",
           f["kind"], x1, f["top"], x2 - x1, bottom - f["top"])
        if f["label"]:
            vx("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=14;fontFamily=Roboto;", f"[{f['label']}]", x1 + tab + 8, f["top"] + 3, x2 - x1 - tab - 16, 24)
        for dy, dl in f["divs"]:
            ed("endArrow=none;dashed=1;html=1;strokeWidth=1.5;strokeColor=#000000;", x1, dy, x2, dy)
            if dl: vx("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=14;fontFamily=Roboto;", f"[{dl}]", x1 + 8, dy + 4, x2 - x1 - 16, 24)
    end_y = y + 10
    for p in order:
        ed("endArrow=none;dashed=1;dashPattern=6 6;html=1;strokeWidth=1.5;strokeColor=#7f7f7f;", cx[p], HEAD_BOTTOM, cx[p], end_y)
    for s, t, ret, text, ay in body:
        d = "dashed=1;" if ret else ""
        ed(f"endArrow=blockThin;endFill=1;html=1;rounded=0;strokeWidth=2;strokeColor=#000000;{d}", cx[s], ay, cx[t], ay)
        w = max(abs(cx[t] - cx[s]) - 16, len(text) * 7.8 + 16)
        vx("text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=bottom;fontSize=14;fontFamily=Roboto;whiteSpace=nowrap;", text, (cx[s] + cx[t]) / 2 - w / 2, ay - 28, w, 24)
    # legend
    ly = end_y + 30
    vx("rounded=1;arcSize=7;whiteSpace=wrap;html=1;fillColor=#f2f2f2;strokeColor=#7f7f7f;strokeWidth=1;", "", 41.8, ly, 1500, 190, "legbox")
    vx("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=16;fontFamily=Roboto;", "<b>Legend</b>", 65.5, ly + 15, 504.7, 31, "legttl")
    def lg(kind, x, w=135.3, h=73.4, yy=None):
        fill, stroke, kl = KINDS[kind]
        v = f'<span style="font-size:12px">name<br></span><span style="font-size:12px">[{kl}]</span>'
        if kind == "person":
            vx(f"html=1;dashed=0;whiteSpace=wrap;fillColor={fill};strokeColor={stroke};fontColor=#ffffff;shape=mxgraph.c4.person2;align=center;metaEdit=1;{PERSON_PTS}resizable=0;fontFamily=Roboto;", v, x, ly + 50, 104.4, 120.2)
        else:
            vx(f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor=#ffffff;align=center;metaEdit=1;fontFamily=Roboto;", v, x, ly + 97, w, h)
    lg("person", 77.8); lg("container", 247); lg("component", 403, 141.3); lg("system", 574, 160)
    ed("endArrow=blockThin;html=1;strokeWidth=2;endFill=1;strokeColor=#000000;labelBackgroundColor=#f2f2f2;fontFamily=Roboto;fontSize=12;", 790, ly + 128, 940, ly + 128, "Call")
    ed("endArrow=blockThin;html=1;dashed=1;strokeWidth=2;endFill=1;strokeColor=#000000;labelBackgroundColor=#f2f2f2;fontFamily=Roboto;fontSize=12;", 790, ly + 168, 940, ly + 168, "Return")
    vx("shape=umlFrame;whiteSpace=wrap;html=1;pointerEvents=0;recursiveResize=0;container=0;collapsible=0;width=56;height=30;fillColor=none;strokeColor=#000000;strokeWidth=1.5;fontFamily=Roboto;fontSize=14;fontStyle=1;", "alt", 1010, ly + 90, 300, 80)
    vx("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=12;fontFamily=Roboto;", "[condition: loop, alt and opt frames]", 1074, ly + 93, 300, 24)
    # frame + title block
    hdr_y = ly + 190 + 25 + 25
    vx("rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;", "", FRAME_X, 2.6, FRAME_W, hdr_y - 25 - 2.6, "frame")
    vx("rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;", "", FRAME_X, hdr_y, FRAME_W, 117.4, "hdr")
    for i, (val, x, dy, w) in enumerate([
        (f"<b>Document Title</b>: {html.escape(a.title)}", 43.2, 15.9, 1200),
        (f"<b>Document Number</b>: {html.escape(a.number)}", 43.2, 46.1, 1200),
        (f"<b>Version Number</b>: {html.escape(a.version)}", 43.2, 80, 419.8),
        (f"Prepared By: {html.escape(a.author)}", 1375.2, 21.6, 419.8),
        (f"Date: {a.date}", 1375.2, 50.4, 419.8)], 1):
        vx(TXT, val, x, hdr_y + dy, w, 25.2, f"t{i}")
    back = [c for c in cells if c.startswith('<mxCell id="frame"') or c.startswith('<mxCell id="hdr"')]
    cells = back + [c for c in cells if c not in back]  # frame fills are white: draw them first
    page_h = int(hdr_y + 117.4 + 40)
    return ('<mxfile host="app.diagrams.net">\n  <diagram id="proposal-1" name="proposal-1">\n'
            f'    <mxGraphModel dx="2049" dy="1143" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2454" pageHeight="{page_h}" math="0" shadow="0" adaptiveColors="auto">\n'
            '      <root>\n        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n        '
            + "\n        ".join(cells) + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("out")
    ap.add_argument("--title", required=True); ap.add_argument("--number", required=True)
    ap.add_argument("--author", required=True); ap.add_argument("--version", default="0.0.1")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y.%m.%d"))
    ap.add_argument("--block", type=int, default=1)
    a = ap.parse_args()
    order, parts, kinds, auto, ops = parse(load_source(a.input, a.block))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(order, parts, kinds, auto, ops, a), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
