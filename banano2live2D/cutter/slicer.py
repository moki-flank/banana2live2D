# -*- coding: utf-8 -*-
"""
Adaptive 3x3 (9-Part) and 4x4 (16-Part) Grid Slicer for Live2D Component Sheets.
Combines Projection Profile Valley Detection with Exterior BFS Matting
and see-through Connected Component Tightening.
Supports standard (1K/2K) and 4K UHD (4096x4096) component sheets.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from PIL import Image

from .matting import remove_background
from .cleaner import clean_and_tighten

GRID_PARTS_MAPPING_3X3 = [
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

GRID_PARTS_MAPPING_4X4 = [
    # Row 0: Hair & Head Structure
    ("back_hair", 0, 0, "00_back_hair"),
    ("head_base", 0, 1, "01_head_base"),
    ("front_hair", 0, 2, "02_front_hair"),
    ("side_hair", 0, 3, "03_side_hair"),
    # Row 1: Facial Expressions
    ("eyes_open", 1, 0, "04_eyes_open"),
    ("eyes_closed", 1, 1, "05_eyes_closed"),
    ("eyebrows", 1, 2, "06_eyebrows"),
    ("mouth", 1, 3, "07_mouth"),
    # Row 2: Upper Body, Skirt & Arms
    ("body_torso", 2, 0, "08_body_torso"),
    ("skirt_lower", 2, 1, "09_skirt_lower"),
    ("arm_left", 2, 2, "10_arm_left"),
    ("arm_right", 2, 3, "11_arm_right"),
    # Row 3: Lower Body, Ears/Headwear, Tail/Wings & Props
    ("legs_stockings", 3, 0, "12_legs_stockings"),
    ("headwear_ears", 3, 1, "13_headwear_ears"),
    ("back_tail_wings", 3, 2, "14_back_tail_wings"),
    ("hand_prop_effect", 3, 3, "15_hand_prop_effect"),
]

# Default backwards-compatible alias
GRID_PARTS_MAPPING = GRID_PARTS_MAPPING_3X3


def get_grid_parts_mapping(grid: str = "3x3") -> List[Tuple[str, int, int, str]]:
    g = str(grid or "3x3").strip().lower()
    if g in ("4x4", "4", "16", "16parts"):
        return GRID_PARTS_MAPPING_4X4
    return GRID_PARTS_MAPPING_3X3


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

    best_rel = int(np.median(candidates))
    return best_rel + a


def compute_adaptive_grid_cuts(img: Image.Image, grid_size: int = 3) -> Tuple[List[int], List[List[int]]]:
    """
    Compute adaptive vertical split lines and per-column horizontal split lines
    by finding zero-ink white valleys between rows and columns for either 3x3 or 4x4 grids.
    """
    rgb = np.array(img.convert("RGB"), dtype=np.float32)
    H, W, _ = rgb.shape

    corners = np.array([rgb[0, 0], rgb[0, W - 1], rgb[H - 1, 0], rgb[H - 1, W - 1]])
    bg_color = corners.mean(axis=0)

    diff = np.linalg.norm(rgb - bg_color, axis=2)
    is_fg = (diff > 18.0) & (rgb.mean(axis=2) < 244.0)
    fg = is_fg.astype(np.float32)

    col_proj = fg.sum(axis=0)
    row_proj = fg.sum(axis=1)

    win_x = max(13, int(W * 0.008))
    win_y = max(13, int(H * 0.008))

    if grid_size == 4:
        x_cuts = [0]
        for k in range(1, 4):
            nom = k / 4.0
            low_x = max(x_cuts[-1] + int(W * 0.14), int(W * (nom - 0.08)))
            high_x = int(W * (nom + 0.08))
            xk = _find_valley_1d(col_proj, low_x, high_x, window=win_x)
            x_cuts.append(xk)
        x_cuts.append(W)

        y_global = [0]
        for k in range(1, 4):
            nom = k / 4.0
            low_y = max(y_global[-1] + int(H * 0.14), int(H * (nom - 0.08)))
            high_y = int(H * (nom + 0.08))
            yk = _find_valley_1d(row_proj, low_y, high_y, window=win_y)
            y_global.append(yk)
        y_global.append(H)

        y_cuts_per_col: List[List[int]] = []
        for c in range(4):
            cx1, cx2 = x_cuts[c], x_cuts[c + 1]
            col_fg = fg[:, cx1:cx2].sum(axis=1)
            col_ys = [0]
            for k in range(1, 4):
                nom = k / 4.0
                yg = y_global[k]
                low_c = max(col_ys[-1] + int(H * 0.13), int(H * (nom - 0.075)), yg - int(H * 0.055))
                high_c = min(int(H * (nom + 0.075)), yg + int(H * 0.055))
                if high_c <= low_c + 4:
                    yk_c = yg
                else:
                    yk_c = _find_valley_1d(col_fg, low_c, high_c, window=win_y)
                col_ys.append(yk_c)
            col_ys.append(H)
            y_cuts_per_col.append(col_ys)

        return x_cuts, y_cuts_per_col

    # Default 3x3 adaptive valleys
    x1 = _find_valley_1d(col_proj, int(W * 0.22), int(W * 0.46), window=win_x)
    x2 = _find_valley_1d(col_proj, int(W * 0.54), int(W * 0.78), window=win_x)
    x_cuts = [0, x1, x2, W]

    y1_global = _find_valley_1d(row_proj, int(H * 0.24), int(H * 0.48), window=win_y)
    y2_low = max(y1_global + int(H * 0.08), int(H * 0.45))
    y2_global = _find_valley_1d(row_proj, y2_low, int(H * 0.76), window=win_y)

    y_cuts_per_col = []
    for c in range(3):
        cx1, cx2 = x_cuts[c], x_cuts[c + 1]
        col_fg = fg[:, cx1:cx2].sum(axis=1)
        y1_c = _find_valley_1d(
            col_fg,
            max(int(H * 0.20), y1_global - int(H * 0.06)),
            min(int(H * 0.50), y1_global + int(H * 0.06)),
            window=win_y,
        )
        y2_c = _find_valley_1d(
            col_fg,
            max(y1_c + int(H * 0.07), y2_global - int(H * 0.08)),
            min(int(H * 0.78), y2_global + int(H * 0.08)),
            window=win_y,
        )
        y_cuts_per_col.append([0, y1_c, y2_c, H])

    return x_cuts, y_cuts_per_col


def slice_3x3_grid(
    image_path: str,
    output_dir: Optional[str] = None,
    apply_matting: bool = True,
    apply_cleaning: bool = True,
    bg_tolerance: int = 28,
    tolerance: Optional[int] = None,
    grid: str = "3x3",
) -> Dict[str, Dict[str, Any]]:
    if tolerance is not None:
        bg_tolerance = tolerance
    """
    Slice 3x3 (9-part) or 4x4 (16-part) grid into semantic Live2D component parts
    using Adaptive Projection Valleys + BFS Matting + Connected Component Tightening.
    """
    img = Image.open(image_path).convert("RGBA")
    W, H = img.size

    mapping = get_grid_parts_mapping(grid)
    grid_size = 4 if len(mapping) == 16 else 3

    x_cuts, y_cuts_per_col = compute_adaptive_grid_cuts(img, grid_size=grid_size)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    results: Dict[str, Dict[str, Any]] = {}

    for name, r, c, filename in mapping:
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
            is_facial = (r == 1) or ("eye" in name) or ("mouth" in name) or ("brow" in name)
            tight_img, rel_bbox = clean_and_tighten(
                matted,
                is_facial_feature=is_facial,
                part_name=name,
            )
        else:
            tight_img = matted
            rel_bbox = (0, 0, cell_crop.width, cell_crop.height)

        save_path = None
        if output_dir:
            save_path = os.path.join(output_dir, f"{filename}.png")
            tight_img.save(save_path)
            alias_path = os.path.join(output_dir, f"{name}.png")
            tight_img.save(alias_path)

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
            "grid": "4x4" if grid_size == 4 else "3x3",
            "source_resolution": (W, H),
        }

    return results


# Semantic alias for both 3x3 and 4x4 grids
slice_component_grid = slice_3x3_grid