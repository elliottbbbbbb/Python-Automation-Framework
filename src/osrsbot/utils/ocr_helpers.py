"""
OCR Helper Utilities - Shape detection and image preprocessing for OCR.

Provides specialized image analysis functions to distinguish problematic digits
that Tesseract commonly confuses (especially 9 vs 4).

Key Functions:
- preprocess_for_shape_detection: Prepare images for shape analysis
- count_holes_and_tail: Analyze digit topology (holes, tails, aspect ratio)
- looks_like_nine: Heuristic to distinguish 9 from 4
- flood_label_components: Connected component labeling for hole detection

These functions use morphological operations and connected component analysis
to supplement OCR when character recognition alone is insufficient.
"""
from typing import Tuple

import numpy as np
<<<<<<< HEAD
import cv2 as cv
=======
from collections import deque as _deque
>>>>>>> origin/main
from PIL import ImageOps, ImageFilter, Image


def preprocess_for_shape_detection(
    pil_img: Image.Image,
    size: Tuple[int, int] = (140, 140)
) -> np.ndarray:
    """Return a small binary numpy array (foreground=1) tuned for
    shape heuristics."""
    img = pil_img.convert("L")
    img = ImageOps.invert(img)
    img = img.resize(size, Image.BILINEAR)
    img = img.filter(ImageFilter.MedianFilter(3))  # denoise
    arr = np.array(img).astype(np.uint8)
    th = arr.mean() * 0.5
    bw = (arr > th).astype(np.uint8)

<<<<<<< HEAD
    # Morphological closing to fill tiny gaps (OpenCV optimized - 10-100x faster)
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (3, 3))
    closed = cv.morphologyEx(bw, cv.MORPH_CLOSE, kernel)
    return closed.astype(np.uint8)


def flood_label_components(inv: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    Connected component labeling using OpenCV (50-200x faster than manual BFS).

    Args:
        inv: Binary image (background=1, foreground=0)

    Returns:
        Tuple of (labeled array, number of components)
    """
    num_labels, labels = cv.connectedComponents(inv.astype(np.uint8))
    return labels, num_labels
=======
    # small closing (dilate then erode) to fill tiny gaps
    padded = np.pad(bw, ((1, 1), (1, 1)), mode='constant', constant_values=0)
    dil = np.zeros_like(bw)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dil |= padded[1 + dy:1 + dy + bw.shape[0],
                          1 + dx:1 + dx + bw.shape[1]]
    padded2 = np.pad(dil, ((1, 1), (1, 1)), mode='constant', constant_values=0)
    ero = np.ones_like(dil)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ero &= padded2[1 + dy:1 + dy + dil.shape[0],
                           1 + dx:1 + dx + dil.shape[1]]
    return ero.astype(np.uint8)


def flood_label_components(inv: np.ndarray) -> Tuple[np.ndarray, int]:
    """Simple BFS label (inv is binary background=1 inside bbox) ->
    returns labeled array and count."""
    H, W = inv.shape
    lbl = np.zeros_like(inv, dtype=np.int32)
    label = 0
    for iy in range(H):
        for ix in range(W):
            if inv[iy, ix] and lbl[iy, ix] == 0:
                label += 1
                dq = _deque()
                dq.append((iy, ix))
                lbl[iy, ix] = label
                while dq:
                    cy, cx = dq.popleft()
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx),
                                   (cy, cx - 1), (cy, cx + 1)):
                        if (0 <= ny < H and 0 <= nx < W and
                                inv[ny, nx] and lbl[ny, nx] == 0):
                            lbl[ny, nx] = label
                            dq.append((ny, nx))
    return lbl, label
>>>>>>> origin/main


def count_holes_and_tail(binary: np.ndarray) -> Tuple[int, float, float]:
    """
    binary: numpy foreground=1 background=0
    Returns (hole_count, tail_frac, aspect)
    """
    ys, xs = np.where(binary)
    if len(ys) == 0:
        return 0, 0.0, 1.0
    miny, maxy = ys.min(), ys.max()
    minx, maxx = xs.min(), xs.max()
    bbox = binary[miny:maxy + 1, minx:maxx + 1]
    h, w = bbox.shape

    inv = 1 - bbox  # background inside bounding box
    lbl, n = flood_label_components(inv)

    hole_count = 0
    for lab in range(1, n + 1):
        comp = (lbl == lab)
        touches_border = comp[0, :].any(
        ) or comp[-1, :].any() or comp[:, 0].any() or comp[:, -1].any()
        if not touches_border:
            hole_count += 1

    ys_b, _ = np.where(bbox == 1)
    if len(ys_b) == 0:
        tail_frac = 0.0
    else:
        centroid_y = ys_b.mean()
        below = np.sum(bbox[int(min(h - 1, centroid_y + 2)):, :])
        total = bbox.sum() if bbox.sum() else 1
        tail_frac = float(below) / float(total)

    aspect = float(h) / (w + 1e-9)
    return hole_count, tail_frac, aspect


def looks_like_nine(pil_img: Image.Image) -> bool:
    """Return True if the glyph looks like a '9' (closed loop + tail).
    Stricter thresholds to avoid false positives converting 4->9.
    """
    try:
        bw = preprocess_for_shape_detection(pil_img, size=(140, 140))
        hole_count, tail_frac, aspect = count_holes_and_tail(bw)

        # Stricter thresholds:
        # - require at least 1 hole
        # - require tail fraction bigger (0.20)
        # - require aspect ratio (taller than wide) > 1.0
        if hole_count >= 1 and tail_frac > 0.20 and aspect > 1.0:
            return True
        # fallback permissive check but require larger hole_count
        if hole_count >= 2 and tail_frac > 0.12 and aspect > 0.9:
            return True
    except Exception as e:
        # shape detection should never crash your script
        print("shape-detect error:", e)
    return False
