"""Generate the themed SVG assets for the steggas/steggas profile README.

Every SVG embeds a woff2 subset of the fonts it uses, because GitHub renders
README images as <img>, which cannot load external fonts. Palette follows
callumstegmann.com: navy, cream, copper.

Usage: python build_readme_assets.py <font_dir> <out_dir>
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

THEMES = {
    "dark": dict(bg="#0a1424", panel="#0e1828", ink="#f0ebdd", soft="#c5c0b1",
                 mute="#7d8090", line="rgba(240,235,221,0.16)", accent="#d68f50"),
    "light": dict(bg="#f5efe0", panel="#f5efe0", ink="#0e1a2b", soft="#2a3a55",
                  mute="#6c7790", line="rgba(14,26,43,0.16)", accent="#9a5e20"),
}

_tt = {k: TTFont(FONT_DIR / v) for k, v in FONTS.items()}


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

    def raw(self, s, font_chars=None):
        for font, chars in (font_chars or {}).items():
            self.chars[font].update(chars)
        self.body.append(s)

    def render(self):
        faces = "".join(font_face(f, "".join(sorted(c))) for f, c in self.chars.items() if c)
        motion = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        if STATIC:
            motion = "*{animation:none!important}"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" role="img" aria-label="{esc(self.title)}">'
                f"<title>{esc(self.title)}</title>"
                f"<style>{faces}{''.join(self.css)}{motion}</style>"
                + "".join(self.body) + "</svg>")


# Shared load-in animation: fade up, staggered by class.
FADE = (
    "@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    ".f{animation:up .9s cubic-bezier(.2,.7,.2,1) backwards}"
    + "".join(f".d{i}{{animation-delay:{i * 0.12:.2f}s}}" for i in range(12))
)


def banner(t):
    W, H = 1200, 420
    s = Svg(W, H, "Callum Stegmann. Senior GRC Consultant at Scytale, Cape Town.")
    s.css.append(FADE)
    frameworks = ["ISO 27001", "ISO 42001", "SOC 2", "DORA", "EU AI ACT", "GDPR", "POPIA"]
    n, step = len(frameworks), 2.2
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
        ".tick{--len:64px;stroke-dasharray:64;animation:draw .8s 1.4s cubic-bezier(.2,.7,.2,1) backwards}"
        ".rule{--len:240px;stroke-dasharray:240;animation:draw 1.2s .9s cubic-bezier(.2,.7,.2,1) backwards}"
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

    # Top bar.
    s.text(60, 58, "CALLUM STEGMANN", "monob", 13, t["ink"], "f d0", tracking=3)
    loc = "CAPE TOWN · SOUTH AFRICA"
    lx = W / 2 - width(loc, "mono", 12, 2) / 2
    s.raw(f'<circle class="pulse" cx="{lx - 14:.1f}" cy="54" r="3.5" fill="{t["accent"]}"/>')
    s.text(lx, 58, loc, "mono", 12, t["mute"], "f d1", tracking=2)
    s.text(W - 60, 58, "GOVERNANCE · RISK · COMPLIANCE", "mono", 12, t["mute"], "f d2",
           tracking=2, anchor="end")
    s.raw(f'<line x1="60" y1="84" x2="{W - 60}" y2="84" stroke="{t["line"]}"/>')

    # Left gutter: section numeral, as on the site.
    s.text(60, 205, "00", "serif", 96, t["accent"], "f d2")
    s.text(62, 240, "INTRO", "monob", 12, t["ink"], "f d3", tracking=3)
    s.text(62, 262, "CAPE TOWN", "mono", 12, t["mute"], "f d3", tracking=3)

    # Main column.
    x0 = 250
    s.text(x0, 140, "SENIOR GRC CONSULTANT · SCYTALE", "monob", 13, t["accent"], "f d3", tracking=3)
    s.chars["sans"].update("Callum Stegmann.")
    s.raw(f'<text class="f d4" x="{x0}" y="226" font-family="cs-sans" font-size="80" '
          f'letter-spacing="-2.4" fill="{t["ink"]}">Callum Stegmann<tspan fill="{t["accent"]}">.</tspan></text>')
    s.raw(f'<line class="rule" x1="{x0 + 2}" y1="250" x2="{x0 + 242}" y2="250" '
          f'stroke="{t["accent"]}" stroke-width="2"/>')
    s.text(x0, 296, "Building management systems that protect", "serif", 31, t["soft"], "f d5")
    s.text(x0, 332, "the people on the receiving end.", "serif", 31, t["soft"], "f d6")

    # Bottom row: rotating frameworks ticker and coordinates.
    s.raw(f'<line x1="60" y1="362" x2="{W - 60}" y2="362" stroke="{t["line"]}"/>')
    label = "NOW DELIVERING"
    s.text(x0, 392, label, "mono", 12, t["mute"], "f d7", tracking=2)
    tx = x0 + width(label, "mono", 12, 2) + 34
    s.raw(f'<line class="f d7" x1="{tx - 22:.1f}" y1="388" x2="{tx - 10:.1f}" y2="388" stroke="{t["accent"]}"/>')
    for i, fw in enumerate(frameworks):
        s.text(tx, 392, fw, "monob", 13, t["accent"], "cy cy0" if i == 0 else "cy", tracking=2,
               extra=f'style="animation-delay:{i * step:.1f}s"')
    s.text(W - 60, 392, "33.9249° S · 18.4241° E", "mono", 12, t["mute"], "f d8",
           tracking=2, anchor="end")

    # Auditor's seal: rotating ring text around a tick that draws itself in.
    ring = "GOVERNANCE · RISK · COMPLIANCE · "
    circ = 2 * math.pi * 56
    track = (circ - width(ring, "mono", 10)) / len(ring)
    s.chars["mono"].update(ring)
    s.raw(
        f'<g class="f d6">'
        f'<circle cx="1066" cy="206" r="72" fill="none" stroke="{t["accent"]}" stroke-opacity=".55"/>'
        f'<circle cx="1066" cy="206" r="40" fill="none" stroke="{t["accent"]}" stroke-opacity=".55"/>'
        f'<g class="spin"><text font-family="cs-mono" font-size="10" fill="{t["accent"]}" '
        f'letter-spacing="{track:.2f}" dy="3.5"><textPath href="#ring">{esc(ring)}</textPath></text></g>'
        f'<path class="tick" d="M1050,207 l11,11 l22,-25" fill="none" stroke="{t["accent"]}" '
        f'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    return s.render()


def section(t, num, label, aside, title):
    W, H = 1200, 96
    s = Svg(W, H, title)
    s.css.append(FADE)
    s.text(0, 66, num, "serif", 58, t["accent"], "f d0")
    s.text(width(num, "serif", 58) + 26, 60, label, "monob", 14, t["ink"], "f d1", tracking=3)
    s.text(W, 60, aside, "mono", 13, t["mute"], "f d2", tracking=3, anchor="end")
    s.raw(f'<line x1="0" y1="92" x2="{W}" y2="92" stroke="{t["line"]}"/>')
    return s.render()


def certs(t):
    W, H, gap = 1200, 180, 24
    cw = (W - 2 * gap) / 3
    items = [
        ("01", "ISO/IEC 42001", "Lead Auditor", "MASTERMIND · 2025"),
        ("02", "ISO/IEC 27001", "Lead Auditor", "MASTERMIND · 2025"),
        ("03", "ISO/IEC 27001", "Implementer", "PECB · 2024"),
    ]
    s = Svg(W, H, "Certifications: ISO/IEC 42001 Lead Auditor, ISO/IEC 27001 Lead Auditor, "
                  "ISO/IEC 27001 Implementer.")
    s.css.append(FADE)
    for i, (n, std, role, issuer) in enumerate(items):
        x = i * (cw + gap)
        d = f"d{i * 2}"
        s.raw(f'<g class="f {d}"><rect x="{x + .5:.1f}" y=".5" width="{cw - 1:.1f}" height="{H - 1}" '
              f'rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/></g>')
        s.text(x + 28, 58, n, "serif", 40, t["accent"], f"f {d}")
        s.text(x + cw - 28, 50, issuer, "mono", 11, t["mute"], f"f {d}", tracking=2, anchor="end")
        s.text(x + 28, 116, std, "sans", 30, t["ink"], f"f {d}", tracking=-0.6)
        s.text(x + 28, 150, role, "serif", 26, t["soft"], f"f {d}")
    return s.render()


def stack(t):
    tags = ["PYTHON", "POWERSHELL", "TYPESCRIPT", "CLAUDE CODE", "OBSIDIAN",
            "POWER PLATFORM", "GITHUB ACTIONS", "GIT"]
    W, H, size, track, padx, gap, h = 1200, 112, 12, 1.6, 16, 9, 42
    s = Svg(W, H, "Stack: " + ", ".join(t_.title() for t_ in tags) + ".")
    s.css.append(FADE)
    x, y = 0.5, 0.5
    for i, tag in enumerate(tags):
        w = width(tag, "monob", size, track) - track + padx * 2 + 14
        if x + w > W:
            x, y = 0.5, y + h + gap
        cls = f"f d{i}"
        s.raw(f'<g class="{cls}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" '
              f'fill="{t["panel"]}" stroke="{t["line"]}"/>'
              f'<circle cx="{x + padx:.1f}" cy="{y + h / 2:.1f}" r="3.5" fill="{t["accent"]}"/></g>')
        s.text(x + padx + 14, y + h / 2 + 4.6, tag, "monob", size, t["ink"], cls, tracking=track)
        x += w + gap
    s.h = int(y + h + 1)
    return s.render()


def footer(t):
    W, H = 1200, 120
    s = Svg(W, H, "Compliance done properly is protective work.")
    s.css.append(FADE)
    s.raw(f'<line x1="0" y1="1" x2="{W}" y2="1" stroke="{t["line"]}"/>')
    s.text(W / 2, 66, "Compliance done properly is protective work.", "serif", 30, t["soft"],
           "f d0", anchor="middle")
    s.text(W / 2, 100, "CAPE TOWN · 33.9249° S · 18.4241° E", "mono", 11, t["mute"], "f d2",
           tracking=3, anchor="middle")
    return s.render()


SECTIONS = [
    ("work", "01", "WORK", "WHAT I ACTUALLY DO", "01. Work: what I actually do."),
    ("credentials", "02", "CREDENTIALS", "WHAT I'VE EARNED", "02. Credentials: what I've earned."),
    ("stack", "03", "STACK", "WHAT I BUILD WITH", "03. Stack: what I build with."),
    ("beyond", "04", "BEYOND", "OFF THE CLOCK", "04. Beyond the day job."),
    ("contact", "05", "CONTACT", "FIND ME", "05. Contact: find me."),
]

for name, t in THEMES.items():
    files = {
        f"banner-{name}.svg": banner(t),
        f"certs-{name}.svg": certs(t),
        f"stack-{name}.svg": stack(t),
        f"footer-{name}.svg": footer(t),
    }
    for slug, num, label, aside, title in SECTIONS:
        files[f"section-{slug}-{name}.svg"] = section(t, num, label, aside, title)
    for fn, svg in files.items():
        (OUT / fn).write_text(svg, encoding="utf-8")
        print(f"{fn:32} {len(svg) / 1024:6.1f} KB")
