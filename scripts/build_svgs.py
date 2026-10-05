"""Generate the terminal-style SVGs used by the profile README.

Run from the repo root:  python scripts/build_svgs.py
Writes assets/header.svg, assets/dashboard.svg and assets/footer.svg.
Edit the data blocks below and re-run; the SVGs are committed as build output.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Phosphor palette (same tokens as the "ccs" console design).
C = {
    "bg": "#030705",
    "panel": "#061009",
    "panel2": "#0a1a10",
    "sel": "#0f2d1b",
    "line": "#174a2e",
    "lineHi": "#2f9a5c",
    "g": "#3dff8a",
    "c": "#39c6ff",
    "text": "#c6f6d8",
    "textHi": "#effff4",
    "dim": "#7cb896",
    "warn": "#ffb347",
}

W = 880
FONT = 13
LH = 19
CHAR = FONT * 0.6  # advance of a monospace glyph; used to size typing clips
MONO = "'JetBrains Mono','Cascadia Mono','SF Mono',Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"

# 5x7 pixel glyphs for the logo.
GLYPHS = {
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}


def t(x: float, y: float, s: str, fill: str, *, weight: str = "400", cls: str = "", anchor: str = "start") -> str:
    c = f' class="{cls}"' if cls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-weight="{weight}"{a}{c}>{escape(s)}</text>'


def spans(x: float, y: float, parts: list[tuple[str, str]], *, cls: str = "") -> str:
    """One text line made of (string, color) runs, laid out with xml:space=preserve."""
    c = f' class="{cls}"' if cls else ""
    body = "".join(f'<tspan fill="{col}">{escape(s)}</tspan>' for s, col in parts)
    return f'<text x="{x:g}" y="{y:g}" xml:space="preserve"{c}>{body}</text>'


def defs(h: int, extra_css: str = "") -> str:
    return f"""<defs>
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">
    <rect y="2" width="4" height="1" fill="#000" opacity=".28"/>
  </pattern>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%">
    <stop offset="62%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".55"/>
  </radialGradient>
  <filter id="glow" x="-5%" y="-20%" width="110%" height="140%">
    <feGaussianBlur stdDeviation="2.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="frame"><rect width="{W}" height="{h}" rx="8"/></clipPath>
</defs>
<style>
  text {{ font-family: {MONO}; font-size: {FONT}px; }}
  .blink {{ animation: blink 1.05s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
{extra_css}</style>"""


def crt(h: int) -> str:
    return (
        f'<rect width="{W}" height="{h}" fill="url(#scan)" pointer-events="none"/>'
        f'<rect width="{W}" height="{h}" fill="url(#vig)" pointer-events="none"/>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="8" fill="none" stroke="{C["line"]}"/>'
    )


def svg(h: int, title: str, body: str, extra_css: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
        f'role="img" aria-labelledby="title">\n<title id="title">{escape(title)}</title>\n'
        f"{defs(h, extra_css)}\n"
        f'<g clip-path="url(#frame)">\n<rect width="{W}" height="{h}" fill="{C["bg"]}"/>\n{body}\n{crt(h)}\n</g>\n</svg>\n'
    )


def bar(y: int, brand: str, path: str, right: list[tuple[str, str]], *, bottom: bool = False) -> str:
    edge = y if bottom else y + LH + 6
    out = [
        f'<rect y="{y}" width="{W}" height="{LH + 6}" fill="{C["panel2"]}"/>',
        f'<line x1="0" x2="{W}" y1="{edge}" y2="{edge}" stroke="{C["line"]}"/>',
    ]
    if brand:
        bw = len(brand) * CHAR + 2 * CHAR
        out.append(f'<rect y="{y}" width="{bw:g}" height="{LH + 6}" fill="{C["g"]}"/>')
        out.append(t(CHAR, y + 17, brand, C["bg"], weight="700"))
        out.append(t(bw + 2 * CHAR, y + 17, path, C["textHi"]))
    x = W - CHAR
    for s, col in reversed(right):
        out.append(t(x, y + 17, s, col, anchor="end"))
        x -= (len(s) + 3) * CHAR
    return "\n".join(out)


def box(x: float, y: float, w: float, h: float, title: str, chip: tuple[str, str] | None = None, color: str = "") -> str:
    color = color or C["g"]
    tw = (len(title) + 1.2) * CHAR
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{C["line"]}"/>',
        f'<rect x="{x + CHAR - 0.6 * CHAR:g}" y="{y - 8}" width="{tw:g}" height="16" fill="{C["bg"]}"/>',
        t(x + CHAR, y + 4.5, title, color, cls="lbl"),
    ]
    if chip:
        s, col = chip
        cw = (len(s) + 1.2) * CHAR
        out.append(f'<rect x="{x + w - CHAR - cw + 0.6 * CHAR:g}" y="{y - 8}" width="{cw:g}" height="16" fill="{C["bg"]}"/>')
        out.append(t(x + w - CHAR, y + 4.5, s, col, anchor="end"))
    return "\n".join(out)


# --------------------------------------------------------------------------- header

BOOT_CMD = "./boot --profile rafabits"
BOOT = [
    [("[ ok ] ", C["g"]), ("godot 4 ", C["textHi"]), ("..................... ", C["line"]), ("gamedev online", C["dim"])],
    [("[ ok ] ", C["g"]), ("python ", C["textHi"]), ("...................... ", C["line"]), ("automation + data", C["dim"])],
    [("[ ok ] ", C["g"]), ("ai / ml ", C["textHi"]), ("..................... ", C["line"]), ("agents + vision", C["dim"])],
    [("[info] ", C["c"]), ("background: finance & data (FP&A, BI, ETL pipelines)", C["text"])],
]


def logo(x0: float, y0: float, word: str, px: float) -> str:
    rects = []
    for i, ch in enumerate(word):
        for r, row in enumerate(GLYPHS[ch]):
            for col, bit in enumerate(row):
                if bit == "#":
                    rx = x0 + (i * 6 + col) * px
                    ry = y0 + r * px
                    rects.append(f'<rect x="{rx:g}" y="{ry:g}" width="{px - 1:g}" height="{px - 1:g}"/>')
    pixels = "".join(rects)
    # cyan ghost offset = cheap chromatic aberration; green on top glows
    return (
        f'<g fill="{C["c"]}" opacity=".35" transform="translate(-2 1)">{pixels}</g>'
        f'<g fill="{C["g"]}" filter="url(#glow)">{pixels}</g>'
    )


def header() -> str:
    h = 330
    px = 9
    word = "RAFABITS"
    logo_w = (len(word) * 6 - 1) * px
    lx = (W - logo_w) / 2
    body = [bar(0, "rafabits", "~/github/RafaBits", [("● online", C["g"]), ("tty0", C["dim"])])]
    body.append(logo(lx, 52, word, px))
    sub = "game dev · python · artificial intelligence"
    body.append(t(W / 2, 140, sub, C["c"], anchor="middle", cls="glowtxt"))

    x, y = 28, 182
    n = len(BOOT_CMD)
    body.append(spans(x, y, [("rafael@rafabits", C["g"]), (":", C["dim"]), ("~", C["c"]), ("$ ", C["dim"])]))
    px0 = x + len("rafael@rafabits:~$ ") * CHAR
    # SMIL instead of CSS: animating rect width via CSS is unreliable in Safari, and
    # SMIL still ends on the final frame when CSS animations are disabled.
    widths = ";".join(f"{k * CHAR:g}" for k in range(n + 1)) + f";{n * CHAR + 4:g}"
    body.append(
        f'<clipPath id="type"><rect x="{px0:g}" y="{y - 14}" width="0" height="{LH}">'
        f'<animate attributeName="width" values="{widths}" calcMode="discrete" begin="0.4s" dur="1.4s" fill="freeze"/>'
        f"</rect></clipPath>"
        f'<g clip-path="url(#type)">{t(px0, y, BOOT_CMD, C["textHi"])}</g>'
    )
    css = f"  .glowtxt {{ filter: drop-shadow(0 0 4px {C['c']}66); }}\n"
    for i, parts in enumerate(BOOT):
        cy = y + (i + 1) * LH + 4
        body.append(f'<g opacity="0">{reveal(2.0 + i * 0.35)}{spans(x, cy, parts)}</g>')
    py = y + (len(BOOT) + 1) * LH + 14
    body.append(
        f'<g opacity="0">{reveal(2.0 + len(BOOT) * 0.35 + 0.2)}'
        + spans(x, py, [("rafael@rafabits", C["g"]), (":", C["dim"]), ("~", C["c"]), ("$ ", C["dim"])])
        + f'<rect class="blink" x="{px0:g}" y="{py - 13}" width="{CHAR:g}" height="16" fill="{C["g"]}"/></g>'
    )
    return svg(h, "rafabits: game dev, python and artificial intelligence", "\n".join(body), css)


def reveal(at: float) -> str:
    return f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/>'


# --------------------------------------------------------------------------- dashboard

PANELS = [
    ("GAMEDEV", ("● active", C["g"]), [("engine", "Godot 4"), ("lang", "GDScript · C#"), ("also", "C++"), ("loop", "build · playtest · ship")]),
    ("PYTHON", ("● daily", C["g"]), [("core", "Python 3"), ("data", "pandas · NumPy"), ("db", "SQL · SQLite · MySQL"), ("infra", "Docker · GCP · Linux")]),
    ("AI / ML", ("● exploring", C["c"]), [("ml", "TensorFlow"), ("vision", "OpenCV"), ("agents", "LLMs · Claude Code"), ("glue", "Python everywhere")]),
]

LOG = [
    ("info", C["c"], "building games with Godot 4 and GDScript"),
    ("ok  ", C["g"], "automating the boring parts with Python"),
    ("info", C["c"], "wiring AI into both: agents, vision, dev tooling"),
    ("warn", C["warn"], "public repos loading... stay tuned"),
]


def dashboard() -> str:
    pad = 16
    gap = 14
    top = 30
    body = [spans(pad, top, [("rafabits://", C["g"]), ("stack", C["textHi"]), ("   what I build with, by area", C["dim"])])]

    by = top + 28
    bh = 4 * LH + 26
    bw = (W - 2 * pad - 2 * gap) / 3
    for i, (title, chip, rows) in enumerate(PANELS):
        bx = pad + i * (bw + gap)
        body.append(box(bx, by, bw, bh, title, chip))
        for r, (k, v) in enumerate(rows):
            ry = by + 24 + r * LH
            body.append(spans(bx + CHAR, ry, [(f"{k:<8}", C["dim"]), (v, C["text"])]))

    ly = by + bh + 28
    lh = len(LOG) * LH + 52
    body.append(box(pad, ly, W - 2 * pad, lh, "NOW.LOG", ("following ↓", C["g"])))
    for i, (tag, col, msg) in enumerate(LOG):
        ry = ly + 24 + i * LH
        body.append(spans(pad + CHAR, ry, [(f"{i:02d}  ", C["dim"]), (f"{tag}  ", col), (msg, C["textHi"] if tag == "warn" else C["text"])]))
    iy = ly + lh - 26
    body.append(f'<line x1="{pad + CHAR:g}" x2="{W - pad - CHAR:g}" y1="{iy}" y2="{iy}" stroke="{C["line"]}"/>')
    prompt = "rafabits ▸ "
    body.append(t(pad + CHAR, iy + 18, prompt, C["g"]))
    cx = pad + CHAR + len(prompt) * CHAR
    body.append(f'<rect class="blink" x="{cx:g}" y="{iy + 5}" width="{CHAR:g}" height="16" fill="{C["g"]}"/>')
    body.append(t(cx + 3 * CHAR, iy + 18, "try: play | build | train | ship", C["dim"]))

    h = int(ly + lh + pad)
    css = "  .lbl { letter-spacing: .06em; }\n"
    return svg(h, "stack: Godot 4, GDScript, C#, Python, SQL, Docker, GCP, TensorFlow, OpenCV, LLM agents", "\n".join(body), css)


# --------------------------------------------------------------------------- footer

KEYS = [("1", "gamedev"), ("2", "python"), ("3", "ai"), ("?", "help"), ("q", "quit")]


def footer() -> str:
    h = LH + 6
    body = [f'<rect width="{W}" height="{h}" fill="{C["panel2"]}"/>']
    x = CHAR
    for k, label in KEYS:
        kw = (len(k) + 1.2) * CHAR
        body.append(f'<rect x="{x:g}" y="3" width="{kw:g}" height="{LH}" fill="{C["c"]}"/>')
        body.append(t(x + 0.6 * CHAR, 17, k, C["bg"], weight="700"))
        body.append(t(x + kw + CHAR, 17, label, C["text"]))
        x += kw + (len(label) + 3) * CHAR
    body.append(t(W - CHAR, 17, "rendered as svg, built with python", C["dim"], anchor="end"))
    return svg(h, "key hints: 1 gamedev, 2 python, 3 ai, ? help, q quit", "\n".join(body))


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for name, build in (("header", header), ("dashboard", dashboard), ("footer", footer)):
        path = ASSETS / f"{name}.svg"
        path.write_text(build(), encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ASSETS.parent)}")


if __name__ == "__main__":
    main()
