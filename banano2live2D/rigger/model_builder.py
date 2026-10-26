# -*- coding: utf-8 -*-
"""
Live2D Model Builder & Texture Atlas Generator (Azur Lane / banerwei_3 Standard).
Packs matted components into a unified texture atlas (textures/texture_00.png),
builds Cubism 3 .model3.json, .cdi3.json, .physics3.json, .motion3.json,
generates composite_preview.png (with armless torso + both articulated arms attached),
and exports character_data.json + action_spec.json for the runtime web player.
"""

import os
import json
from typing import Dict, Any, Tuple
from PIL import Image


def pack_texture_atlas(
    parts_dict: Dict[str, Image.Image],
    atlas_size: int = 1024,
    padding: int = 8,
) -> Tuple[Image.Image, Dict[str, Dict[str, Any]]]:
    """
    Pack individual component images into a single texture atlas (texture_00.png).
    Automatically selects 2048x2048 or 4096x4096 for 4x4 (16-part) and 4K UHD textures.
    Returns: (atlas_image, uv_mapping)
    """
    total_area = sum(img.width * img.height for img in parts_dict.values())
    max_side = max((max(img.width, img.height) for img in parts_dict.values()), default=256)
    if total_area > 1024 * 1024 * 0.65 or len(parts_dict) > 9 or max_side > 512:
        atlas_size = max(atlas_size, 2048)
    if total_area > 2048 * 2048 * 0.65 or max_side > 900:
        atlas_size = max(atlas_size, 4096)

    atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
    mapping: Dict[str, Dict[str, Any]] = {}

    # Sort parts by height descending for efficient shelf packing
    sorted_items = sorted(parts_dict.items(), key=lambda item: item[1].height, reverse=True)

    curr_x = padding
    curr_y = padding
    shelf_h = 0

    for name, img in sorted_items:
        w, h = img.size
        while w + padding * 2 > atlas_size or h + padding * 2 > atlas_size:
            larger_size = atlas_size * 2
            larger_atlas = Image.new("RGBA", (larger_size, larger_size), (0, 0, 0, 0))
            larger_atlas.paste(atlas, (0, 0))
            atlas = larger_atlas
            atlas_size = larger_size

        if curr_x + w + padding > atlas_size:
            curr_x = padding
            curr_y += shelf_h + padding
            shelf_h = 0

        while curr_y + h + padding > atlas_size:
            larger_size = atlas_size * 2
            larger_atlas = Image.new("RGBA", (larger_size, larger_size), (0, 0, 0, 0))
            larger_atlas.paste(atlas, (0, 0))
            atlas = larger_atlas
            atlas_size = larger_size

        atlas.paste(img, (curr_x, curr_y))
        mapping[name] = {
            "x": curr_x,
            "y": curr_y,
            "width": w,
            "height": h,
        }

        curr_x += w + padding
        if h > shelf_h:
            shelf_h = h

    for name, rect in mapping.items():
        rx, ry, rw, rh = rect["x"], rect["y"], rect["width"], rect["height"]
        rect["uv"] = {
            "u0": round(rx / atlas_size, 6),
            "v0": round(ry / atlas_size, 6),
            "u1": round((rx + rw) / atlas_size, 6),
            "v1": round((ry + rh) / atlas_size, 6),
        }

    return atlas, mapping


def build_live2d_model_package(
    character_name: str,
    parts_data: Dict[str, Dict[str, Any]],
    rig_config: Dict[str, Any],
    output_dir: str,
) -> Dict[str, Any]:
    """
    Assemble sliced parts into a complete Azur Lane style Live2D Cubism 3 package:
    - <character_name>.model3.json
    - <character_name>.cdi3.json
    - <character_name>.physics3.json
    - textures/texture_00.png
    - motions/*.motion3.json (14 Azur Lane standard + 5 classic motions)
    - action_spec.json (LLM-generated secretary dialogues & physics tuning)
    - composite_preview.png
    - character_data.json
    """
    os.makedirs(output_dir, exist_ok=True)
    textures_dir = os.path.join(output_dir, "textures")
    motions_dir = os.path.join(output_dir, "motions")
    parts_dir = os.path.join(output_dir, "parts")
    os.makedirs(textures_dir, exist_ok=True)
    os.makedirs(motions_dir, exist_ok=True)
    os.makedirs(parts_dir, exist_ok=True)

    # 1. Save individual matted parts
    parts_images: Dict[str, Image.Image] = {}
    for name, pdata in parts_data.items():
        img = pdata["image"]
        parts_images[name] = img
        pdata_path = os.path.join(parts_dir, f"{name}.png")
        img.save(pdata_path)

    # 2. Pack texture atlas
    atlas_img, uv_map = pack_texture_atlas(parts_images, atlas_size=1024)
    atlas_path = os.path.join(textures_dir, "texture_00.png")
    atlas_img.save(atlas_path)

    # 3. Generate Cubism 3 motions, physics3.json, and cdi3.json (banerwei_3 standard)
    from .motion_builder import (
        generate_standard_motions,
        build_physics3_json,
        build_cdi3_json,
    )

    action_spec_cfg = rig_config.get("action_spec", {}) or {}
    custom_motions_list = action_spec_cfg.get("custom_motions", []) or []
    physics_profile_cfg = action_spec_cfg.get("physics_profile", {}) or {}

    motion_paths = generate_standard_motions(
        motions_dir,
        llm_choreography=physics_profile_cfg,
        custom_motions=custom_motions_list,
    )
    physics_path = os.path.join(output_dir, f"{character_name}.physics3.json")
    build_physics3_json(physics_path, llm_physics=physics_profile_cfg)
    cdi3_path = os.path.join(output_dir, f"{character_name}.cdi3.json")
    build_cdi3_json(cdi3_path, character_name=character_name)

    # 4. Create Azur Lane standard Live2D Cubism 3 model3.json
    model3_data = {
        "Version": 3,
        "FileReferences": {
            "Moc": f"{character_name}.moc3",
            "Textures": [
                "textures/texture_00.png",
            ],
            "Physics": f"{character_name}.physics3.json",
            "DisplayInfo": f"{character_name}.cdi3.json",
            "Motions": {
                "Idle": [{"File": "motions/idle.motion3.json"}],
                "Login": [{"File": "motions/login.motion3.json"}],
                "Home": [{"File": "motions/home.motion3.json"}],
                "Main": [
                    {"File": "motions/main_1.motion3.json"},
                    {"File": "motions/main_2.motion3.json"},
                    {"File": "motions/main_3.motion3.json"},
                ],
                "TouchHead": [{"File": "motions/touch_head.motion3.json"}],
                "TouchBody": [{"File": "motions/touch_body.motion3.json"}],
                "TouchSpecial": [{"File": "motions/touch_special.motion3.json"}],
                "Wedding": [{"File": "motions/wedding.motion3.json"}],
                "Mail": [{"File": "motions/mail.motion3.json"}],
                "Mission": [{"File": "motions/mission.motion3.json"}],
                "MissionComplete": [{"File": "motions/mission_complete.motion3.json"}],
                "Complete": [{"File": "motions/complete.motion3.json"}],
                "TapBody": [
                    {"File": "motions/wave.motion3.json"},
                    {"File": "motions/nod.motion3.json"},
                ],
                "Talk": [{"File": "motions/talk.motion3.json"}],
                "Shake": [{"File": "motions/shake.motion3.json"}],
                "Wink": [{"File": "motions/wink.motion3.json"}],
            },
        },
        "Groups": [
            {
                "Target": "Parameter",
                "Name": "EyeBlink",
                "Ids": ["ParamEyeLOpen", "ParamEyeROpen"],
            },
            {
                "Target": "Parameter",
                "Name": "LipSync",
                "Ids": ["ParamMouthOpenY"],
            },
        ],
        "HitAreas": [
            {"Name": "Head", "Id": "HitAreaHead"},
            {"Name": "Special", "Id": "HitAreaSpecial"},
            {"Name": "Body", "Id": "HitAreaBody"},
        ],
    }

    # Register LLM-generated custom motions into model3.json FileReferences.Motions
    for cm in custom_motions_list:
        if isinstance(cm, dict) and cm.get("id"):
            cm_id = cm["id"]
            model3_data["FileReferences"]["Motions"][cm_id] = [
                {"File": f"motions/{cm_id}.motion3.json"}
            ]

    model3_path = os.path.join(output_dir, f"{character_name}.model3.json")
    with open(model3_path, "w", encoding="utf-8") as f:
        json.dump(model3_data, f, indent=2, ensure_ascii=False)

    # 5. Build assembled composite preview (armless torso + both articulated arms attached!)
    canvas_w = rig_config.get("canvas", {}).get("width", 1000)
    canvas_h = rig_config.get("canvas", {}).get("height", 1000)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    components_cfg = rig_config.get("components", {})
    sorted_comps = sorted(
        components_cfg.items(),
        key=lambda item: item[1].get("z_index", 0),
    )

    # Only skip eyes_closed in rest pose preview; arm_left and arm_right MUST be rendered
    # because body_torso is strictly armless in the Azur Lane (banerwei_3) architecture.
    preview_skip = {"eyes_closed"}

    runtime_parts = {}

    for name, comp_info in sorted_comps:
        if name not in parts_images:
            continue
        p_img = parts_images[name]
        scale = comp_info.get("scale", 1.0)
        cx, cy = comp_info.get("canvas_center", [canvas_w // 2, canvas_h // 2])
        pivot = comp_info.get("pivot", [0.5, 0.5])
        z_idx = comp_info.get("z_index", 0)

        pw, ph = p_img.size
        scaled_w = max(1, int(pw * scale))
        scaled_h = max(1, int(ph * scale))

        paste_x = int(cx - scaled_w / 2)
        paste_y = int(cy - scaled_h / 2)

        anchor_x = int(paste_x + scaled_w * pivot[0])
        anchor_y = int(paste_y + scaled_h * pivot[1])

        runtime_parts[name] = {
            "name": name,
            "z_index": z_idx,
            "center": [cx, cy],
            "scale": scale,
            "pivot": pivot,
            "anchor": [anchor_x, anchor_y],
            "width": scaled_w,
            "height": scaled_h,
            "raw_size": [pw, ph],
            "paste_pos": [paste_x, paste_y],
            "live2d_params": comp_info.get("live2d_params", []),
            "texture_file": f"parts/{name}.png",
            "atlas_rect": uv_map.get(name, {}),
        }

        if name not in preview_skip:
            scaled_img = p_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            canvas.alpha_composite(scaled_img, (paste_x, paste_y))

    preview_path = os.path.join(output_dir, "composite_preview.png")
    canvas.save(preview_path)

    # 6. Save LLM-generated action & dialogue specification
    action_spec = rig_config.get("action_spec", {})
    action_spec_path = os.path.join(output_dir, "action_spec.json")
    with open(action_spec_path, "w", encoding="utf-8") as f:
        json.dump(action_spec, f, indent=2, ensure_ascii=False)

    # 7. Save comprehensive character metadata for web player
    meta = {
        "character_name": character_name,
        "architecture": "Azur Lane Cubism 3 (banerwei_3 Reference)",
        "canvas": {"width": canvas_w, "height": canvas_h},
        "model3_json": f"{character_name}.model3.json",
        "cdi3_json": f"{character_name}.cdi3.json",
        "physics3_json": f"{character_name}.physics3.json",
        "action_spec_json": "action_spec.json",
        "composite_preview": "composite_preview.png",
        "texture_atlas": "textures/texture_00.png",
        "parts": runtime_parts,
        "action_spec": action_spec,
        "motions": {
            "Idle": "motions/idle.motion3.json",
            "Login": "motions/login.motion3.json",
            "Home": "motions/home.motion3.json",
            "Main1": "motions/main_1.motion3.json",
            "Main2": "motions/main_2.motion3.json",
            "Main3": "motions/main_3.motion3.json",
            "TouchHead": "motions/touch_head.motion3.json",
            "TouchBody": "motions/touch_body.motion3.json",
            "TouchSpecial": "motions/touch_special.motion3.json",
            "Wedding": "motions/wedding.motion3.json",
            "Mail": "motions/mail.motion3.json",
            "Mission": "motions/mission.motion3.json",
            "MissionComplete": "motions/mission_complete.motion3.json",
            "Complete": "motions/complete.motion3.json",
            "Nod": "motions/nod.motion3.json",
            "Shake": "motions/shake.motion3.json",
            "Wave": "motions/wave.motion3.json",
            "Talk": "motions/talk.motion3.json",
            "Wink": "motions/wink.motion3.json",
        },
        "custom_motions": custom_motions_list,
    }
    for cm in custom_motions_list:
        if isinstance(cm, dict) and cm.get("id"):
            cm_id = cm["id"]
            meta["motions"][cm_id] = f"motions/{cm_id}.motion3.json"

    meta_path = os.path.join(output_dir, "character_data.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return {
        "model_dir": output_dir,
        "model3_json": model3_path,
        "cdi3_json": cdi3_path,
        "physics3_json": physics_path,
        "action_spec_json": action_spec_path,
        "preview_path": preview_path,
        "texture_atlas": atlas_path,
        "character_data": meta_path,
        "parts_count": len(parts_images),
        "motions_count": len(motion_paths),
    }
