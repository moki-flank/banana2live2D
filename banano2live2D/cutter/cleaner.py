# -*- coding: utf-8 -*-
"""
Connected Component Filtering, Bounding Box Tightener & Azur Lane Joint Normalizer.
Adapted from see-through-main (cv2.connectedComponentsWithStats & scrap_model.py)
and Azur Lane (banerwei_3) Live2D component preparation rules.
"""

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
    """
    1. Filter out edge noise, isolated specks, and inter-cell bleeds using connected components analysis.
    2. Normalize Azur Lane shoulder/sleeve joints for body_torso, arm_left, and arm_right.
    3. Crop tightly to the true bounding box with optional padding.
    Returns: (tight_rgba_image, (x1, y1, x2, y2))
    """
    arr = np.array(rgba_image)
    if arr.shape[2] < 4:
        return rgba_image, (0, 0, rgba_image.width, rgba_image.height)

    alpha = arr[:, :, 3]
    h, w = alpha.shape

    # Connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        (alpha > alpha_threshold).astype(np.uint8)
    )

    if num_labels <= 1:
        return rgba_image, (0, 0, w, h)

    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = areas.max() if len(areas) > 0 else 0

    mask = np.zeros_like(alpha)
    for lbl in range(1, num_labels):
        area = stats[lbl, cv2.CC_STAT_AREA]
        top = stats[lbl, cv2.CC_STAT_TOP]
        height = stats[lbl, cv2.CC_STAT_HEIGHT]

        touches_tb = (top <= 2 or top + height >= h - 2)

        if is_facial_feature:
            if not touches_tb and area >= min_area:
                mask[labels == lbl] = 255
        else:
            if area >= 0.08 * max_area or area >= 450:
                mask[labels == lbl] = 255

    arr[:, :, 3] = np.minimum(arr[:, :, 3], mask)
    cleaned = Image.fromarray(arr)

    # Tight bounding box
    bbox = cleaned.getbbox()
    if not bbox:
        return cleaned, (0, 0, w, h)

    b_x1 = max(0, bbox[0] - pad)
    b_y1 = max(0, bbox[1] - pad)
    b_x2 = min(w, bbox[2] + pad)
    b_y2 = min(h, bbox[3] + pad)
    tight = cleaned.crop((b_x1, b_y1, b_x2, b_y2))

    if part_name:
        tight = normalize_joint_seam(tight, part_name)

    return tight, (b_x1, b_y1, b_x2, b_y2)


def _clean_sleeve_cross_section(arm_img: Image.Image) -> Image.Image:
    """
    If the image generator drew a warm skin-colored mannequin cross-section circle
    at the top shoulder cap of a white/light sleeve, blend it into the surrounding sleeve color
    so the shoulder seam under the collar is invisible.
    """
    arr = np.array(arm_img)
    ah, aw, _ = arr.shape
    # Sample sleeve fabric color from the middle third of the arm
    mid_slice = arr[int(ah * 0.25):int(ah * 0.55), :, :]
    opaque_mid = mid_slice[mid_slice[:, :, 3] > 180]
    if len(opaque_mid) > 50:
        # Find bright/neutral sleeve pixels (low saturation)
        r_m = opaque_mid[:, 0].astype(np.int32)
        g_m = opaque_mid[:, 1].astype(np.int32)
        b_m = opaque_mid[:, 2].astype(np.int32)
        neutral = opaque_mid[(np.abs(r_m - b_m) < 20) & (r_m > 180)]
        if len(neutral) > 20:
            sleeve_rgb = np.median(neutral[:, :3], axis=0).astype(np.uint8)
        else:
            return arm_img
    else:
        return arm_img

    # In the top 34% of the arm, replace warm peach cross-section fill with sleeve_rgb
    top_h = int(ah * 0.34)
    sub = arr[:top_h, :, :]
    r = sub[:, :, 0].astype(np.int32)
    b = sub[:, :, 2].astype(np.int32)
    a = sub[:, :, 3]
    is_peach_cap = (a > 40) & ((r - b) > 13) & (r > 195)
    # Only apply on the shoulder half (not on a raised hand on the right side of arm_right)
    col_mask = np.zeros((top_h, aw), dtype=bool)
    col_mask[:, :int(aw * 0.62)] = True
    replace_mask = is_peach_cap & col_mask
    sub[replace_mask, 0] = sleeve_rgb[0]
    sub[replace_mask, 1] = sleeve_rgb[1]
    sub[replace_mask, 2] = sleeve_rgb[2]
    arr[:top_h, :, :] = sub
    return Image.fromarray(arr)


def normalize_joint_seam(img: Image.Image, part_name: str) -> Image.Image:
    """
    Apply Azur Lane (banerwei_3) joint normalization:
    - body_torso: Remove bare-skin mannequin shoulder balls sticking out left/right of the collar
      at the top 13% of an armless torso so sleeves tuck seamlessly under the collar flaps.
    - arm_left: Clean sleeve cap and auto-orient so shoulder cap is at top-right and hand hangs down-left.
    - arm_right: Clean sleeve cap and orient for natural right-shoulder attachment.
    """
    if part_name == "body_torso":
        arr = np.array(img)
        th, tw, _ = arr.shape
        # Check if torso is armless (width-to-height ratio < 0.52)
        if tw / max(1.0, float(th)) < 0.52:
            top_limit = int(th * 0.13)
            for y in range(top_limit):
                for x in range(tw):
                    if x < int(tw * 0.34) or x > int(tw * 0.66):
                        r, g, b, a = arr[y, x]
                        if a > 0 and (int(r) > 195 and int(g) > 140 and (int(r) - int(b)) > 16):
                            arr[y, x, 3] = 0
            return Image.fromarray(arr)
        return img

    elif part_name == "arm_left":
        cleaned = _clean_sleeve_cross_section(img)
        arr = np.array(cleaned)
        ah, aw, _ = arr.shape
        alpha = arr[:, :, 3]
        top_xs = np.where(alpha[:max(1, int(ah * 0.15)), :] > 40)[1]
        bot_xs = np.where(alpha[int(ah * 0.80):, :] > 40)[1]
        if len(top_xs) > 0 and len(bot_xs) > 0:
            # If shoulder cap is at top-left and hand goes down-right, mirror so it attaches to viewer's left shoulder
            if top_xs.mean() < aw * 0.45 and bot_xs.mean() > aw * 0.52:
                cleaned = ImageOps.mirror(cleaned)
        return cleaned

    elif part_name == "arm_right":
        cleaned = _clean_sleeve_cross_section(img)
        arr = np.array(cleaned)
        ah, aw, _ = arr.shape
        alpha = arr[:, :, 3]
        # Check if it's a bent-elbow peace/wave arm (opaque pixels at both top-left shoulder and top-right hand)
        top_Right = alpha[:int(ah * 0.25), int(aw * 0.60):]
        mid_Left = alpha[int(ah * 0.20):int(ah * 0.55), :int(aw * 0.55)]
        if (top_Right > 40).sum() > 80 and (mid_Left > 40).sum() > 80:
            cleaned = cleaned.rotate(-12, resample=Image.Resampling.BICUBIC, expand=True)
            bbox = cleaned.getbbox()
            if bbox:
                cleaned = cleaned.crop(bbox)
        return cleaned

    return img
