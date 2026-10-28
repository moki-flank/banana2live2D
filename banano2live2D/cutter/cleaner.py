# -*- coding: utf-8 -*-
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps


def clean_and_tighten(
    rgba_image: Image.Image,
    min_area: int = 40,
    alpha_threshold: int = 15,
    pad: int = 2,
    is_facial_feature: bool = False,
    part_name: Optional[str] = None,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    arr = np.array(rgba_image)
    if arr.shape[2] < 4:
        return rgba_image, (0, 0, rgba_image.width, rgba_image.height)

    alpha = arr[:, :, 3]
    h, w = alpha.shape
    cell_area = max(1, h * w)

    scaled_min_area = max(min_area, int(cell_area * 0.00025))
    scaled_pad = max(pad, int(min(h, w) * 0.006))

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        (alpha > alpha_threshold).astype(np.uint8)
    )

    if num_labels <= 1:
        return rgba_image, (0, 0, w, h)

    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = areas.max() if len(areas) > 0 else 0

    mask = np.zeros_like(alpha)
    border_margin = max(2, int(min(h, w) * 0.006))

    valid_lbls = []
    for lbl in range(1, num_labels):
        area = stats[lbl, cv2.CC_STAT_AREA]
        left = stats[lbl, cv2.CC_STAT_LEFT]
        top = stats[lbl, cv2.CC_STAT_TOP]
        width = stats[lbl, cv2.CC_STAT_WIDTH]
        height = stats[lbl, cv2.CC_STAT_HEIGHT]

        touches_tb = (top <= border_margin or top + height >= h - border_margin)
        touches_lr = (left <= border_margin or left + width >= w - border_margin)
        touches_border = touches_tb or touches_lr

        if part_name in ("head_base", "body_torso", "mouth"):
            if area == max_area:
                valid_lbls.append(lbl)
        elif is_facial_feature:
            if not touches_border and area >= scaled_min_area and area >= 0.05 * max_area:
                valid_lbls.append(lbl)
        else:
            if area == max_area:
                valid_lbls.append(lbl)
            elif not touches_border and area >= 0.05 * max_area:
                valid_lbls.append(lbl)
            elif touches_border and area >= 0.35 * max_area and width >= w * 0.14 and height >= h * 0.14:
                valid_lbls.append(lbl)

    # If eyebrows cell [1,2] has both eyebrows (top) and blush ovals (bottom), keep only the top eyebrows
    if part_name == "eyebrows" and len(valid_lbls) >= 3:
        cys = [centroids[lbl][1] for lbl in valid_lbls]
        min_cy, max_cy = min(cys), max(cys)
        if (max_cy - min_cy) > h * 0.12:
            mid_split = (min_cy + max_cy) * 0.5
            upper_lbls = [lbl for lbl in valid_lbls if centroids[lbl][1] <= mid_split]
            if len(upper_lbls) >= 1:
                valid_lbls = upper_lbls

    for lbl in valid_lbls:
        mask[labels == lbl] = 255

    if mask.max() == 0 and max_area > 0:
        largest_lbl = 1 + int(np.argmax(areas))
        mask[labels == largest_lbl] = 255

    arr[:, :, 3] = np.minimum(arr[:, :, 3], mask)
    cleaned = Image.fromarray(arr)

    bbox = cleaned.getbbox()
    if not bbox:
        return cleaned, (0, 0, w, h)

    b_x1 = max(0, bbox[0] - scaled_pad)
    b_y1 = max(0, bbox[1] - scaled_pad)
    b_x2 = min(w, bbox[2] + scaled_pad)
    b_y2 = min(h, bbox[3] + scaled_pad)
    tight = cleaned.crop((b_x1, b_y1, b_x2, b_y2))

    if part_name:
        tight = normalize_joint_seam(tight, part_name)

    return tight, (b_x1, b_y1, b_x2, b_y2)


def _is_skin_tone(r: np.ndarray, g: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    ri = r.astype(np.int32)
    gi = g.astype(np.int32)
    bi = b.astype(np.int32)
    return (a > 15) & (ri > 175) & (gi > 120) & ((ri - bi) > 14) & (ri >= gi)


def _clean_sleeve_cross_section(arm_img: Image.Image) -> Image.Image:
    arr = np.array(arm_img)
    ah, aw, _ = arr.shape
    # Check if top of arm has a bare-skin shoulder stump above the sleeve cuff
    top_h = int(ah * 0.32)
    sub = arr[:top_h, :, :]
    skin_mask = _is_skin_tone(sub[:, :, 0], sub[:, :, 1], sub[:, :, 2], sub[:, :, 3])
    if skin_mask.sum() > (top_h * aw * 0.03):
        # Softly fade out the bare upper-arm stump in top 22% so it tucks cleanly under the shoulder/hair
        fade_h = int(ah * 0.20)
        for y in range(fade_h):
            factor = (y / float(max(1, fade_h))) ** 1.6
            row_skin = skin_mask[y, :]
            # Also include dark outline pixels adjacent to skin in top 15%
            if y < int(ah * 0.14):
                arr[y, :, 3] = (arr[y, :, 3].astype(np.float32) * factor).astype(np.uint8)
            else:
                arr[y, row_skin, 3] = (arr[y, row_skin, 3].astype(np.float32) * factor).astype(np.uint8)
    return Image.fromarray(arr)


def normalize_joint_seam(img: Image.Image, part_name: str) -> Image.Image:
    if part_name == "head_base":
        arr = np.array(img)
        hh, hw, _ = arr.shape
        alpha = arr[:, :, 3]
        row_widths = np.zeros(hh, dtype=np.int32)
        for y in range(hh):
            xs = np.where(alpha[y, :] > 25)[0]
            if len(xs) >= 2:
                row_widths[y] = xs[-1] - xs[0]
        max_w = max(1, int(row_widths.max()))

        # Keep full V-shaped chin AND upper neck! Only trim if neck extends excessively far below chin (> 88% height)
        neck_cut_y = int(hh * 0.92)
        arr = arr[:neck_cut_y, :, :]
        hh = arr.shape[0]

        # Taper upper 20% bald skull dome inward so it stays 100% hidden under front_hair bangs
        dome_h = int(hh * 0.20)
        for y in range(dome_h):
            t = y / max(1.0, float(dome_h))
            shrink = 0.48 + 0.52 * (t ** 0.65)
            cx = hw * 0.5
            half_allow = (max_w * 0.5) * shrink
            for x in range(hw):
                if abs(x - cx) > half_allow:
                    arr[y, x, 3] = 0

        out = Image.fromarray(arr)
        bbox = out.getbbox()
        return out.crop(bbox) if bbox else out

    elif part_name == "body_torso":
        arr = np.array(img)
        th, tw, _ = arr.shape

        # 1. Remove duplicate bare-skin neck above the collar in top 9% of body_torso
        # so head_base\x27s natural V-shaped chin & neck never get covered by a duplicate neck!
        top_neck_h = int(th * 0.095)
        sub_top = arr[:top_neck_h, :, :]
        top_skin = _is_skin_tone(sub_top[:, :, 0], sub_top[:, :, 1], sub_top[:, :, 2], sub_top[:, :, 3]).astype(np.uint8)
        if top_skin.sum() > 20:
            k_neck = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            neck_full = cv2.dilate(top_skin, k_neck) > 0
            sub_top[neck_full, 3] = 0
            arr[:top_neck_h, :, :] = sub_top

        # 2. Remove bare-skin shoulder stumps + their dark outlines on left (< 25% w) and right (> 75% w) in upper 38%
        y_end = int(th * 0.38)
        sub = arr[:y_end, :, :]
        skin_m = _is_skin_tone(sub[:, :, 0], sub[:, :, 1], sub[:, :, 2], sub[:, :, 3])
        side_zone = np.zeros((y_end, tw), dtype=np.uint8)
        side_zone[:, :int(tw * 0.25)] = 1
        side_zone[:, int(tw * 0.75):] = 1
        stump_skin = (skin_m & (side_zone > 0)).astype(np.uint8)
        if stump_skin.sum() > 50:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
            stump_full = (cv2.dilate(stump_skin, kernel) > 0) & (side_zone > 0)
            sub[stump_full, 3] = 0
            arr[:y_end, :, :] = sub

        # 3. If torso is very tall (h/w > 1.55, e.g. long qipao), trim bottom 16% that is hidden under skirt_lower
        if th / max(1.0, float(tw)) > 1.42:
            arr[int(th * 0.72):, :, 3] = 0

        num_l, lbls, stats, _ = cv2.connectedComponentsWithStats((arr[:, :, 3] > 15).astype(np.uint8))
        if num_l > 2:
            main_lbl = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            arr[lbls != main_lbl, 3] = 0

        out = Image.fromarray(arr)
        bbox = out.getbbox()
        return out.crop(bbox) if bbox else out

    elif part_name == "arm_left":
        cleaned = _clean_sleeve_cross_section(img)
        arr = np.array(cleaned)
        ah, aw, _ = arr.shape
        alpha = arr[:, :, 3]
        top_xs = np.where(alpha[:max(1, int(ah * 0.15)), :] > 40)[1]
        bot_xs = np.where(alpha[int(ah * 0.80):, :] > 40)[1]
        if len(top_xs) > 0 and len(bot_xs) > 0:
            if top_xs.mean() < aw * 0.45 and bot_xs.mean() > aw * 0.52:
                cleaned = ImageOps.mirror(cleaned)
        return cleaned

    elif part_name == "arm_right":
        cleaned = _clean_sleeve_cross_section(img)
        return cleaned

    return img
