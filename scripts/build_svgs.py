"""Generate the profile README terminal as ONE connected SVG.

    python scripts/build_svgs.py [--snake PATH] [--out PATH]

Sections, top to bottom, inside a single terminal frame:
boot header, stack dashboard, live stats, contribution snake, key-hint footer.

Stats come from the GitHub GraphQL API when GITHUB_TOKEN is set (CI does this,
see .github/workflows/profile.yml); without it the stats box says "offline".
--snake embeds an SVG made by Platane/snk; without it the box shows a notice.
Edit the data blocks below and push: CI rebuilds the image into the `output` branch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
USER = "RafaBits"

# Phosphor palette (same tokens as the "ccs" console design).
C = {
    "bg": "#030705",
    "panel2": "#0a1a10",
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
PAD = 16
FONT = 13
LH = 19
CHAR = FONT * 0.6  # advance of a monospace glyph; sizes typing clips and chips
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

BOOT_CMD = "./boot --profile rafabits"
BOOT = [
    [("[ ok ] ", C["g"]), ("godot 4 ", C["textHi"]), ("..................... ", C["line"]), ("gamedev online", C["dim"])],
    [("[ ok ] ", C["g"]), ("python ", C["textHi"]), ("...................... ", C["line"]), ("automation + data", C["dim"])],
    [("[ ok ] ", C["g"]), ("ai / ml ", C["textHi"]), ("..................... ", C["line"]), ("agents + vision", C["dim"])],
    [("[info] ", C["c"]), ("background: finance & data (FP&A, BI, ETL pipelines)", C["text"])],
]

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

KEYS = [("1", "gamedev"), ("2", "python"), ("3", "ai"), ("?", "help"), ("q", "quit")]


# --------------------------------------------------------------------------- stats

@dataclass(frozen=True)
class Stats:
    contributions: int
    commits: int
    pull_requests: int
    private: int
    current_streak: int
    longest_streak: int
    best_day: int
    last_active: str
    public_repos: int
    stars: int
    followers: int
    since: int
    fetched: str


QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def streaks(days: list[tuple[str, int]], today: str) -> tuple[int, int]:
    """(current, longest) runs of days with contributions, days sorted by date.

    Today with zero contributions does not break the current streak: the day is
    not over yet, so counting starts from yesterday.
    """
    longest = run = 0
    for _, n in days:
        run = run + 1 if n > 0 else 0
        longest = max(longest, run)
    current = 0
    for date, n in reversed(days):
        if date > today:
            continue
        if n == 0:
            if date == today and current == 0:
                continue
            break
        current += 1
    return current, longest


def fetch_stats(token: str, now: dt.datetime) -> Stats:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "rafabits-profile"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub GraphQL error: {payload.get('errors') or 'user not found'}")
    u = payload["data"]["user"]
    cc = u["contributionsCollection"]
    days = sorted(
        (d["date"], d["contributionCount"])
        for w in cc["contributionCalendar"]["weeks"]
        for d in w["contributionDays"]
    )
    today = now.date().isoformat()
    current, longest = streaks(days, today)
    active = [d for d, n in days if n > 0 and d <= today]
    return Stats(
        contributions=cc["contributionCalendar"]["totalContributions"],
        commits=cc["totalCommitContributions"],
        pull_requests=cc["totalPullRequestContributions"],
        private=cc["restrictedContributionsCount"],
        current_streak=current,
        longest_streak=longest,
        best_day=max((n for _, n in days), default=0),
        last_active=active[-1] if active else "--",
        public_repos=u["repositories"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        followers=u["followers"]["totalCount"],
        since=int(u["createdAt"][:4]),
        fetched=today,
    )


# --------------------------------------------------------------------------- svg primitives

def t(x: float, y: float, s: str, fill: str, *, weight: str = "400", cls: str = "", anchor: str = "start") -> str:
    c = f' class="{cls}"' if cls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-weight="{weight}"{a}{c}>{escape(s)}</text>'


def spans(x: float, y: float, parts: list[tuple[str, str]]) -> str:
    """One text line made of (string, color) runs."""
    body = "".join(f'<tspan fill="{col}">{escape(s)}</tspan>' for s, col in parts)
    return f'<text x="{x:g}" y="{y:g}" xml:space="preserve">{body}</text>'


def reveal(at: float) -> str:
    return f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/>'


def cursor(x: float, y: float) -> str:
    return f'<rect class="rb-blink" x="{x:g}" y="{y:g}" width="{CHAR:g}" height="16" fill="{C["g"]}"/>'


def chip_at(x_right: float, y: float, s: str, col: str) -> str:
    cw = (len(s) + 1.2) * CHAR
    return (
        f'<rect x="{x_right - cw + 0.6 * CHAR:g}" y="{y - 8}" width="{cw:g}" height="16" fill="{C["bg"]}"/>'
        + t(x_right, y + 4.5, s, col, anchor="end")
    )


def box(x: float, y: float, w: float, h: float, title: str, chip: tuple[str, str] | None = None) -> str:
    tw = (len(title) + 1.2) * CHAR
    out = [
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" stroke="{C["line"]}"/>',
        f'<rect x="{x + 0.4 * CHAR:g}" y="{y - 8:g}" width="{tw:g}" height="16" fill="{C["bg"]}"/>',
        t(x + CHAR, y + 4.5, title, C["g"], cls="rb-lbl"),
    ]
    if chip:
        out.append(chip_at(x + w - CHAR, y, *chip))
    return "\n".join(out)


def prompt(y: float, path: str, note: str) -> str:
    return spans(PAD, y, [("rafabits://", C["g"]), (path, C["textHi"]), (f"   {note}", C["dim"])])


def kv_boxes(y: float, panels: list[tuple[str, tuple[str, str], list[tuple[str, str]]]], key_w: int = 8) -> tuple[str, float]:
    gap = 14
    rows = max(len(p[2]) for p in panels)
    bh = rows * LH + 26
    bw = (W - 2 * PAD - (len(panels) - 1) * gap) / len(panels)
    out = []
    for i, (title, chip, kvs) in enumerate(panels):
        bx = PAD + i * (bw + gap)
        out.append(box(bx, y, bw, bh, title, chip))
        for r, (k, v) in enumerate(kvs):
            out.append(spans(bx + CHAR, y + 24 + r * LH, [(f"{k:<{key_w}}", C["dim"]), (v, C["text"])]))
    return "\n".join(out), bh


def divider(y: float) -> str:
    return f'<line x1="0" x2="{W}" y1="{y:g}" y2="{y:g}" stroke="{C["line"]}" stroke-dasharray="2 4"/>'


# --------------------------------------------------------------------------- sections
# Each returns (markup in local coordinates, height); compose() stacks them.

def title_bar() -> tuple[str, float]:
    h = LH + 6
    brand = "rafabits"
    bw = (len(brand) + 2) * CHAR
    out = [
        f'<rect width="{W}" height="{h}" fill="{C["panel2"]}"/>',
        f'<line x1="0" x2="{W}" y1="{h}" y2="{h}" stroke="{C["line"]}"/>',
        f'<rect width="{bw:g}" height="{h}" fill="{C["g"]}"/>',
        t(CHAR, 17, brand, C["bg"], weight="700"),
        t(bw + 2 * CHAR, 17, f"~/github/{USER}", C["textHi"]),
        t(W - CHAR, 17, "tty0", C["dim"], anchor="end"),
        t(W - 7 * CHAR, 17, "● online", C["g"], anchor="end"),
    ]
    return "\n".join(out), h


def logo(x0: float, y0: float, word: str, px: float) -> str:
    rects = []
    for i, ch in enumerate(word):
        for r, row in enumerate(GLYPHS[ch]):
            for col, bit in enumerate(row):
                if bit == "#":
                    rects.append(f'<rect x="{x0 + (i * 6 + col) * px:g}" y="{y0 + r * px:g}" width="{px - 1:g}" height="{px - 1:g}"/>')
    pixels = "".join(rects)
    # cyan ghost offset = cheap chromatic aberration; green on top glows
    return (
        f'<g fill="{C["c"]}" opacity=".35" transform="translate(-2 1)">{pixels}</g>'
        f'<g fill="{C["g"]}" filter="url(#rb-glow)">{pixels}</g>'
    )


def boot(stats: Stats | None) -> tuple[str, float]:
    px, word = 9, "RAFABITS"
    logo_w = (len(word) * 6 - 1) * px
    out = [logo((W - logo_w) / 2, 26, word, px)]
    out.append(t(W / 2, 114, "game dev · python · artificial intelligence", C["c"], anchor="middle", cls="rb-glowtxt"))

    x, y = 28, 156
    ps1 = [("rafael@rafabits", C["g"]), (":", C["dim"]), ("~", C["c"]), ("$ ", C["dim"])]
    cmd_x = x + len("rafael@rafabits:~$ ") * CHAR
    n = len(BOOT_CMD)
    # SMIL, not CSS: CSS width animation is unreliable in Safari, and SMIL still
    # lands on the final frame where CSS animations are disabled.
    widths = ";".join(f"{k * CHAR:g}" for k in range(n + 1)) + f";{n * CHAR + 4:g}"
    out.append(spans(x, y, ps1))
    out.append(
        f'<clipPath id="rb-type"><rect x="{cmd_x:g}" y="{y - 14}" width="0" height="{LH}">'
        f'<animate attributeName="width" values="{widths}" calcMode="discrete" begin="0.4s" dur="1.4s" fill="freeze"/>'
        f'</rect></clipPath><g clip-path="url(#rb-type)">{t(cmd_x, y, BOOT_CMD, C["textHi"])}</g>'
    )
    sync = (
        [("[ ok ] ", C["g"]), ("stats ", C["textHi"]), ("....................... ", C["line"]), (f"synced {stats.fetched}", C["dim"])]
        if stats
        else [("[ -- ] ", C["warn"]), ("stats ", C["textHi"]), ("....................... ", C["line"]), ("offline (local build)", C["dim"])]
    )
    lines = BOOT[:3] + [sync] + BOOT[3:]
    for i, parts in enumerate(lines):
        out.append(f'<g opacity="0">{reveal(2.0 + i * 0.3)}{spans(x, y + (i + 1) * LH + 4, parts)}</g>')
    py = y + (len(lines) + 1) * LH + 14
    out.append(f'<g opacity="0">{reveal(2.2 + len(lines) * 0.3)}{spans(x, py, ps1)}{cursor(cmd_x, py - 13)}</g>')
    return "\n".join(out), py + 22


def stack() -> tuple[str, float]:
    out = [prompt(22, "stack", "what I build with, by area")]
    boxes, bh = kv_boxes(50, PANELS)
    out.append(boxes)

    ly = 50 + bh + 28
    lh = len(LOG) * LH + 52
    out.append(box(PAD, ly, W - 2 * PAD, lh, "NOW.LOG", ("following ↓", C["g"])))
    for i, (tag, col, msg) in enumerate(LOG):
        out.append(spans(PAD + CHAR, ly + 24 + i * LH, [(f"{i:02d}  ", C["dim"]), (f"{tag}  ", col), (msg, C["textHi"] if tag == "warn" else C["text"])]))
    iy = ly + lh - 26
    out.append(f'<line x1="{PAD + CHAR:g}" x2="{W - PAD - CHAR:g}" y1="{iy}" y2="{iy}" stroke="{C["line"]}"/>')
    ps = "rafabits ▸ "
    out.append(t(PAD + CHAR, iy + 18, ps, C["g"]))
    cx = PAD + CHAR + len(ps) * CHAR
    out.append(cursor(cx, iy + 5))
    out.append(t(cx + 3 * CHAR, iy + 18, "try: play | build | train | ship", C["dim"]))
    return "\n".join(out), ly + lh + 18


def fmt(n: int) -> str:
    return f"{n:,}"


def stats_section(s: Stats | None) -> tuple[str, float]:
    if s:
        note = f"live from the GitHub API · {s.fetched}"
        live = ("● live", C["g"])
        panels = [
            ("ACTIVITY", ("● 12 months", C["g"]), [("contribs", fmt(s.contributions)), ("commits", fmt(s.commits)), ("pull reqs", fmt(s.pull_requests)), ("private", fmt(s.private))]),
            ("STREAK", live, [("current", f"{s.current_streak} days"), ("longest", f"{s.longest_streak} days"), ("best day", fmt(s.best_day)), ("last", s.last_active)]),
            ("PROFILE", live, [("repos", f"{s.public_repos} public"), ("stars", fmt(s.stars)), ("followers", fmt(s.followers)), ("since", str(s.since))]),
        ]
    else:
        note = "offline: CI fills this in from the GitHub API"
        off = ("○ offline", C["warn"])
        panels = [
            ("ACTIVITY", off, [("contribs", "--"), ("commits", "--"), ("pull reqs", "--"), ("private", "--")]),
            ("STREAK", off, [("current", "--"), ("longest", "--"), ("best day", "--"), ("last", "--")]),
            ("PROFILE", off, [("repos", "--"), ("stars", "--"), ("followers", "--"), ("since", "--")]),
        ]
    boxes, bh = kv_boxes(50, panels, key_w=10)
    return prompt(22, "stats", note) + "\n" + boxes, 50 + bh + 18


def snake_section(snake_svg: str | None) -> tuple[str, float]:
    out = [prompt(22, "contrib", "the last 12 months, eaten by a snake")]
    bx, by, bw = PAD, 50, W - 2 * PAD
    if snake_svg:
        inner_w = bw - 2 * CHAR
        vb = re.search(r'viewBox="([^"]+)"', snake_svg)
        if not vb:
            raise ValueError("snake svg has no viewBox")
        _, _, vw, vh = (float(v) for v in vb.group(1).split())
        inner_h = inner_w * vh / vw
        body = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", snake_svg.strip(), flags=re.S)
        bh = inner_h + 20
        out.append(box(bx, by, bw, bh, "CONTRIB.GRID", ("● snk", C["g"])))
        out.append(
            f'<svg x="{bx + CHAR:g}" y="{by + 10:g}" width="{inner_w:g}" height="{inner_h:g}" viewBox="{vb.group(1)}">{body}</svg>'
        )
    else:
        bh = 3 * LH + 10
        out.append(box(bx, by, bw, bh, "CONTRIB.GRID", ("○ offline", C["warn"])))
        out.append(t(bx + CHAR, by + 34, "the snake is drawn in CI by Platane/snk (.github/workflows/profile.yml)", C["dim"]))
    return "\n".join(out), by + bh + 14


def footer() -> tuple[str, float]:
    h = LH + 6
    out = [
        f'<line x1="0" x2="{W}" y1="0" y2="0" stroke="{C["line"]}"/>',
        f'<rect y="0.5" width="{W}" height="{h}" fill="{C["panel2"]}"/>',
    ]
    x = CHAR
    for k, label in KEYS:
        kw = (len(k) + 1.2) * CHAR
        out.append(f'<rect x="{x:g}" y="3.5" width="{kw:g}" height="{LH}" fill="{C["c"]}"/>')
        out.append(t(x + 0.6 * CHAR, 17.5, k, C["bg"], weight="700"))
        out.append(t(x + kw + CHAR, 17.5, label, C["text"]))
        x += kw + (len(label) + 3) * CHAR
    out.append(t(W - CHAR, 17.5, "rendered as svg, built with python", C["dim"], anchor="end"))
    return "\n".join(out), h


# --------------------------------------------------------------------------- compose

CSS = f"""
  text {{ font-family: {MONO}; font-size: {FONT}px; }}
  .rb-lbl {{ letter-spacing: .06em; }}
  .rb-glowtxt {{ filter: drop-shadow(0 0 4px {C['c']}66); }}
  .rb-blink {{ animation: rb-blink 1.05s steps(1) infinite; }}
  @keyframes rb-blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .rb-blink {{ animation: none; }} }}
"""


def compose(stats: Stats | None, snake_svg: str | None) -> str:
    parts = [title_bar(), boot(stats), stack(), stats_section(stats), snake_section(snake_svg), footer()]
    y = 0.0
    body = []
    for i, (markup, h) in enumerate(parts):
        if 1 < i < len(parts) - 1:
            body.append(divider(y))
        body.append(f'<g transform="translate(0 {y:g})">\n{markup}\n</g>')
        y += h
    h = int(round(y))
    title = "rafabits terminal: game dev (Godot 4), Python and AI; stack, live GitHub stats and contribution snake"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-labelledby="rb-title">
<title id="rb-title">{escape(title)}</title>
<defs>
  <pattern id="rb-scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect y="2" width="4" height="1" fill="#000" opacity=".28"/></pattern>
  <radialGradient id="rb-vig" cx="50%" cy="50%" r="75%">
    <stop offset="62%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".55"/>
  </radialGradient>
  <filter id="rb-glow" x="-5%" y="-20%" width="110%" height="140%">
    <feGaussianBlur stdDeviation="2.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="rb-frame"><rect width="{W}" height="{h}" rx="8"/></clipPath>
</defs>
<style>{CSS}</style>
<g clip-path="url(#rb-frame)">
<rect width="{W}" height="{h}" fill="{C["bg"]}"/>
{chr(10).join(body)}
<rect width="{W}" height="{h}" fill="url(#rb-scan)" pointer-events="none"/>
<rect width="{W}" height="{h}" fill="url(#rb-vig)" pointer-events="none"/>
<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="8" fill="none" stroke="{C["line"]}"/>
</g>
</svg>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snake", type=Path, help="SVG generated by Platane/snk to embed")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "profile.svg")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        stats = fetch_stats(token, dt.datetime.now(dt.timezone.utc))
    else:
        stats = None
        print("GITHUB_TOKEN not set: stats render as offline", file=sys.stderr)
    snake = args.snake.read_text(encoding="utf-8") if args.snake else None
    if snake is None:
        print("--snake not given: snake box renders as offline", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(compose(stats, snake), encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
