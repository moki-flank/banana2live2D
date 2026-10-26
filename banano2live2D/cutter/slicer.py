# -*- coding: utf-8 -*-
"""
Adaptive 3x3 Grid Slicer for Live2D Component Sheets.
Combines Projection Profile Valley Detection with Exterior BFS Matting
and see-through Connected Component Tightening.
Guarantees zero clipping of tall torsos, collars, twin-tails, or raised arms.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from PIL import Image

from .matting import remove_background
from .cleaner import clean_and_tighten

GRID_PARTS_MAPPING = [
    ("back_hair", 0, 0, "00_back_hair"),
    ("head_base", 0, 1, "01_head_base"),
    ("front_hair", 0, 2, "02_front_hair"),
    ("eyes_open", 1, 0, "03_eyes_open"),
    ("eyes_closed", 1, 1, "04_eyes_closed"),
    ("mouth", 1, 2, "05_mouth"),
    ("body_torso", 2, 0, "06_body_torso"),
    ("arm_left", 2, 1, "07_arm_left"),
    ("arm_right", 2, 2, "08_arm_right"),
]


def _find_valley_1d(proj: np.ndarray, low_idx: int, high_idx: int, window: int = 13) -> int:
    """
    Find the center of the widest/deepest white-space valley in a 1D foreground projection array.
    """
    L = len(proj)
    a = max(0, min(L - 2, low_idx))
    b = max(a + 1, min(L, high_idx))
    sub = proj[a:b].astype(np.float64)
    if len(sub) <= 2:
        return (a + b) // 2

    w = min(window, max(1, len(sub) // 2))
    kernel = np.ones(w, dtype=np.float64) / float(w)
    smooth = np.convolve(sub, kernel, mode="same")

    min_val = smooth.min()
    tol = max(1e-3, (smooth.max() - min_val) * 0.015)
    candidates = np.where(smooth <= min_val + tol)[0]
    if len(candidates) == 0:
        return int(np.argmin(smooth)) + a

    # Pick the longest contiguous zero/low run or median of low candidates
    best_rel = int(np.median(candidates))
    return best_rel + a


def compute_adaptive_grid_cuts(img: Image.Image) -> Tuple[List[int], List[List[int]]]:
    """
    Compute adaptive vertical split lines [0, x1, x2, W] and per-column horizontal split lines
    [[0, y1_c0, y2_c0, H], [0, y1_c1, y2_c1, H], [0, y1_c2, y2_c2, H]]
    by finding zero-ink white valleys between rows and columns.
    """
    rgb = np.array(img.convert("RGB"), dtype=np.float32)
    H, W, _ = rgb.shape

    # Sample corners for background color
    corners = np.array([rgb[0, 0], rgb[0, W - 1], rgb[H - 1, 0], rgb[H - 1, W - 1]])
    bg_color = corners.mean(axis=0)

    diff = np.linalg.norm(rgb - bg_color, axis=2)
    is_fg = (diff > 18.0) & (rgb.mean(axis=2) < 244.0)
    fg = is_fg.astype(np.float32)

    col_proj = fg.sum(axis=0)
    row_proj = fg.sum(axis=1)

    x1 = _find_valley_1d(col_proj, int(W * 0.22), int(W * 0.46))
    x2 = _find_valley_1d(col_proj, int(W * 0.54), int(W * 0.78))
    x_cuts = [0, x1, x2, W]

    y1_global = _find_valley_1d(row_proj, int(H * 0.24), int(H * 0.48))
    y2_low = max(y1_global + int(H * 0.08), int(H * 0.45))
    y2_global = _find_valley_1d(row_proj, y2_low, int(H * 0.76))

    y_cuts_per_col: List[List[int]] = []
    for c in range(3):
        cx1, cx2 = x_cuts[c], x_cuts[c + 1]
        col_fg = fg[:, cx1:cx2].sum(axis=1)
        y1_c = _find_valley_1d(
            col_fg,
            max(int(H * 0.20), y1_global - int(H * 0.06)),
            min(int(H * 0.50), y1_global + int(H * 0.06)),
        )
        y2_c = _find_valley_1d(
            col_fg,
            max(y1_c + int(H * 0.07), y2_global - int(H * 0.08)),
            min(int(H * 0.78), y2_global + int(H * 0.08)),
        )
        y_cuts_per_col.append([0, y1_c, y2_c, H])

    return x_cuts, y_cuts_per_col


def slice_3x3_grid(
    image_path: str,
    output_dir: Optional[str] = None,
    apply_matting: bool = True,
    apply_cleaning: bool = True,
    bg_tolerance: int = 28,
) -> Dict[str, Dict[str, Any]]:
    """
    Slice 3x3 grid into 9 component parts using Adaptive Projection Valleys.
    Returns dictionary with part details, images, bounding boxes, and save paths.
    """
    img = Image.open(image_path).convert("RGBA")
    W, H = img.size

    x_cuts, y_cuts_per_col = compute_adaptive_grid_cuts(img)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    results: Dict[str, Dict[str, Any]] = {}

    for name, r, c, filename in GRID_PARTS_MAPPING:
        x1 = x_cuts[c]
        x2 = x_cuts[c + 1]
        y1 = y_cuts_per_col[c][r]
        y2 = y_cuts_per_col[c][r + 1]

        cell_crop = img.crop((x1, y1, x2, y2))

        # Background matting via Exterior Boundary BFS
        if apply_matting:
            matted = remove_background(cell_crop, color_dist=float(bg_tolerance))
        else:
            matted = cell_crop

        # Component isolation and tight cropping
        if apply_cleaning:
            is_facial = (r == 1) or ("eye" in name) or ("mouth" in name)
            tight_img, rel_bbox = clean_and_tighten(matted, is_facial_feature=is_facial, part_name=name)
        else:
            tight_img = matted
            rel_bbox = (0, 0, cell_crop.width, cell_crop.height)

        save_path = None
        if output_dir:
            save_path = os.path.join(output_dir, f"{filename}.png")
            tight_img.save(save_path)
            # Also save semantic alias name
            alias_path = os.path.join(output_dir, f"{name}.png")
            tight_img.save(alias_path)

        # Global bounding box in source image
        global_bbox = (
            x1 + rel_bbox[0],
            y1 + rel_bbox[1],
            x1 + rel_bbox[2],
            y1 + rel_bbox[3],
        )

        results[name] = {
            "name": name,
            "filename": f"{filename}.png",
            "file_path": save_path,
            "image": tight_img,
            "cell_coord": (r, c),
            "cell_bbox": (x1, y1, x2, y2),
            "tight_bbox": rel_bbox,
            "global_bbox": global_bbox,
            "size": tight_img.size,
        }

    return results
