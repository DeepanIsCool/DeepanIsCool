#!/usr/bin/env python3
"""Restyle lowlighter/metrics' isocalendar.svg into this page's own material.

The action draws a good isometric calendar and a wrong-looking card: GitHub
green cubes, blue headings, and a system sans face, none of which belong on a
page that is otherwise monochrome JetBrains Mono. This pass fixes that without
forking the action.

Two mechanisms, because the file needs both:

  * the cube colours are presentation attributes (fill="#40c463"), not CSS
    variables, so the light-theme ramp is substituted directly in the markup;
  * a CSS block then overrides those same fills through attribute selectors
    under prefers-color-scheme: dark — a stylesheet beats a presentation
    attribute, which is what makes one file work in both themes the way the
    graphics in scripts/generate_stats.py already do.

The 3D shading survives the swap: the side faces are the same fill run through
feComponentTransfer brightness filters (slope 0.6 and 0.2), so they follow
whatever hue the top face is given.

Idempotent: running it twice changes nothing.
"""
import base64
import functools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "'Liberation Mono',monospace")

# Same tokens as scripts/generate_stats.py, so the card reads as one material
# with the graphics stacked above it.
LIGHT = dict(data="#6e7681", emph="#424a53", dim="#8c959f")
DARK = dict(data="#8b949e", emph="#f0f6fc", dim="#8b949e")

# GitHub's five calendar levels -> a grey ramp of the same five steps.
# Index 0 is an empty day; 4 is the busiest.
GREEN = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
RAMP_LIGHT = ["#eaeef2", "#c2c9d1", "#98a1ab", "#6e7681", "#424a53"]
RAMP_DARK = ["#21262d", "#3d444d", "#656d76", "#8b949e", "#c9d1d9"]


@functools.lru_cache(maxsize=None)
def face(filename, weight):
    with open(os.path.join(FONT_DIR, filename), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def css():
    """The override block, injected into the action's own extras slot."""
    dark_cubes = "".join(
        f'[fill="{lo}"]{{fill:{dk}}}'
        for lo, dk in zip(RAMP_LIGHT, RAMP_DARK))

    return (
        face("jbmono-400.woff2", 400)
        + face("jbmono-600.woff2", 600)
        + f"svg{{font-family:{MONO};color:{LIGHT['data']}}}"
        # The action's headings are blue, icon-led and sentence case. Every
        # other label on the page is a small uppercase tag, so match that
        # rather than leaving one widget speaking its own dialect.
        + "h2,h3{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;"
        + f"font-weight:600;color:{LIGHT['dim']};margin:8px 0 4px}}"
        + "h2 svg,h3 svg{display:none}"
        + f".field{{color:{LIGHT['emph']};font-size:11px}}"
        + f".field svg{{fill:{LIGHT['dim']}}}"
        + "@media(prefers-color-scheme:dark){"
        + f"svg{{color:{DARK['data']}}}"
        + f"h2,h3{{color:{DARK['dim']}}}"
        + f".field{{color:{DARK['emph']}}}"
        + f".field svg{{fill:{DARK['dim']}}}"
        + dark_cubes
        + "}"
    )


# The action emits a 480x330 box whose ink stops at y=273.5, so a sixth of the
# card is empty and shows up as a gap under it in the README. Only the height is
# trimmed: the content is top-anchored so cropping down is safe, whereas the
# foreignObject is 100% wide and narrowing it would reflow the flex row.
BOX = (480, 330)
CROPPED_H = 282


def restyle(svg):
    if "JBMono" in svg:
        return svg

    for green, grey in zip(GREEN, RAMP_LIGHT):
        svg = svg.replace(f'fill="{green}"', f'fill="{grey}"')

    # Guarded on the exact box we measured — if upstream changes the layout,
    # skip the crop rather than silently clipping the calendar.
    w, h = BOX
    old_box = f'width="{w}" height="{h}"'
    if old_box in svg:
        svg = svg.replace(
            old_box,
            f'width="{w}" height="{CROPPED_H}" '
            f'viewBox="0 0 {w} {CROPPED_H}"', 1)

    # The empty <style/> straight after the action's own stylesheet is the
    # slot it leaves for overrides; taking it means these rules land last and
    # win on specificity ties.
    marker = "</style>\n    <style/>"
    if marker not in svg:
        raise SystemExit("isocalendar.svg: no override <style/> slot found")
    return svg.replace(marker, f"</style>\n    <style>{css()}</style>", 1)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(HERE), "isocalendar.svg")
    with open(target, encoding="utf-8") as f:
        svg = f.read()

    out = restyle(svg)
    if out == svg:
        print(f"{target}: already restyled")
        return
    with open(target, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{target}: recoloured to the page's ramp, font inlined")


if __name__ == "__main__":
    main()
