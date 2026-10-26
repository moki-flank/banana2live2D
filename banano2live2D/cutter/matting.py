# -*- coding: utf-8 -*-
"""
Alpha Matting & Background Removal (Exterior Boundary BFS).
Adapted from banano2gif.
Performs floodfill matting from outer borders inwards,
preserving 100% of internal character whites (teeth, sclera, white shirt, ribbons, hairclips).
"""

from collections import deque
from typing import Union
from PIL import Image, ImageFilter
import numpy as np


def remove_background(
    image: Union[str, Image.Image],
    bg_threshold: int = 240,
    color_dist: float = 25.0,
    feather_radius: float = 0.5,
) -> Image.Image:
    """
    Remove background by exterior floodfill BFS.
    Returns RGBA image with transparent background.
    """
    if isinstance(image, str):
        im = Image.open(image).convert("RGB")
    else:
        im = image.convert("RGB")

    orig_w, orig_h = im.size

    # Fast downscale computation for ultra-high resolution
    scale = 1.0
    if max(orig_w, orig_h) > 512:
        scale = 512.0 / max(orig_w, orig_h)
        small_im = im.resize((int(orig_w * scale), int(orig_h * scale)), Image.Resampling.BILINEAR)
    else:
        small_im = im

    arr = np.array(small_im, dtype=np.int32)
    h, w, _ = arr.shape

    # Sample corners as background reference
    corners = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    bg_color = np.mean(corners, axis=0)

    mask = np.zeros((h, w), dtype=bool)
    q = deque()

    # Seed BFS from all outer boundary pixels
    for x in range(w):
        for y in (0, h - 1):
            if np.linalg.norm(arr[y, x] - bg_color) < color_dist or np.all(arr[y, x] > bg_threshold):
                mask[y, x] = True
                q.append((x, y))

    for y in range(h):
        for x in (0, w - 1):
            if not mask[y, x]:
                if np.linalg.norm(arr[y, x] - bg_color) < color_dist or np.all(arr[y, x] > bg_threshold):
                    mask[y, x] = True
                    q.append((x, y))

    # 4-connected BFS
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q:
        cx, cy = q.popleft()
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and not mask[ny, nx]:
                diff = np.linalg.norm(arr[ny, nx] - bg_color)
                is_light = np.all(arr[ny, nx] > bg_threshold)
                if diff < color_dist or is_light:
                    mask[ny, nx] = True
                    q.append((nx, ny))

    # Mask: 0 = transparent background, 255 = opaque foreground
    alpha = np.where(mask, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, mode="L")

    if scale < 1.0:
        alpha_img = alpha_img.resize((orig_w, orig_h), Image.Resampling.BILINEAR)

    eff_radius = feather_radius / scale if scale < 1.0 else feather_radius
    if eff_radius > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=eff_radius))

    res = im.convert("RGBA")
    res.putalpha(alpha_img)
    return res
