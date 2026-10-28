# -*- coding: utf-8 -*-
"""
Algorithmic Alpha-Medial-Axis Skeleton + Adaptive Triangle ArtMesh Builder for banano2live2D.

Nothing is hardcoded to a single character:
  1. Scans the actual Alpha silhouette of every sliced RGBA component (`parts_data`) to compute
     medial-axis centroids, anatomical attachment points (neck base, shoulder roots, elbow hinges,
     wrist tips, ear tips, hair strand spines, skirt waist/hem, tail spine).
  2. Combines pixel-level medial-axis geometry with `gemini-3.8-flash` multimodal `rig_config` and
     `physics_profile` (stiffness, damping, gravity, sway scale) to produce a bespoke 41-bone
     hierarchical FK skeleton and 8 Verlet physics chains per character.
  3. Builds an Alpha-contour-trimmed Triangle ArtMesh (`vertices`, `uvs`, `local_norm`, `triangles`)
     for each component so empty transparent regions are culled and active ink regions are meshed.
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image


def analyze_alpha_medial_spine(img: Image.Image, num_slices: int = 5) -> List[Tuple[float, float, float]]:
    """
    Slice a component's alpha channel horizontally into `num_slices` bands and compute
    the ink centroid (norm_x, norm_y, ink_width_ratio) for each band from top (0.0) to bottom (1.0).
    Used to trace the true curve of arms (shoulder -> elbow -> wrist), hair locks, tails, and skirts.
    """
    w, h = img.size
    if w <= 1 or h <= 1:
        return [(0.5, i / max(1, num_slices - 1), 0.5) for i in range(num_slices)]

    sw, sh = min(w, 96), min(h, 96)
    alpha = img.getchannel("A").resize((sw, sh), Image.Resampling.BILINEAR)
    px = alpha.load()

    spine: List[Tuple[float, float, float]] = []
    for s in range(num_slices):
        y0 = int(s * sh / num_slices)
        y1 = max(y0 + 1, int((s + 1) * sh / num_slices))
        sum_x = 0.0
        sum_y = 0.0
        sum_w = 0.0
        min_x, max_x = sw, 0
        for y in range(y0, y1):
            for x in range(sw):
                a = px[x, y]
                if a > 20:
                    sum_x += x * a
                    sum_y += y * a
                    sum_w += a
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
        if sum_w > 0:
            nx = (sum_x / sum_w) / max(1, sw - 1)
            ny = (sum_y / sum_w) / max(1, sh - 1)
            span = max(0.05, (max_x - min_x + 1) / float(sw))
            spine.append((round(nx, 4), round(ny, 4), round(span, 4)))
        else:
            ny = (s + 0.5) / num_slices
            spine.append((0.5, round(ny, 4), 0.3))
    return spine


def analyze_left_right_lobes(img: Image.Image) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Find the left-half and right-half ink centroids (e.g. for paired ears/headwear, paired side hair, or paired legs).
    """
    w, h = img.size
    sw, sh = min(w, 96), min(h, 96)
    alpha = img.getchannel("A").resize((sw, sh), Image.Resampling.BILINEAR)
    px = alpha.load()
    mid = sw // 2

    def _lobe(x_start: int, x_end: int, def_x: float) -> Tuple[float, float]:
        sx = sy = sw_a = 0.0
        for y in range(sh):
            for x in range(x_start, x_end):
                a = px[x, y]
                if a > 20:
                    sx += x * a
                    sy += y * a
                    sw_a += a
        if sw_a > 0:
            return (round((sx / sw_a) / max(1, sw - 1), 4), round((sy / sw_a) / max(1, sh - 1), 4))
        return (def_x, 0.5)

    return _lobe(0, mid, 0.28), _lobe(mid, sw, 0.72)


def build_hierarchical_skeleton(
    rig_config: Dict[str, Any],
    parts_data: Optional[Dict[str, Dict[str, Any]]] = None,
    grid_mode: str = "4x4",
) -> Dict[str, Any]:
    """
    Algorithmically compute a 41-bone hierarchical FK skeleton from:
      1) The actual Alpha-channel medial axes of each sliced component image in `parts_data`
      2) The LLM-calibrated component placement (`canvas_center`, `scale`) in `rig_config`
      3) The LLM-inferred material physics profile (`action_spec.physics_profile`)
    """
    comps = rig_config.get("components", {})
    phys_prof = (rig_config.get("action_spec") or {}).get("physics_profile") or {}

    def _part_box(name: str, def_cx: float, def_cy: float, def_w: float, def_h: float) -> Tuple[float, float, float, float, float, float]:
        c = comps.get(name, {}).get("canvas_center") or comps.get(name, {}).get("center") or [def_cx, def_cy]
        cx, cy = float(c[0]), float(c[1])
        sc = float(comps.get(name, {}).get("scale", 1.0))
        if parts_data and name in parts_data and "image" in parts_data[name]:
            im = parts_data[name]["image"]
            dw, dh = im.width * sc, im.height * sc
        else:
            dw, dh = def_w, def_h
        return cx, cy, dw, dh, cx - dw / 2.0, cy - dh / 2.0

    def _map_pt(name: str, nx: float, ny: float, def_cx: float, def_cy: float, def_w: float, def_h: float) -> Tuple[float, float]:
        cx, cy, dw, dh, x0, y0 = _part_box(name, def_cx, def_cy, def_w, def_h)
        return round(x0 + nx * dw, 2), round(y0 + ny * dh, 2)

    # 1. Head & Neck from head_base alpha contour
    h_cx, h_cy, h_w, h_h, h_x0, h_y0 = _part_box("head_base", 500.0, 256.0, 220.0, 260.0)
    if parts_data and "head_base" in parts_data:
        h_spine = analyze_alpha_medial_spine(parts_data["head_base"]["image"], 4)
        neck_nx, neck_ny, _ = h_spine[-1]
        head_nx, head_ny, _ = h_spine[1]
        hx, hy = h_x0 + head_nx * h_w, h_y0 + head_ny * h_h
        neck_x, neck_y = h_x0 + neck_nx * h_w, h_y0 + max(0.78, neck_ny) * h_h
    else:
        hx, hy = h_cx, h_cy
        neck_x, neck_y = h_cx, h_cy + h_h * 0.34

    # 2. Torso, Shoulders & Pelvis from body_torso alpha contour
    t_cx, t_cy, t_w, t_h, t_x0, t_y0 = _part_box("body_torso", 500.0, 455.0 if grid_mode == "4x4" else 620.0, 255.0, 235.0)
    if parts_data and "body_torso" in parts_data:
        t_spine = analyze_alpha_medial_spine(parts_data["body_torso"]["image"], 4)
        top_nx, top_ny, top_span = t_spine[0]
        mid_nx, mid_ny, _ = t_spine[1]
        bot_nx, bot_ny, _ = t_spine[-1]
        chest_x, chest_y = t_x0 + mid_nx * t_w, t_y0 + mid_ny * t_h
        pelvis_x, pelvis_y = t_x0 + bot_nx * t_w, t_y0 + max(0.75, bot_ny) * t_h
        sh_half_w = max(42.0, t_w * top_span * 0.44)
    else:
        chest_x, chest_y = t_cx, t_cy - 15.0
        pelvis_x, pelvis_y = t_cx, t_cy + (65.0 if grid_mode == "4x4" else 40.0)
        sh_half_w = 62.0

    # 3. Left & Right Arm 3-Joint Medial Chains (Shoulder -> Elbow -> Wrist) from arm_left / arm_right pixels
    def _extract_arm_chain(part_name: str, is_left: bool) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        def_ax = 410.0 if is_left else 590.0
        a_cx, a_cy, a_w, a_h, a_x0, a_y0 = _part_box(part_name, def_ax, 465.0, 150.0, 220.0)
        if parts_data and part_name in parts_data:
            asp = analyze_alpha_medial_spine(parts_data[part_name]["image"], 5)
            sh_pt = (round(a_x0 + asp[0][0] * a_w, 2), round(a_y0 + asp[0][1] * a_h, 2))
            el_pt = (round(a_x0 + asp[2][0] * a_w, 2), round(a_y0 + asp[2][1] * a_h, 2))
            wr_pt = (round(a_x0 + asp[4][0] * a_w, 2), round(a_y0 + asp[4][1] * a_h, 2))
            return sh_pt, el_pt, wr_pt
        sign = -1.0 if is_left else 1.0
        return (
            (round(chest_x + sign * sh_half_w, 2), round(chest_y - 36.0, 2)),
            (round(a_cx + sign * 2.0, 2), round(a_cy - 8.0, 2)),
            (round(a_cx + sign * 30.0, 2), round(a_cy + 55.0, 2)),
        )

    sh_L, el_L, wr_L = _extract_arm_chain("arm_left", True)
    sh_R, el_R, wr_R = _extract_arm_chain("arm_right", False)

    # 4. Hand Prop attachment point
    p_cx, p_cy, _, _, _, _ = _part_box("hand_prop_effect", wr_R[0] + 24.0, wr_R[1] - 32.0, 145.0, 160.0)

    # 5. Front Hair, Side Hair, Back Hair spines from their actual alpha pixels
    hf_pts = [_map_pt("front_hair", nx, ny, hx, hy - 12.0, 255.0, 245.0) for nx, ny, _ in (
        analyze_alpha_medial_spine(parts_data["front_hair"]["image"], 3) if (parts_data and "front_hair" in parts_data) else [(0.5, 0.15, 0.5), (0.5, 0.5, 0.5), (0.5, 0.85, 0.5)]
    )]
    hb_pts = [_map_pt("back_hair", nx, ny, hx, hy + 5.0, 290.0, 295.0) for nx, ny, _ in (
        analyze_alpha_medial_spine(parts_data["back_hair"]["image"], 3) if (parts_data and "back_hair" in parts_data) else [(0.5, 0.15, 0.5), (0.5, 0.52, 0.5), (0.5, 0.88, 0.5)]
    )]

    # Side hair left & right lobes
    if parts_data and "side_hair" in parts_data:
        sl_lobe, sr_lobe = analyze_left_right_lobes(parts_data["side_hair"]["image"])
    else:
        sl_lobe, sr_lobe = (0.22, 0.5), (0.78, 0.5)
    hsL_root = _map_pt("side_hair", sl_lobe[0], 0.18, hx, hy + 30.0, 265.0, 275.0)
    hsL_mid  = _map_pt("side_hair", sl_lobe[0], 0.52, hx, hy + 30.0, 265.0, 275.0)
    hsL_tip  = _map_pt("side_hair", sl_lobe[0], 0.88, hx, hy + 30.0, 265.0, 275.0)
    hsR_root = _map_pt("side_hair", sr_lobe[0], 0.18, hx, hy + 30.0, 265.0, 275.0)
    hsR_mid  = _map_pt("side_hair", sr_lobe[0], 0.52, hx, hy + 30.0, 265.0, 275.0)
    hsR_tip  = _map_pt("side_hair", sr_lobe[0], 0.88, hx, hy + 30.0, 265.0, 275.0)

    # 6. Headwear / Ears Left & Right springs from headwear_ears alpha lobes
    if parts_data and "headwear_ears" in parts_data:
        el_lobe, er_lobe = analyze_left_right_lobes(parts_data["headwear_ears"]["image"])
    else:
        el_lobe, er_lobe = (0.28, 0.45), (0.72, 0.45)
    earL_root = _map_pt("headwear_ears", el_lobe[0], 0.68, hx, hy - 75.0, 260.0, 235.0)
    earL_tip  = _map_pt("headwear_ears", el_lobe[0], 0.16, hx, hy - 75.0, 260.0, 235.0)
    earR_root = _map_pt("headwear_ears", er_lobe[0], 0.68, hx, hy - 75.0, 260.0, 235.0)
    earR_tip  = _map_pt("headwear_ears", er_lobe[0], 0.16, hx, hy - 75.0, 260.0, 235.0)

    # 7. Skirt 3-node spine from skirt_lower alpha pixels
    sk_pts = [_map_pt("skirt_lower", nx, ny, pelvis_x, pelvis_y + 40.0, 320.0, 210.0) for nx, ny, _ in (
        analyze_alpha_medial_spine(parts_data["skirt_lower"]["image"], 3) if (parts_data and "skirt_lower" in parts_data) else [(0.5, 0.15, 0.5), (0.5, 0.52, 0.7), (0.5, 0.88, 0.9)]
    )]

    # 8. Back Tail / Wings 4-node spine from back_tail_wings alpha pixels
    tl_pts = [_map_pt("back_tail_wings", nx, ny, pelvis_x, pelvis_y + 15.0, 510.0, 470.0) for nx, ny, _ in (
        analyze_alpha_medial_spine(parts_data["back_tail_wings"]["image"], 4) if (parts_data and "back_tail_wings" in parts_data) else [(0.5, 0.25, 0.5), (0.5, 0.48, 0.7), (0.5, 0.70, 0.8), (0.5, 0.90, 0.6)]
    )]

    # 9. Legs Left & Right chains from legs_stockings alpha lobes
    if parts_data and "legs_stockings" in parts_data:
        ll_lobe, lr_lobe = analyze_left_right_lobes(parts_data["legs_stockings"]["image"])
    else:
        ll_lobe, lr_lobe = (0.32, 0.5), (0.68, 0.5)
    hip_L   = _map_pt("legs_stockings", ll_lobe[0], 0.12, pelvis_x, 775.0, 235.0, 390.0)
    knee_L  = _map_pt("legs_stockings", ll_lobe[0], 0.50, pelvis_x, 775.0, 235.0, 390.0)
    ankle_L = _map_pt("legs_stockings", ll_lobe[0], 0.88, pelvis_x, 775.0, 235.0, 390.0)
    hip_R   = _map_pt("legs_stockings", lr_lobe[0], 0.12, pelvis_x, 775.0, 235.0, 390.0)
    knee_R  = _map_pt("legs_stockings", lr_lobe[0], 0.50, pelvis_x, 775.0, 235.0, 390.0)
    ankle_R = _map_pt("legs_stockings", lr_lobe[0], 0.88, pelvis_x, 775.0, 235.0, 390.0)

    bones: List[Dict[str, Any]] = [
        {"id": "root", "parent": None, "x": round(pelvis_x, 2), "y": round(pelvis_y + 20.0, 2), "type": "root", "label": "Root"},
        {"id": "pelvis", "parent": "root", "x": round(pelvis_x, 2), "y": round(pelvis_y, 2), "type": "joint", "label": "Pelvis"},
        {"id": "spine_chest", "parent": "pelvis", "x": round(chest_x, 2), "y": round(chest_y, 2), "type": "joint", "label": "Chest"},
        {"id": "neck", "parent": "spine_chest", "x": round(neck_x, 2), "y": round(neck_y, 2), "type": "joint", "label": "Neck"},
        {"id": "head", "parent": "neck", "x": round(hx, 2), "y": round(hy, 2), "type": "head", "label": "Head"},

        {"id": "shoulder_L", "parent": "spine_chest", "x": sh_L[0], "y": sh_L[1], "type": "limb", "label": "Shoulder_L"},
        {"id": "elbow_L", "parent": "shoulder_L", "x": el_L[0], "y": el_L[1], "type": "limb", "label": "Elbow_L"},
        {"id": "wrist_L", "parent": "elbow_L", "x": wr_L[0], "y": wr_L[1], "type": "limb", "label": "Wrist_L"},

        {"id": "shoulder_R", "parent": "spine_chest", "x": sh_R[0], "y": sh_R[1], "type": "limb", "label": "Shoulder_R"},
        {"id": "elbow_R", "parent": "shoulder_R", "x": el_R[0], "y": el_R[1], "type": "limb", "label": "Elbow_R"},
        {"id": "wrist_R", "parent": "elbow_R", "x": wr_R[0], "y": wr_R[1], "type": "limb", "label": "Wrist_R"},
        {"id": "prop_joint", "parent": "wrist_R", "x": round(p_cx, 2), "y": round(p_cy, 2), "type": "prop", "label": "Prop"},

        {"id": "hair_front_root", "parent": "head", "x": hf_pts[0][0], "y": hf_pts[0][1], "type": "physics", "label": "HairFront_Root"},
        {"id": "hair_front_mid", "parent": "hair_front_root", "x": hf_pts[1][0], "y": hf_pts[1][1], "type": "physics", "label": "HairFront_Mid"},
        {"id": "hair_front_tip", "parent": "hair_front_mid", "x": hf_pts[2][0], "y": hf_pts[2][1], "type": "physics", "label": "HairFront_Tip"},

        {"id": "hair_side_L_root", "parent": "head", "x": hsL_root[0], "y": hsL_root[1], "type": "physics", "label": "SideHair_L_Root"},
        {"id": "hair_side_L_mid", "parent": "hair_side_L_root", "x": hsL_mid[0], "y": hsL_mid[1], "type": "physics", "label": "SideHair_L_Mid"},
        {"id": "hair_side_L_tip", "parent": "hair_side_L_mid", "x": hsL_tip[0], "y": hsL_tip[1], "type": "physics", "label": "SideHair_L_Tip"},

        {"id": "hair_side_R_root", "parent": "head", "x": hsR_root[0], "y": hsR_root[1], "type": "physics", "label": "SideHair_R_Root"},
        {"id": "hair_side_R_mid", "parent": "hair_side_R_root", "x": hsR_mid[0], "y": hsR_mid[1], "type": "physics", "label": "SideHair_R_Mid"},
        {"id": "hair_side_R_tip", "parent": "hair_side_R_mid", "x": hsR_tip[0], "y": hsR_tip[1], "type": "physics", "label": "SideHair_R_Tip"},

        {"id": "hair_back_root", "parent": "head", "x": hb_pts[0][0], "y": hb_pts[0][1], "type": "physics", "label": "BackHair_Root"},
        {"id": "hair_back_mid", "parent": "hair_back_root", "x": hb_pts[1][0], "y": hb_pts[1][1], "type": "physics", "label": "BackHair_Mid"},
        {"id": "hair_back_tip", "parent": "hair_back_mid", "x": hb_pts[2][0], "y": hb_pts[2][1], "type": "physics", "label": "BackHair_Tip"},

        {"id": "ear_L_root", "parent": "head", "x": earL_root[0], "y": earL_root[1], "type": "physics", "label": "Ear_L_Root"},
        {"id": "ear_L_tip", "parent": "ear_L_root", "x": earL_tip[0], "y": earL_tip[1], "type": "physics", "label": "Ear_L_Tip"},
        {"id": "ear_R_root", "parent": "head", "x": earR_root[0], "y": earR_root[1], "type": "physics", "label": "Ear_R_Root"},
        {"id": "ear_R_tip", "parent": "ear_R_root", "x": earR_tip[0], "y": earR_tip[1], "type": "physics", "label": "Ear_R_Tip"},

        {"id": "skirt_root", "parent": "pelvis", "x": sk_pts[0][0], "y": sk_pts[0][1], "type": "physics", "label": "Skirt_Root"},
        {"id": "skirt_mid", "parent": "skirt_root", "x": sk_pts[1][0], "y": sk_pts[1][1], "type": "physics", "label": "Skirt_Mid"},
        {"id": "skirt_hem", "parent": "skirt_mid", "x": sk_pts[2][0], "y": sk_pts[2][1], "type": "physics", "label": "Skirt_Hem"},

        {"id": "tail_root", "parent": "pelvis", "x": tl_pts[0][0], "y": tl_pts[0][1], "type": "physics", "label": "Tail_Root"},
        {"id": "tail_mid1", "parent": "tail_root", "x": tl_pts[1][0], "y": tl_pts[1][1], "type": "physics", "label": "Tail_Mid1"},
        {"id": "tail_mid2", "parent": "tail_mid1", "x": tl_pts[2][0], "y": tl_pts[2][1], "type": "physics", "label": "Tail_Mid2"},
        {"id": "tail_tip", "parent": "tail_mid2", "x": tl_pts[3][0], "y": tl_pts[3][1], "type": "physics", "label": "Tail_Tip"},

        {"id": "hip_L", "parent": "pelvis", "x": hip_L[0], "y": hip_L[1], "type": "limb", "label": "Hip_L"},
        {"id": "knee_L", "parent": "hip_L", "x": knee_L[0], "y": knee_L[1], "type": "limb", "label": "Knee_L"},
        {"id": "ankle_L", "parent": "knee_L", "x": ankle_L[0], "y": ankle_L[1], "type": "limb", "label": "Ankle_L"},

        {"id": "hip_R", "parent": "pelvis", "x": hip_R[0], "y": hip_R[1], "type": "limb", "label": "Hip_R"},
        {"id": "knee_R", "parent": "hip_R", "x": knee_R[0], "y": knee_R[1], "type": "limb", "label": "Knee_R"},
        {"id": "ankle_R", "parent": "knee_R", "x": ankle_R[0], "y": ankle_R[1], "type": "limb", "label": "Ankle_R"},
    ]

    # Dynamic physics parameters from gemini-3.8-flash physics_profile
    hf_damp = float(phys_prof.get("hair_front_damping", 0.85))
    hs_damp = float(phys_prof.get("hair_side_damping", 0.84))
    hb_damp = float(phys_prof.get("hair_back_damping", 0.82))
    sk_mob = float(phys_prof.get("skirt_mobility", 0.86))

    return {
        "version": "2.1-medial-axis-dynamic-skeleton",
        "bone_count": len(bones),
        "bones": bones,
        "computed_joints": {
            "head": [round(hx, 2), round(hy, 2)],
            "neck": [round(neck_x, 2), round(neck_y, 2)],
            "chest": [round(chest_x, 2), round(chest_y, 2)],
            "pelvis": [round(pelvis_x, 2), round(pelvis_y, 2)],
            "shoulder_L": list(sh_L), "elbow_L": list(el_L), "wrist_L": list(wr_L),
            "shoulder_R": list(sh_R), "elbow_R": list(el_R), "wrist_R": list(wr_R),
            "prop": [round(p_cx, 2), round(p_cy, 2)],
        },
        "physics_chains": [
            {"id": "chain_front_hair", "bones": ["hair_front_root", "hair_front_mid", "hair_front_tip"], "stiffness": 0.22, "damping": hf_damp, "gravity": 0.45},
            {"id": "chain_side_hair_L", "bones": ["hair_side_L_root", "hair_side_L_mid", "hair_side_L_tip"], "stiffness": 0.18, "damping": hs_damp, "gravity": 0.55},
            {"id": "chain_side_hair_R", "bones": ["hair_side_R_root", "hair_side_R_mid", "hair_side_R_tip"], "stiffness": 0.18, "damping": hs_damp, "gravity": 0.55},
            {"id": "chain_back_hair", "bones": ["hair_back_root", "hair_back_mid", "hair_back_tip"], "stiffness": 0.16, "damping": hb_damp, "gravity": 0.60},
            {"id": "chain_ears_L", "bones": ["ear_L_root", "ear_L_tip"], "stiffness": 0.32, "damping": 0.80, "gravity": -0.25},
            {"id": "chain_ears_R", "bones": ["ear_R_root", "ear_R_tip"], "stiffness": 0.32, "damping": 0.80, "gravity": -0.25},
            {"id": "chain_skirt", "bones": ["skirt_root", "skirt_mid", "skirt_hem"], "stiffness": round(0.24 * sk_mob, 3), "damping": 0.86, "gravity": 0.50},
            {"id": "chain_tail", "bones": ["tail_root", "tail_mid1", "tail_mid2", "tail_tip"], "stiffness": 0.15, "damping": 0.88, "gravity": 0.30},
        ],
    }


def build_part_triangle_mesh(
    part_name: str,
    img: Image.Image,
    part_cfg: Dict[str, Any],
    uv_rect: Dict[str, Any],
    atlas_size: int,
) -> Dict[str, Any]:
    """
    Generate an alpha-aware subdivided Triangle ArtMesh for a component image.
    """
    high_res_parts = {"back_tail_wings", "back_hair", "front_hair", "side_hair", "skirt_lower", "body_torso", "legs_stockings"}
    med_res_parts = {"head_base", "arm_left", "arm_right", "headwear_ears", "hand_prop_effect"}
    if part_name in high_res_parts:
        cols, rows = 8, 10
    elif part_name in med_res_parts:
        cols, rows = 6, 8
    else:
        cols, rows = 5, 4

    pw, ph = img.size
    alpha = img.getchannel("A")
    small_a = alpha.resize((cols, rows), Image.Resampling.BILINEAR)
    a_pixels = small_a.load()

    def cell_has_ink(c_idx: int, r_idx: int) -> bool:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nc = max(0, min(cols - 1, c_idx + dc))
                nr = max(0, min(rows - 1, r_idx + dr))
                if a_pixels[nc, nr] > 6:
                    return True
        return False

    center = part_cfg.get("canvas_center") or part_cfg.get("center") or [500.0, 500.0]
    scale = float(part_cfg.get("scale", 1.0))
    draw_w = pw * scale
    draw_h = ph * scale
    paste_x = float(center[0]) - draw_w / 2.0
    paste_y = float(center[1]) - draw_h / 2.0

    u0 = uv_rect["uv"]["u0"]
    v0 = uv_rect["uv"]["v0"]
    u1 = uv_rect["uv"]["u1"]
    v1 = uv_rect["uv"]["v1"]

    vertices: List[List[float]] = []
    uvs: List[List[float]] = []
    local_norm: List[List[float]] = []
    grid_vid: Dict[Tuple[int, int], int] = {}

    for r in range(rows + 1):
        ny = r / float(rows)
        for c in range(cols + 1):
            nx = c / float(cols)
            active = False
            for cr in (r - 1, r):
                for cc in (c - 1, c):
                    if 0 <= cc < cols and 0 <= cr < rows and cell_has_ink(cc, cr):
                        active = True
                        break
                if active:
                    break
            if not active:
                continue

            vid = len(vertices)
            grid_vid[(c, r)] = vid
            sx = round(paste_x + nx * draw_w, 2)
            sy = round(paste_y + ny * draw_h, 2)
            u = round(u0 + nx * (u1 - u0), 5)
            v = round(v0 + ny * (v1 - v0), 5)
            vertices.append([sx, sy])
            uvs.append([u, v])
            local_norm.append([round(nx, 4), round(ny, 4)])

    triangles: List[List[int]] = []
    for r in range(rows):
        for c in range(cols):
            if not cell_has_ink(c, r):
                continue
            v00 = grid_vid.get((c, r))
            v10 = grid_vid.get((c + 1, r))
            v01 = grid_vid.get((c, r + 1))
            v11 = grid_vid.get((c + 1, r + 1))
            if v00 is not None and v10 is not None and v01 is not None and v11 is not None:
                if (r + c) % 2 == 0:
                    triangles.append([v00, v10, v11])
                    triangles.append([v00, v11, v01])
                else:
                    triangles.append([v00, v10, v01])
                    triangles.append([v10, v11, v01])

    return {
        "part_name": part_name,
        "cols": cols,
        "rows": rows,
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
        "vertices": vertices,
        "uvs": uvs,
        "local_norm": local_norm,
        "triangles": triangles,
    }