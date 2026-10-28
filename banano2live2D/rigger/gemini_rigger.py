# -*- coding: utf-8 -*-
"""
Gemini Multimodal Live2D Rigger & Unified Action/Motion Generator (Azur Lane / banerwei_3 Architecture).
Supports both 3x3 (9-Part Standard) and 4x4 (16-Part High-Flexibility) Component Grids,
as well as Standard (1K/2K) and 4K UHD (4096x4096) component resolutions.
"""

import io
import os
import re
import copy
import json
import base64
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageDraw
from ..sdk.client import HrioClient

COMPONENT_ORDER_3X3 = [
    "back_hair", "head_base", "front_hair",
    "eyes_open", "eyes_closed", "mouth",
    "body_torso", "arm_left", "arm_right",
]

COMPONENT_ORDER_4X4 = [
    "back_hair", "head_base", "front_hair", "side_hair",
    "eyes_open", "eyes_closed", "eyebrows", "mouth",
    "body_torso", "skirt_lower", "arm_left", "arm_right",
    "legs_stockings", "headwear_ears", "back_tail_wings", "hand_prop_effect",
]

# Backwards-compatible default alias
COMPONENT_ORDER = COMPONENT_ORDER_3X3

DEFAULT_RIG_CONFIG_3X3: Dict[str, Any] = {
    "character_name": "banerwei_sailor",
    "grid": "3x3",
    "canvas": {"width": 1000, "height": 1000},
    "components": {
        "back_hair": {
            "box_1000": [15, 15, 450, 440],
            "z_index": 10,
            "canvas_center": [500, 260],
            "scale": 0.84,
            "pivot": [0.5, 0.35],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairBack"],
        },
        "head_base": {
            "box_1000": [20, 460, 450, 800],
            "z_index": 20,
            "canvas_center": [500, 256],
            "scale": 0.78,
            "pivot": [0.5, 0.86],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamCheek"],
        },
        "arm_left": {
            "box_1000": [665, 460, 990, 800],
            "z_index": 25,
            "canvas_center": [422, 444],
            "scale": 0.60,
            "pivot": [0.82, 0.10],
            "live2d_params": ["ParamArmLAngle", "ParamBodyAngleX", "ParamBreath"],
        },
        "arm_right": {
            "box_1000": [665, 815, 990, 990],
            "z_index": 26,
            "canvas_center": [570, 400],
            "scale": 0.64,
            "pivot": [0.28, 0.25],
            "live2d_params": ["ParamArmRAngle", "ParamBodyAngleX", "ParamBreath"],
        },
        "body_torso": {
            "box_1000": [665, 15, 995, 445],
            "z_index": 30,
            "canvas_center": [500, 635],
            "scale": 1.15,
            "pivot": [0.5, 0.45],
            "live2d_params": ["ParamBodyAngleX", "ParamBodyAngleY", "ParamBodyAngleZ", "ParamBreath"],
        },
        "mouth": {
            "box_1000": [470, 815, 650, 990],
            "z_index": 40,
            "canvas_center": [500, 314],
            "scale": 0.27,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamMouthForm", "ParamMouthOpenY"],
        },
        "eyes_open": {
            "box_1000": [470, 15, 650, 445],
            "z_index": 50,
            "canvas_center": [500, 272],
            "scale": 0.44,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamEyeLOpen", "ParamEyeROpen", "ParamEyeBallX", "ParamEyeBallY"],
        },
        "eyes_closed": {
            "box_1000": [470, 460, 650, 800],
            "z_index": 51,
            "canvas_center": [500, 272],
            "scale": 0.44,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamEyeLSmile", "ParamEyeRSmile"],
        },
        "front_hair": {
            "box_1000": [15, 815, 450, 995],
            "z_index": 60,
            "canvas_center": [500, 244],
            "scale": 0.82,
            "pivot": [0.5, 0.32],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairFront", "ParamHairSide"],
        },
    },
}

DEFAULT_RIG_CONFIG_4X4: Dict[str, Any] = {
    "character_name": "azur_4x4_4k_heroine",
    "grid": "4x4",
    "canvas": {"width": 1000, "height": 1000},
    "components": {
        "back_tail_wings": {
            "z_index": 5,
            "canvas_center": [505, 520],
            "scale": 0.48,
            "pivot": [0.50, 0.50],
            "live2d_params": ["ParamBodyAngleX", "ParamBodyAngleZ", "ParamHairBack", "ParamBreath"],
        },
        "back_hair": {
            "z_index": 10,
            "canvas_center": [500, 265],
            "scale": 0.84,
            "pivot": [0.5, 0.35],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairBack"],
        },
        "legs_stockings": {
            "z_index": 15,
            "canvas_center": [500, 775],
            "scale": 0.88,
            "pivot": [0.5, 0.12],
            "live2d_params": ["ParamBodyAngleX", "ParamBodyAngleZ"],
        },
        "head_base": {
            "z_index": 38,
            "canvas_center": [500, 256],
            "scale": 0.78,
            "pivot": [0.5, 0.86],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamCheek"],
        },
        "arm_left": {
            "z_index": 25,
            "canvas_center": [410, 468],
            "scale": 0.60,
            "pivot": [0.82, 0.10],
            "live2d_params": ["ParamArmLAngle", "ParamBodyAngleX", "ParamBreath"],
        },
        "arm_right": {
            "z_index": 26,
            "canvas_center": [588, 462],
            "scale": 0.64,
            "pivot": [0.28, 0.25],
            "live2d_params": ["ParamArmRAngle", "ParamBodyAngleX", "ParamBreath"],
        },
        "body_torso": {
            "z_index": 30,
            "canvas_center": [500, 455],
            "scale": 0.80,
            "pivot": [0.5, 0.25],
            "live2d_params": ["ParamBodyAngleX", "ParamBodyAngleY", "ParamBodyAngleZ", "ParamBreath"],
        },
        "skirt_lower": {
            "z_index": 32,
            "canvas_center": [500, 552],
            "scale": 0.82,
            "pivot": [0.5, 0.15],
            "live2d_params": ["ParamBodyAngleX", "ParamBodyAngleZ", "ParamHairBack", "ParamBreath"],
        },
        "mouth": {
            "z_index": 40,
            "canvas_center": [500, 314],
            "scale": 0.27,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamMouthForm", "ParamMouthOpenY"],
        },
        "eyes_open": {
            "z_index": 50,
            "canvas_center": [500, 272],
            "scale": 0.44,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamEyeLOpen", "ParamEyeROpen", "ParamEyeBallX", "ParamEyeBallY"],
        },
        "eyes_closed": {
            "z_index": 51,
            "canvas_center": [500, 272],
            "scale": 0.44,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamEyeLSmile", "ParamEyeRSmile"],
        },
        "eyebrows": {
            "z_index": 55,
            "canvas_center": [500, 240],
            "scale": 0.42,
            "pivot": [0.5, 0.50],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamEyeLSmile"],
        },
        "side_hair": {
            "z_index": 58,
            "canvas_center": [500, 295],
            "scale": 0.80,
            "pivot": [0.5, 0.22],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairSide"],
        },
        "front_hair": {
            "z_index": 60,
            "canvas_center": [500, 242],
            "scale": 0.82,
            "pivot": [0.5, 0.32],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairFront", "ParamHairSide"],
        },
        "headwear_ears": {
            "z_index": 65,
            "canvas_center": [500, 178],
            "scale": 0.62,
            "pivot": [0.5, 0.80],
            "live2d_params": ["ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamHairFront"],
        },
        "hand_prop_effect": {
            "z_index": 70,
            "canvas_center": [642, 448],
            "scale": 0.50,
            "pivot": [0.35, 0.75],
            "live2d_params": ["ParamArmRAngle", "ParamBodyAngleX", "ParamBreath"],
        },
    },
}

DEFAULT_RIG_CONFIG = DEFAULT_RIG_CONFIG_3X3

DEFAULT_CUSTOM_MOTIONS: List[Dict[str, Any]] = [
    {
        "id": "custom_cheer_jump",
        "label": "✨ 元气欢呼跳跃",
        "duration": 2.4,
        "loop": False,
        "dialogue": "太棒啦！指挥官快看，我的新动作充满活力吧~☆",
        "curves": {
            "ParamBodyAngleY": [[0.0, 0.0], [0.35, 15.0], [0.7, -6.0], [1.1, 16.0], [1.5, -5.0], [2.0, 4.0], [2.4, 0.0]],
            "ParamAngleY": [[0.0, 0.0], [0.35, 14.0], [0.7, -8.0], [1.1, 15.0], [1.6, -4.0], [2.4, 0.0]],
            "ParamAngleZ": [[0.0, 0.0], [0.5, -8.0], [1.2, 8.0], [1.8, -5.0], [2.4, 0.0]],
            "ParamArmLAngle": [[0.0, 0.0], [0.35, -26.0], [0.75, 8.0], [1.15, -26.0], [1.7, 6.0], [2.4, 0.0]],
            "ParamArmRAngle": [[0.0, 0.0], [0.35, 30.0], [0.75, -10.0], [1.15, 30.0], [1.7, -6.0], [2.4, 0.0]],
            "ParamEyeLOpen": [[0.0, 1.0], [0.25, 0.0], [1.5, 0.0], [1.9, 1.0], [2.4, 1.0]],
            "ParamEyeROpen": [[0.0, 1.0], [0.25, 0.0], [1.5, 0.0], [1.9, 1.0], [2.4, 1.0]],
            "ParamEyeLSmile": [[0.0, 0.0], [0.25, 1.0], [1.5, 1.0], [1.9, 0.0], [2.4, 0.0]],
            "ParamEyeRSmile": [[0.0, 0.0], [0.25, 1.0], [1.5, 1.0], [1.9, 0.0], [2.4, 0.0]],
            "ParamMouthOpenY": [[0.0, 0.0], [0.3, 0.95], [0.7, 0.25], [1.1, 0.9], [1.6, 0.2], [2.1, 0.0], [2.4, 0.0]],
            "ParamCheek": [[0.0, 0.0], [0.3, 0.85], [1.9, 0.85], [2.4, 0.0]],
            "ParamEmotionStar": [[0.0, 0.0], [0.25, 1.0], [1.8, 1.0], [2.4, 0.0]],
        },
    },
    {
        "id": "custom_shy_blush",
        "label": "✨ 害羞扭捏捂脸",
        "duration": 2.8,
        "loop": False,
        "dialogue": "呜……指挥官突然提这种要求，人家会不好意思的啦……♥",
        "curves": {
            "ParamAngleX": [[0.0, 0.0], [0.5, -14.0], [1.2, 12.0], [1.9, -10.0], [2.8, 0.0]],
            "ParamAngleY": [[0.0, 0.0], [0.4, -12.0], [1.4, -10.0], [2.2, -5.0], [2.8, 0.0]],
            "ParamAngleZ": [[0.0, 0.0], [0.6, -10.0], [1.5, 9.0], [2.2, -6.0], [2.8, 0.0]],
            "ParamBodyAngleX": [[0.0, 0.0], [0.6, -10.0], [1.5, 10.0], [2.2, -6.0], [2.8, 0.0]],
            "ParamBodyAngleZ": [[0.0, 0.0], [0.6, -4.0], [1.5, 4.0], [2.8, 0.0]],
            "ParamArmLAngle": [[0.0, 0.0], [0.45, 28.0], [1.3, 22.0], [2.1, 14.0], [2.8, 0.0]],
            "ParamArmRAngle": [[0.0, 0.0], [0.45, -24.0], [1.3, -18.0], [2.1, -10.0], [2.8, 0.0]],
            "ParamCheek": [[0.0, 0.0], [0.25, 1.0], [2.3, 1.0], [2.8, 0.0]],
            "ParamEmotionHeart": [[0.0, 0.0], [0.3, 1.0], [2.2, 1.0], [2.8, 0.0]],
            "ParamMouthOpenY": [[0.0, 0.0], [0.4, 0.5], [1.0, 0.15], [1.6, 0.45], [2.3, 0.0], [2.8, 0.0]],
        },
    },
]

DEFAULT_ACTION_SPEC: Dict[str, Any] = {
    "archetype": "Azur Lane Secretary (banerwei_3 Standard)",
    "dialogues": {
        "login": "指挥官，欢迎回来！今天的委托和演习安排都已经整理好啦~",
        "home": "港区海风真舒服呢，指挥官累了的话随时可以靠在我身边休息哦。",
        "main_1": "那个……指挥官一直盯着我看，我脸上有什么东西吗？",
        "main_2": "只要和指挥官在一起，无论什么任务都能顺利完成的！耶~✌",
        "main_3": "新的战术教材已经读完了！下次出击请务必让我担任旗舰吧！",
        "touch_head": "嘿嘿……被指挥官摸头的话，感觉整个人都充满干劲了呢~♥",
        "touch_body": "哇啊！指、指挥官，突然碰哪里呀……正在执勤中呢！",
        "touch_special": "呀啊？！那、那里不行啦指挥官！！笨蛋……><",
        "wedding": "从今往后，无论风浪还是晴空，我的航向永远属于指挥官一人……♥",
        "mail": "指挥官，有新的信件送达港区邮箱，要现在拆开看看吗？",
        "mission": "还有尚未完成的作战任务哦，我们一起去确认一下吧！",
        "mission_complete": "太棒啦！任务奖励已经全部送达仓库，辛苦指挥官了~",
        "complete": "建造与整备工作圆满完成！来看看新伙伴吧~",
    },
    "physics_profile": {
        "hair_mobility": 0.90,
        "hair_delay": 0.72,
        "skirt_mobility": 0.85,
        "hair_front_damping": 0.86,
        "hair_side_damping": 0.84,
        "hair_back_damping": 0.82,
        "skirt_sway_scale": 1.15,
    },
    "custom_motions": copy.deepcopy(DEFAULT_CUSTOM_MOTIONS),
    "hit_areas": [
        {"name": "Head", "id": "HitAreaHead", "y_range": [80, 360], "motion": "touch_head"},
        {"name": "Special", "id": "HitAreaSpecial", "y_range": [360, 490], "motion": "touch_special"},
        {"name": "Body", "id": "HitAreaBody", "y_range": [490, 920], "motion": "touch_body"},
    ],
}


def _detect_grid_mode(parts_data: Optional[Dict[str, Dict[str, Any]]] = None, grid: Optional[str] = None) -> str:
    if grid and str(grid).strip().lower() in ("4x4", "4", "16", "16parts"):
        return "4x4"
    if parts_data and (len(parts_data) > 9 or "skirt_lower" in parts_data or "side_hair" in parts_data):
        return "4x4"
    return "3x3"


def build_matted_contact_sheet(
    parts_data: Dict[str, Dict[str, Any]],
    output_path: Optional[str] = None,
    sheet_size: int = 720,
    grid: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Composite the sliced & BFS-matted transparent components (9 parts for 3x3, or 16 parts for 4x4)
    into a clean contact sheet so gemini-3.8-flash can inspect all matted parts alongside pixel dimensions.
    Returns: (data_uri, parts_summary_dict)
    """
    grid_mode = _detect_grid_mode(parts_data, grid)
    order = COMPONENT_ORDER_4X4 if grid_mode == "4x4" else COMPONENT_ORDER_3X3
    grid_n = 4 if grid_mode == "4x4" else 3
    if grid_mode == "4x4" and sheet_size < 800:
        sheet_size = 800

    cell_size = sheet_size // grid_n
    sheet = Image.new("RGBA", (sheet_size, sheet_size), (242, 245, 250, 255))
    draw = ImageDraw.Draw(sheet)

    for i in range(1, grid_n):
        draw.line([(i * cell_size, 0), (i * cell_size, sheet_size)], fill=(205, 213, 225, 255), width=2)
        draw.line([(0, i * cell_size), (sheet_size, i * cell_size)], fill=(205, 213, 225, 255), width=2)

    parts_summary: Dict[str, Any] = {}
    for idx, name in enumerate(order):
        r, c = divmod(idx, grid_n)
        x0, y0 = c * cell_size, r * cell_size
        pdata = parts_data.get(name)
        if not pdata or "image" not in pdata:
            continue
        pimg: Image.Image = pdata["image"]
        pw, ph = pimg.size
        parts_summary[name] = {
            "cell": [r, c],
            "cropped_width_px": pw,
            "cropped_height_px": ph,
            "aspect_ratio": round(pw / max(1.0, float(ph)), 3),
        }

        max_dim = int(cell_size * 0.84)
        scale = min(max_dim / max(1, pw), max_dim / max(1, ph))
        tw = max(1, int(pw * scale))
        th = max(1, int(ph * scale))
        thumb = pimg.resize((tw, th), Image.Resampling.LANCZOS)

        px = x0 + (cell_size - tw) // 2
        py = y0 + (cell_size - th) // 2
        sheet.alpha_composite(thumb, (px, py))
        draw.text((x0 + 6, y0 + 4), f"{name} ({pw}x{ph})", fill=(30, 41, 59, 255))

    rgb_sheet = sheet.convert("RGB")
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        rgb_sheet.save(output_path, format="JPEG", quality=88)

    buf = io.BytesIO()
    rgb_sheet.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}", parts_summary


def _find_arm_anchors(img: Image.Image, is_left: bool) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    import numpy as np
    a = np.array(img.convert("RGBA"))[:, :, 3]
    h, w = a.shape
    if h < 4 or w < 4:
        return ((0.82 if is_left else 0.18), 0.14), ((0.18 if is_left else 0.85), 0.75)

    # Shoulder cap: top 35% of image, inner side (right for arm_left, left for arm_right)
    top_band = a[:max(1, int(h * 0.35)), :]
    ys, xs = np.where(top_band > 25)
    if len(xs) > 10:
        if is_left:
            q = np.percentile(xs, 78)
            sel = xs >= q
        else:
            q = np.percentile(xs, 22)
            sel = xs <= q
        sh_nx = float(np.median(xs[sel])) / w
        sh_ny = float(np.median(ys[sel])) / h
    else:
        sh_nx, sh_ny = (0.82 if is_left else 0.18), 0.14

    # Hand / wrist extremity: outer side
    ys_all, xs_all = np.where(a > 25)
    if len(xs_all) > 10:
        if is_left:
            q_h = np.percentile(xs_all, 15)
            sel_h = xs_all <= q_h
        else:
            q_h = np.percentile(xs_all, 85)
            sel_h = xs_all >= q_h
        hand_nx = float(np.median(xs_all[sel_h])) / w
        hand_ny = float(np.median(ys_all[sel_h])) / h
    else:
        hand_nx, hand_ny = (0.18 if is_left else 0.85), 0.75

    return (sh_nx, sh_ny), (hand_nx, hand_ny)


def calibrate_anatomical_rig(
    rig_config: Dict[str, Any],
    parts_data: Optional[Dict[str, Dict[str, Any]]] = None,
    grid: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Contour Seam-Locked Anatomical Calibration:
    Locks head chin -> torso collar, front_hair crown -> head cranium,
    arm_left/arm_right shoulder caps -> torso shoulder sockets,
    hand_prop_effect -> right hand extremity, skirt waist -> torso waist,
    and legs -> under skirt hem, while incorporating gemini-3.8-flash visual adjustments.
    """
    import numpy as np
    grid_mode = _detect_grid_mode(parts_data, grid or rig_config.get("grid"))
    base_template = DEFAULT_RIG_CONFIG_4X4 if grid_mode == "4x4" else DEFAULT_RIG_CONFIG_3X3
    calibrated = copy.deepcopy(base_template)

    if "character_name" in rig_config and rig_config["character_name"]:
        calibrated["character_name"] = rig_config["character_name"]

    if not parts_data:
        return calibrated

    def _sz(name: str, def_w: float = 250.0, def_h: float = 250.0) -> Tuple[float, float]:
        p = parts_data.get(name)
        if p and "size" in p:
            return float(max(1, p["size"][0])), float(max(1, p["size"][1]))
        return def_w, def_h

    comps = calibrated["components"]

    if grid_mode == "4x4":
        # 1. Body Torso (Anchor at center spine x=500)
        tw, th = _sz("body_torso", 500, 900)
        t_scale = min(195.0 / tw, 245.0 / th)
        t_draw_w, t_draw_h = tw * t_scale, th * t_scale
        t_cx, t_cy = 500.0, 466.0
        t_top_y = t_cy - t_draw_h * 0.5
        t_bot_y = t_cy + t_draw_h * 0.5
        comps["body_torso"]["scale"] = round(t_scale, 4)
        comps["body_torso"]["canvas_center"] = [round(t_cx, 1), round(t_cy, 1)]
        comps["body_torso"]["z_index"] = 28

        # Detect true shoulder width on body_torso at y=22%
        sh_span_ratio = 0.72
        if "body_torso" in parts_data and "image" in parts_data["body_torso"]:
            t_arr = np.array(parts_data["body_torso"]["image"].convert("RGBA"))[:, :, 3]
            sy_idx = int(t_arr.shape[0] * 0.22)
            xs_sh = np.where(t_arr[sy_idx, :] > 25)[0]
            if len(xs_sh) >= 2:
                sh_span_ratio = max(0.52, min(0.88, float(xs_sh[-1] - xs_sh[0]) / max(1, t_arr.shape[1])))

        sh_socket_L_x = t_cx - (t_draw_w * sh_span_ratio * 0.5) + 8.0
        sh_socket_R_x = t_cx + (t_draw_w * sh_span_ratio * 0.5) - 8.0
        sh_socket_y = t_top_y + t_draw_h * 0.39

        # 2. Head Base (Full V-shaped chin + neck tucks cleanly into collar top; body_torso duplicate neck is erased!)
        hw, hh = _sz("head_base", 600, 760)
        h_scale = min(215.0 / hw, 255.0 / hh)
        h_draw_w, h_draw_h = hw * h_scale, hh * h_scale
        neck_bot_target_y = t_top_y + 44.0
        h_cx = 500.0
        h_cy = neck_bot_target_y - h_draw_h * 0.5
        h_top_y = h_cy - h_draw_h * 0.5
        face_h = h_draw_h * 0.92
        comps["head_base"]["scale"] = round(h_scale, 4)
        comps["head_base"]["canvas_center"] = [round(h_cx, 1), round(h_cy, 1)]
        comps["head_base"]["z_index"] = 26

        # 3. Front Hair (Crown locks 14px ABOVE head_top_y and width >= 1.28x head_draw_w so skull never shows!)
        fhw, fhh = _sz("front_hair", 800, 820)
        fh_scale = max((h_draw_w * 1.28) / fhw, min(268.0 / fhw, 265.0 / fhh))
        fh_draw_w, fh_draw_h = fhw * fh_scale, fhh * fh_scale
        fh_top_y = h_top_y - 14.0
        fh_cy = fh_top_y + fh_draw_h * 0.5
        comps["front_hair"]["scale"] = round(fh_scale, 4)
        comps["front_hair"]["canvas_center"] = [500.0, round(fh_cy, 1)]
        comps["front_hair"]["z_index"] = 62

        # 4. Side Hair & Back Hair (Aligned to Front Hair crown)
        shw, shh = _sz("side_hair", 760, 960)
        sh_scale = min((fh_draw_w * 1.06) / shw, 295.0 / shh)
        sh_draw_h = shh * sh_scale
        comps["side_hair"]["scale"] = round(sh_scale, 4)
        comps["side_hair"]["canvas_center"] = [500.0, round(fh_top_y + 10.0 + sh_draw_h * 0.5, 1)]
        comps["side_hair"]["z_index"] = 58

        bhw, bhh = _sz("back_hair", 1050, 1150)
        bh_scale = min(325.0 / bhw, 335.0 / bhh)
        bh_draw_h = bhh * bh_scale
        comps["back_hair"]["scale"] = round(bh_scale, 4)
        comps["back_hair"]["canvas_center"] = [500.0, round(fh_top_y - 4.0 + bh_draw_h * 0.5, 1)]
        comps["back_hair"]["z_index"] = 10

        # 5. Facial Features (Proportional to face_h, excluding neck bottom)
        eow, eoh = _sz("eyes_open", 920, 280)
        eo_scale = min((h_draw_w * 0.68) / eow, 62.0 / eoh)
        eyes_cy = h_top_y + face_h * 0.74
        comps["eyes_open"]["scale"] = round(eo_scale, 4)
        comps["eyes_open"]["canvas_center"] = [500.0, round(eyes_cy, 1)]
        comps["eyes_open"]["z_index"] = 50

        ecw, ech = _sz("eyes_closed", 920, 140)
        ec_scale = (h_draw_w * 0.68) / ecw
        comps["eyes_closed"]["scale"] = round(ec_scale, 4)
        comps["eyes_closed"]["canvas_center"] = [500.0, round(eyes_cy, 1)]
        comps["eyes_closed"]["z_index"] = 51

        ebw, ebh = _sz("eyebrows", 840, 85)
        eb_scale = min((h_draw_w * 0.66) / ebw, 36.0 / ebh)
        comps["eyebrows"]["scale"] = round(eb_scale, 4)
        comps["eyebrows"]["canvas_center"] = [500.0, round(h_top_y + face_h * 0.60, 1)]
        comps["eyebrows"]["z_index"] = 55

        mw, mh = _sz("mouth", 200, 140)
        m_scale = min((h_draw_w * 0.21) / mw, 28.0 / mh)
        comps["mouth"]["scale"] = round(m_scale, 4)
        comps["mouth"]["canvas_center"] = [500.0, round(h_top_y + face_h * 0.89, 1)]
        comps["mouth"]["z_index"] = 42

        # 6. Headwear / Ears / Horns (Anchored into front_hair crown)
        hw_w, hw_h = _sz("headwear_ears", 820, 880)
        hw_scale = min(255.0 / hw_w, 225.0 / hw_h)
        hw_draw_h = hw_h * hw_scale
        comps["headwear_ears"]["scale"] = round(hw_scale, 4)
        comps["headwear_ears"]["canvas_center"] = [500.0, round(fh_top_y + hw_draw_h * 0.34, 1)]
        comps["headwear_ears"]["z_index"] = 68

        # 7. Left & Right Arms (Shoulder-Cap Pixel Locked to Torso Shoulder Sockets!)
        alw, alh = _sz("arm_left", 580, 980)
        al_scale = min(145.0 / alw, 225.0 / alh)
        al_draw_w, al_draw_h = alw * al_scale, alh * al_scale
        if "arm_left" in parts_data and "image" in parts_data["arm_left"]:
            (sh_nx_L, sh_ny_L), _ = _find_arm_anchors(parts_data["arm_left"]["image"], is_left=True)
        else:
            sh_nx_L, sh_ny_L = 0.85, 0.14
        al_cx = sh_socket_L_x + (0.5 - sh_nx_L) * al_draw_w
        al_cy = sh_socket_y + (0.5 - sh_ny_L) * al_draw_h
        comps["arm_left"]["scale"] = round(al_scale, 4)
        comps["arm_left"]["canvas_center"] = [round(al_cx, 1), round(al_cy, 1)]
        comps["arm_left"]["pivot"] = [round(sh_nx_L, 3), round(sh_ny_L, 3)]
        comps["arm_left"]["z_index"] = 24

        arw, arh = _sz("arm_right", 650, 720)
        ar_scale = min(165.0 / arw, 210.0 / arh)
        ar_draw_w, ar_draw_h = arw * ar_scale, arh * ar_scale
        if "arm_right" in parts_data and "image" in parts_data["arm_right"]:
            (sh_nx_R, sh_ny_R), (hand_nx_R, hand_ny_R) = _find_arm_anchors(parts_data["arm_right"]["image"], is_left=False)
        else:
            sh_nx_R, sh_ny_R = 0.14, 0.16
            hand_nx_R, hand_ny_R = 0.88, 0.55
        ar_cx = sh_socket_R_x + (0.5 - sh_nx_R) * ar_draw_w
        ar_cy = sh_socket_y + (0.5 - sh_ny_R) * ar_draw_h
        comps["arm_right"]["scale"] = round(ar_scale, 4)
        comps["arm_right"]["canvas_center"] = [round(ar_cx, 1), round(ar_cy, 1)]
        comps["arm_right"]["pivot"] = [round(sh_nx_R, 3), round(sh_ny_R, 3)]
        comps["arm_right"]["z_index"] = 25

        # 8. Hand Prop (Locked to Right Hand Extremity!)
        hand_stage_x = (ar_cx - ar_draw_w * 0.5) + hand_nx_R * ar_draw_w
        hand_stage_y = (ar_cy - ar_draw_h * 0.5) + hand_ny_R * ar_draw_h
        pw_p, ph_p = _sz("hand_prop_effect", 620, 880)
        p_scale = min(145.0 / pw_p, 165.0 / ph_p)
        comps["hand_prop_effect"]["scale"] = round(p_scale, 4)
        comps["hand_prop_effect"]["canvas_center"] = [round(hand_stage_x + 6.0, 1), round(hand_stage_y - 12.0, 1)]
        comps["hand_prop_effect"]["z_index"] = 72

        # 9. Skirt Lower (Waist top locks to torso waist at 52% of torso height)
        skw, skh = _sz("skirt_lower", 1000, 800)
        sk_scale = min(315.0 / skw, 215.0 / skh)
        sk_draw_h = skh * sk_scale
        sk_top_y = t_top_y + t_draw_h * 0.58
        sk_cy = sk_top_y + sk_draw_h * 0.5
        sk_bot_y = sk_top_y + sk_draw_h
        comps["skirt_lower"]["scale"] = round(sk_scale, 4)
        comps["skirt_lower"]["canvas_center"] = [500.0, round(sk_cy, 1)]
        comps["skirt_lower"]["z_index"] = 32

        # 10. Legs Stockings (Tucked under skirt hem)
        lw, lh = _sz("legs_stockings", 620, 1000)
        l_scale = min(235.0 / lw, 385.0 / lh)
        l_draw_h = lh * l_scale
        l_top_y = sk_bot_y - 52.0
        comps["legs_stockings"]["scale"] = round(l_scale, 4)
        comps["legs_stockings"]["canvas_center"] = [500.0, round(l_top_y + l_draw_h * 0.5, 1)]
        comps["legs_stockings"]["z_index"] = 15

        # 11. Back Tail / Wings (Centered behind waist/pelvis)
        btw, bth = _sz("back_tail_wings", 1000, 950)
        bt_scale = min(510.0 / btw, 465.0 / bth)
        comps["back_tail_wings"]["scale"] = round(bt_scale, 4)
        comps["back_tail_wings"]["canvas_center"] = [504.0, round(sk_top_y + 45.0, 1)]
        comps["back_tail_wings"]["z_index"] = 5

    return calibrated



def sanitize_custom_motions(raw_motions: Any) -> List[Dict[str, Any]]:
    """
    Validate and normalize LLM-generated custom_motions so every motion has valid
    parameter curves that can be compiled into .motion3.json and played on stage.
    """
    if not isinstance(raw_motions, list) or not raw_motions:
        return copy.deepcopy(DEFAULT_CUSTOM_MOTIONS)

    valid_motions: List[Dict[str, Any]] = []
    for idx, m in enumerate(raw_motions[:6]):
        if not isinstance(m, dict):
            continue
        raw_id = str(m.get("id") or f"custom_action_{idx + 1}").strip()
        clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", raw_id).strip("_").lower()
        if not clean_id:
            clean_id = f"custom_action_{idx + 1}"
        if not clean_id.startswith("custom_"):
            clean_id = f"custom_{clean_id}"

        label = str(m.get("label") or m.get("name") or f"✨ 专属动作 {idx + 1}").strip()
        if not label.startswith("✨"):
            label = f"✨ {label}"

        duration = float(m.get("duration") or 2.4)
        duration = max(1.0, min(8.0, duration))
        loop = bool(m.get("loop", False))
        dialogue = str(
            m.get("dialogue")
            or f"指挥官，这是为你展示的专属动作【{label.replace('✨', '').strip()}】哦~！"
        ).strip()

        raw_curves = m.get("curves")
        clean_curves: Dict[str, List[List[float]]] = {}
        if isinstance(raw_curves, dict):
            for param_id, pts in raw_curves.items():
                if not isinstance(pts, list) or len(pts) < 2:
                    continue
                parsed_pts: List[List[float]] = []
                for pt in pts:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        try:
                            t = round(max(0.0, min(duration, float(pt[0]))), 3)
                            v = round(float(pt[1]), 3)
                            parsed_pts.append([t, v])
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(pt, dict) and "t" in pt and "v" in pt:
                        try:
                            t = round(max(0.0, min(duration, float(pt["t"]))), 3)
                            v = round(float(pt["v"]), 3)
                            parsed_pts.append([t, v])
                        except (ValueError, TypeError):
                            pass
                if len(parsed_pts) >= 2:
                    parsed_pts.sort(key=lambda x: x[0])
                    default_rest = 1.0 if param_id in ("ParamEyeLOpen", "ParamEyeROpen") else 0.0
                    if parsed_pts[0][0] > 0.05:
                        parsed_pts.insert(0, [0.0, default_rest])
                    if parsed_pts[-1][0] < duration - 0.05:
                        parsed_pts.append([round(duration, 3), default_rest])
                    clean_curves[param_id] = parsed_pts

        if not clean_curves:
            clean_curves = copy.deepcopy(DEFAULT_CUSTOM_MOTIONS[idx % len(DEFAULT_CUSTOM_MOTIONS)]["curves"])

        valid_motions.append({
            "id": clean_id,
            "label": label,
            "duration": round(duration, 2),
            "loop": loop,
            "dialogue": dialogue,
            "curves": clean_curves,
        })

    return valid_motions if valid_motions else copy.deepcopy(DEFAULT_CUSTOM_MOTIONS)


def build_dual_inspection_sheet(
    parts_data: Dict[str, Dict[str, Any]],
    calibrated_rig: Dict[str, Any],
    output_path: Optional[str] = None,
    grid: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    contact_uri, parts_summary = build_matted_contact_sheet(parts_data, output_path=output_path, grid=grid)
    try:
        # Render assembled preview next to the contact sheet so gemini-3.8-flash visually inspects the actual assembly
        stage = Image.new("RGBA", (1000, 1000), (242, 245, 250, 255))
        comps = calibrated_rig.get("components", {})
        for name, cfg in sorted(comps.items(), key=lambda kv: kv[1].get("z_index", 0)):
            if name == "eyes_closed" or name not in parts_data:
                continue
            pimg = parts_data[name]["image"]
            sc = float(cfg.get("scale", 1.0))
            cx, cy = cfg.get("canvas_center", [500, 500])
            sw = max(1, int(pimg.width * sc))
            sh = max(1, int(pimg.height * sc))
            resized = pimg.resize((sw, sh), Image.Resampling.LANCZOS)
            stage.alpha_composite(resized, (int(cx - sw / 2), int(cy - sh / 2)))

        raw_b64 = contact_uri.split(",", 1)[-1]
        grid_sheet = Image.open(io.BytesIO(base64.b64decode(raw_b64))).convert("RGB")
        gh = grid_sheet.height
        stage_thumb = stage.convert("RGB").resize((gh, gh), Image.Resampling.LANCZOS)
        dual = Image.new("RGB", (grid_sheet.width + gh, gh), (242, 245, 250))
        dual.paste(grid_sheet, (0, 0))
        dual.paste(stage_thumb, (grid_sheet.width, 0))
        d = ImageDraw.Draw(dual)
        d.text((grid_sheet.width + 12, 10), "Assembled Preview (1000x1000 Stage)", fill=(15, 23, 42))
        buf = io.BytesIO()
        dual.save(buf, format="JPEG", quality=86)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8"), parts_summary
    except Exception:
        return contact_uri, parts_summary


class GeminiRigger:
    """
    Uses gemini-3.8-flash multimodal capabilities to inspect the sliced & matted
    9-part (3x3) or 16-part (4x4) transparent components + user prompt in ONE unified call, returning:
      1. Calibrated anatomical rigging (components)
      2. Custom motion keyframe curves & algorithms (custom_motions)
      3. Pendulum physics parameters (physics_profile)
      4. Secretary dialogues (dialogues)
    """

    def __init__(self, client: HrioClient):
        self.client = client

    def rig(
        self,
        grid_image_path: str,
        character_hint: str = "Azur Lane anime girl",
        model: str = "gemini-3.8-flash",
        parts_data: Optional[Dict[str, Dict[str, Any]]] = None,
        matted_sheet_path: Optional[str] = None,
        grid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified Stage 3 Multimodal Call:
        Sends the sliced/matted contact sheet (3x3 9-part or 4x4 16-part) + cropped part dimensions + user prompt
        to gemini-3.8-flash (reasoning_effort='low') to generate rigging, physics, dialogues,
        and custom motion keyframe curves in a single fast call.
        """
        grid_mode = _detect_grid_mode(parts_data, grid)
        comp_order = COMPONENT_ORDER_4X4 if grid_mode == "4x4" else COMPONENT_ORDER_3X3
        base_rig = DEFAULT_RIG_CONFIG_4X4 if grid_mode == "4x4" else DEFAULT_RIG_CONFIG_3X3

        parts_summary: Dict[str, Any] = {}
        image_input = grid_image_path

        calibrated_rig = calibrate_anatomical_rig(base_rig, parts_data=parts_data, grid=grid_mode)
        if parts_data:
            try:
                contact_uri, parts_summary = build_dual_inspection_sheet(
                    parts_data,
                    calibrated_rig=calibrated_rig,
                    output_path=matted_sheet_path,
                    grid=grid_mode,
                )
                image_input = contact_uri
            except Exception as e:
                print(f"[GeminiRigger] Contact sheet build warning ({e}), using raw grid image.")

        dims_json = json.dumps(parts_summary, ensure_ascii=False) if parts_summary else "{}"
        comp_list_str = ", ".join(comp_order)

        unified_prompt = (
            f"You are the Lead Live2D Cubism 3 Technical Artist & Motion Designer for Azur Lane (banerwei_3 architecture).\n"
            f"You are given:\n"
            f"1) The sliced & background-matted {grid_mode} ({len(comp_order)}-component) Live2D contact sheet image.\n"
            f"2) Exact cropped pixel dimensions of each matted component: {dims_json}\n"
            f"3) The user's original prompt & action request: \"{character_hint}\"\n\n"
            f"Generate a SINGLE unified JSON object containing:\n"
            f"1. 'character_name': snake_case identifier.\n"
            f"2. 'archetype': Personality archetype description.\n"
            f"3. 'components': Rigging anchors on a 1000x1000 canvas for ({comp_list_str}), each with 'canvas_center' [cx, cy] and 'scale'.\n"
            f"4. 'physics_profile': {{'hair_mobility': 0.90, 'hair_delay': 0.72, 'skirt_mobility': 0.88, 'hair_front_damping': 0.86, 'hair_side_damping': 0.84, 'hair_back_damping': 0.82, 'skirt_sway_scale': 1.18}}\n"
            f"5. 'dialogues': Chinese Azur Lane secretary voice lines for keys: login, home, main_1, main_2, main_3, touch_head, touch_body, touch_special, wedding, mail, mission, mission_complete, complete.\n"
            f"6. 'custom_motions': An array of 2 to 3 bespoke Live2D motions with keyframe curves! "
            f"IMPORTANT: If the user prompt mentions any specific actions, poses, emotions, or motions (e.g. jump, wave, shy, angry, dance, wink, salute, bow, cheer, tail wag, ear twitch, magic cast, etc.), "
            f"you MUST create custom_motions implementing those exact requested actions! Even if the user only describes a character, design 2 signature custom motions matching their personality.\n"
            f"Each item in 'custom_motions' MUST follow this schema:\n"
            f"{{\n"
            f"  \"id\": \"custom_<short_english_slug>\",\n"
            f"  \"label\": \"✨ <Chinese action button name, 4-7 chars>\",\n"
            f"  \"duration\": 2.4,\n"
            f"  \"loop\": false,\n"
            f"  \"dialogue\": \"<Matching Chinese voice line spoken during this action>\",\n"
            f"  \"curves\": {{\n"
            f"    \"ParamAngleX\": [[0.0, 0.0], [0.6, 12.0], [1.4, -10.0], [2.4, 0.0]],\n"
            f"    \"ParamAngleY\": [[0.0, 0.0], [0.5, 14.0], [1.2, -8.0], [2.4, 0.0]],\n"
            f"    \"ParamAngleZ\": [[0.0, 0.0], [0.7, -8.0], [1.6, 8.0], [2.4, 0.0]],\n"
            f"    \"ParamBodyAngleX\": [[0.0, 0.0], [0.7, 8.0], [1.6, -8.0], [2.4, 0.0]],\n"
            f"    \"ParamBodyAngleY\": [[0.0, 0.0], [0.4, 15.0], [0.8, -6.0], [1.2, 15.0], [2.4, 0.0]],\n"
            f"    \"ParamArmLAngle\": [[0.0, 0.0], [0.5, -25.0], [1.2, 12.0], [2.4, 0.0]],\n"
            f"    \"ParamArmRAngle\": [[0.0, 0.0], [0.5, 28.0], [1.2, -14.0], [2.4, 0.0]],\n"
            f"    \"ParamEyeLOpen\": [[0.0, 1.0], [0.3, 0.0], [1.5, 0.0], [1.9, 1.0], [2.4, 1.0]],\n"
            f"    \"ParamEyeROpen\": [[0.0, 1.0], [0.3, 0.0], [1.5, 0.0], [1.9, 1.0], [2.4, 1.0]],\n"
            f"    \"ParamEyeLSmile\": [[0.0, 0.0], [0.3, 1.0], [1.5, 1.0], [1.9, 0.0], [2.4, 0.0]],\n"
            f"    \"ParamMouthOpenY\": [[0.0, 0.0], [0.4, 0.9], [0.9, 0.2], [1.4, 0.85], [2.4, 0.0]],\n"
            f"    \"ParamCheek\": [[0.0, 0.0], [0.3, 1.0], [1.9, 1.0], [2.4, 0.0]],\n"
            f"    \"ParamEmotionHeart\": [[0.0, 0.0], [0.3, 1.0], [1.8, 1.0], [2.4, 0.0]]\n"
            f"  }}\n"
            f"}}\n"
            f"Design each motion using 4-Phase Hierarchical Skeletal Choreography (0~15% Anticipation -> 15~55% Main Action -> 55~80% Secondary Overshoot -> 80~100% Smooth Settle).\n"
            f"(Parameter ranges: ParamAngleX/Y/Z [-30, 30], ParamBodyAngleX/Y/Z [-20, 20], ParamArmLAngle/RAngle [-40, 40], "
            f"ParamElbowLAngle/RAngle [-55, 55] (forearm hinge bend), ParamTailWag [-30, 30] (S-curve tail wave), ParamEarTwitch [-20, 20] (ear spring bounce), "
            f"ParamSkirtSway [-20, 20], ParamEyeBallX/Y [-1, 1], ParamMouthForm [-1, 1], "
            f"ParamEyeLOpen/ROpen [0, 1], ParamEyeLSmile/RSmile [0, 1], ParamMouthOpenY [0, 1], ParamCheek [0, 1], "
            f"ParamEmotionHeart/Star/Exclaim/Sweat [0, 1]).\n"
            f"Return strictly valid JSON."
        )

        raw_config: Dict[str, Any] = copy.deepcopy(base_rig)
        action_spec: Dict[str, Any] = copy.deepcopy(DEFAULT_ACTION_SPEC)

        try:
            raw_resp = self.client.multimodal_chat(
                prompt=unified_prompt,
                image_path_or_url=image_input,
                model=model,
                response_format_json=True,
                reasoning_effort="low",
            )
            data = json.loads(raw_resp)
            if isinstance(data, dict):
                if "character_name" in data and data["character_name"]:
                    raw_config["character_name"] = data["character_name"]
                if "components" in data and isinstance(data["components"], dict):
                    raw_config["components"] = data["components"]
                if "archetype" in data and data["archetype"]:
                    action_spec["archetype"] = data["archetype"]
                if "dialogues" in data and isinstance(data["dialogues"], dict):
                    action_spec["dialogues"].update(data["dialogues"])
                if "physics_profile" in data and isinstance(data["physics_profile"], dict):
                    action_spec["physics_profile"].update(data["physics_profile"])
                if "custom_motions" in data:
                    action_spec["custom_motions"] = sanitize_custom_motions(data["custom_motions"])
        except Exception as e:
            print(f"[GeminiRigger] Multimodal unified rig note ({e}), applying calibrated defaults...")

        for cm in action_spec.get("custom_motions", []):
            if cm.get("id") and cm.get("dialogue"):
                action_spec["dialogues"][cm["id"]] = cm["dialogue"]
                action_spec["dialogues"][cm["id"].lower()] = cm["dialogue"]

        calibrated_rig = calibrate_anatomical_rig(raw_config, parts_data=parts_data, grid=grid_mode)
        if isinstance(raw_config.get("visual_fine_tune"), dict):
            for pname, adj in raw_config["visual_fine_tune"].items():
                if pname in calibrated_rig["components"] and isinstance(adj, dict):
                    dx = max(-14.0, min(14.0, float(adj.get("dx", 0.0) or 0.0)))
                    dy = max(-14.0, min(14.0, float(adj.get("dy", 0.0) or 0.0)))
                    sm = max(0.92, min(1.08, float(adj.get("scale_mult", 1.0) or 1.0)))
                    c_xy = calibrated_rig["components"][pname]["canvas_center"]
                    calibrated_rig["components"][pname]["canvas_center"] = [round(c_xy[0] + dx, 1), round(c_xy[1] + dy, 1)]
                    calibrated_rig["components"][pname]["scale"] = round(calibrated_rig["components"][pname]["scale"] * sm, 4)
        calibrated_rig["action_spec"] = action_spec
        calibrated_rig["parts_summary"] = parts_summary
        calibrated_rig["grid"] = grid_mode
        return calibrated_rig
