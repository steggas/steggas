"""Generate the themed SVG assets for the steggas/steggas profile README.

Every SVG embeds a woff2 subset of the fonts it uses, because GitHub renders
README images as <img>, which cannot load external fonts. Palette follows
callumstegmann.com: navy, cream, copper. Text colours are checked against
WCAG AA (4.5:1) at build time.

Usage: python build_readme_assets.py <font_dir> <out_dir> [--static]
  --static  renders the no-animation fallback, for previews and screenshots.
"""
import base64
import io
import math
import sys
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

FONT_DIR = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
STATIC = len(sys.argv) > 3 and sys.argv[3] == "--static"

FONTS = {
    "sans": "InstrumentSans-Bold.ttf",
    "serif": "InstrumentSerif-Italic.ttf",
    "mono": "JetBrainsMono-Regular.ttf",
    "monob": "JetBrainsMono-Bold.ttf",
}

# page = the GitHub background a transparent SVG sits on.
THEMES = {
    "dark": dict(page="#0d1117", bg="#0a1424", panel="#0e1828", ink="#f0ebdd", soft="#c5c0b1",
                 mute="#8d91a1", line="rgba(240,235,221,0.16)", accent="#d68f50"),
    "light": dict(page="#ffffff", bg="#f5efe0", panel="#f5efe0", ink="#0e1a2b", soft="#2a3a55",
                  mute="#5c6680", line="rgba(14,26,43,0.16)", accent="#9a5e20"),
}

MONO_MIN = 16  # smallest mono size for information-bearing text, in SVG units

_tt = {k: TTFont(FONT_DIR / v) for k, v in FONTS.items()}


def _lum(hex_):
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


for _name, _t in THEMES.items():
    for _fg in ("ink", "soft", "mute", "accent"):
        for _bg in ("page", "bg", "panel"):
            _r = contrast(_t[_fg], _t[_bg])
            assert _r >= 4.5, f"{_name}: {_fg} on {_bg} is {_r:.2f}:1"


def width(text, font, size, tracking=0.0):
    """Advance width of text in px (no kerning), plus letter-spacing."""
    f = _tt[font]
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    adv = sum(hmtx[cmap.get(ord(c), cmap[ord(" ")])][0] for c in text)
    return adv / upm * size + tracking * len(text)


def font_face(font, text):
    """@font-face rule with a base64 woff2 subset covering text."""
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    f = TTFont(FONT_DIR / FONTS[font])
    sub = Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:'cs-{font}';"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    """Collects elements and the characters each font needs."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.body, self.css = [], []
        self.chars = {k: set() for k in FONTS}

    def text(self, x, y, s, font, size, fill, cls="", tracking=0, anchor="start", extra=""):
        self.chars[font].update(s)
        attrs = (f'x="{x:.1f}" y="{y:.1f}" font-family="cs-{font}" font-size="{size}" '
                 f'fill="{fill}"')
        if tracking:
            attrs += f' letter-spacing="{tracking}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if cls:
            attrs += f' class="{cls}"'
        self.body.append(f"<text {attrs} {extra}>{esc(s)}</text>")

    def raw(self, s):
        self.body.append(s)

    def render(self):
        faces = "".join(font_face(f, "".join(sorted(c))) for f, c in self.chars.items() if c)
        motion = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        if STATIC:
            motion = "*{animation:none!important}"
        css = "".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" role="img" aria-label="{esc(self.title)}">'
                f"<title>{esc(self.title)}</title>"
                f"<style>{faces}{css}{motion if css else ''}</style>"
                + "".join(self.body) + "</svg>")


# Entrance: fade up, staggered. Banner only: anything below the fold would
# finish animating before anyone scrolled to it.
FADE = (
    "@keyframes up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
    ".f{animation:up .7s cubic-bezier(.2,.7,.2,1) backwards}"
    + "".join(f".d{i}{{animation-delay:{i * 0.1:.2f}s}}" for i in range(8))
)

FRAMEWORKS = ["ISO 27001", "ISO 42001", "SOC 2", "DORA", "EU AI ACT", "GDPR", "POPIA"]


def banner(t):
    W, H = 1200, 384
    s = Svg(W, H, "Callum Stegmann. Senior GRC Consultant at Scytale, Cape Town. "
                  "Building management systems that protect the people on the receiving end.")
    s.css.append(FADE)
    n, step = len(FRAMEWORKS), 2.2
    cycle = n * step
    on = step / cycle * 100
    s.css.append(
        f"@keyframes cyc{{0%{{opacity:0;transform:translateY(8px)}}"
        f"{on * 0.15:.2f}%{{opacity:1;transform:none}}"
        f"{on * 0.85:.2f}%{{opacity:1;transform:none}}"
        f"{on:.2f}%,100%{{opacity:0;transform:translateY(-8px)}}}}"
        f".cy{{opacity:0;animation:cyc {cycle:.1f}s linear infinite both}}.cy0{{opacity:1}}"
        "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}"
        ".pulse{animation:pulse 2.4s ease-in-out infinite}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".spin{transform-origin:1066px 206px;animation:spin 60s linear infinite}"
        "@keyframes draw{from{stroke-dashoffset:var(--len)}}"
        ".tick{--len:64px;stroke-dasharray:64;animation:draw .7s 1s cubic-bezier(.2,.7,.2,1) backwards}"
        ".rule{--len:240px;stroke-dasharray:240;animation:draw 1s .5s cubic-bezier(.2,.7,.2,1) backwards}"
    )

    # Ground, dot grid fading in from the right.
    s.raw(
        f'<defs><pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1" fill="{t["ink"]}" fill-opacity=".10"/></pattern>'
        f'<radialGradient id="fade" cx="88%" cy="50%" r="55%"><stop offset="0" stop-color="#fff"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
        f'<path id="ring" d="M1066,206 m-56,0 a56,56 0 1,1 112,0 a56,56 0 1,1 -112,0"/></defs>'
        f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>'
        f'<rect width="{W}" height="{H}" rx="18" fill="url(#dots)" mask="url(#m)"/>'
    )

    # Top bar: location left, frameworks ticker right. The name lives once, below.
    s.raw(f'<circle class="pulse" cx="64" cy="54.5" r="4" fill="{t["accent"]}"/>')
    s.text(80, 60, "CAPE TOWN · SOUTH AFRICA", "mono", MONO_MIN, t["mute"], "f d1", tracking=2)
    label = "NOW DELIVERING"
    tx = W - 60 - max(width(fw, "monob", MONO_MIN, 2) for fw in FRAMEWORKS) + 2
    s.text(tx - 36 - width(label, "mono", MONO_MIN, 2), 60, label, "mono", MONO_MIN, t["mute"],
           "f d1", tracking=2)
    s.raw(f'<line class="f d1" x1="{tx - 24:.1f}" y1="54.5" x2="{tx - 10:.1f}" y2="54.5" '
          f'stroke="{t["accent"]}" stroke-width="1.5"/>')
    for i, fw in enumerate(FRAMEWORKS):
        s.text(tx, 60, fw, "monob", MONO_MIN, t["accent"], "cy cy0" if i == 0 else "cy",
               tracking=2, extra=f'style="animation-delay:{i * step:.1f}s"')
    s.raw(f'<line x1="60" y1="86" x2="{W - 60}" y2="86" stroke="{t["line"]}"/>')

    # Left gutter: section numeral, as on the site.
    s.text(60, 205, "00", "serif", 96, t["accent"], "f d2")
    s.text(62, 242, "INTRO", "monob", MONO_MIN, t["ink"], "f d2", tracking=3)

    # Main column. The name leads the entrance.
    x0 = 250
    s.text(x0, 140, "SENIOR GRC CONSULTANT · SCYTALE", "monob", MONO_MIN, t["accent"], "f d1",
           tracking=3)
    s.chars["sans"].update("Callum Stegmann.")
    s.raw(f'<text class="f d0" x="{x0}" y="226" font-family="cs-sans" font-size="80" '
          f'letter-spacing="-2.4" fill="{t["ink"]}">Callum Stegmann<tspan fill="{t["accent"]}">.</tspan></text>')
    s.raw(f'<line class="rule" x1="{x0 + 2}" y1="250" x2="{x0 + 242}" y2="250" '
          f'stroke="{t["accent"]}" stroke-width="2"/>')
    s.text(x0, 296, "Building management systems that protect", "serif", 31, t["soft"], "f d2")
    s.text(x0, 332, "the people on the receiving end.", "serif", 31, t["soft"], "f d3")

    # Auditor's seal: ring text (decorative) around a tick that draws itself in.
    ring = "GOVERNANCE · RISK · COMPLIANCE · "
    circ = 2 * math.pi * 56
    track = (circ - width(ring, "mono", 11)) / len(ring)
    s.chars["mono"].update(ring)
    s.raw(
        f'<g class="f d3">'
        f'<circle cx="1066" cy="206" r="72" fill="none" stroke="{t["accent"]}" stroke-opacity=".55"/>'
        f'<circle cx="1066" cy="206" r="40" fill="none" stroke="{t["accent"]}" stroke-opacity=".55"/>'
        f'<g class="spin"><text font-family="cs-mono" font-size="11" fill="{t["accent"]}" '
        f'letter-spacing="{track:.2f}" dy="3.8"><textPath href="#ring">{esc(ring)}</textPath></text></g>'
        f'<path class="tick" d="M1050,207 l11,11 l22,-25" fill="none" stroke="{t["accent"]}" '
        f'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    return s.render()


def section(t, num, label, aside, title):
    W, H = 1200, 96
    s = Svg(W, H, title)
    s.text(0, 66, num, "serif", 58, t["accent"])
    s.text(width(num, "serif", 58) + 26, 61, label, "monob", MONO_MIN, t["ink"], tracking=3)
    s.text(W, 61, aside, "mono", MONO_MIN, t["mute"], tracking=3, anchor="end")
    s.raw(f'<line x1="0" y1="92" x2="{W}" y2="92" stroke="{t["line"]}"/>')
    return s.render()


CERTS = [
    ("01", "ISO/IEC 42001", "Lead Auditor", "Mastermind", "2025"),
    ("02", "ISO/IEC 27001", "Lead Auditor", "Mastermind", "2025"),
    ("03", "ISO/IEC 27001", "Implementer", "PECB", "2024"),
]


def cert_text():
    return "; ".join(f"{std} {role} ({issuer}, {year})" for _, std, role, issuer, year in CERTS)


def certs(t):
    W, H, gap = 1200, 232, 24
    cw = (W - 2 * gap) / 3
    s = Svg(W, H, cert_text() + ".")
    for i, (n, std, role, issuer, year) in enumerate(CERTS):
        x = i * (cw + gap)
        s.raw(f'<rect x="{x + .5:.1f}" y=".5" width="{cw - 1:.1f}" height="{H - 1}" '
              f'rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>')
        s.text(x + 28, 68, n, "serif", 48, t["accent"])
        s.text(x + cw - 28, 60, f"{issuer.upper()} · {year}", "mono", 20, t["mute"],
               tracking=1.5, anchor="end")
        assert width(std, "sans", 40, -0.8) < cw - 56, std
        s.text(x + 28, 152, std, "sans", 40, t["ink"], tracking=-0.8)
        s.text(x + 28, 198, role, "serif", 35, t["soft"])
    return s.render()


STACK = ["Python", "PowerShell", "TypeScript", "Claude Code", "Obsidian",
         "Power Platform", "GitHub Actions", "Git"]


def stack(t):
    W, size, track, padx, gap, h = 1200, 20, 1.6, 22, 12, 58
    s = Svg(W, 0, ", ".join(STACK) + ".")
    tags = [x_.upper() for x_ in STACK]
    widths = [width(g, "monob", size, track) - track + padx * 2 + 20 for g in tags]
    total = sum(widths) + gap * (len(tags) - 1)
    rows = math.ceil(total / W)
    x, y, run = 0.5, 0.5, 0.0
    for tag, w in zip(tags, widths):
        if run and (run + w / 2 > total / rows * (y // (h + gap) + 1) or x + w > W):
            x, y = 0.5, y + h + gap
        run += w + gap
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" '
              f'fill="{t["panel"]}" stroke="{t["line"]}"/>'
              f'<circle cx="{x + padx:.1f}" cy="{y + h / 2:.1f}" r="5" fill="{t["accent"]}"/>')
        s.text(x + padx + 20, y + h / 2 + 7.2, tag, "monob", size, t["ink"], tracking=track)
        x += w + gap
    s.h = int(y + h + 1)
    return s.render()


def pill(t, label, value):
    """A contact link pill. Rendered at natural size, so text stays legible."""
    size, padx, h, gap = 13, 16, 38, 10
    lw = width(label, "monob", size, 2) - 2
    vw = width(value, "mono", size)
    W = int(padx + 12 + lw + gap + vw + gap + 10 + padx)
    s = Svg(W, h + 1, f"{label.title()}: {value}")
    s.raw(f'<rect x=".5" y=".5" width="{W - 1}" height="{h}" rx="{h / 2}" '
          f'fill="{t["panel"]}" stroke="{t["line"]}"/>'
          f'<circle cx="{padx:.1f}" cy="{h / 2 + .5:.1f}" r="4" fill="{t["accent"]}"/>')
    x = padx + 12
    s.text(x, h / 2 + 5, label, "monob", size, t["ink"], tracking=2)
    x += lw + gap
    s.text(x, h / 2 + 5, value, "mono", size, t["mute"])
    x += vw + gap
    cy = h / 2 + .5
    s.raw(f'<path d="M{x:.1f},{cy + 4:.1f} l8,-8 m-6,0 h6 v6" fill="none" stroke="{t["accent"]}" '
          f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    return s.render()


def footer(t):
    W, H = 1200, 96
    s = Svg(W, H, "Compliance done properly is protective work.")
    s.raw(f'<line x1="0" y1="1" x2="{W}" y2="1" stroke="{t["line"]}"/>')
    s.text(W / 2, 64, "Compliance done properly is protective work.", "serif", 32, t["soft"],
           anchor="middle")
    return s.render()


SECTIONS = [
    ("work", "01", "WORK", "WHAT I ACTUALLY DO", "01. Work: what I actually do."),
    ("credentials", "02", "CREDENTIALS", "WHAT I'VE EARNED", "02. Credentials: what I've earned."),
    ("stack", "03", "STACK", "WHAT I BUILD WITH", "03. Stack: what I build with."),
    ("beyond", "04", "BEYOND", "OFF THE CLOCK", "04. Beyond: off the clock."),
    ("contact", "05", "CONTACT", "FIND ME", "05. Contact: find me."),
]

CONTACT = [
    ("linkedin", "LINKEDIN", "/in/callumstegmann"),
    ("podcast", "PODCAST", "InCyber"),
    ("email", "EMAIL", "callumstegmann@gmail.com"),
]

if __name__ == "__main__":
    for name, t in THEMES.items():
        files = {
            f"banner-{name}.svg": banner(t),
            f"certs-{name}.svg": certs(t),
            f"stack-{name}.svg": stack(t),
            f"footer-{name}.svg": footer(t),
        }
        for slug, num, label, aside, title in SECTIONS:
            files[f"section-{slug}-{name}.svg"] = section(t, num, label, aside, title)
        for slug, label, value in CONTACT:
            files[f"contact-{slug}-{name}.svg"] = pill(t, label, value)
        for fn, svg in files.items():
            (OUT / fn).write_text(svg, encoding="utf-8")
            print(f"{fn:32} {len(svg) / 1024:6.1f} KB")
