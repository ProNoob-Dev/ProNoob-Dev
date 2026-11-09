# Low-memory alternative to prep_photo.py (rembg needs a ~1GB model and was
# OOM-killed on this VM). Same pipeline, but the subject cut-out uses
# cv2.grabCut with a rectangle hint instead of rembg — no model download,
# runs in seconds on a 460px photo.
#
# Adapted from Avi Vashishta's terminal-style profile art
# (https://github.com/AVIVASHISHTA29/AVIVASHISHTA29) — reused with credit,
# reworked for ProNoob-Dev. Manual use only; NOT run by the daily workflow.
"""
Prepare the dp (a flat illustration) for clean ASCII conversion:
  1. cut out the subject (cv2.grabCut, rect hint) so it is isolated
  2. bilateral-smooth away the paper texture while keeping drawn lines sharp
  3. stretch tones so skin lands near white and hair/lines stay dark
  4. darken the line work (difference-of-gaussians ridges)
  5. composite onto white and crop square around the subject

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.

    python scripts/prep_photo_grabcut.py <input.png> [output.png] [x y w h]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")
# Rect around head + shoulders for the 460x460 avatar photo.
RECT = tuple(int(v) for v in sys.argv[3:7]) if len(sys.argv) > 6 else (40, 5, 380, 450)

LINE_WEIGHT = float(os.environ.get("LINE_WEIGHT", 0.6))  # how hard drawn lines are pushed toward black
SMOOTH_PASSES = int(os.environ.get("SMOOTH_PASSES", 3))
HI_PCT = float(os.environ.get("HI_PCT", 92))

img = cv2.imread(INP)
if img is None:
    raise SystemExit(f"could not read {INP}")

# 1. cut out the subject with grabCut
mask = np.zeros(img.shape[:2], np.uint8)
bgd = np.zeros((1, 65), np.float64)
fgd = np.zeros((1, 65), np.float64)
cv2.grabCut(img, mask, RECT, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
# clean specks / fill pinholes in the subject
alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 2. smooth texture, keep edges
smooth = gray
for _ in range(SMOOTH_PASSES):
    smooth = cv2.bilateralFilter(smooth, 9, 40, 9)

# 3. tone stretch over the subject only
lo, hi = np.percentile(smooth[alpha > 128], [2, HI_PCT])
tone = np.clip((smooth.astype(np.float32) - lo) / (hi - lo), 0, 1)

# 4. dark-on-light ridges -> darken
fine = cv2.GaussianBlur(smooth, (0, 0), 1.5).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 6).astype(np.float32)
lines = np.clip((coarse - fine) / 40.0, 0, 1)
out = np.clip(tone - LINE_WEIGHT * lines, 0, 1) * 255

# 5. paste onto white (feathered a hair to avoid a halo), square crop
mask_f = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
out = out * mask_f + 255.0 * (1.0 - mask_f)

ys, xs = np.where(alpha > 20)
side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 60
cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
canvas = np.full((side, side), 255, np.uint8)
x0, y0 = cx - side // 2, cy - side // 2
sx0, sy0 = max(x0, 0), max(y0, 0)
sx1, sy1 = min(x0 + side, out.shape[1]), min(y0 + side, out.shape[0])
canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = out[sy0:sy1, sx0:sx1].astype(np.uint8)

Image.fromarray(canvas, mode="L").save(OUT)
print("wrote", OUT, canvas.shape)
