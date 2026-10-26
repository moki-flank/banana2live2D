# -*- coding: utf-8 -*-
"""
Gemini Multimodal Live2D Rigger & Unified Action/Motion Generator (Azur Lane / banerwei_3 Architecture).
Strictly follows the 3-stage pipeline:
  Stage 1: gemini-nano-banana-2.1 generates the 3x3 component sheet.
  Stage 2: Adaptive Valley Slicing + Exterior BFS Matting extracts 9 transparent RGBA parts.
  Stage 3: Unified Multimodal Call to gemini-3.8-flash with BOTH:
           (a) The sliced & matted 9-part transparent contact sheet + cropped pixel dimensions
           (b) The user's original prompt (including any custom motion/action requests)
           Returns in ONE unified JSON:
             - components (anatomical rigging anchors, scales, pivots, z_index)
             - custom_motions (parameterized keyframe curves for user-requested & character-specific motions)
             - physics_profile (4-vertex pendulum physics parameters)
             - dialogues (secretary interaction lines + custom motion voice lines)
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

COMPONENT_ORDER = [
    "back_hair", "head_base", "front_hair",
    "eyes_open", "eyes_closed", "mouth",
    "body_torso", "arm_left", "arm_right",
]

DEFAULT_RIG_CONFIG: Dict[str, Any] = {
    "character_name": "banerwei_sailor",
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


def build_matted_contact_sheet(
    parts_data: Dict[str, Dict[str, Any]],
    output_path: Optional[str] = None,
    sheet_size: int = 600,
) -> Tuple[str, Dict[str, Any]]:
    """
    Composite the 9 sliced & BFS-matted transparent components into a clean 3x3 contact sheet
    so gemini-3.8-flash can inspect the exact matted parts alongside their pixel dimensions.
    Returns: (data_uri, parts_summary_dict)
    """
    cell_size = sheet_size // 3
    sheet = Image.new("RGBA", (sheet_size, sheet_size), (242, 245, 250, 255))
    draw = ImageDraw.Draw(sheet)

    # Subtle grid lines separating the 9 matted cells
    for i in range(1, 3):
        draw.line([(i * cell_size, 0), (i * cell_size, sheet_size)], fill=(205, 213, 225, 255), width=2)
        draw.line([(0, i * cell_size), (sheet_size, i * cell_size)], fill=(205, 213, 225, 255), width=2)

    parts_summary: Dict[str, Any] = {}
    for idx, name in enumerate(COMPONENT_ORDER):
        r, c = divmod(idx, 3)
        x0, y0 = c * cell_size, r * cell_size
        pdata = parts_data.get(name)
        if not pdata or "image" not in pdata:
            continue
        pimg: Image.Image = pdata["image"]
        pw, ph = pimg.size
        parts_summary[name] = {
            "cell": [r, c],
            "cropped_size": [pw, ph],
            "bbox": list(pdata.get("bbox", (0, 0, pw, ph))),
        }

        # Fit matted part inside cell with padding
        pad = 16
        avail = cell_size - pad * 2
        scale = min(avail / max(1, pw), avail / max(1, ph))
        tw = max(1, int(pw * scale))
        th = max(1, int(ph * scale))
        thumb = pimg.resize((tw, th), Image.Resampling.LANCZOS)
        px = x0 + (cell_size - tw) // 2
        py = y0 + (cell_size - th) // 2
        sheet.alpha_composite(thumb, (px, py))
        draw.text((x0 + 6, y0 + 4), f"{name} ({pw}x{ph})", fill=(30, 41, 59, 255))

    rgb_sheet = sheet.convert("RGB")
    if output_path:
        rgb_sheet.save(output_path, format="JPEG", quality=88)

    buf = io.BytesIO()
    rgb_sheet.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}", parts_summary


def calibrate_anatomical_rig(
    rig_config: Dict[str, Any],
    parts_data: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Ensure Azur Lane (banerwei_3) anatomical joints (neck-to-collar seam,
    hollow bangs over face, eyes/mouth inside face, armless torso shoulder sockets)
    lock to exact calibrated coordinates so components never float or drift.
    """
    calibrated = copy.deepcopy(DEFAULT_RIG_CONFIG)
    if "character_name" in rig_config and rig_config["character_name"]:
        calibrated["character_name"] = rig_config["character_name"]

    raw_comps = rig_config.get("components", {})

    bounds = {
        "back_hair":  {"cx": (480, 520), "cy": (235, 285), "scale": (0.72, 0.96)},
        "head_base":  {"cx": (490, 510), "cy": (242, 270), "scale": (0.70, 0.86)},
        "front_hair": {"cx": (490, 510), "cy": (230, 260), "scale": (0.74, 0.92)},
        "eyes_open":  {"cx": (492, 508), "cy": (262, 282), "scale": (0.36, 0.52)},
        "eyes_closed":{"cx": (492, 508), "cy": (262, 282), "scale": (0.36, 0.52)},
        "mouth":      {"cx": (494, 506), "cy": (305, 324), "scale": (0.20, 0.34)},
        "body_torso": {"cx": (485, 515), "cy": (615, 655), "scale": (1.05, 1.25)},
        "arm_left":   {"cx": (405, 438), "cy": (428, 460), "scale": (0.52, 0.68)},
        "arm_right":  {"cx": (552, 588), "cy": (385, 420), "scale": (0.55, 0.72)},
    }

    for name, default_comp in calibrated["components"].items():
        if name in raw_comps and isinstance(raw_comps[name], dict):
            rc = raw_comps[name]
            b = bounds.get(name)
            if b:
                if isinstance(rc.get("canvas_center"), list) and len(rc["canvas_center"]) == 2:
                    cx = max(b["cx"][0], min(b["cx"][1], float(rc["canvas_center"][0])))
                    cy = max(b["cy"][0], min(b["cy"][1], float(rc["canvas_center"][1])))
                    default_comp["canvas_center"] = [round(cx, 1), round(cy, 1)]
                if isinstance(rc.get("scale"), (int, float)):
                    sc = max(b["scale"][0], min(b["scale"][1], float(rc["scale"])))
                    default_comp["scale"] = round(sc, 3)

    if parts_data:
        def _aspect_adjust(part_name: str, target_w: float, target_h: float, blend: float = 0.35):
            pinfo = parts_data.get(part_name)
            if not pinfo or "size" not in pinfo:
                return
            pw, ph = pinfo["size"]
            if pw <= 10 or ph <= 10:
                return
            ideal_scale = min(target_w / pw, target_h / ph)
            base_scale = calibrated["components"][part_name]["scale"]
            merged = base_scale * (1.0 - blend) + ideal_scale * blend
            b = bounds[part_name]["scale"]
            calibrated["components"][part_name]["scale"] = round(max(b[0], min(b[1], merged)), 3)

        _aspect_adjust("head_base", 220, 260)
        _aspect_adjust("front_hair", 255, 245)
        _aspect_adjust("back_hair", 285, 285)
        _aspect_adjust("eyes_open", 140, 62)
        _aspect_adjust("eyes_closed", 140, 58)
        _aspect_adjust("mouth", 45, 30)
        _aspect_adjust("body_torso", 345, 665)
        _aspect_adjust("arm_left", 130, 215)
        _aspect_adjust("arm_right", 190, 210)

    calibrated["components"]["eyes_closed"]["canvas_center"] = list(
        calibrated["components"]["eyes_open"]["canvas_center"]
    )
    calibrated["components"]["eyes_closed"]["scale"] = calibrated["components"]["eyes_open"]["scale"]

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


class GeminiRigger:
    """
    Uses gemini-3.8-flash multimodal capabilities to inspect the sliced & matted
    9-part transparent components + user prompt in ONE unified call, returning:
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
    ) -> Dict[str, Any]:
        """
        Unified Stage 3 Multimodal Call:
        Sends the sliced/matted 9-part contact sheet + cropped part dimensions + user prompt
        to gemini-3.8-flash (reasoning_effort='low') to generate rigging, physics, dialogues,
        and custom motion keyframe curves in a single fast call.
        """
        image_input = grid_image_path
        parts_summary: Dict[str, Any] = {}

        if parts_data:
            matted_uri, parts_summary = build_matted_contact_sheet(
                parts_data=parts_data,
                output_path=matted_sheet_path,
            )
            image_input = matted_sheet_path if (matted_sheet_path and os.path.isfile(matted_sheet_path)) else matted_uri

        parts_json_str = json.dumps(parts_summary, ensure_ascii=False) if parts_summary else "{}"

        unified_prompt = (
            f"You are an expert Live2D Cubism 3 Technical Artist & Motion Designer (Azur Lane / banerwei_3 standard).\n"
            f"We have completed Stage 1 (3x3 component sheet generation) and Stage 2 (Adaptive Valley Slicing + BFS Matting).\n"
            f"Attached is the MATTED 9-PART COMPONENT SHEET along with the cropped pixel dimensions of each part:\n"
            f"{parts_json_str}\n\n"
            f"USER PROMPT & ACTION REQUESTS:\n"
            f"\"{character_hint}\"\n\n"
            f"Your task is to analyze BOTH the sliced/matted components image AND the user prompt, and return a single unified JSON object containing:\n"
            f"1. 'character_name' & 'archetype': A fitting name and archetype description.\n"
            f"2. 'components': Anatomical assembly calibration on a 1000x1000 canvas for the 9 parts "
            f"(back_hair, head_base, front_hair, eyes_open, eyes_closed, mouth, body_torso, arm_left, arm_right), "
            f"each with 'z_index', 'canvas_center' [cx, cy], 'scale', and 'pivot' [px, py].\n"
            f"   Reference coordinates: back_hair [500,260] scale 0.84; head_base [500,256] scale 0.78; "
            f"arm_left [422,444] scale 0.60; arm_right [570,400] scale 0.64; body_torso [500,635] scale 1.15; "
            f"mouth [500,314] scale 0.27; eyes_open [500,272] scale 0.44; eyes_closed [500,272] scale 0.44; front_hair [500,244] scale 0.82.\n"
            f"3. 'physics_profile': {{'hair_mobility': 0.90, 'hair_delay': 0.72, 'skirt_mobility': 0.85, 'hair_front_damping': 0.86, 'hair_side_damping': 0.84, 'hair_back_damping': 0.82, 'skirt_sway_scale': 1.15}}\n"
            f"4. 'dialogues': Chinese Azur Lane secretary voice lines for keys: login, home, main_1, main_2, main_3, touch_head, touch_body, touch_special, wedding, mail, mission, mission_complete, complete.\n"
            f"5. 'custom_motions': An array of 2 to 3 bespoke Live2D motions with keyframe curves! "
            f"IMPORTANT: If the user prompt mentions any specific actions, poses, emotions, or motions (e.g. jump, wave, shy, angry, dance, wink, salute, bow, cheer, etc.), "
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
            f"(Parameter ranges: ParamAngleX/Y/Z [-30, 30], ParamBodyAngleX/Y/Z [-20, 20], ParamArmLAngle/RAngle [-40, 40], "
            f"ParamEyeLOpen/ROpen [0, 1], ParamEyeLSmile/RSmile [0, 1], ParamMouthOpenY [0, 1], ParamCheek [0, 1], "
            f"ParamEmotionHeart/Star/Exclaim/Sweat [0, 1]).\n"
            f"Return strictly valid JSON."
        )

        raw_config: Dict[str, Any] = copy.deepcopy(DEFAULT_RIG_CONFIG)
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

        # Register custom motion dialogues into action_spec["dialogues"] for seamless lookup
        for cm in action_spec.get("custom_motions", []):
            if cm.get("id") and cm.get("dialogue"):
                action_spec["dialogues"][cm["id"]] = cm["dialogue"]
                action_spec["dialogues"][cm["id"].lower()] = cm["dialogue"]

        calibrated_rig = calibrate_anatomical_rig(raw_config, parts_data=parts_data)
        calibrated_rig["action_spec"] = action_spec
        calibrated_rig["parts_summary"] = parts_summary
        return calibrated_rig
