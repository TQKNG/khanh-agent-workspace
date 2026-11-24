"""Shared drawing helpers for the Mermaid class and state converters.

Provides the page shell (frame, legend box, title block) that matches the sequence converter,
a small canvas that collects draw.io cells, and a layered graph layout.
"""
import html

FRAME_X, FRAME_W = 9.4, 1797.1
USABLE_W = FRAME_W - 80
esc = lambda s: html.escape(s, quote=True)

FONT = "fontFamily=Roboto;"
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;align=center;metaEdit=1;" + FONT
TXT = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=18;fontFamily=Roboto;spacingLeft=0;spacingTop=0;"
CAPTION = "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=12;" + FONT
LABEL = "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=14;" + FONT
LINE = "html=1;strokeWidth=2;strokeColor=#000000;labelBackgroundColor=#ffffff;fontSize=14;" + FONT
FILL = {
    "class": "fillColor=#438dd5;strokeColor=#3d81c3;fontColor=#ffffff;",
    "interface": "fillColor=#85bbf0;strokeColor=#78a8d8;fontColor=#ffffff;",
    "enumeration": "fillColor=#1168bd;strokeColor=#1864ad;fontColor=#ffffff;",
}


class Canvas:
    def __init__(self):
        self.cells, self.n = [], 0

    def cid(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def vx(self, style, value, x, y, w, h, i=None, parent="1"):
        i = i or self.cid("v")
        self.cells.append(f'<mxCell id="{i}" parent="{parent}" style="{style}" value="{esc(value)}" vertex="1">'
                          f'<mxGeometry height="{h:.1f}" width="{w:.1f}" x="{x:.1f}" y="{y:.1f}" as="geometry" /></mxCell>')
        return i

    def free_edge(self, style, x1, y1, x2, y2, value=""):
        self.cells.append(f'<mxCell id="{self.cid("e")}" edge="1" parent="1" style="{style}" value="{esc(value)}">'
                          f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1:.1f}" y="{y1:.1f}" as="sourcePoint" />'
                          f'<mxPoint x="{x2:.1f}" y="{y2:.1f}" as="targetPoint" /></mxGeometry></mxCell>')

    def link(self, style, src, dst, value=""):
        self.cells.append(f'<mxCell id="{self.cid("e")}" edge="1" parent="1" source="{src}" target="{dst}" '
                          f'style="{style}" value="{esc(value)}"><mxGeometry relative="1" as="geometry" /></mxCell>')


def layered(sizes, edges, horizontal=False, rank_sep=90, node_sep=60):
    """Layered layout. sizes: {id: (w, h)}; edges: [(upper, lower)].

    Returns ({id: (x, y)} top-left positions, width, height). Cycles are broken by ignoring back edges.
    """
    parent = {i: i for i in sizes}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for u, v in edges:
        parent[find(u)] = find(v)
    first = {}
    for k, i in enumerate(sizes):
        first.setdefault(find(i), k)
    ids = sorted(sizes, key=lambda i: first[find(i)])  # keep each connected cluster together
    succ = {i: [] for i in ids}
    pred = {i: [] for i in ids}
    for u, v in edges:
        if u != v and v not in succ[u]:
            succ[u].append(v)
    colour, back = {}, set()

    def dfs(u):
        colour[u] = 1
        for v in succ[u]:
            if colour.get(v) == 1:
                back.add((u, v))
            elif v not in colour:
                dfs(v)
        colour[u] = 2

    for i in ids:
        if i not in colour:
            dfs(i)
    for u in ids:
        succ[u] = [v for v in succ[u] if (u, v) not in back]
        for v in succ[u]:
            pred[v].append(u)
    rank, indeg = {i: 0 for i in ids}, {i: len(pred[i]) for i in ids}
    queue = [i for i in ids if indeg[i] == 0]
    while queue:
        u = queue.pop(0)
        for v in succ[u]:
            rank[v] = max(rank[v], rank[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    layers = [[] for _ in range(max(rank.values(), default=0) + 1)]
    for i in ids:
        layers[rank[i]].append(i)
    where = {}

    def place():
        for layer in layers:
            for k, n in enumerate(layer):
                where[n] = (k + 0.5) / len(layer)

    place()
    for _ in range(8):
        for layer in layers:
            def barycentre(n):
                neighbours = [where[m] for m in pred[n] + succ[n]]
                return sum(neighbours) / len(neighbours) if neighbours else where[n]
            layer.sort(key=barycentre)
            place()
    main = (lambda s: s[0]) if horizontal else (lambda s: s[1])
    cross = (lambda s: s[1]) if horizontal else (lambda s: s[0])
    thickness = [max(main(sizes[n]) for n in layer) for layer in layers]
    extent = [sum(cross(sizes[n]) for n in layer) + node_sep * (len(layer) - 1) for layer in layers]
    total_cross = max(extent, default=0)
    start = {}
    for r, layer in enumerate(layers):
        c = (total_cross - extent[r]) / 2
        for n in layer:
            start[n] = c
            c += cross(sizes[n]) + node_sep
    centre = lambda n: start[n] + cross(sizes[n]) / 2
    def relax(layer, neighbours_of):
        want = []
        for n in layer:
            near = [centre(m) for m in neighbours_of(n)]
            want.append((sum(near) / len(near) if near else centre(n)) - cross(sizes[n]) / 2)
        put = list(want)
        for k in range(1, len(layer)):
            put[k] = max(put[k], put[k - 1] + cross(sizes[layer[k - 1]]) + node_sep)
        for k in range(len(layer) - 2, -1, -1):
            put[k] = min(put[k], put[k + 1] - cross(sizes[layer[k]]) - node_sep)
        for k, n in enumerate(layer):
            start[n] = put[k]

    for step in range(6):  # pull each node toward its parents (down) or children (up), keeping order and spacing
        if step % 2 == 0:
            for layer in layers:
                relax(layer, lambda n: pred[n] or succ[n])
        else:
            for layer in reversed(layers):
                relax(layer, lambda n: succ[n] or pred[n])
    for layer in layers:  # a layer made only of leaves sits under the mean of their parents
        if all(not succ[n] for n in layer):
            relax(layer, lambda n: pred[n])
    low = min(start.values(), default=0)
    total_cross = max((start[n] - low + cross(sizes[n]) for n in ids), default=0)
    pos, offset = {}, 0
    for r, layer in enumerate(layers):
        for n in layer:
            m_pos = offset + (thickness[r] - main(sizes[n])) / 2
            c_pos = start[n] - low
            pos[n] = (m_pos, c_pos) if horizontal else (c_pos, m_pos)
        offset += thickness[r] + rank_sep
    total_main = offset - rank_sep if layers else 0
    return pos, (total_main if horizontal else total_cross), (total_cross if horizontal else total_main)


def assemble(canvas, body_bottom, legend, args):
    """Add the legend, frame and title block below the body and return the draw.io XML."""
    c = canvas
    ly = body_bottom + 30
    c.vx("rounded=1;arcSize=7;whiteSpace=wrap;html=1;fillColor=#f2f2f2;strokeColor=#7f7f7f;strokeWidth=1;", "", 41.8, ly, 1500, 190, "legbox")
    c.vx("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=16;fontFamily=Roboto;", "<b>Legend</b>", 65.5, ly + 15, 504.7, 31, "legttl")
    legend(c, ly)
    hdr_y = ly + 190 + 25 + 25
    c.vx("rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;", "", FRAME_X, 2.6, FRAME_W, hdr_y - 25 - 2.6, "frame")
    c.vx("rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;", "", FRAME_X, hdr_y, FRAME_W, 117.4, "hdr")
    for i, (val, x, dy, w) in enumerate([
        (f"<b>Document Title</b>: {html.escape(args.title)}", 43.2, 15.9, 1200),
        (f"<b>Document Number</b>: {html.escape(args.number)}", 43.2, 46.1, 1200),
        (f"<b>Version Number</b>: {html.escape(args.version)}", 43.2, 80, 419.8),
        (f"Prepared By: {html.escape(args.author)}", 1375.2, 21.6, 419.8),
        (f"Date: {args.date}", 1375.2, 50.4, 419.8)], 1):
        c.vx(TXT, val, x, hdr_y + dy, w, 25.2, f"t{i}")
    back = [x for x in c.cells if x.startswith('<mxCell id="frame"') or x.startswith('<mxCell id="hdr"')]
    cells = back + [x for x in c.cells if x not in back]  # frame fills are white: draw them first
    page_h = int(hdr_y + 117.4 + 40)
    return ('<mxfile host="app.diagrams.net">\n  <diagram id="proposal-1" name="proposal-1">\n'
            f'    <mxGraphModel dx="2049" dy="1143" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2454" pageHeight="{page_h}" math="0" shadow="0" adaptiveColors="auto">\n'
            '      <root>\n        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n        '
            + "\n        ".join(cells) + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n")


def add_common_args(ap):
    import datetime
    ap.add_argument("input")
    ap.add_argument("out")
    ap.add_argument("--title", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--version", default="0.0.1")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y.%m.%d"))
    ap.add_argument("--block", type=int, default=1)


def load_source(path, block, header):
    """Read a .mmd file, or pick the Nth fenced mermaid block that starts with `header` from an .mdx page."""
    import re, sys
    from pathlib import Path
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".mdx") or path.endswith(".md"):
        blocks = [b for b in re.findall(r"```mermaid\n(.*?)```", text, re.S) if b.lstrip().startswith(header)]
        if not blocks:
            sys.exit(f"no {header} block found")
        if not 1 <= block <= len(blocks):
            sys.exit(f"--block must be 1..{len(blocks)}")
        return blocks[block - 1]
    return text
