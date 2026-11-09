# Edge-outline prep for photos: renders the portrait as line art (Canny edges
# only, dark on white) instead of a luminance map. A photo's mid-tones turn
# into a solid block under the luminance ramp; edges give the thin-outline
# look of the reference portrait (flat illustration style).
#
# Uses cv2.grabCut (same rect as prep_photo_grabcut.py) to keep background
# edges (bokeh lights) out. Lightweight — no model download.
#
#     python scripts/prep_photo_edges.py [input.png] [output.png]
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-edges.png")
RECT = (40, 5, 380, 450)  # head + shoulders for the 460x460 avatar photo

img = cv2.imread(INP)
if img is None:
    raise SystemExit(f"could not read {INP}")

mask = np.zeros(img.shape[:2], np.uint8)
bgd = np.zeros((1, 65), np.float64)
fgd = np.zeros((1, 65), np.float64)
cv2.grabCut(img, mask, RECT, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
smooth = gray
for _ in range(3):
    smooth = cv2.bilateralFilter(smooth, 9, 40, 9)

edges = cv2.Canny(smooth, 50, 150)
# keep edges only inside the subject, thicken a hair so they survive the
# downsample to 180 ascii columns
edges = cv2.bitwise_and(edges, edges, mask=alpha)
edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
out = 255 - edges  # dark lines on white, like the line-art source

Image.fromarray(out, mode="L").save(OUT)
print("wrote", OUT, out.shape)
