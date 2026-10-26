# -*- coding: utf-8 -*-
"""
Azur Lane (banerwei_3 Standard) Live2D Cubism 3/4 Motion, Physics & DisplayInfo Builder.
Generates:
  - <name>.cdi3.json (Cubism 3 DisplayInfo with Chinese/Japanese readable Parameter & Part names)
  - <name>.physics3.json (Multi-pendulum 4-vertex physics chains modeled after banerwei_3.physics3.json)
  - motions/*.motion3.json (Complete Azur Lane interactive motion suite + classic motions)
"""

import os
import json
from typing import Dict, Any, List, Tuple, Optional


def build_cdi3_json(output_path: str, character_name: str = "banano_char") -> str:
    """
    Generate Cubism 3 DisplayInfo (.cdi3.json) modeled directly after Azur Lane's banerwei_3.cdi3.json.
    """
    cdi3 = {
        "Version": 3,
        "Parameters": [
            {"Id": "All_Angle", "GroupId": "", "Name": "总体角度"},
            {"Id": "All_Size", "GroupId": "", "Name": "总体大小"},
            {"Id": "All_X", "GroupId": "", "Name": "总体左右"},
            {"Id": "All_Y", "GroupId": "", "Name": "总体上下"},
            {"Id": "ParamAngleX", "GroupId": "", "Name": "角度 X"},
            {"Id": "ParamAngleY", "GroupId": "", "Name": "角度 Y"},
            {"Id": "ParamAngleZ", "GroupId": "", "Name": "角度 Z"},
            {"Id": "ParamEyeLOpen", "GroupId": "", "Name": "左目　開閉"},
            {"Id": "ParamEyeLSmile", "GroupId": "", "Name": "左目　微笑み"},
            {"Id": "ParamEyeROpen", "GroupId": "", "Name": "右目　開閉"},
            {"Id": "ParamEyeRSmile", "GroupId": "", "Name": "右目　微笑み"},
            {"Id": "ParamEyeBallX", "GroupId": "", "Name": "目玉 X"},
            {"Id": "ParamEyeBallY", "GroupId": "", "Name": "目玉 Y"},
            {"Id": "ParamBrowLY", "GroupId": "", "Name": "左眉　上下"},
            {"Id": "ParamBrowRY", "GroupId": "", "Name": "右眉　上下"},
            {"Id": "ParamMouthForm", "GroupId": "", "Name": "口变形"},
            {"Id": "ParamMouthOpenY", "GroupId": "", "Name": "口开关"},
            {"Id": "ParamCheek", "GroupId": "", "Name": "脸部红切换"},
            {"Id": "ParamBodyAngleX", "GroupId": "", "Name": "体の回転　X"},
            {"Id": "ParamBodyAngleY", "GroupId": "", "Name": "身体 Y"},
            {"Id": "ParamBodyAngleZ", "GroupId": "", "Name": "身体 Z"},
            {"Id": "ParamBreath", "GroupId": "", "Name": "呼吸"},
            {"Id": "ParamArmLAngle", "GroupId": "", "Name": "左手动画"},
            {"Id": "ParamArmRAngle", "GroupId": "", "Name": "右手动画"},
            {"Id": "ArmRAy", "GroupId": "", "Name": "右肩上下"},
            {"Id": "ParamHairFront", "GroupId": "", "Name": "刘海L1"},
            {"Id": "ParamHairSide", "GroupId": "", "Name": "R刘海1"},
            {"Id": "ParamHairBack", "GroupId": "", "Name": "后发z1"},
            {"Id": "ParamHairTailL", "GroupId": "", "Name": "左辫子物理"},
            {"Id": "ParamHairTailR", "GroupId": "", "Name": "右辫子物理"},
            {"Id": "ParamSkirtSway", "GroupId": "", "Name": "裙子挤压"},
            {"Id": "ParamRibbonSway", "GroupId": "", "Name": "领结物理"},
            {"Id": "ParamWindA", "GroupId": "", "Name": "风动A"},
            {"Id": "ParamWindB", "GroupId": "", "Name": "风动B"},
            {"Id": "ParamEmotionHeart", "GroupId": "", "Name": "爱心"},
            {"Id": "ParamEmotionStar", "GroupId": "", "Name": "星星"},
            {"Id": "ParamEmotionExclaim", "GroupId": "", "Name": "感叹号"},
            {"Id": "ParamEmotionSweat", "GroupId": "", "Name": "汗_1"},
            {"Id": "ParamRing", "GroupId": "", "Name": "戒指"},
        ],
        "ParameterGroups": [],
        "Parts": [
            {"Id": "Part_Main", "Name": "Main (人物主体)"},
            {"Id": "Part_back_tail_wings", "Name": "尾巴 / 翅膀 / 后背大蝴蝶结"},
            {"Id": "Part_back_hair", "Name": "后发扎 / 辫子L / 辫子R"},
            {"Id": "Part_legs_stockings", "Name": "双腿 / 丝袜 / 鞋靴"},
            {"Id": "Part_head_base", "Name": "头 / 脸部 / 脖子"},
            {"Id": "Part_front_hair", "Name": "前发MF / 前发L / 前发R"},
            {"Id": "Part_side_hair", "Name": "两侧垂发 / 左右鬓发"},
            {"Id": "Part_eyes_open", "Name": "默认睁眼"},
            {"Id": "Part_eyes_closed", "Name": "闭眼微笑"},
            {"Id": "Part_eyebrows", "Name": "独立双眉 / 腮红"},
            {"Id": "Part_mouth", "Name": "口腔 / 口开默认 / 口2默认"},
            {"Id": "Part_body_torso", "Name": "上半身躯干 / 胸衣 / 领结"},
            {"Id": "Part_skirt_lower", "Name": "百褶裙摆 / 围裙下摆"},
            {"Id": "Part_arm_left", "Name": "手臂L / 袖子L / 左手"},
            {"Id": "Part_arm_right", "Name": "手臂R / 袖子R / 右手"},
            {"Id": "Part_headwear_ears", "Name": "兽耳 / 猫耳 / 头饰发箍"},
            {"Id": "Part_hand_prop_effect", "Name": "手持道具 / 特效挂件"},
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cdi3, f, ensure_ascii=False, indent=2)
    return output_path


def build_motion3_json(
    name: str,
    duration: float,
    fps: float = 60.0,
    loop: bool = True,
    curves: Optional[Dict[str, List[Tuple[float, float]]]] = None,
) -> Dict[str, Any]:
    """
    Build a Live2D Cubism 3 .motion3.json dictionary using smooth Cubic Bezier segments (type 1)
    just like Azur Lane's banerwei_3 motions.
    """
    curves = curves or {}
    curve_list = []
    total_segments = 0
    total_points = 0

    for param_id, keyframes in curves.items():
        if not keyframes:
            continue
        segments: List[float] = [
            round(float(keyframes[0][0]), 3),
            round(float(keyframes[0][1]), 3),
        ]
        total_points += 1
        for i in range(1, len(keyframes)):
            t0, v0 = float(keyframes[i - 1][0]), float(keyframes[i - 1][1])
            t1, v1 = float(keyframes[i][0]), float(keyframes[i][1])
            dt = t1 - t0
            if dt > 0.08:
                # Cubic Bezier segment (type 1): [1, ct1, cv1, ct2, cv2, t1, v1]
                ct1 = round(t0 + dt * 0.333, 3)
                ct2 = round(t0 + dt * 0.667, 3)
                cv1 = round(v0 + (v1 - v0) * 0.15, 3)
                cv2 = round(v0 + (v1 - v0) * 0.85, 3)
                segments.extend([1, ct1, cv1, ct2, cv2, round(t1, 3), round(v1, 3)])
                total_segments += 1
                total_points += 3
            else:
                # Linear segment (type 0): [0, t1, v1]
                segments.extend([0, round(t1, 3), round(v1, 3)])
                total_segments += 1
                total_points += 1

        curve_list.append({
            "Target": "Parameter",
            "Id": param_id,
            "FadeInTime": -1,
            "FadeOutTime": -1,
            "Segments": segments,
        })

    return {
        "Version": 3,
        "Meta": {
            "Duration": round(float(duration), 3),
            "Fps": float(fps),
            "Loop": loop,
            "AreBeziersRestricted": True,
            "FadeInTime": 0.2,
            "FadeOutTime": 0.2,
            "CurveCount": len(curve_list),
            "TotalSegmentCount": total_segments,
            "TotalPointCount": total_points,
            "UserDataCount": 0,
            "TotalUserDataSize": 0,
        },
        "Curves": curve_list,
    }


def generate_standard_motions(
    output_dir: str,
    llm_choreography: Optional[Dict[str, Any]] = None,
    custom_motions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Generate the complete Azur Lane (banerwei_3) interactive motion library + standard motions.
    Incorporates LLM-generated tempo/amplitude modifiers from gemini-3.8-flash when provided.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths: Dict[str, str] = {}

    choreo = llm_choreography or {}
    energy = float(choreo.get("energy_scale", 1.0))
    energy = max(0.7, min(1.4, energy))

    motions_spec: Dict[str, Dict[str, Any]] = {
        # 1. Azur Lane Idle (待机呼吸 + 微风发丝摆动 + 自然眨眼)
        "idle": {
            "duration": 4.8,
            "loop": True,
            "curves": {
                "ParamBreath": [(0.0, 0.0), (1.2, 0.5), (2.4, 1.0), (3.6, 0.5), (4.8, 0.0)],
                "ParamAngleX": [(0.0, 0.0), (1.2, 4.5 * energy), (2.4, 0.0), (3.6, -4.5 * energy), (4.8, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (1.2, 2.5), (2.4, -2.0), (3.6, 2.0), (4.8, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (1.6, 3.0 * energy), (3.2, -3.0 * energy), (4.8, 0.0)],
                "ParamBodyAngleX": [(0.0, 0.0), (1.6, 2.2), (3.2, -2.2), (4.8, 0.0)],
                "ParamBodyAngleZ": [(0.0, 0.0), (1.6, 1.2), (3.2, -1.2), (4.8, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (2.1, 1.0), (2.22, 0.0), (2.36, 1.0), (4.8, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (2.1, 1.0), (2.22, 0.0), (2.36, 1.0), (4.8, 1.0)],
                "ParamHairFront": [(0.0, -3.5), (1.2, 4.2), (2.4, -3.5), (3.6, 4.2), (4.8, -3.5)],
                "ParamHairBack": [(0.0, -5.0), (1.4, 5.5), (2.6, -5.0), (3.8, 5.5), (4.8, -5.0)],
                "ParamArmLAngle": [(0.0, 0.0), (2.4, 4.0), (4.8, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (2.4, -5.0), (4.8, 0.0)],
            },
        },
        # 2. Azur Lane Login (登录迎宾：元气挥手 + 微笑眨眼 + 欢迎台词)
        "login": {
            "duration": 3.6,
            "loop": False,
            "curves": {
                "ParamAngleX": [(0.0, 0.0), (0.5, -10.0), (1.4, 8.0), (2.5, -4.0), (3.6, 0.0)],
                "ParamAngleY": [(0.0, -6.0), (0.5, 10.0), (1.5, -4.0), (2.6, 6.0), (3.6, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.6, -7.0), (1.6, 6.0), (2.6, -3.0), (3.6, 0.0)],
                "ParamBodyAngleX": [(0.0, -12.0), (0.6, 6.0), (1.8, -4.0), (3.6, 0.0)],
                "ParamBodyAngleY": [(0.0, -5.0), (0.5, 12.0), (1.4, -3.0), (3.6, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.35, 28.0), (0.7, -18.0), (1.05, 28.0), (1.4, -18.0), (1.8, 22.0), (2.4, 0.0), (3.6, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.6, -12.0), (1.5, 6.0), (3.6, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.5, 0.0), (1.2, 0.0), (1.5, 1.0), (3.6, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.5, 0.0), (1.2, 0.0), (1.5, 1.0), (3.6, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.5, 1.0), (1.2, 1.0), (1.5, 0.0), (3.6, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.5, 1.0), (1.2, 1.0), (1.5, 0.0), (3.6, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.4, 0.85), (0.8, 0.2), (1.2, 0.9), (1.6, 0.3), (2.1, 0.8), (2.6, 0.0), (3.6, 0.0)],
                "ParamEmotionStar": [(0.0, 0.0), (0.4, 1.0), (2.2, 1.0), (3.0, 0.0), (3.6, 0.0)],
            },
        },
        # 3. Azur Lane Home (归港问候：温柔点头 + 浅笑交谈)
        "home": {
            "duration": 3.4,
            "loop": False,
            "curves": {
                "ParamAngleX": [(0.0, 0.0), (0.7, 8.5), (1.8, -6.0), (3.4, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (0.5, -10.0), (1.1, 8.0), (2.2, 3.0), (3.4, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.8, -8.0), (2.0, 4.0), (3.4, 0.0)],
                "ParamBodyAngleX": [(0.0, 0.0), (0.9, 8.0), (2.2, -3.0), (3.4, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.8, 16.0), (1.8, -8.0), (3.4, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.5, 0.75), (0.9, 0.2), (1.4, 0.85), (1.9, 0.2), (2.4, 0.65), (3.0, 0.0), (3.4, 0.0)],
                "ParamEyeLOpen": [(0.0, 0.0), (0.35, 1.0), (1.8, 1.0), (1.95, 0.0), (2.15, 1.0), (3.4, 1.0)],
                "ParamEyeROpen": [(0.0, 0.0), (0.35, 1.0), (1.8, 1.0), (1.95, 0.0), (2.15, 1.0), (3.4, 1.0)],
            },
        },
        # 4. Azur Lane Main 1 (主界面台词1：元气对话)
        "main_1": {
            "duration": 3.6,
            "loop": False,
            "curves": {
                "ParamAngleX": [(0.0, 0.0), (0.7, 10.0), (1.7, -10.0), (2.7, 5.0), (3.6, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (0.7, -12.0), (1.6, 6.0), (2.5, -5.0), (3.6, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (1.1, -11.0), (2.3, 6.0), (3.6, 0.0)],
                "ParamBodyAngleX": [(0.0, 0.0), (1.1, -12.0), (2.4, 6.0), (3.6, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.65, 24.0), (1.5, -10.0), (2.4, 18.0), (3.6, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.3, 0.9), (0.6, 0.2), (1.0, 0.85), (1.4, 0.25), (1.8, 0.9), (2.2, 0.2), (2.7, 0.75), (3.2, 0.0), (3.6, 0.0)],
            },
        },
        # 5. Azur Lane Main 2 (主界面台词2：俏皮单眼Wink + 歪头)
        "main_2": {
            "duration": 3.2,
            "loop": False,
            "curves": {
                "ParamAngleX": [(0.0, 0.0), (0.6, -12.0), (1.8, 8.0), (3.2, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.5, -12.0), (1.5, -10.0), (2.4, 4.0), (3.2, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.3, 0.0), (1.3, 0.0), (1.6, 1.0), (3.2, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.3, 1.0), (1.3, 1.0), (1.6, 0.0), (3.2, 0.0)],
                "ParamEyeROpen": [(0.0, 1.0), (3.2, 1.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.6, -18.0), (1.6, 8.0), (3.2, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.5, 22.0), (1.5, 16.0), (3.2, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.4, 0.8), (0.9, 0.3), (1.4, 0.9), (2.0, 0.2), (2.6, 0.7), (3.2, 0.0)],
                "ParamEmotionStar": [(0.0, 0.0), (0.3, 1.0), (1.8, 1.0), (2.4, 0.0), (3.2, 0.0)],
            },
        },
        # 6. Azur Lane Main 3 (主界面台词3：开心欢呼比耶)
        "main_3": {
            "duration": 3.4,
            "loop": False,
            "curves": {
                "ParamAngleY": [(0.0, 0.0), (0.4, 14.0), (0.9, -8.0), (1.4, 12.0), (2.2, 0.0), (3.4, 0.0)],
                "ParamBodyAngleY": [(0.0, 0.0), (0.4, 12.0), (0.9, -6.0), (1.4, 10.0), (2.2, 0.0), (3.4, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.3, 0.0), (1.6, 0.0), (2.0, 1.0), (3.4, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.3, 0.0), (1.6, 0.0), (2.0, 1.0), (3.4, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.3, 1.0), (1.6, 1.0), (2.0, 0.0), (3.4, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.3, 1.0), (1.6, 1.0), (2.0, 0.0), (3.4, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.4, 32.0), (0.9, 10.0), (1.4, 32.0), (2.2, 0.0), (3.4, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.4, -22.0), (0.9, -6.0), (1.4, -22.0), (2.2, 0.0), (3.4, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.35, 1.0), (0.8, 0.3), (1.3, 0.95), (1.9, 0.2), (2.5, 0.7), (3.4, 0.0)],
            },
        },
        # 7. Azur Lane Touch Head (摸头反应：闭眼幸福微笑 + 脑袋蹭手 + 爱心特效)
        "touch_head": {
            "duration": 2.8,
            "loop": False,
            "curves": {
                "ParamEyeLOpen": [(0.0, 1.0), (0.2, 0.0), (2.1, 0.0), (2.5, 1.0), (2.8, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.2, 0.0), (2.1, 0.0), (2.5, 1.0), (2.8, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.2, 1.0), (2.1, 1.0), (2.5, 0.0), (2.8, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.2, 1.0), (2.1, 1.0), (2.5, 0.0), (2.8, 0.0)],
                "ParamAngleX": [(0.0, 0.0), (0.5, 14.0), (1.1, -14.0), (1.7, 12.0), (2.3, -6.0), (2.8, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (0.4, -14.0), (0.9, 8.0), (1.4, -12.0), (2.0, 6.0), (2.8, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.5, 8.0), (1.1, -8.0), (1.7, 7.0), (2.8, 0.0)],
                "ParamBodyAngleZ": [(0.0, 0.0), (0.6, 3.0), (1.3, -3.0), (2.0, 2.0), (2.8, 0.0)],
                "ParamCheek": [(0.0, 0.0), (0.25, 1.0), (2.3, 1.0), (2.8, 0.0)],
                "ParamEmotionHeart": [(0.0, 0.0), (0.25, 1.0), (2.2, 1.0), (2.8, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.5, -14.0), (1.2, 6.0), (1.9, -12.0), (2.8, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.5, 16.0), (1.2, -8.0), (1.9, 14.0), (2.8, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.4, 0.65), (1.2, 0.25), (1.8, 0.7), (2.5, 0.0), (2.8, 0.0)],
            },
        },
        # 8. Azur Lane Touch Body (身体触摸互动：害羞微跳 + 侧身反应)
        "touch_body": {
            "duration": 2.6,
            "loop": False,
            "curves": {
                "ParamBodyAngleY": [(0.0, 0.0), (0.2, 12.0), (0.5, -6.0), (1.0, 4.0), (2.6, 0.0)],
                "ParamBodyAngleX": [(0.0, 0.0), (0.4, 14.0), (1.2, -8.0), (2.6, 0.0)],
                "ParamAngleX": [(0.0, 0.0), (0.4, 12.0), (1.1, -10.0), (1.9, 4.0), (2.6, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (0.35, -12.0), (1.0, 6.0), (2.6, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.45, 7.0), (1.2, -5.0), (2.6, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.3, 16.0), (0.9, -10.0), (1.7, 8.0), (2.6, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.3, -18.0), (0.9, 14.0), (1.7, -8.0), (2.6, 0.0)],
                "ParamCheek": [(0.0, 0.0), (0.2, 0.8), (2.0, 0.8), (2.6, 0.0)],
                "ParamEmotionExclaim": [(0.0, 0.0), (0.15, 1.0), (1.5, 1.0), (2.1, 0.0), (2.6, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.25, 0.85), (0.6, 0.2), (1.1, 0.75), (1.7, 0.2), (2.2, 0.0), (2.6, 0.0)],
            },
        },
        # 9. Azur Lane Touch Special (特殊触摸反应：惊讶睁大眼 -> 害羞闭眼脸红摆手)
        "touch_special": {
            "duration": 3.0,
            "loop": False,
            "curves": {
                "ParamEyeLOpen": [(0.0, 1.0), (0.2, 1.2), (0.55, 1.2), (0.75, 0.0), (2.2, 0.0), (2.6, 1.0), (3.0, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.2, 1.2), (0.55, 1.2), (0.75, 0.0), (2.2, 0.0), (2.6, 1.0), (3.0, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.55, 0.0), (0.75, 1.0), (2.2, 1.0), (2.6, 0.0), (3.0, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.55, 0.0), (0.75, 1.0), (2.2, 1.0), (2.6, 0.0), (3.0, 0.0)],
                "ParamBodyAngleY": [(0.0, 0.0), (0.22, 16.0), (0.6, -14.0), (1.3, -8.0), (3.0, 0.0)],
                "ParamBodyAngleX": [(0.0, 0.0), (0.35, -16.0), (0.9, 12.0), (1.6, -8.0), (3.0, 0.0)],
                "ParamAngleX": [(0.0, 0.0), (0.3, 14.0), (0.7, -16.0), (1.2, 14.0), (1.7, -10.0), (2.3, 5.0), (3.0, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.35, -12.0), (0.85, 10.0), (1.5, -8.0), (3.0, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.25, -28.0), (0.55, 20.0), (0.85, -25.0), (1.2, 18.0), (1.7, -15.0), (2.4, 0.0), (3.0, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.25, 30.0), (0.55, -22.0), (0.85, 28.0), (1.2, -18.0), (1.7, 20.0), (2.4, 0.0), (3.0, 0.0)],
                "ParamCheek": [(0.0, 0.0), (0.2, 1.0), (2.6, 1.0), (3.0, 0.0)],
                "ParamEmotionExclaim": [(0.0, 0.0), (0.15, 1.0), (1.2, 1.0), (1.6, 0.0), (3.0, 0.0)],
                "ParamEmotionSweat": [(0.0, 0.0), (0.5, 1.0), (2.4, 1.0), (3.0, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.2, 1.0), (0.6, 0.3), (1.0, 0.9), (1.4, 0.2), (1.9, 0.8), (2.5, 0.0), (3.0, 0.0)],
            },
        },
        # 10. Azur Lane Wedding (誓约之戒互动：深情鞠躬 + 幸福闭眼微笑 + 满屏爱心)
        "wedding": {
            "duration": 4.2,
            "loop": False,
            "curves": {
                "ParamAngleY": [(0.0, 0.0), (0.7, -15.0), (1.5, -10.0), (2.4, 8.0), (3.4, 4.0), (4.2, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.8, 6.0), (2.2, -5.0), (3.4, 3.0), (4.2, 0.0)],
                "ParamBodyAngleY": [(0.0, 0.0), (0.7, -12.0), (1.6, -8.0), (2.5, 6.0), (4.2, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.4, 0.0), (2.0, 0.0), (2.5, 1.0), (4.2, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.4, 0.0), (2.0, 0.0), (2.5, 1.0), (4.2, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.4, 1.0), (2.0, 1.0), (2.5, 0.0), (4.2, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.4, 1.0), (2.0, 1.0), (2.5, 0.0), (4.2, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.8, 26.0), (2.6, 22.0), (3.6, 8.0), (4.2, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.8, 12.0), (2.6, 10.0), (4.2, 0.0)],
                "ParamCheek": [(0.0, 0.0), (0.3, 1.0), (3.8, 1.0), (4.2, 0.0)],
                "ParamEmotionHeart": [(0.0, 0.0), (0.3, 1.0), (3.8, 1.0), (4.2, 0.0)],
                "ParamRing": [(0.0, 0.0), (0.6, 1.0), (3.6, 1.0), (4.2, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.8, 0.6), (1.4, 0.2), (2.1, 0.8), (2.8, 0.25), (3.4, 0.65), (4.0, 0.0), (4.2, 0.0)],
            },
        },
        # 11. Azur Lane Mail / Mission / Mission Complete / Complete
        "mail": {
            "duration": 2.4,
            "loop": False,
            "curves": {
                "ParamAngleZ": [(0.0, 0.0), (0.4, 8.0), (1.2, -6.0), (2.4, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.4, 22.0), (1.2, 15.0), (2.4, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.3, 0.8), (0.8, 0.2), (1.3, 0.75), (1.9, 0.0), (2.4, 0.0)],
                "ParamEmotionExclaim": [(0.0, 0.0), (0.2, 1.0), (1.6, 1.0), (2.4, 0.0)],
            },
        },
        "mission": {
            "duration": 2.4,
            "loop": False,
            "curves": {
                "ParamAngleY": [(0.0, 0.0), (0.4, -10.0), (1.0, 6.0), (2.4, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.5, -18.0), (1.4, -10.0), (2.4, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.35, 0.85), (0.9, 0.25), (1.5, 0.8), (2.1, 0.0), (2.4, 0.0)],
            },
        },
        "mission_complete": {
            "duration": 2.8,
            "loop": False,
            "curves": {
                "ParamBodyAngleY": [(0.0, 0.0), (0.35, 14.0), (0.75, -4.0), (1.15, 12.0), (2.8, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.3, 0.0), (1.8, 0.0), (2.2, 1.0), (2.8, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.3, 0.0), (1.8, 0.0), (2.2, 1.0), (2.8, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.3, 1.0), (1.8, 1.0), (2.2, 0.0), (2.8, 0.0)],
                "ParamEyeRSmile": [(0.0, 0.0), (0.3, 1.0), (1.8, 1.0), (2.2, 0.0), (2.8, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.35, 30.0), (0.8, 10.0), (1.25, 30.0), (2.8, 0.0)],
                "ParamArmLAngle": [(0.0, 0.0), (0.35, -24.0), (0.8, -8.0), (1.25, -24.0), (2.8, 0.0)],
                "ParamEmotionStar": [(0.0, 0.0), (0.2, 1.0), (2.2, 1.0), (2.8, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.3, 0.95), (0.8, 0.3), (1.4, 0.9), (2.2, 0.0), (2.8, 0.0)],
            },
        },
        "complete": {
            "duration": 2.4,
            "loop": False,
            "curves": {
                "ParamAngleY": [(0.0, 0.0), (0.4, -12.0), (0.9, 6.0), (2.4, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.4, 20.0), (1.2, -10.0), (2.4, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.3, 0.8), (0.9, 0.2), (1.5, 0.75), (2.1, 0.0), (2.4, 0.0)],
            },
        },
        # Classic aliases (Nod, Shake, Wave, Talk, Wink)
        "nod": {
            "duration": 1.4,
            "loop": False,
            "curves": {
                "ParamAngleY": [(0.0, 0.0), (0.3, -16.0), (0.65, 8.0), (1.0, -10.0), (1.4, 0.0)],
                "ParamEyeLOpen": [(0.0, 1.0), (0.25, 0.0), (0.55, 1.0), (1.4, 1.0)],
                "ParamEyeROpen": [(0.0, 1.0), (0.25, 0.0), (0.55, 1.0), (1.4, 1.0)],
                "ParamBreath": [(0.0, 0.0), (0.7, 0.8), (1.4, 0.0)],
            },
        },
        "shake": {
            "duration": 1.5,
            "loop": False,
            "curves": {
                "ParamAngleX": [(0.0, 0.0), (0.25, -20.0), (0.6, 20.0), (0.95, -14.0), (1.25, 8.0), (1.5, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.25, -6.0), (0.6, 6.0), (0.95, -4.0), (1.5, 0.0)],
            },
        },
        "wave": {
            "duration": 2.0,
            "loop": False,
            "curves": {
                "ParamArmRAngle": [(0.0, 0.0), (0.3, 30.0), (0.65, -20.0), (1.0, 30.0), (1.35, -20.0), (1.7, 20.0), (2.0, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.4, 7.0), (1.6, 7.0), (2.0, 0.0)],
                "ParamMouthOpenY": [(0.0, 0.0), (0.3, 0.75), (0.8, 0.2), (1.3, 0.75), (1.8, 0.0), (2.0, 0.0)],
            },
        },
        "talk": {
            "duration": 2.4,
            "loop": False,
            "curves": {
                "ParamMouthOpenY": [(0.0, 0.0), (0.25, 0.9), (0.5, 0.2), (0.8, 0.85), (1.1, 0.25), (1.45, 0.9), (1.8, 0.2), (2.1, 0.7), (2.4, 0.0)],
                "ParamAngleY": [(0.0, 0.0), (0.6, -5.0), (1.4, 4.0), (2.4, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.8, 12.0), (1.6, -6.0), (2.4, 0.0)],
            },
        },
        "wink": {
            "duration": 1.3,
            "loop": False,
            "curves": {
                "ParamEyeLOpen": [(0.0, 1.0), (0.2, 0.0), (0.85, 0.0), (1.1, 1.0), (1.3, 1.0)],
                "ParamEyeLSmile": [(0.0, 0.0), (0.2, 1.0), (0.85, 1.0), (1.1, 0.0), (1.3, 0.0)],
                "ParamAngleZ": [(0.0, 0.0), (0.3, -8.0), (0.9, -8.0), (1.3, 0.0)],
                "ParamArmRAngle": [(0.0, 0.0), (0.3, 18.0), (0.9, 18.0), (1.3, 0.0)],
            },
        },
    }

    for m_key, spec in motions_spec.items():
        m_data = build_motion3_json(
            name=m_key,
            duration=spec["duration"],
            fps=60.0,
            loop=spec["loop"],
            curves=spec["curves"],
        )
        m_file = os.path.join(output_dir, f"{m_key}.motion3.json")
        with open(m_file, "w", encoding="utf-8") as f:
            json.dump(m_data, f, indent=2)
        paths[m_key] = m_file

    # Compile custom motions generated by gemini-3.8-flash from user prompt & matted parts
    if custom_motions and isinstance(custom_motions, list):
        for cm in custom_motions:
            if not isinstance(cm, dict):
                continue
            cm_id = str(cm.get("id") or "").strip()
            raw_curves = cm.get("curves")
            if not cm_id or not isinstance(raw_curves, dict) or not raw_curves:
                continue
            cm_duration = float(cm.get("duration") or 2.4)
            cm_loop = bool(cm.get("loop", False))
            tuple_curves: Dict[str, List[Tuple[float, float]]] = {}
            for pid, pts in raw_curves.items():
                if isinstance(pts, list) and len(pts) >= 2:
                    t_pts = []
                    for p in pts:
                        if isinstance(p, (list, tuple)) and len(p) >= 2:
                            t_pts.append((float(p[0]), float(p[1])))
                    if len(t_pts) >= 2:
                        tuple_curves[pid] = t_pts
            if tuple_curves:
                cm_data = build_motion3_json(
                    name=cm_id,
                    duration=cm_duration,
                    fps=60.0,
                    loop=cm_loop,
                    curves=tuple_curves,
                )
                cm_file = os.path.join(output_dir, f"{cm_id}.motion3.json")
                with open(cm_file, "w", encoding="utf-8") as f:
                    json.dump(cm_data, f, indent=2)
                paths[cm_id] = cm_file

    return paths


def build_physics3_json(output_path: str, llm_physics: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate Cubism 3 multi-pendulum physics3.json modeled directly after Azur Lane's banerwei_3.physics3.json.
    Includes 4-vertex pendulum chains for:
      1. Front Bangs (前发物理)
      2. Side Locks (鬓发物理)
      3. Back Hair & Left Twintail (左马尾多段物理)
      4. Back Hair & Right Twintail (右马尾多段物理)
      5. Sailor Collar & Ribbon Bow (水手领结物理)
      6. Pleated Skirt Sway (百褶裙摆物理)
    """
    p_cfg = llm_physics or {}
    hair_mobility = float(p_cfg.get("hair_mobility", 0.90))
    hair_delay = float(p_cfg.get("hair_delay", 0.72))
    skirt_mobility = float(p_cfg.get("skirt_mobility", 0.85))

    def make_4vertex_chain(mobility: float, delay: float, accel: float, r1: float = 10.0, r2: float = 10.0, r3: float = 8.0):
        return [
            {"Position": {"X": 0.0, "Y": 0.0}, "Mobility": 1.0, "Delay": delay, "Acceleration": accel, "Radius": 0.0},
            {"Position": {"X": 0.0, "Y": 10.0}, "Mobility": round(mobility * 0.95, 3), "Delay": delay, "Acceleration": accel, "Radius": r1},
            {"Position": {"X": 0.0, "Y": 20.0}, "Mobility": round(mobility, 3), "Delay": delay, "Acceleration": accel, "Radius": r2},
            {"Position": {"X": 0.0, "Y": 28.0}, "Mobility": round(mobility, 3), "Delay": delay, "Acceleration": round(accel * 0.85, 3), "Radius": r3},
        ]

    settings = [
        {
            "Id": "PhysicsSetting1",
            "Input": [
                {"Source": {"Target": "Parameter", "Id": "ParamAngleX"}, "Weight": 60.0, "Type": "X", "Reflect": False},
                {"Source": {"Target": "Parameter", "Id": "ParamAngleZ"}, "Weight": 40.0, "Type": "Angle", "Reflect": False},
                {"Source": {"Target": "Parameter", "Id": "ParamWindA"}, "Weight": 100.0, "Type": "Angle", "Reflect": False},
            ],
            "Output": [
                {"Destination": {"Target": "Parameter", "Id": "ParamHairFront"}, "VertexIndex": 2, "Scale": 2.4, "Weight": 100.0, "Type": "Angle", "Reflect": False},
                {"Destination": {"Target": "Parameter", "Id": "ParamHairSide"}, "VertexIndex": 3, "Scale": 3.2, "Weight": 100.0, "Type": "Angle", "Reflect": False},
            ],
            "Vertices": make_4vertex_chain(hair_mobility, hair_delay, 1.2),
            "Normalization": {
                "Position": {"Minimum": -50.0, "Default": 0.0, "Maximum": 50.0},
                "Angle": {"Minimum": -120.0, "Default": 0.0, "Maximum": 120.0},
            },
        },
        {
            "Id": "PhysicsSetting2",
            "Input": [
                {"Source": {"Target": "Parameter", "Id": "ParamAngleX"}, "Weight": 75.0, "Type": "X", "Reflect": True},
                {"Source": {"Target": "Parameter", "Id": "ParamBodyAngleX"}, "Weight": 50.0, "Type": "X", "Reflect": False},
                {"Source": {"Target": "Parameter", "Id": "ParamWindB"}, "Weight": 100.0, "Type": "Angle", "Reflect": False},
            ],
            "Output": [
                {"Destination": {"Target": "Parameter", "Id": "ParamHairBack"}, "VertexIndex": 2, "Scale": 3.0, "Weight": 100.0, "Type": "Angle", "Reflect": False},
                {"Destination": {"Target": "Parameter", "Id": "ParamHairTailL"}, "VertexIndex": 3, "Scale": 4.5, "Weight": 100.0, "Type": "Angle", "Reflect": False},
                {"Destination": {"Target": "Parameter", "Id": "ParamHairTailR"}, "VertexIndex": 3, "Scale": 4.5, "Weight": 100.0, "Type": "Angle", "Reflect": True},
            ],
            "Vertices": make_4vertex_chain(hair_mobility, hair_delay * 1.05, 1.1, 12.0, 14.0, 10.0),
            "Normalization": {
                "Position": {"Minimum": -50.0, "Default": 0.0, "Maximum": 50.0},
                "Angle": {"Minimum": -120.0, "Default": 0.0, "Maximum": 120.0},
            },
        },
        {
            "Id": "PhysicsSetting3",
            "Input": [
                {"Source": {"Target": "Parameter", "Id": "ParamBodyAngleX"}, "Weight": 70.0, "Type": "X", "Reflect": False},
                {"Source": {"Target": "Parameter", "Id": "ParamBodyAngleZ"}, "Weight": 50.0, "Type": "Angle", "Reflect": False},
                {"Source": {"Target": "Parameter", "Id": "ParamBreath"}, "Weight": 30.0, "Type": "Y", "Reflect": False},
            ],
            "Output": [
                {"Destination": {"Target": "Parameter", "Id": "ParamRibbonSway"}, "VertexIndex": 2, "Scale": 2.2, "Weight": 100.0, "Type": "Angle", "Reflect": False},
                {"Destination": {"Target": "Parameter", "Id": "ParamSkirtSway"}, "VertexIndex": 3, "Scale": 3.6, "Weight": 100.0, "Type": "Angle", "Reflect": False},
            ],
            "Vertices": make_4vertex_chain(skirt_mobility, 0.75, 1.3, 8.0, 10.0, 8.0),
            "Normalization": {
                "Position": {"Minimum": -50.0, "Default": 0.0, "Maximum": 50.0},
                "Angle": {"Minimum": -120.0, "Default": 0.0, "Maximum": 120.0},
            },
        },
    ]

    physics = {
        "Version": 3,
        "Meta": {
            "PhysicsSettingCount": len(settings),
            "TotalInputCount": sum(len(s["Input"]) for s in settings),
            "TotalOutputCount": sum(len(s["Output"]) for s in settings),
            "VertexCount": sum(len(s["Vertices"]) for s in settings),
            "EffectiveForces": {
                "Gravity": {"X": 0.0, "Y": -1.0},
                "Wind": {"X": 0.0, "Y": 0.0},
            },
            "PhysicsDictionary": [
                {"Id": "PhysicsSetting1", "Name": "FrontHairAndSideLocks (前发与鬓发物理)"},
                {"Id": "PhysicsSetting2", "Name": "BackHairAndTwinTails (后发与双马尾物理)"},
                {"Id": "PhysicsSetting3", "Name": "CollarRibbonAndSkirt (水手领结与百褶裙物理)"},
            ],
        },
        "PhysicsSettings": settings,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(physics, f, ensure_ascii=False, indent=2)
    return output_path
