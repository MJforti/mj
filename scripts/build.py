#!/usr/bin/env python3
"""Render every profile card in assets/ from scripts/content.py and data/stats.json.

    python scripts/build.py            render only (offline, standard library only)
    python scripts/build.py --fetch    refresh data/stats.json from GitHub first

--fetch reads PROFILE_TOKEN or GITHUB_TOKEN. With a classic PAT in PROFILE_TOKEN
(scope read:user) private contributions are counted too; otherwise public ones only.
"""
import base64, datetime as dt, html, json, math, os, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import content as C  # noqa: E402

FONT_DIR = ROOT / "scripts" / "fonts"
ASSETS = ROOT / "assets"
STATS = ROOT / "data" / "stats.json"
METRICS = json.loads((FONT_DIR / "metrics.json").read_text())
ICONS = json.loads((ROOT / "scripts" / "icons.json").read_text())

# ── design tokens ────────────────────────────────────────────────────────────
W = 900
PANEL, RAISED, LINE, LINE2 = "#0E1016", "#13161D", "#1E222B", "#2A2F3A"
TEXT, MUTED, DIM = "#F2F3F5", "#9198A4", "#5D636F"
EMBER, AMBER, SKY, OK = "#FF7A3D", "#FFB25C", "#7CC4FA", "#4ADE80"
EMPTY = "#1A1E26"

FONTS = {
    "display": ("mjD", "-apple-system,'SF Pro Display','Segoe UI',Helvetica,Arial,sans-serif"),
    "sans": ("mjS", "-apple-system,'SF Pro Text','Segoe UI',Helvetica,Arial,sans-serif"),
    "sans-medium": ("mjSM", "-apple-system,'SF Pro Text','Segoe UI',Helvetica,Arial,sans-serif"),
    "sans-semibold": ("mjSS", "-apple-system,'SF Pro Text','Segoe UI',Helvetica,Arial,sans-serif"),
    "mono": ("mjM", "'SF Mono',Menlo,Consolas,monospace"),
    "mono-medium": ("mjMM", "'SF Mono',Menlo,Consolas,monospace"),
}
_B64 = {}

TITLES = {
    "typescript": "TypeScript", "javascript": "JavaScript", "python": "Python", "cplusplus": "C++",
    "react": "React", "nextdotjs": "Next.js", "tailwindcss": "Tailwind CSS", "vite": "Vite",
    "nodedotjs": "Node.js", "express": "Express", "fastapi": "FastAPI", "postgresql": "PostgreSQL",
    "supabase": "Supabase", "sqlite": "SQLite", "prisma": "Prisma", "googlecloud": "Google Cloud",
    "vercel": "Vercel", "docker": "Docker", "git": "Git", "github": "GitHub", "pytest": "pytest",
}
# Brand colours that vanish on a dark panel get a readable stand-in.
ICON_COLOR = {
    "amazonwebservices": "#FF9900", "sqlite": "#6FB3E0", "cplusplus": "#6A9FDB", "openjdk": "#F0932B",
    "googlegemini": "#A98BF0", "pwa": "#A57CF2", "prisma": TEXT, "postgresql": "#6E93E8",
    "python": "#5A9BD5", "typescript": "#4C8FE0", "googlecloud": "#5B9BF8",
}
GLOBE = ("M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm6.9 6h-2.95a15.7 15.7 0 0 0-1.38-3.56A8.03 8.03 0 0 1 18.9 8ZM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96ZM4.26 14a8.2 8.2 0 0 1 0-4h3.38a16.5 16.5 0 0 0 0 4H4.26Zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56A7.99 7.99 0 0 1 5.08 16Zm2.95-8H5.08a7.99 7.99 0 0 1 4.33-3.56A15.7 15.7 0 0 0 8.03 8ZM12 19.96A14.1 14.1 0 0 1 10.09 16h3.82A14.1 14.1 0 0 1 12 19.96ZM14.34 14H9.66a14.7 14.7 0 0 1 0-4h4.68a14.7 14.7 0 0 1 0 4Zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95a8.03 8.03 0 0 1-4.33 3.56ZM16.36 14a16.5 16.5 0 0 0 0-4h3.38a8.2 8.2 0 0 1 0 4h-3.38Z")


def esc(s):
    return html.escape(str(s), quote=True)


def measure(s, font="sans", size=14, ls=0.0):
    m = METRICS[font]
    w = sum(m["widths"].get(ch, m["upm"] * 0.6) for ch in s) / m["upm"] * size
    return w + ls * max(len(s) - 1, 0)


def wrap(s, font, size, maxw):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if measure(trial, font, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def icon_color(slug):
    if slug in ICON_COLOR:
        return ICON_COLOR[slug]
    hexc = ICONS.get(slug, {}).get("hex", "FFFFFF")
    return TEXT if lum(hexc) < 0.3 else "#" + hexc


def parse_item(item):
    slug, _, label = item.partition(":")
    return slug or None, label or TITLES.get(slug, slug)


# ── SVG card ─────────────────────────────────────────────────────────────────
BASE_CSS = """
.fi{animation:fi .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
@keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.grow{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
@keyframes grow{from{transform:scaleY(.04)}to{transform:scaleY(1)}}
.blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.pulse{animation:pulse 2.4s ease-in-out infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 1.6s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.fi,.grow,.blink,.pulse,.spin{animation:none!important}}
"""


class Card:
    def __init__(self, h, title, desc, w=W):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.body, self.defs, self.css, self.fonts = [], [], [], set()
        self._ids = 0

    def uid(self, p="i"):
        self._ids += 1
        return f"{p}{self._ids}"

    def add(self, *parts):
        self.body.extend(parts)

    def text(self, x, y, s, font="sans", size=14, fill=TEXT, anchor=None, ls=0, extra=""):
        missing = {ch for ch in s if ch not in METRICS[font]["widths"]}
        if missing:
            print(f"  ! {self.title}: font '{font}' lacks {''.join(sorted(missing))!r} in {s!r}")
        self.fonts.add(font)
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                f'class="f-{font}"{a}{l}{extra}>{esc(s)}</text>')

    def tspans(self, x, y, runs, font="sans", size=14, anchor=None, extra=""):
        """runs: [(text, fill, font_or_None)] on one line."""
        out = []
        for s, fill, f in runs:
            f = f or font
            self.fonts.add(f)
            out.append(f'<tspan fill="{fill}" class="f-{f}">{esc(s)}</tspan>')
        a = f' text-anchor="{anchor}"' if anchor else ""
        return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}"{a}{extra} xml:space="preserve">{"".join(out)}</text>'

    def panel(self, glow=None):
        hid = self.uid("hl")
        self.defs.append(
            f'<linearGradient id="{hid}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity=".14"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
        self.body.insert(0, f'<rect x=".5" y=".5" width="{self.w - 1}" height="{self.h - 1}" rx="20" fill="{PANEL}" stroke="{LINE}"/>'
                            f'<rect x="60" y=".5" width="{self.w - 120}" height="1" fill="url(#{hid})"/>')
        if glow:
            gx, gy, r, col, op = glow
            gid = self.uid("gl")
            cid = self.uid("cl")
            self.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                             f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
                             f'<clipPath id="{cid}"><rect x="1" y="1" width="{self.w - 2}" height="{self.h - 2}" rx="20"/></clipPath>')
            self.body.insert(1, f'<g clip-path="url(#{cid})"><circle cx="{gx}" cy="{gy}" r="{r}" fill="url(#{gid})">'
                                f'<animate attributeName="cx" values="{gx};{gx - 60};{gx}" dur="14s" repeatCount="indefinite"/></circle></g>')

    def header(self, kicker, title, right=None, y=40):
        self.add(self.text(36, y, kicker, "mono", 12, EMBER, ls=1.8),
                 self.text(36, y + 38, title, "display", 30, TEXT, ls=-0.4))
        if right:
            self.add(self.text(self.w - 36, y, right, "mono", 11, DIM, "end", ls=1.2))

    def icon(self, slug, x, y, size, color=None):
        d = GLOBE if slug == "globe" else ICONS[slug]["path"]
        return f'<path transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})" d="{d}" fill="{color or icon_color(slug)}"/>'

    def chip(self, x, y, item, h=34, fs=14, isz=16, font="sans-medium", fill=RAISED):
        slug, label = parse_item(item)
        pad = h * 0.36
        tw = measure(label, font, fs)
        w = pad + (isz + h * 0.24 if slug else 0) + tw + pad
        if not slug:
            w += h * 0.22  # room for the dot
        parts = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h * 0.3:.1f}" fill="{fill}" stroke="{LINE2}"/>']
        tx = x + pad
        if slug:
            parts.append(self.icon(slug, tx, y + (h - isz) / 2, isz))
            tx += isz + h * 0.24
        else:
            parts.append(f'<circle cx="{tx + 3:.1f}" cy="{y + h / 2:.1f}" r="3" fill="{AMBER}"/>')
            tx += h * 0.22 + 6
        parts.append(self.text(tx, y + h / 2 + fs * 0.36, label, font, fs, TEXT))
        self.add(*parts)
        return w

    def render(self):
        faces = []
        for f in sorted(self.fonts):
            if f not in _B64:
                _B64[f] = base64.b64encode((FONT_DIR / f"{f}.woff2").read_bytes()).decode()
            fam, fallback = FONTS[f]
            faces.append(f"@font-face{{font-family:{fam};src:url(data:font/woff2;base64,{_B64[f]}) format('woff2')}}"
                         f".f-{f}{{font-family:{fam},{fallback}}}")
        css = "".join(faces) + BASE_CSS + "".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'fill="none" role="img" aria-labelledby="t d"><title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>'
                f'<defs><style>{css}</style>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')

    def save(self, name):
        path = ASSETS / f"{name}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render())
        print(f"  {path.relative_to(ASSETS.parent) if path.is_relative_to(ASSETS.parent) else path}  {path.stat().st_size / 1024:.1f} KB")


def check_icon(c, x, y, r, color, stroke=PANEL):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'
            f'<path d="M{x - r * .42:.1f} {y + r * .02:.1f}l{r * .3:.1f} {r * .3:.1f} {r * .56:.1f}-{r * .62:.1f}" '
            f'stroke="{stroke}" stroke-width="{max(r * .26, 1.6):.1f}" stroke-linecap="round" stroke-linejoin="round"/>')


def arrow_ne(x, y, s, color, sw=1.6):
    return (f'<path d="M{x:.1f} {y + s:.1f}L{x + s:.1f} {y:.1f}M{x + s * .3:.1f} {y:.1f}H{x + s:.1f}V{y + s * .7:.1f}" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


# ── stats ────────────────────────────────────────────────────────────────────
def load_stats():
    return json.loads(STATS.read_text()) if STATS.exists() else {}


def _request(url, token=None, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-card-builder"})
    if token:
        req.add_header("Authorization", f"bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


GQL = """query($login:String!){user(login:$login){
 contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}
 repositories(first:100,privacy:PUBLIC,isFork:false,ownerAffiliations:OWNER){nodes{isEmpty primaryLanguage{name color}}}}}"""


def fetch_stats():
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    stats = load_stats()
    days, languages, source = None, None, None
    if token:
        try:
            body = json.dumps({"query": GQL, "variables": {"login": C.USER}}).encode()
            res = json.loads(_request("https://api.github.com/graphql", token, body))
            user = res["data"]["user"]
            cal = user["contributionsCollection"]["contributionCalendar"]
            days = [[d["date"], d["contributionCount"]] for w in cal["weeks"] for d in w["contributionDays"]]
            counts = {}
            for n in user["repositories"]["nodes"]:
                if n["primaryLanguage"] and not n["isEmpty"]:
                    k = n["primaryLanguage"]["name"]
                    counts.setdefault(k, [0, n["primaryLanguage"]["color"] or "#888888"])[0] += 1
            languages = sorted(([k, v[0], v[1]] for k, v in counts.items()), key=lambda r: -r[1])
            source = "graphql"
        except Exception as e:  # fall back to the public calendar
            print(f"  graphql failed: {e}")
    if days is None:
        try:
            page = _request(f"https://github.com/users/{C.USER}/contributions")
            tips = {m[0]: m[1] for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page)}
            days = []
            for td in re.findall(r"<td\b[^>]*>", page):
                date, cid = re.search(r'data-date="([\d-]+)"', td), re.search(r'\bid="([^"]+)"', td)
                if not (date and cid):
                    continue
                m = re.match(r"\s*(\d[\d,]*) contribution", tips.get(cid.group(1), ""))
                days.append([date.group(1), int(m.group(1).replace(",", "")) if m else 0])
            days.sort()
            if not days:
                raise ValueError("no contribution cells found")
            source = "calendar"
        except Exception as e:
            print(f"  calendar failed: {e}")
    if days:
        stats["days"] = days
        stats["source"] = source
        stats["updated"] = dt.date.today().isoformat()
    if languages:
        stats["languages"] = languages
    STATS.parent.mkdir(exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=1))
    print(f"  stats: {len(days or [])} days via {source}, {len(languages or stats.get('languages', []))} languages")


def summarize(stats, today=None):
    days = stats.get("days") or []
    if not days:
        return None
    today = today or dt.date.fromisoformat(stats.get("updated", days[-1][0]))
    days = [(dt.date.fromisoformat(d), n) for d, n in days if dt.date.fromisoformat(d) <= today]
    counts = {d: n for d, n in days}
    year = [n for d, n in days if (today - d).days < 365]
    longest = run = 0
    for _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    cur, d = 0, today
    if not counts.get(d):
        d -= dt.timedelta(days=1)  # today may still be in progress
    while counts.get(d):
        cur += 1
        d -= dt.timedelta(days=1)
    last90 = [counts.get(today - dt.timedelta(days=i), 0) for i in range(89, -1, -1)]
    return {"total": sum(year), "active": sum(1 for n in year if n), "current": cur, "longest": longest,
            "last90": last90, "pct90": round(100 * sum(1 for n in last90 if n) / 90)}


# ── cards ────────────────────────────────────────────────────────────────────
def hero():
    H = 420
    c = Card(H, "Manthan Jain", "Manthan Jain. I turn manual workflows into software that runs itself. "
             "B.Tech CSE, Cloud Computing at Bennett University, class of 2028.")
    c.panel(glow=(790, 40, 380, EMBER, 0.20))
    # dot field on the right, fading toward the copy
    pid, mid, fid = c.uid("dots"), c.uid("mask"), c.uid("fade")
    c.defs.append(f'<pattern id="{pid}" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#2A2F3A"/></pattern>'
                  f'<radialGradient id="{fid}" cx=".78" cy=".5" r=".55"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                  f'<mask id="{mid}"><rect width="{W}" height="{H}" fill="url(#{fid})"/></mask>')
    c.add(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="url(#{pid})" mask="url(#{mid})"/>')

    x0 = 48
    k = C.HERO["kicker"]
    kw = measure(k, "mono", 11.5, 1.4) + 46
    c.add(f'<g class="fi">',
          f'<rect x="{x0}" y="44" width="{kw:.1f}" height="30" rx="15" fill="{RAISED}" stroke="{LINE2}"/>',
          f'<circle cx="{x0 + 17}" cy="59" r="4" fill="{OK}" class="pulse"/>',
          c.text(x0 + 30, 63, k, "mono", 11.5, MUTED, ls=1.4), "</g>")

    # name with a slow light sweep
    nsize = 74
    while measure(C.NAME, "display", nsize, -1.5) > 500:
        nsize -= 1
    gid = c.uid("name")
    c.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">'
                  f'<stop offset="0" stop-color="{TEXT}"/><stop offset=".43" stop-color="{TEXT}"/>'
                  f'<stop offset=".5" stop-color="#FFD3A6"/><stop offset=".57" stop-color="{TEXT}"/><stop offset="1" stop-color="{TEXT}"/>'
                  f'<animateTransform attributeName="gradientTransform" type="translate" values="-{W} 0;{W} 0;{W} 0" keyTimes="0;.4;1" dur="8s" repeatCount="indefinite"/>'
                  f'</linearGradient>')
    c.add(f'<g class="fi" style="--d:.1s">', c.text(x0 - 3, 160, C.NAME, "display", nsize, f"url(#{gid})", ls=-1.5), "</g>")

    eg = c.uid("ember")
    c.defs.append(f'<linearGradient id="{eg}" x1="0" x2="1"><stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{EMBER}"/></linearGradient>')
    s1, s2a, s2b = C.HERO["statement"]
    c.add(f'<g class="fi" style="--d:.25s">',
          c.text(x0, 212, s1, "sans-medium", 26, TEXT, ls=-0.3),
          c.tspans(x0, 248, [(s2a, TEXT, None), (s2b, f"url(#{eg})", "sans-semibold")], "sans-medium", 26, extra=' letter-spacing="-0.3"'),
          "</g>")
    c.add(f'<g class="fi" style="--d:.4s">',
          *[c.text(x0, 290 + i * 25, ln, "sans", 16.5, MUTED) for i, ln in enumerate(C.HERO["lines"])], "</g>")

    # terminal line with a typing loop
    ty, cmd = 342, C.HERO["command"]
    cw = METRICS["mono"]["widths"]["a"] / 1000 * 14
    prompt_w = measure("~ $ ", "mono", 14)
    cx = x0 + 18 + prompt_w
    full = len(cmd) * cw
    n = len(cmd)
    t_type, t_out, t_end = 0.30, 0.36, 0.93
    vals = [f"{i * cw:.1f}" for i in range(n + 1)] + [f"{full:.1f}", "0"]
    keys = [f"{t_type * i / n:.3f}" for i in range(n + 1)] + [f"{t_end:.3f}", "1"]
    keys[0] = "0"
    clip = c.uid("type")
    c.defs.append(f'<clipPath id="{clip}"><rect x="{cx:.1f}" y="{ty}" width="{full:.1f}" height="44">'
                  f'<animate attributeName="width" dur="9s" repeatCount="indefinite" calcMode="discrete" values="{";".join(vals)}" keyTimes="{";".join(keys)}"/>'
                  f'</rect></clipPath>')
    cur_vals = [f"{cx + float(v):.1f}" for v in vals[:-1]] + [f"{cx:.1f}"]
    out_x = cx + full + 16
    c.add(f'<g class="fi" style="--d:.55s">',
          f'<rect x="{x0}" y="{ty}" width="{min(out_x + 70 - x0, 500):.1f}" height="44" rx="12" fill="#0A0B0F" stroke="{LINE}"/>',
          c.tspans(x0 + 18, ty + 27, [("~ ", SKY, None), ("$ ", DIM, None)], "mono", 14),
          f'<g clip-path="url(#{clip})">', c.text(cx, ty + 27, cmd, "mono", 14, TEXT), "</g>",
          f'<rect x="{cx + full:.1f}" y="{ty + 14}" width="8" height="17" rx="1.5" fill="{AMBER}" class="blink">'
          f'<animate attributeName="x" dur="9s" repeatCount="indefinite" calcMode="discrete" values="{";".join(cur_vals)}" keyTimes="{";".join(keys)}"/></rect>',
          f'<g><animate attributeName="opacity" dur="9s" repeatCount="indefinite" calcMode="discrete" values="0;1;0" keyTimes="0;{t_out};{t_end}"/>',
          check_icon(c, round(out_x + 7), ty + 22, 7, OK, "#0A0B0F"),
          c.text(out_x + 20, ty + 27, "live", "mono", 14, OK), "</g>",
          "</g>")

    # topology: users → edge → api → {llm, postgres, cron}
    nodes = {"users": (652, 112), "edge": (814, 112), "api": (733, 214),
             "llm": (632, 318), "postgres": (733, 340), "cron": (834, 318)}
    dotc = {"users": SKY, "edge": SKY, "api": EMBER, "llm": "#A98BF0", "postgres": "#6E93E8", "cron": OK}
    edges = [("users", "edge"), ("edge", "api"), ("api", "llm"), ("api", "postgres"), ("api", "cron")]
    box = {k: measure(k, "mono", 12.5) + 36 for k in nodes}

    def path(a, b):
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        if ay == by:
            return f"M{ax + box[a] / 2:.1f} {ay}H{bx - box[b] / 2:.1f}"
        my = (ay + by) / 2
        return f"M{ax:.1f} {ay + 15}C{ax:.1f} {my:.1f} {bx:.1f} {my:.1f} {bx:.1f} {by - 15}"

    g = ['<g class="fi" style="--d:.3s">',
         c.text(W - 32, 48, "TOPOLOGY · AP-SOUTH-1", "mono", 10.5, DIM, "end", ls=1.4)]
    for a, b in edges:
        g.append(f'<path d="{path(a, b)}" stroke="{LINE2}" stroke-width="1.3"/>')
    for i, (a, b) in enumerate(edges):
        col = AMBER if i % 2 == 0 else SKY
        g.append(f'<circle r="2.8" fill="{col}" opacity="0"><animateMotion dur="2.6s" begin="{i * 0.5:.1f}s" repeatCount="indefinite" path="{path(a, b)}"/>'
                 f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.85;1" dur="2.6s" begin="{i * 0.5:.1f}s" repeatCount="indefinite"/></circle>')
    ax, ay = nodes["api"]
    g.append(f'<circle cx="{ax}" cy="{ay}" r="24" stroke="{EMBER}" stroke-width="1.2" fill="none" opacity="0">'
             f'<animate attributeName="r" values="24;54" dur="3s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values=".55;0" dur="3s" repeatCount="indefinite"/></circle>')
    for k_, (nx, ny) in nodes.items():
        bw = box[k_]
        stroke = EMBER if k_ == "api" else LINE2
        g.append(f'<rect x="{nx - bw / 2:.1f}" y="{ny - 15}" width="{bw:.1f}" height="30" rx="9" fill="{RAISED}" stroke="{stroke}"/>'
                 f'<circle cx="{nx - bw / 2 + 14:.1f}" cy="{ny}" r="3.2" fill="{dotc[k_]}"/>')
        g.append(c.text(nx - bw / 2 + 24, ny + 4.3, k_, "mono", 12.5, TEXT))
    g.append("</g>")
    c.add(*g)
    c.save("hero")


def status(stats):
    H = 404
    s = summarize(stats)
    today = dt.date.today()
    start, end = (dt.date.fromisoformat(C.DEGREE[k]) for k in ("start", "end"))
    pct = max(0, min(100, round(100 * (today - start).days / (end - start).days)))
    synced = s is not None
    c = Card(H, "Status", (f"{s['total']} contributions and {s['active']} active days in the last year. "
                           f"Current streak {s['current']} days, longest {s['longest']} days. " if synced else
                           "GitHub activity is synced by a daily workflow. ") + f"Degree {pct}% complete, graduating 2028.")
    c.panel()
    c.header("STATUS", "All systems shipping.")
    label = "OPERATIONAL" if synced else "SYNCING"
    col = OK if synced else AMBER
    lw = measure(label, "mono", 11, 1.4) + 40
    c.add(f'<rect x="{W - 36 - lw:.1f}" y="30" width="{lw:.1f}" height="28" rx="14" fill="{RAISED}" stroke="{LINE2}"/>',
          f'<circle cx="{W - 36 - lw + 16:.1f}" cy="44" r="4" fill="{col}" class="pulse"/>',
          c.text(W - 36 - lw + 28, 48, label, "mono", 11, col, ls=1.4),
          c.text(W - 36, 78, f"UPDATED {stats.get('updated', today.isoformat())}", "mono", 11.5, DIM, "end", ls=1.2))

    # metrics
    mets = [(s["total"] if synced else "—", "CONTRIBUTIONS · 12 MO"), (s["active"] if synced else "—", "ACTIVE DAYS · 12 MO"),
            (s["current"] if synced else "—", "CURRENT STREAK"), (s["longest"] if synced else "—", "LONGEST STREAK")]
    colw = (W - 72) / 4
    for i, (v, lab) in enumerate(mets):
        x = 36 + i * colw
        if i:
            c.add(f'<rect x="{x - 14:.1f}" y="112" width="1" height="50" fill="{LINE}"/>')
        unit = " d" if i >= 2 and synced else ""
        c.add(f'<g class="fi" style="--d:{.1 + i * .08:.2f}s">',
              c.tspans(x, 146, [(f"{v:,}" if isinstance(v, int) else v, TEXT, "display"), (unit, MUTED, "sans-medium")], "display", 34),
              c.text(x, 168, lab, "mono", 11.5, MUTED, ls=1.2), "</g>")

    # 90-day "uptime" bars
    y0 = 206
    c.add(c.text(36, y0, "COMMIT UPTIME · LAST 90 DAYS", "mono", 11.5, MUTED, ls=1.2),
          c.text(W - 36, y0, f"{s['pct90']}% OF DAYS ACTIVE" if synced else "AWAITING FIRST SYNC", "mono", 11.5, MUTED, "end", ls=1.2))
    gap, n = 2.6, 90
    bw = (W - 72 - gap * (n - 1)) / n
    last = s["last90"] if synced else [0] * n
    nz = sorted(v for v in last if v)
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]
    shades = ["#5A2E16", "#9A4A1F", "#D9652A", EMBER]
    bars = []
    for i, v in enumerate(last):
        x = 36 + i * (bw + gap)
        fill = EMPTY if not v else shades[sum(v > t for t in q)]
        bars.append(f'<rect x="{x:.2f}" y="{y0 + 14}" width="{bw:.2f}" height="38" rx="1.6" fill="{fill}" class="grow" style="--d:{.2 + i * .008:.3f}s"/>')
    c.add(*bars,
          c.text(36, y0 + 72, "90 DAYS AGO", "mono", 11, DIM, ls=1),
          c.text(W - 36, y0 + 72, "TODAY", "mono", 11, DIM, "end", ls=1))

    # degree build
    y1 = 312
    tw = W - 72 - 150
    eg = c.uid("deg")
    c.defs.append(f'<linearGradient id="{eg}" x1="0" x2="1"><stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{EMBER}"/></linearGradient>')
    c.add(c.text(36, y1, f"BUILD · {C.DEGREE['label']}", "mono", 11.5, MUTED, ls=1.2),
          f'<rect x="36" y="{y1 + 12}" width="{tw}" height="8" rx="4" fill="{EMPTY}"/>',
          f'<rect x="36" y="{y1 + 12}" width="{tw * pct / 100:.1f}" height="8" rx="4" fill="url(#{eg})"><animate attributeName="width" from="0" to="{tw * pct / 100:.1f}" dur="1.6s" begin=".3s" fill="freeze" calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1"/></rect>',
          c.tspans(W - 36, y1 + 21, [(f"{pct}%", TEXT, "mono-medium"), (f"  ETA {end.strftime('%b %Y').upper()}", DIM, None)], "mono", 12, "end"))

    # languages by public repo
    y2 = 360
    langs = stats.get("languages", [])
    tot = sum(r[1] for r in langs) or 1
    c.add(c.text(36, y2, "LANGUAGES · SHARE OF PUBLIC REPOS", "mono", 11.5, MUTED, ls=1.2))
    lx, lw_ = 36, W - 72 - 0
    legend_x = 330
    seg_x = lx
    segs, leg = [], []
    shown = langs[:5]
    for i, (name, cnt, col) in enumerate(shown):
        wseg = lw_ * cnt / tot if i < len(shown) - 1 or len(langs) > len(shown) else lx + lw_ - seg_x
        segs.append(f'<rect x="{seg_x:.1f}" y="{y2 + 12}" width="{max(wseg - 2, 1):.1f}" height="8" rx="2" fill="{col}"/>')
        seg_x += wseg
    for name, cnt, col in shown:
        label = f"{name} {round(100 * cnt / tot)}%"
        leg.append(f'<circle cx="{legend_x + 4:.1f}" cy="{y2 - 4}" r="4" fill="{col}"/>')
        leg.append(c.text(legend_x + 13, y2, label, "mono", 11.5, TEXT))
        legend_x += measure(label, "mono", 10.5) + 30
    c.add(*segs, *leg)
    c.save("status")


def about():
    rows = C.ABOUT
    lh, top = 28, 88
    H = top + len(rows) * lh + 34
    c = Card(H, "manthan.yaml", "About Manthan: " + "; ".join(
        f"{k}: {v}" if k else v for _, k, v, _ in rows if v))
    c.panel()
    c.add(f'<rect x="1" y="1" width="{W - 2}" height="50" rx="20" fill="{RAISED}"/>',
          f'<rect x="1" y="30" width="{W - 2}" height="21" fill="{RAISED}"/>',
          f'<rect x="1" y="51" width="{W - 2}" height="1" fill="{LINE}"/>')
    for i, col in enumerate(("#3A3F4B", "#3A3F4B", "#3A3F4B")):
        c.add(f'<circle cx="{30 + i * 18}" cy="26" r="5.5" fill="{col}"/>')
    tab = "manthan.yaml"
    tabw = measure(tab, "mono", 12.5) + 44
    c.add(f'<rect x="96" y="12" width="{tabw:.1f}" height="28" rx="8" fill="{PANEL}" stroke="{LINE2}"/>',
          f'<circle cx="112" cy="26" r="3.5" fill="{EMBER}"/>',
          c.text(122, 30.5, tab, "mono", 12.5, TEXT),
          c.text(W - 30, 30.5, "YAML · UTF-8 · ABOUT ME", "mono", 10.5, DIM, "end", ls=1.2))
    fs = 16
    cw = METRICS["mono"]["widths"]["a"] / 1000 * fs
    for i, (ind, key, val, comment) in enumerate(rows):
        y = top + i * lh
        runs = [("  " * ind, TEXT, None)]
        if key:
            runs += [(key, SKY, None), (":", DIM, None)]
            if val:
                runs += [(" " + val, TEXT, None)]
        else:
            runs += [("- ", DIM, None), (val, TEXT, None)]
        line = [c.text(58, y, str(i + 1), "mono", 12.5, DIM, "end"), c.tspans(80, y, runs, "mono", fs)]
        if comment:
            line.append(c.text(W - 36, y, "# " + comment, "mono", 14, AMBER, "end"))
        used = sum(len(r[0]) for r in runs) * cw + 80
        if comment and used > W - 36 - measure("# " + comment, "mono", 14) - 16:
            print(f"  ! about line {i + 1} collides with its comment")
        if used > W - 36:
            print(f"  ! about line {i + 1} is too long")
        c.add(f'<g class="fi" style="--d:{.05 + i * .04:.2f}s">', *line, "</g>")
    y = top + len(rows) * lh
    c.add(c.text(58, y, str(len(rows) + 1), "mono", 12.5, DIM, "end"),
          f'<rect x="80" y="{y - 14}" width="{cw:.1f}" height="18" rx="1.5" fill="{AMBER}" class="blink"/>')
    c.save("about")


def stack():
    rows = C.STACK
    top, rh = 104, 56
    H = top + len(rows) * rh + 14
    c = Card(H, "Stack", "Technologies Manthan builds with. " + ". ".join(
        f"{layer.title()}: " + ", ".join(parse_item(i)[1] for i in items) for layer, items in rows))
    c.panel()
    c.header("STACK", "The layers I build with.", "FROM PUBLIC REPOS, COURSEWORK + CERTS")
    sx = 50
    y_first, y_last = top + 17, top + (len(rows) - 1) * rh + 17
    c.add(f'<path d="M{sx} {y_first}V{y_last}" stroke="{LINE2}" stroke-width="1.2"/>',
          f'<circle cx="{sx}" r="3" fill="{AMBER}"><animateMotion dur="5s" repeatCount="indefinite" path="M0 {y_first}V{y_last}" calcMode="spline" keySplines=".5 0 .5 1" keyTimes="0;1"/>'
          f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.9;1" dur="5s" repeatCount="indefinite"/></circle>')
    for r, (layer, items) in enumerate(rows):
        y = top + r * rh
        c.add(f'<g class="fi" style="--d:{.08 + r * .07:.2f}s">',
              f'<circle cx="{sx}" cy="{y + 17}" r="5" fill="{PANEL}" stroke="{LINE2}" stroke-width="1.2"/>',
              c.text(72, y + 21.5, f"{r + 1:02d}", "mono", 11, DIM),
              c.text(98, y + 21.5, layer, "mono", 11.5, MUTED, ls=1.4))
        x = 220
        for it in items:
            x += c.chip(x, y, it) + 10
        if x - 10 > W - 30:
            print(f"  ! stack row {layer} overflows ({x:.0f}px)")
        c.add("</g>")
    c.save("stack")


def project_art(c, kind, cx, cy):
    g = []
    if kind == "shield":
        sh = f"M{cx} {cy - 58}L{cx + 46} {cy - 40}V{cy + 2}C{cx + 46} {cy + 32} {cx + 24} {cy + 50} {cx} {cy + 60}C{cx - 24} {cy + 50} {cx - 46} {cy + 32} {cx - 46} {cy + 2}V{cy - 40}Z"
        g += [f'<path d="{sh}" fill="{RAISED}" stroke="{EMBER}" stroke-width="1.6"/>',
              f'<path d="M{cx - 16} {cy}l11 11 22-24" stroke="{AMBER}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>']
        for i in range(3):  # injected payloads deflecting off the shield
            yy = cy - 30 + i * 30
            p = f"M{cx + 130} {yy}L{cx + 52} {yy}L{cx + 92} {yy - 24 + i * 6}"
            g.append(f'<circle r="3" fill="{SKY}" opacity="0"><animateMotion dur="3s" begin="{i * 1:.1f}s" repeatCount="indefinite" path="{p}" keyPoints="0;.62;1" keyTimes="0;.6;1" calcMode="linear"/>'
                     f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.6;1" dur="3s" begin="{i * 1:.1f}s" repeatCount="indefinite"/>'
                     f'<animate attributeName="fill" values="{SKY};{SKY};{EMBER}" keyTimes="0;.6;1" dur="3s" begin="{i * 1:.1f}s" repeatCount="indefinite"/></circle>')
        g.append(f'<path d="{sh}" fill="none" stroke="{EMBER}" stroke-width="1.2" opacity="0" transform-origin="{cx} {cy}">'
                 f'<animate attributeName="opacity" values=".6;0" dur="3s" repeatCount="indefinite"/>'
                 f'<animateTransform attributeName="transform" type="scale" values="1;1.25" dur="3s" repeatCount="indefinite"/></path>')
    elif kind == "scan":
        x, y, w, h = cx - 50, cy - 66, 100, 132
        g += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{RAISED}" stroke="{LINE2}"/>',
              f'<rect x="{x + 12}" y="{y + 14}" width="44" height="6" rx="3" fill="{MUTED}"/>',
              f'<rect x="{x + 12}" y="{y + 26}" width="28" height="4" rx="2" fill="{DIM}"/>']
        for i in range(6):
            yy = y + 46 + i * 13
            g.append(f'<rect x="{x + 12}" y="{yy}" width="{48 - (i % 3) * 8}" height="4" rx="2" fill="{DIM}"/>'
                     f'<rect x="{x + 70}" y="{yy}" width="18" height="4" rx="2" fill="{DIM}"/>')
        cid = c.uid("doc")
        c.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/></clipPath>'
                      f'<linearGradient id="{cid}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{EMBER}" stop-opacity="0"/><stop offset="1" stop-color="{EMBER}" stop-opacity=".35"/></linearGradient>')
        g.append(f'<g clip-path="url(#{cid})"><g><animateTransform attributeName="transform" type="translate" values="0 -30;0 {h};0 {h}" keyTimes="0;.8;1" dur="3.2s" repeatCount="indefinite"/>'
                 f'<rect x="{x}" y="{y - 28}" width="{w}" height="28" fill="url(#{cid}g)"/><rect x="{x}" y="{y - 1}" width="{w}" height="2" fill="{AMBER}"/></g></g>')
        # spreadsheet output
        gx, gy = cx + 66, cy - 26
        for r in range(4):
            for col in range(3):
                g.append(f'<rect x="{gx + col * 15}" y="{gy + r * 15}" width="13" height="13" rx="2.5" fill="{OK if r == 0 else LINE2}" opacity="{1 if r == 0 else .9}"/>')
        g.append(f'<path d="M{cx + 54} {cy - 4}h8" stroke="{DIM}" stroke-width="1.5" stroke-linecap="round"/>')
    elif kind == "dial":
        r, cy = 46, cy + 8
        for i in range(12):  # month ticks
            ang = 2 * math.pi * i / 12
            x1, y1 = cx + (r + 11) * math.sin(ang), cy - (r + 11) * math.cos(ang)
            x2, y2 = cx + (r + 16) * math.sin(ang), cy - (r + 16) * math.cos(ang)
            g.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{AMBER if i in (9, 10) else LINE2}" stroke-width="2" stroke-linecap="round"/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{LINE2}" stroke-width="6"/>')
        circ = 2 * math.pi * r
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{EMBER}" stroke-width="6" stroke-linecap="round" '
                 f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" transform="rotate(-90 {cx} {cy})">'
                 f'<animate attributeName="stroke-dashoffset" values="{circ:.1f};{circ * .22:.1f};{circ * .22:.1f}" keyTimes="0;.6;1" dur="4s" repeatCount="indefinite"/></circle>')
        g.append(c.text(cx, cy + 4, "7d", "display", 26, TEXT, "middle"))
        g.append(c.text(cx, cy + 22, "UNTIL DUE", "mono", 8.5, MUTED, "middle", ls=1))
    elif kind == "boxes":
        def cube(x, y, s, top_col):
            return (f'<path d="M{x} {y}l{s} {-s * .5} {s} {s * .5} {-s} {s * .5}z" fill="{top_col}"/>'
                    f'<path d="M{x} {y}v{s}l{s} {s * .5}v{-s}z" fill="#1A1E27"/>'
                    f'<path d="M{x + 2 * s} {y}v{s}l{-s} {s * .5}v{-s}z" fill="#232834"/>')
        s = 26
        bx, by = cx - 70, cy - 4
        g += [cube(bx, by, s, "#3A3F4B"), cube(bx + 2 * s, by, s, "#3A3F4B"), cube(bx + s, by - s * 1.0, s, AMBER)]
        # sync ring
        rx_, ry_ = cx + 62, cy + 2
        g.append(f'<circle cx="{rx_}" cy="{ry_}" r="26" stroke="{LINE2}" stroke-width="1.5"/>'
                 f'<g><animateTransform attributeName="transform" type="rotate" values="0 {rx_} {ry_};360 {rx_} {ry_}" dur="2.4s" repeatCount="indefinite"/>'
                 f'<path d="M{rx_ + 26} {ry_}a26 26 0 0 1-26 26" stroke="{SKY}" stroke-width="2.4" stroke-linecap="round"/>'
                 f'<path d="M{rx_ - 26} {ry_}a26 26 0 0 1 26-26" stroke="{SKY}" stroke-width="2.4" stroke-linecap="round"/></g>')
        g.append(c.text(rx_, ry_ + 50, "SYNC", "mono", 9, MUTED, "middle", ls=1.4))
        g.append(f'<circle cx="{cx - 44}" cy="{cy + 58}" r="3.5" fill="{OK}" class="pulse"/>')
        g.append(c.text(cx - 34, cy + 61.5, "OFFLINE OK", "mono", 9, MUTED, ls=1.4))
    elif kind == "agent":
        ax_, bx_ = cx - 74, cx + 74
        p = f"M{ax_ + 34} {cy}H{bx_ - 36}"
        g += [f'<path d="{p}" stroke="{LINE2}" stroke-width="1.4" stroke-dasharray="3 5"/>',
              f'<circle cx="{ax_}" cy="{cy}" r="22" fill="{RAISED}" stroke="#A98BF0" stroke-width="1.5"/>',
              f'<circle cx="{ax_ - 7}" cy="{cy - 3}" r="2.6" fill="#A98BF0"/><circle cx="{ax_ + 7}" cy="{cy - 3}" r="2.6" fill="#A98BF0"/>',
              f'<path d="M{ax_ - 7} {cy + 7}q7 5 14 0" stroke="#A98BF0" stroke-width="1.8" stroke-linecap="round"/>',
              f'<rect x="{bx_ - 22}" y="{cy - 22}" width="44" height="44" rx="11" fill="{RAISED}" stroke="{LINE2}" stroke-width="1.5"/>',
              c.text(bx_, cy + 4.5, "API", "mono", 12, TEXT, "middle"),
              c.text(ax_, cy + 42, "AGENT", "mono", 9, MUTED, "middle", ls=1.4),
              c.text(bx_, cy + 42, "PAID", "mono", 9, MUTED, "middle", ls=1.4)]
        g.append(f'<g><animateMotion dur="2.8s" repeatCount="indefinite" path="{p}" keyPoints="0;1;1" keyTimes="0;.75;1" calcMode="linear"/>'
                 f'<circle r="11" fill="{AMBER}"/>' + c.text(0, 3.5, "402", "mono", 7.5, PANEL, "middle") + "</g>")
        g.append(c.text(cx, cy - 34, "x402", "mono", 11, AMBER, "middle", ls=1))
    return g


def project(p):
    H = 236
    c = Card(H, p["title"], f"{p['title']}. {p['desc']} {p['facts']}.")
    c.panel()
    # art panel on the right
    ax, aw = 640, W - 640 - 18
    pid, mid, fid = c.uid("grid"), c.uid("m"), c.uid("f")
    c.defs.append(f'<pattern id="{pid}" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" stroke="#1A1E27" stroke-width=".8"/></pattern>'
                  f'<radialGradient id="{fid}"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                  f'<mask id="{mid}"><rect x="{ax}" y="18" width="{aw}" height="{H - 36}" fill="url(#{fid})"/></mask>')
    c.add(f'<rect x="{ax}" y="18" width="{aw}" height="{H - 36}" rx="14" fill="#0B0D12" stroke="{LINE}"/>',
          f'<rect x="{ax}" y="18" width="{aw}" height="{H - 36}" rx="14" fill="url(#{pid})" mask="url(#{mid})"/>')
    c.add(f'<g class="fi" style="--d:.2s">', *project_art(c, p["art"], ax + aw / 2, H / 2 + 6), "</g>")
    if p.get("live"):
        lw = measure("LIVE", "mono", 10.5, 1.4) + 52
        c.add(f'<rect x="{ax + aw - 14 - lw:.1f}" y="30" width="{lw:.1f}" height="24" rx="12" fill="{PANEL}" stroke="{LINE2}"/>',
              f'<circle cx="{ax + aw - 14 - lw + 13:.1f}" cy="42" r="3.5" fill="{OK}" class="pulse"/>',
              c.text(ax + aw - 14 - lw + 23, 46, "LIVE", "mono", 10.5, TEXT, ls=1.4),
              arrow_ne(ax + aw - 33, 38.5, 7, MUTED, 1.4))
    # copy
    x0, maxw = 36, ax - 36 - 28
    c.add('<g class="fi">',
          c.text(x0, 44, p["kicker"], "mono", 11.5, EMBER, ls=1.6),
          c.text(x0, 84, p["title"], "display", 31, TEXT, ls=-0.4))
    tw = measure(p["title"], "display", 31, -0.4)
    c.add(arrow_ne(x0 + tw + 12, 66, 11, DIM, 1.8))
    lines = wrap(p["desc"], "sans", 16, maxw)
    if len(lines) > 2:
        print(f"  ! {p['title']} description wraps to {len(lines)} lines; shorten it in content.py")
    for i, ln in enumerate(lines[:2]):
        c.add(c.text(x0, 115 + i * 23, ln, "sans", 16, MUTED))
    fy = 115 + len(lines[:2]) * 23 + 6
    c.add(c.text(x0, fy, p["facts"], "mono", 12, AMBER))
    if measure(p["facts"], "mono", 12) > maxw:
        print(f"  ! {p['title']} facts overflow")
    c.add("</g>")
    x = x0
    c.add('<g class="fi" style="--d:.12s">')
    for it in p["stack"]:
        x += c.chip(x, H - 52, it, h=28, fs=12.5, isz=14) + 8
    c.add("</g>")
    c.save(f"projects/{p['slug']}")


def exploring():
    items = C.EXPLORING
    top, rh = 108, 62
    H = top + len(items) * rh + 6
    c = Card(H, "Currently exploring", "Currently exploring: " + "; ".join(
        f"{t} ({s})" for s, t, _ in items))
    c.panel()
    today = dt.date.today()
    c.header("NOW", "Currently exploring.", f"PIPELINE · RUN {today:%Y.%m}")
    ix = 54
    y_first, y_last = top + 4, top + (len(items) - 1) * rh + 4
    c.add(f'<path d="M{ix} {y_first}V{y_last}" stroke="{LINE2}" stroke-width="1.4"/>')
    lab = {"done": ("PASSED", OK), "running": ("RUNNING", AMBER), "queued": ("QUEUED", DIM)}
    for i, (st, title, detail) in enumerate(items):
        y = top + i * rh
        g = [f'<g class="fi" style="--d:{.08 + i * .08:.2f}s">']
        if st == "done":
            g.append(check_icon(c, ix, y + 4, 11, OK))
        elif st == "running":
            g.append(f'<circle cx="{ix}" cy="{y + 4}" r="11" fill="{PANEL}" stroke="{LINE2}" stroke-width="2"/>'
                     f'<path d="M{ix} {y - 7}a11 11 0 0 1 11 11" stroke="{AMBER}" stroke-width="2.4" stroke-linecap="round">'
                     f'<animateTransform attributeName="transform" type="rotate" values="0 {ix} {y + 4};360 {ix} {y + 4}" dur="1.6s" begin="-{i * .4:.1f}s" repeatCount="indefinite"/></path>'
                     f'<circle cx="{ix}" cy="{y + 4}" r="3" fill="{AMBER}" class="pulse"/>')
        else:
            g.append(f'<circle cx="{ix}" cy="{y + 4}" r="10" fill="{PANEL}" stroke="{DIM}" stroke-width="1.6" stroke-dasharray="3 3"/>')
        name, col = lab[st]
        g += [c.text(88, y + 9, title, "sans-medium", 18, TEXT if st != "queued" else "#C9CDD4", ls=-0.2),
              c.text(88, y + 31, detail, "sans", 14.5, MUTED)]
        pw = measure(name, "mono", 10.5, 1.4) + 24
        g += [f'<rect x="{W - 36 - pw:.1f}" y="{y - 9}" width="{pw:.1f}" height="24" rx="12" fill="{RAISED}" stroke="{LINE2}"/>',
              c.text(W - 36 - pw / 2, y + 7.5, name, "mono", 10.5, col, "middle", ls=1.4), "</g>"]
        c.add(*g)
    c.save("exploring")


def section(name, kicker, title, right=None):
    c = Card(84, title, f"{kicker.title()}: {title}")
    c.panel()
    tw = measure(title, "display", 26, -0.3)
    rw = measure(right, "mono", 11, 1.2) + 24 if right else 0
    c.add(c.text(36, 34, kicker, "mono", 11.5, EMBER, ls=1.8),
          c.text(36, 66, title, "display", 26, TEXT, ls=-0.3),
          f'<rect x="{36 + tw + 22:.1f}" y="57" width="{W - 36 - tw - 22 - 36 - rw:.1f}" height="1" fill="{LINE2}"/>')
    if right:
        c.add(c.text(W - 36, 61, right, "mono", 11, DIM, "end", ls=1.2))
    c.save(f"sections/{name}")


def divider():
    c = Card(28, "Divider", "Section divider")
    gid = c.uid("dv")
    c.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" x2="220"><stop offset="0" stop-color="{EMBER}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{AMBER}"/><stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></linearGradient>')
    c.add(f'<rect x="0" y="13.5" width="{W}" height="1" fill="{LINE}"/>',
          f'<rect x="-220" y="13" width="220" height="2" fill="url(#{gid})"><animate attributeName="x" values="-220;{W};{W}" keyTimes="0;.7;1" dur="6s" repeatCount="indefinite"/></rect>',
          f'<rect x="{W / 2 - 4}" y="10" width="8" height="8" rx="1.5" transform="rotate(45 {W / 2} 14)" fill="{PANEL}" stroke="{DIM}"/>')
    c.save("divider")


def connect():
    H = 206
    c = Card(H, "Connect", f"{C.CONNECT['title']} {C.CONNECT['sub']}")
    c.panel(glow=(120, 220, 320, EMBER, 0.14))
    c.header("CONNECT", C.CONNECT["title"])
    for i, ln in enumerate(wrap(C.CONNECT["sub"], "sans", 16, 560)):
        c.add(c.text(36, 112 + i * 24, ln, "sans", 16, MUTED))
    c.add(c.text(36, H - 30, f"@{C.USER.lower()}", "mono", 12.5, DIM))
    # broadcast rings
    bx, by = W - 120, H / 2 + 4
    c.add(f'<circle cx="{bx}" cy="{by}" r="7" fill="{EMBER}"/>')
    for i in range(3):
        c.add(f'<circle cx="{bx}" cy="{by}" r="10" stroke="{AMBER}" stroke-width="1.4" opacity="0">'
              f'<animate attributeName="r" values="10;70" dur="3.6s" begin="{i * 1.2:.1f}s" repeatCount="indefinite"/>'
              f'<animate attributeName="opacity" values=".7;0" dur="3.6s" begin="{i * 1.2:.1f}s" repeatCount="indefinite"/></circle>')
    c.save("connect")


def social_tiles():
    for slug, label, _ in C.SOCIAL:
        fs, isz, h = 14, 18, 44
        w = round(16 + isz + 10 + measure(label, "sans-medium", fs) + 16 + 14)
        c = Card(h, label, f"{label} profile", w=w)
        c.add(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{PANEL}" stroke="{LINE2}"/>',
              c.icon(slug, 16, (h - isz) / 2, isz, TEXT),
              c.text(16 + isz + 10, h / 2 + 5, label, "sans-medium", fs, TEXT),
              arrow_ne(w - 22, h / 2 - 3.5, 7, DIM, 1.4))
        c.save(f"social/{slug}")


def snake_placeholder():
    """Shown only until the workflow has generated the real snake."""
    for theme in ("dark", "light"):
        path = ASSETS / "generated" / f"snake-{theme}.svg"
        if path.exists():
            continue
        c = Card(120, "Contribution snake", "The contribution snake appears after the first workflow run.")
        c.add(f'<rect x=".5" y=".5" width="{W - 1}" height="119" rx="16" fill="{PANEL if theme == "dark" else "#F6F8FA"}" stroke="{LINE if theme == "dark" else "#D0D7DE"}" stroke-dasharray="4 6"/>',
              c.text(W / 2, 66, "The snake hatches after the first “Refresh profile” workflow run.", "mono", 13,
                     MUTED if theme == "dark" else "#57606A", "middle"))
        c.save(f"generated/snake-{theme}")


def readme():
    gh = f"https://github.com/{C.USER}"
    social = "&nbsp;\n".join(
        f'  <a href="{url}"><img src="./assets/social/{slug}.svg" height="44" alt="{label}" /></a>'
        for slug, label, url in C.SOCIAL)
    projects = "\n\n".join(
        f'<a href="{gh}/{p["repo"]}"><img src="./assets/projects/{p["slug"]}.svg" width="100%" '
        f'alt="{esc(p["title"])}: {esc(p["desc"])}" /></a>' for p in C.PROJECTS)
    lives = " &nbsp;·&nbsp; ".join(f'<a href="{p["live"]}">{esc(p["title"])}</a>' for p in C.PROJECTS if p.get("live"))
    linkedin = next(url for slug, _, url in C.SOCIAL if slug == "linkedin")
    text = f"""<!--
  This README is generated by scripts/build.py from scripts/content.py.
  Edit the content file and run `python scripts/build.py`; the daily workflow does the same.
-->

<p align="center">
  <img src="./assets/hero.svg" width="100%" alt="Manthan Jain. I turn manual workflows into software that runs itself. B.Tech CSE, Cloud Computing at Bennett University, class of 2028." />
</p>

<p align="center">
{social}
</p>

<img src="./assets/status.svg" width="100%" alt="Status: GitHub contributions, streaks, 90-day activity, degree progress and language mix. Refreshed daily." />

<img src="./assets/about.svg" width="100%" alt="About me, written as manthan.yaml: CSE undergrad at Bennett University building toward cloud and AI systems engineering." />

<img src="./assets/divider.svg" width="100%" alt="" />

<img src="./assets/stack.svg" width="100%" alt="Stack: TypeScript, JavaScript, Python, C++, Java, SQL; React, Next.js, Tailwind CSS, Vite; Node.js, Express, FastAPI; PostgreSQL, Supabase, SQLite, Prisma; AWS, Google Cloud, Vercel, Docker; Gemini API, prompt engineering, LLM evaluation, RAG; Git, GitHub, pytest." />

<img src="./assets/sections/work.svg" width="100%" alt="Selected work" />

{projects}

<p align="center"><sub>Live: &nbsp;{lives}</sub></p>

<img src="./assets/divider.svg" width="100%" alt="" />

<img src="./assets/exploring.svg" width="100%" alt="Currently exploring: cloud architecture on AWS, LLM security and evaluation, agentic AI, automation, Kubernetes and Terraform." />

<img src="./assets/sections/graph.svg" width="100%" alt="The graph" />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/generated/snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/generated/snake-light.svg" />
  <img src="./assets/generated/snake-dark.svg" width="100%" alt="A snake eating Manthan's GitHub contribution graph, regenerated daily." />
</picture>

<a href="{linkedin}"><img src="./assets/connect.svg" width="100%" alt="{esc(C.CONNECT['title'])} {esc(C.CONNECT['sub'])}" /></a>

<p align="center"><sub>Every card here is a hand-built SVG, re-rendered daily by GitHub Actions. &nbsp;<a href="./scripts/content.py">Edit the content</a></sub></p>
"""
    (ROOT / "README.md").write_text(text)
    print("  README.md")


def main():
    if "--fetch" in sys.argv:
        fetch_stats()
    stats = load_stats()
    print("rendering")
    hero(); status(stats); about(); stack(); exploring(); divider(); connect(); social_tiles()
    section("work", "SELECTED WORK", "Things I’ve shipped.", f"{len(C.PROJECTS)} PROJECTS")
    section("graph", "THE GRAPH", "Contribution history, eaten daily.")
    for p in C.PROJECTS:
        project(p)
    snake_placeholder()
    readme()


if __name__ == "__main__":
    main()
