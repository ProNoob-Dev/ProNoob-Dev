#!/usr/bin/env python3
"""Prepare Jaikishan's PN avatar for ASCII conversion.

The avatar is a chrome monogram logo, not a photo: a filled-luminance ASCII
render turns the letters into one solid blob, so this script renders the
LETTER OUTLINES instead (blur -> edge detect -> invert), which reads as "PN"
at ASCII resolution. It also paints the image's white rounded corners the
dark navy background colour, or they invert to "@@@@" blocks.

    python scripts/prep_avatar.py [input.webp] [output.png]
"""
# Adapted from Avi Vashishta's terminal-style profile art (https://github.com/AVIVASHISHTA29/AVIVASHISHTA29) — reused with credit, reworked for ProNoob-Dev.
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-avatar.webp")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

im = Image.open(INP).convert("RGB")
# square centre-crop
s = min(im.size)
im = im.crop(((im.width - s) // 2, (im.height - s) // 2,
              (im.width + s) // 2, (im.height + s) // 2))

# 1. the avatar is a rounded-rectangle logo: the white corners would invert
#    to "@@@@" blocks, and painting them over leaves a seam that edge
#    detection draws as an arc. Simplest robust fix: crop the corners off
#    entirely — the monogram sits well inside, so nothing is lost.
#    measure the corner radius from the top edge (first non-white pixel).
gray0 = im.convert("L")
px0 = gray0.load()
R = None
for x in range(im.width // 2):
    if px0[x, 10] < 200:
        R = x
        break
R = R or int(im.width * 0.08)
inset = R + 20
im = im.crop((inset, inset, im.width - inset, im.height - inset))

# 2. outline render: soften internal chrome reflections, find the letter
#    boundaries, then invert so edges are dark on a white field.
gray = im.convert("L")
soft = gray.filter(ImageFilter.GaussianBlur(3))
edges = soft.filter(ImageFilter.FIND_EDGES)
# FIND_EDGES draws a frame along the image border; erase a 3px ring so the
# frame does not become ASCII border lines.
ed = ImageDraw.Draw(edges)
ed.rectangle((0, 0, edges.width - 1, 2), fill=0)
ed.rectangle((0, edges.height - 3, edges.width - 1, edges.height - 1), fill=0)
ed.rectangle((0, 0, 2, edges.height - 1), fill=0)
ed.rectangle((edges.width - 3, 0, edges.width - 1, edges.height - 1), fill=0)
out = ImageOps.invert(edges)
out = ImageOps.autocontrast(out, cutoff=1)
# kill the background's fine-grain noise: weak edges go to white, only the
# strong letter boundaries survive.
out = out.point(lambda v: 255 if v > 180 else v)
out = ImageEnhance.Contrast(out).enhance(1.4)
out.save(OUT)
print("wrote", OUT, out.size, "corner radius:", R)
