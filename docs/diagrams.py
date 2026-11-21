"""Regenerate the SVG diagrams used by the mdBook in this directory.

    uv run python docs/diagrams.py

Every diagram is a self-contained card with its own background, so it reads the
same in all of mdBook's themes. `corridor.svg` is drawn from the real sample
route with garmap's own corridor code; the rest are schematic.
"""

from __future__ import annotations

import math
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "src" / "img"

SANS = "system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

INK = "#1f2933"
MUTED = "#5b6770"
LINE = "#8a96a3"
PAPER = "#fbfaf7"
CARD = "#ffffff"
BLUE = "#0050C8"
BLUE_BG = "#e6eefb"
BROWN = "#8C5A28"
BROWN_BG = "#f4ebe0"
RED = "#C8102E"
RED_BG = "#fbe9ec"
GREEN = "#1b7f4d"
GREEN_BG = "#e4f4ea"
AMBER = "#9a6700"
AMBER_BG = "#fff4d6"
GREY_BG = "#eef1f4"


class Svg:
    def __init__(self, width: int, height: int, title: str, desc: str):
        self.w, self.h = width, height
        self.title, self.desc = title, desc
        self.parts: list[str] = []

    # -- primitives ------------------------------------------------------- #

    def raw(self, markup: str) -> None:
        self.parts.append(markup)

    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: float = 13,
        fill: str = INK,
        anchor: str = "middle",
        weight: str = "400",
        mono: bool = False,
        italic: bool = False,
    ) -> None:
        style = ' font-style="italic"' if italic else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-family="{MONO if mono else SANS}"{style}>{escape(content)}</text>'
        )

    def box(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        lines: list[str],
        fill: str = CARD,
        stroke: str = LINE,
        dashed: bool = False,
        size: float = 13,
        sub_size: float = 11,
        mono_title: bool = False,
        radius: float = 8,
        ink: str = INK,
    ) -> None:
        """A rounded box; the first line is the title, the rest are sub-lines."""
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"{dash}/>'
        )
        gap = sub_size + 4
        block = size + gap * (len(lines) - 1)
        baseline = y + (h - block) / 2 + size - 2
        self.text(x + w / 2, baseline, lines[0], size, ink, weight="600", mono=mono_title)
        for i, line in enumerate(lines[1:], start=1):
            self.text(x + w / 2, baseline + gap * i, line, sub_size, MUTED)

    def diamond(self, cx: float, cy: float, w: float, h: float, lines: list[str]) -> None:
        pts = f"{cx - w / 2},{cy} {cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2}"
        self.parts.append(
            f'<polygon points="{pts}" fill="{AMBER_BG}" stroke="{AMBER}" stroke-width="1.4"/>'
        )
        start = cy - (len(lines) - 1) * 7.5 + 4
        for i, line in enumerate(lines):
            self.text(cx, start + i * 15, line, 12, INK, weight="600")

    def arrow(
        self,
        points: list[tuple[float, float]],
        label: str | None = None,
        label_at: tuple[float, float] | None = None,
        colour: str = MUTED,
        dashed: bool = False,
        anchor: str = "middle",
    ) -> None:
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        marker = {MUTED: "a", BLUE: "ab", RED: "ar", GREEN: "ag"}.get(colour, "a")
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="1.6"{dash} '
            f'marker-end="url(#{marker})"/>'
        )
        if label:
            lx, ly = label_at or (
                (points[0][0] + points[1][0]) / 2,
                (points[0][1] + points[1][1]) / 2 - 6,
            )
            self.text(lx, ly, label, 11, colour if colour != MUTED else INK, anchor=anchor,
                      weight="600")

    def heading(self, title: str, subtitle: str | None = None) -> None:
        self.text(24, 34, title, 17, INK, anchor="start", weight="700")
        if subtitle:
            self.text(24, 54, subtitle, 12, MUTED, anchor="start")

    # -- output ----------------------------------------------------------- #

    def render(self) -> str:
        markers = "".join(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{colour}"/></marker>'
            for mid, colour in (("a", MUTED), ("ab", BLUE), ("ar", RED), ("ag", GREEN))
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f'width="{self.w}" height="{self.h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(self.title)}</title>\n'
            f'<desc id="d">{escape(self.desc)}</desc>\n'
            f"<defs>{markers}</defs>\n"
            f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="12" '
            f'fill="{PAPER}" stroke="#d9dde2"/>\n' + "\n".join(self.parts) + "\n</svg>\n"
        )

    def save(self, name: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text(self.render(), encoding="utf-8")


# --------------------------------------------------------------------------- #


def pipeline() -> None:
    s = Svg(1000, 430, "garmap build pipeline",
            "Six stages turn a GPX file into a Garmin .img: route, corridor, extracts, "
            "clip and split, optional contours, compile.")
    s.heading("garmap build — six stages",
              "Top row: what each stage pulls in. Bottom row: what it leaves in the work directory.")

    stages = [
        ("1 Route", "gpx.py", ["tour.gpx"], ["LineStrings", "(lon, lat)"], False),
        ("2 Corridor", "corridor.py", ["--buffer"], ["corridor.poly"], False),
        ("3 Extracts", "geofabrik.py", ["Geofabrik index", "+ .osm.pbf"], ["cached extracts"], False),
        ("4 Clip + split", "splitter.py", ["splitter r654", "(Java)"], ["tiles/passN/", "6324xxxx.osm.pbf"], False),
        ("5 Contours", "contours.py", ["pyhgtmap +", "Viewfinder HGT"], ["contours/", "*.osm.pbf"], True),
        ("6 Compile", "mkgmap.py", ["mkgmap r4924", "style + TYP"], ["gmapsupp.img", "→ your -o path"], False),
    ]
    w, gap, x0 = 140, 22, 26
    for i, (name, module, top, bottom, optional) in enumerate(stages):
        x = x0 + i * (w + gap)
        cx = x + w / 2
        s.box(x + 8, 84, w - 16, 46, top, fill=GREY_BG, stroke="#c5ccd3", size=11.5, sub_size=11.5)
        s.arrow([(cx, 130), (cx, 168)])
        s.box(x, 170, w, 70, [name, module], fill=BLUE_BG, stroke=BLUE, dashed=optional,
              size=14, sub_size=11.5)
        s.arrow([(cx, 240), (cx, 288)])
        final = i == len(stages) - 1
        s.box(x + 4, 290, w - 8, 50, bottom, fill=GREEN_BG if final else CARD,
              stroke=GREEN if final else LINE, size=11.5, sub_size=11.5, mono_title=True)
        if i < len(stages) - 1:
            s.arrow([(x + w, 205), (x + w + gap, 205)], colour=BLUE)
    s.text(x0 + 4 * (w + gap) + w / 2 + 10, 268, "only with --contours", 11, MUTED, anchor="start", italic=True)
    s.raw(f'<rect x="26" y="366" width="948" height="40" rx="8" fill="{BROWN_BG}" stroke="{BROWN}" '
          'stroke-width="1.2"/>')
    s.text(500, 391, "~/.cache/garmap  —  jars/ (stages 4, 6)  ·  geofabrik/ + index (stage 3)  ·  "
           "hgt/ (stage 5, and --dem in stage 6)", 12.5, INK)
    s.save("pipeline.svg")


def modules() -> None:
    s = Svg(1000, 412, "garmap module map",
            "cli.py drives nine feature modules; geofabrik and tools use http; splitter, mkgmap "
            "and style use tools; config holds pins and cache paths.")
    s.heading("Module map", "Arrows are imports. cli.py imports each feature module lazily, inside the command that needs it.")
    s.box(18, 76, 964, 50, ["cli.py", "click commands: build · preview · install · doctor · cache"],
          fill=BLUE_BG, stroke=BLUE, size=14, mono_title=True)
    mods = [
        ("gpx.py", "gpxpy"), ("corridor.py", "shapely · pyproj"), ("geofabrik.py", "set cover"),
        ("splitter.py", "clip + tile"), ("contours.py", "pyhgtmap"), ("mkgmap.py", "compile"),
        ("style.py", "patch style"), ("preview.py", "Leaflet HTML"), ("device.py", "volume · MTP"),
    ]
    w, gap, x0 = 100, 8, 18
    xs = {}
    for i, (name, sub) in enumerate(mods):
        x = x0 + i * (w + gap)
        xs[name] = x + w / 2
        s.arrow([(x + w / 2, 126), (x + w / 2, 168)], colour=BLUE)
        s.box(x, 170, w, 56, [name, sub], size=12.5, sub_size=10.5, mono_title=True)
    # shared layer
    s.box(x0 + 2 * (w + gap), 290, w, 56, ["http.py", "requests · tqdm"], fill=GREY_BG,
          size=12.5, sub_size=10.5, mono_title=True)
    tools_x = x0 + 3 * (w + gap)
    tools_w = 4 * w + 3 * gap
    s.box(tools_x, 290, tools_w, 56, ["tools.py", "find Java · fetch + unpack jars · run_java()"],
          fill=GREY_BG, size=12.5, sub_size=10.5, mono_title=True)
    s.box(x0 + 7 * (w + gap), 290, 2 * w + gap, 56, ["config.py", "version pins · cache paths · defaults"],
          fill=GREY_BG, size=12.5, sub_size=10.5, mono_title=True)
    s.arrow([(xs["geofabrik.py"], 226), (xs["geofabrik.py"], 288)])
    for name in ("splitter.py", "mkgmap.py", "style.py"):
        s.arrow([(xs[name], 226), (xs[name], 288)])
    hx = x0 + 2 * (w + gap) + w / 2
    s.arrow([(tools_x + 40, 346), (tools_x + 40, 364), (hx, 364), (hx, 348)])
    s.text(xs["contours.py"], 262, "runs pyhgtmap itself", 10.5, MUTED, italic=True)
    s.text(x0 + 7 * (w + gap) + w + gap / 2, 366, "imported by six of the other modules",
           10.5, MUTED, italic=True)
    s.text(18, 392, "gpx, corridor, preview and device depend on nothing else in the package.", 10.5,
           MUTED, anchor="start", italic=True)
    s.save("modules.svg")


def corridor() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from garmap.corridor import area_km2, build_corridor
    from garmap.gpx import read_gpx

    lines = read_gpx(ROOT / "resources" / "Lajkonik_250km_.final.gpx")
    wide, narrow = build_corridor(lines, 8000), build_corridor(lines, 3000)

    min_lon, min_lat, max_lon, max_lat = wide.bounds
    k = math.cos(math.radians((min_lat + max_lat) / 2))
    size = 400
    scale = size / max((max_lon - min_lon) * k, max_lat - min_lat)
    ox, oy = 40, 80

    def project(lon: float, lat: float) -> tuple[float, float]:
        return ox + (lon - min_lon) * k * scale, oy + (max_lat - lat) * scale

    def path(geom) -> str:
        rings = []
        polys = geom.geoms if hasattr(geom, "geoms") else [geom]
        for poly in polys:
            for ring in [poly.exterior, *poly.interiors]:
                pts = [project(*c) for c in ring.coords]
                rings.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
        return " ".join(rings)

    s = Svg(1000, 520, "Corridor for the Lajkonik sample route",
            "The 243 km Lajkonik route buffered by 8 km and by 3 km, drawn from the real GPX "
            "with garmap's corridor code, next to the six steps that produce the clip polygon.")
    s.heading("From route to clip polygon",
              "resources/Lajkonik_250km_.final.gpx, drawn with garmap.corridor.build_corridor()")
    s.raw(f'<rect x="26" y="68" width="430" height="430" rx="8" fill="{CARD}" stroke="#d9dde2"/>')
    s.raw(f'<path d="{path(wide)}" fill="{BLUE}" fill-opacity="0.13" stroke="{BLUE}" stroke-width="1.5"/>')
    s.raw(f'<path d="{path(narrow)}" fill="{BLUE}" fill-opacity="0.22" stroke="{BLUE}" '
          'stroke-width="1" stroke-dasharray="4 3"/>')
    for line in lines:
        pts = [project(*c) for c in line.simplify(0.0005).coords]
        s.raw('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
              f'" fill="none" stroke="{RED}" stroke-width="2.4" stroke-linejoin="round"/>')
    km10 = 10_000 / 111_320 * scale
    s.raw(f'<path d="M50,482 h{km10:.1f}" stroke="{INK}" stroke-width="2"/>'
          f'<path d="M50,477 v10 M{50 + km10:.1f},477 v10" stroke="{INK}" stroke-width="1.5"/>')
    s.text(50 + km10 + 8, 486, "10 km", 11, INK, anchor="start")

    lx = 490
    s.raw(f'<path d="M{lx},92 h28" stroke="{RED}" stroke-width="2.4"/>')
    s.text(lx + 38, 96, "GPX track — 243 km, one segment", 12.5, anchor="start")
    s.raw(f'<rect x="{lx}" y="110" width="28" height="14" fill="{BLUE}" fill-opacity="0.22" '
          f'stroke="{BLUE}" stroke-dasharray="4 3"/>')
    s.text(lx + 38, 122, f"--buffer 3km  →  {area_km2(narrow):,.0f} km²", 12.5, anchor="start")
    s.raw(f'<rect x="{lx}" y="136" width="28" height="14" fill="{BLUE}" fill-opacity="0.13" stroke="{BLUE}"/>')
    s.text(lx + 38, 148, f"--buffer 8km  →  {area_km2(wide):,.0f} km²", 12.5, anchor="start")

    steps = [
        ("unary_union", "all track segments and routes become one geometry"),
        ("project", "to an azimuthal-equidistant CRS centred on the route centroid"),
        ("buffer", "by --buffer, in metres on the ground (quad_segs=8)"),
        ("unproject", "back to WGS84 lon/lat"),
        ("drop interior rings", "splitter r654 mishandles holes; a loop is filled in"),
        ("write corridor.poly", "osmosis polygon format, read by splitter and pyhgtmap"),
    ]
    y = 186
    for i, (name, detail) in enumerate(steps, start=1):
        s.raw(f'<circle cx="{lx + 13}" cy="{y + 16}" r="13" fill="{BLUE_BG}" stroke="{BLUE}"/>')
        s.text(lx + 13, y + 20.5, str(i), 12.5, BLUE, weight="700")
        s.text(lx + 38, y + 13, name, 13, INK, anchor="start", weight="600", mono=True)
        s.text(lx + 38, y + 29, detail, 11.5, MUTED, anchor="start")
        if i < len(steps):
            s.raw(f'<path d="M{lx + 13},{y + 30} v20" stroke="{BLUE}" stroke-width="1.2"/>')
        y += 50
    s.text(lx, 494, "At either buffer this loop closes over its own middle, so there is no hole to drop.",
           11, MUTED, anchor="start", italic=True)
    s.save("corridor.svg")


def set_cover() -> None:
    s = Svg(1000, 470, "Greedy extract selection",
            "A corridor crossing two voivodeships inside Poland: the greedy set cover picks the "
            "two small extracts rather than the country, and ignores a sliver over the border.")
    s.heading("Choosing extracts — weighted greedy set cover",
              "Each round takes the candidate with the most newly covered corridor per unit of its own area. Numbers are illustrative.")
    # left: schematic map
    s.raw(f'<rect x="30" y="80" width="400" height="290" rx="26" fill="{GREY_BG}" stroke="{LINE}" '
          'stroke-dasharray="6 4" stroke-width="1.4"/>')
    s.text(48, 102, "poland  (parent)", 12, MUTED, anchor="start", mono=True)
    s.raw(f'<rect x="70" y="190" width="150" height="160" rx="14" fill="{CARD}" stroke="{LINE}" stroke-width="1.4"/>')
    s.raw(f'<rect x="220" y="170" width="170" height="180" rx="14" fill="{CARD}" stroke="{LINE}" stroke-width="1.4"/>')
    s.text(145, 212, "malopolskie", 12, INK, mono=True)
    s.text(305, 192, "podkarpackie", 12, INK, mono=True)
    s.raw(f'<rect x="30" y="372" width="400" height="70" rx="14" fill="{CARD}" stroke="{LINE}" stroke-width="1.4"/>')
    s.text(90, 414, "slovakia", 12, INK, mono=True)
    # corridor blob
    s.raw(f'<path d="M105,300 C120,250 180,240 215,270 C250,300 290,250 330,262 '
          f'C362,272 366,320 335,334 C300,350 276,404 238,366 C200,338 150,362 122,346 C104,336 98,320 105,300 Z" '
          f'fill="{BLUE}" fill-opacity="0.2" stroke="{BLUE}" stroke-width="1.6"/>')
    s.raw(f'<path d="M128,318 C160,270 200,300 235,318 C270,336 300,290 338,300" fill="none" '
          f'stroke="{RED}" stroke-width="2.4"/>')
    s.arrow([(262, 404), (262, 384)], colour=AMBER)
    s.text(190, 420, "sliver < 0.1 % of corridor: ignored", 11, AMBER, anchor="start", weight="600")

    # right: rounds
    x = 470
    s.text(x, 96, "score = newly covered corridor ÷ region area", 13, INK, anchor="start", weight="600", mono=True)
    rows = [
        ("Round 1", [("malopolskie", "58 % ÷ 1.9", "0.31", True), ("podkarpackie", "42 % ÷ 2.2", "0.19", False),
                     ("poland", "100 % ÷ 40", "0.03", False), ("slovakia", "gain 0.05 % < MIN_GAIN", "skip", False)]),
        ("Round 2", [("podkarpackie", "42 % ÷ 2.2", "0.19", True), ("poland", "42 % ÷ 40", "0.01", False)]),
    ]
    y = 116
    for title, cands in rows:
        s.text(x, y + 16, title, 12.5, BLUE, anchor="start", weight="700")
        y += 24
        for name, calc, score, win in cands:
            if win:
                s.raw(f'<rect x="{x - 6}" y="{y - 3}" width="506" height="22" rx="5" fill="{GREEN_BG}" stroke="{GREEN}"/>')
            s.text(x + 4, y + 12, name, 12, INK, anchor="start", mono=True)
            s.text(x + 150, y + 12, calc, 12, MUTED, anchor="start")
            s.text(x + 400, y + 12, score, 12, INK, anchor="end", weight="600", mono=True)
            if win:
                s.text(x + 490, y + 12, "✓ chosen", 11.5, GREEN, anchor="end", weight="700")
            y += 24
        y += 6
    s.text(x, y + 14, "Stop: less than 0.1 % of the corridor is still uncovered (COVERAGE_TARGET = 0.999).",
           12, INK, anchor="start")
    y += 34
    s.box(x - 6, y, 245, 62, ["drop redundant", "a region whose ancestor was", "also chosen is removed"],
          size=12.5, sub_size=11)
    s.box(x + 255, y, 245, 62, ["more than 6 regions?", "replace them all with their", "smallest common ancestor"],
          size=12.5, sub_size=11)
    s.arrow([(x + 239, y + 31), (x + 255, y + 31)])
    s.text(x - 6, y + 86, "Result here: malopolskie + podkarpackie — two small downloads instead of all of Poland.",
           12, GREEN, anchor="start", weight="600")
    s.save("set-cover.svg")


def cache_flow() -> None:
    s = Svg(1000, 520, "Download cache decision flow",
            "http.download reuses a cached file younger than 14 days, revalidates older ones by "
            "ETag, and writes new downloads to a .part file before renaming.")
    s.heading("http.download() — when a cached file is reused",
              "Used for Geofabrik extracts and for the mkgmap / splitter release zips.")
    cx, lx, gx, fx = 400, 120, 690, 880
    s.diamond(cx, 110, 250, 70, ["file cached and", "no --refresh?"])
    s.diamond(cx, 210, 250, 70, ["younger than", "14 days?"])
    s.diamond(cx, 310, 250, 70, [".etag sidecar", "present?"])
    s.box(cx - 110, 385, 220, 50, ["HEAD", "If-None-Match: <etag>"], size=12.5, sub_size=11.5)
    s.arrow([(cx, 145), (cx, 175)], "yes", (cx + 16, 164))
    s.arrow([(cx, 245), (cx, 275)], "no", (cx + 14, 264))
    s.arrow([(cx, 345), (cx, 385)], "yes", (cx + 16, 368))

    s.box(lx - 96, 185, 192, 50, ["return cached file", "no network at all"], fill=GREEN_BG, stroke=GREEN,
          size=12.5, sub_size=11)
    s.arrow([(cx - 125, 210), (lx + 96, 210)], "yes", (250, 203))
    s.box(lx - 96, 360, 192, 50, ["return cached file", "304: mtime reset"], fill=GREEN_BG, stroke=GREEN,
          size=12.5, sub_size=11)
    s.box(lx - 96, 430, 192, 50, ["return cached file", "request failed: offline"], fill=GREEN_BG, stroke=GREEN,
          size=12.5, sub_size=11)
    s.arrow([(cx - 110, 400), (lx + 96, 388)], "304", (252, 386))
    s.arrow([(cx - 110, 422), (lx + 96, 452)], "error", (252, 452))

    s.box(gx - 100, 85, 200, 50, ["GET, streamed", "into <file>.part"], fill=BLUE_BG, stroke=BLUE,
          size=12.5, sub_size=11.5)
    s.arrow([(cx + 125, 110), (gx - 100, 110)], "no", (545, 103))
    s.arrow([(cx + 125, 310), (560, 310), (560, 126), (gx - 100, 126)], "no", (545, 303))
    s.arrow([(cx + 110, 410), (575, 410), (575, 131), (gx - 100, 131)], "any other status", (518, 428), anchor="start")
    s.diamond(gx, 210, 200, 70, ["completed?"])
    s.arrow([(gx, 135), (gx, 175)])
    s.box(gx - 100, 285, 200, 50, ["write .etag sidecar", "rename .part → file"], size=12.5, sub_size=11.5)
    s.arrow([(gx, 245), (gx, 285)], "yes", (gx + 16, 268))
    s.box(gx - 100, 375, 200, 50, ["return fresh file"], fill=GREEN_BG, stroke=GREEN, size=12.5)
    s.arrow([(gx, 335), (gx, 375)])
    s.box(fx - 85, 285, 170, 50, ["delete .part"], size=12.5)
    s.arrow([(gx + 100, 210), (fx, 210), (fx, 285)], "request error", (fx - 42, 203))
    s.box(fx - 85, 375, 170, 50, ["old copy? return it", "(stale but usable)"], fill=GREEN_BG, stroke=GREEN,
          size=12, sub_size=11)
    s.arrow([(fx, 335), (fx, 375)])
    s.box(fx - 85, 445, 170, 46, ["else GarmapError"], fill=RED_BG, stroke=RED, size=12.5, ink=RED)
    s.arrow([(fx, 425), (fx, 445)])
    s.save("cache-flow.svg")


def mapids() -> None:
    s = Svg(1000, 412, "Map id allocation",
            "splitter is given a block of 1000 map ids per extract starting at 63240001; contour "
            "tiles start at 63250001; mkgmap.args then renumbers OSM tiles consecutively.")
    s.heading("Map ids — two numbering steps",
              "splitter names tile files from per-extract blocks; mkgmap.args then assigns the ids that end up in the .img.")
    x0, bw = 40, 62
    for i in range(10):
        x = x0 + i * bw
        on = i < 2
        s.raw(f'<rect x="{x}" y="88" width="{bw}" height="44" fill="{BLUE_BG if on else CARD}" '
              f'stroke="{BLUE if on else LINE}" stroke-width="1.2"/>')
        s.text(x + bw / 2, 107, f"pass{i}", 11.5, INK if on else MUTED, weight="600", mono=True)
        s.text(x + bw / 2, 123, f"6324{i}001", 10, MUTED, mono=True)
    cx0 = x0 + 10 * bw + 26
    s.raw(f'<rect x="{cx0}" y="88" width="260" height="44" fill="{BROWN_BG}" stroke="{BROWN}" stroke-width="1.2"/>')
    s.text(cx0 + 130, 107, "contour tiles", 11.5, INK, weight="600")
    s.text(cx0 + 130, 123, "63250001 …", 10, MUTED, mono=True)
    s.text(x0, 152, "OSM range: 10 blocks × 1000 ids — one block per extract (MAPID_BLOCK, MAX_PASSES)", 11.5,
           MUTED, anchor="start")

    s.text(x0, 196, "Tile files written by splitter", 12.5, INK, anchor="start", weight="700")
    files = [("tiles/pass0/63240001.osm.pbf", 0), ("tiles/pass0/63240002.osm.pbf", 0),
             ("tiles/pass1/63241001.osm.pbf", 1), ("contours/lon…lat….osm.pbf", None)]
    names = ["mapname: 63240001", "mapname: 63240002", "mapname: 63240003", "mapname: 63250001"]
    w, gap = 218, 16
    for i, ((label, block), name) in enumerate(zip(files, names)):
        x = x0 + i * (w + gap)
        contour = block is None
        s.box(x, 206, w, 36, [label], fill=BROWN_BG if contour else BLUE_BG,
              stroke=BROWN if contour else BLUE, size=11.5, mono_title=True)
        s.arrow([(x + w / 2, 242), (x + w / 2, 330)])
        s.box(x, 332, w, 36, [name], size=12, mono_title=True)
    s.text(x0 + 2 * (w + gap) + w / 2 + 10, 290, "renumbered: 63241001 → 63240003", 11, AMBER,
           anchor="start", weight="600")
    s.text(x0, 392, "Lines written to mkgmap.args", 12.5, INK, anchor="start", weight="700")
    s.text(x0 + 200, 392, "— ids run consecutively from OSM_MAPID and CONTOUR_MAPID, in tile order", 11.5,
           MUTED, anchor="start")
    s.save("mapids.svg")


def style_typ() -> None:
    s = Svg(1000, 470, "Style and TYP",
            "The mkgmap default style is copied from the jar and patched in two places; the TYP "
            "file separately restyles existing line types; both feed mkgmap.")
    s.heading("Style decides what a way is; TYP decides how it looks",
              "style.materialise() builds the left-hand branch for every build; the TYP source ships inside the package.")
    # style branch
    s.box(30, 84, 200, 60, ["mkgmap.jar", "styles/default/*"], fill=GREY_BG, size=13, mono_title=True)
    s.arrow([(230, 114), (290, 114)], "copy", (260, 107))
    s.box(290, 84, 250, 60, ["<work>/cycle/", "a full copy of the default style"], size=13, mono_title=True)
    patches = [
        ("replace", "inc/contour_lines", "labels in metres, not feet"),
        ("append", "relations", "cycle route ref → way name"),
        ("rewrite", "info", "style summary"),
    ]
    for i, (verb, target, why) in enumerate(patches):
        y = 172 + i * 46
        s.box(30, y, 200, 38, [f"{verb}  {target}"], fill=AMBER_BG, stroke=AMBER, size=11.5, mono_title=True)
        s.arrow([(230, y + 19), (290, y + 19)])
        s.text(300, y + 23, why, 11.5, MUTED, anchor="start")
    s.raw(f'<path d="M290,144 V310 H540 V144" fill="none" stroke="{LINE}" stroke-width="1.4"/>')
    s.arrow([(540, 114), (700, 114), (700, 196)], "--style-file", (622, 107), colour=BLUE)

    # typ branch
    s.box(30, 368, 200, 60, ["style/cycle.txt", "TYP source, in the package"], fill=GREY_BG, size=13,
          mono_title=True)
    s.arrow([(230, 398), (700, 398), (700, 262)], "extra input file → compiled to cycle.typ", (440, 391),
            colour=BROWN)

    s.box(610, 198, 180, 62, ["mkgmap r4924", "--route --index --gmapsupp"], fill=BLUE_BG, stroke=BLUE, size=14,
          sub_size=11)
    s.arrow([(790, 229), (840, 229)])
    s.box(840, 204, 130, 50, ["gmapsupp.img"], fill=GREEN_BG, stroke=GREEN, size=12.5, mono_title=True)

    # typ legend
    s.text(726, 296, "Line types the TYP restyles", 12.5, INK, anchor="start", weight="700")
    legend = [
        ("0x11", "cycleway", "#0050C8", 6), ("0x0a", "track", "#8C5A28", 4), ("0x16", "path", "#786464", 2),
        ("0x06", "residential", "#A0A0A0", 4), ("0x20–22", "contours", "#B4783C", 1.5),
    ]
    for i, (code, label, colour, width) in enumerate(legend):
        x, y = 726, 318 + i * 20
        s.raw(f'<path d="M{x},{y} h34" stroke="{colour}" stroke-width="{width}" stroke-linecap="round"/>')
        s.text(x + 44, y + 4, code, 11.5, INK, anchor="start", mono=True)
        s.text(x + 100, y + 4, label, 11.5, MUTED, anchor="start")
    s.text(974, 448, "No custom (0x10000+) types: they would draw but not route.", 11, MUTED,
           anchor="end", italic=True)
    s.save("style-typ.svg")


def install_flow() -> None:
    s = Svg(1000, 440, "garmap install decision flow",
            "install copies to a mounted Garmin volume if one exists, otherwise uses mtp-sendfile "
            "if available, otherwise prints manual instructions.")
    s.heading("garmap install — three paths, tried in order",
              "The Edge 1040 is MTP-only, so on macOS the first path usually finds nothing.")
    s.diamond(190, 130, 280, 80, ["volume under /Volumes", "with a Garmin/ folder?"])
    s.diamond(190, 260, 280, 80, ["--mtp (default) and", "mtp-sendfile on PATH?"])
    s.arrow([(190, 170), (190, 220)], "none", (212, 200))
    s.box(80, 350, 220, 56, ["print manual steps", "MTP mode · OpenMTP · Garmin/Map/"], fill=AMBER_BG,
          stroke=AMBER, size=12.5, sub_size=11)
    s.arrow([(190, 300), (190, 350)], "no", (208, 330))

    s.box(410, 107, 180, 46, ["several volumes?", "prompt for one"], size=12, sub_size=11)
    s.arrow([(330, 130), (410, 130)], "one or more", (370, 123))
    s.diamond(700, 130, 190, 70, ["target exists,", "no --force?"])
    s.arrow([(590, 130), (605, 130)])
    s.box(830, 107, 150, 46, ["GarmapError", "use --force / --name"], fill=RED_BG, stroke=RED, size=12,
          sub_size=10.5, ink=RED)
    s.arrow([(795, 130), (830, 130)], "yes", (812, 123))
    s.box(610, 196, 180, 50, ["copy to", "<volume>/Garmin/Map/<name>"], fill=GREEN_BG, stroke=GREEN,
          size=12, sub_size=11)
    s.arrow([(700, 165), (700, 196)], "no", (716, 185))

    s.box(410, 236, 180, 50, ["mtp-sendfile IMG", "Garmin/Map/<name>"], fill=BLUE_BG, stroke=BLUE, size=12,
          sub_size=11, mono_title=True)
    s.arrow([(330, 260), (410, 260)], "yes", (370, 253))
    s.box(610, 300, 180, 46, ["sent over MTP"], fill=GREEN_BG, stroke=GREEN, size=12.5)
    s.arrow([(590, 270), (700, 270), (700, 300)], "exit 0", (650, 263))
    s.box(410, 350, 380, 56, ["GarmapError: mtp-sendfile failed", "its output, followed by the manual steps"],
          fill=RED_BG, stroke=RED, size=12.5, sub_size=11, ink=RED)
    s.arrow([(500, 286), (500, 350)], "non-zero exit", (508, 322), anchor="start")
    s.text(820, 222, "then: map-list-cap reminder", 11, MUTED, anchor="start", italic=True)
    s.text(820, 326, "then: map-list-cap reminder", 11, MUTED, anchor="start", italic=True)
    s.save("install-flow.svg")


if __name__ == "__main__":
    for draw in (pipeline, modules, corridor, set_cover, cache_flow, mapids, style_typ, install_flow):
        draw()
        print(f"wrote {draw.__name__}")
