# -*- coding: utf-8 -*-
"""
Live2D 3x3 Component Grid Prompt Engine (Azur Lane / banerwei_3 Standard).
Supports:
  1. Pure Text-to-Image (文生图): Generates 3x3 component sprite sheet strictly matching the user's text description.
  2. Image-to-Image (图生图): Generates 3x3 component sprite sheet strictly preserving the uploaded reference character image.
Modeled after Azur Lane (碧蓝航线 banerwei_3) Live2D texture atlas standards:
  - Strictly ARMLESS torso in Cell (2,0) so detached left/right arms in Cells (2,1) & (2,2) attach without arm duplication.
  - Pure rear hair in Cell (0,0) without front bangs bleed.
  - Faceless head + narrow cylindrical neck in Cell (0,1) without wide shoulders.
  - Hollow-center front bangs + headwear/ears in Cell (0,2) without rear hair.
  - Generous pure-white margins inside every cell so no collar, hair tip, or shoe is ever clipped.
"""

import re
from typing import Optional, Dict

CHARACTER_PRESETS: Dict[str, Dict[str, str]] = {
    "sailor_girl": {
        "name": "Azur Navy Sailor Girl (碧蓝水手服舰娘)",
        "description": (
            "cute anime girl in Azur Lane style with vibrant sky-blue twin-tails tied with white flower ribbons, "
            "crisp white-and-navy sailor uniform with a blue ribbon bowtie at the collar, pleated navy skirt with gold buttons, "
            "white knee-high socks and brown loafers"
        ),
        "hair_color": "vibrant sky blue with white flower hair ribbons",
        "eye_color": "sparkling sapphire blue",
        "outfit": "white and navy-blue sailor collar uniform with blue bowtie and pleated mini skirt",
    },
    "banerwei_healer": {
        "name": "Iris Libre Healer (鸢尾圣洁礼装)",
        "description": (
            "adorable anime girl inspired by Azur Lane Iris Libre style, soft blonde-champagne twin-tails with white wing hairpins and halo crown, "
            "white and gold naval cleric dress with blue gem brooch, white thigh-highs and ribbon sandals"
        ),
        "hair_color": "soft champagne blonde with white ribbon ornaments",
        "eye_color": "gentle violet-blue",
        "outfit": "white and gold Iris Libre naval dress with blue gem ribbon collar and pleated skirt",
    },
    "catgirl_maid": {
        "name": "Royal Navy Catgirl Maid (皇家猫耳女仆)",
        "description": (
            "adorable anime catgirl maid with fluffy cat ears, silver-white hair, ruby red eyes, pink twin ribbons, white lace maid headdress, "
            "and classic black-and-white frilled maid dress with white apron"
        ),
        "hair_color": "silver-white hair with fluffy cat ears",
        "eye_color": "ruby red",
        "outfit": "frilled black and white maid dress with white apron and pink collar bow",
    },
    "cyberpunk_idol": {
        "name": "Muse System Idol (μ兵装偶像)",
        "description": (
            "futuristic anime idol with neon magenta twin-tails, holographic star hairclips, "
            "cropped idol jacket with glowing cyan circuit trims and layered stage skirt"
        ),
        "hair_color": "neon gradient magenta and violet",
        "eye_color": "glowing neon cyan",
        "outfit": "idol stage uniform with cropped jacket, pleated skirt, and glowing ribbon accessories",
    },
    "fantasy_elf": {
        "name": "Elf Vanguard Mage (精灵魔导舰娘)",
        "description": (
            "gentle anime elf girl with long pointed ears, golden blonde braided hair, emerald green eyes, white floral hairpin, "
            "emerald and white gold-trimmed fantasy mage robe"
        ),
        "hair_color": "golden blonde with floral wreath",
        "eye_color": "radiant emerald green",
        "outfit": "emerald and white gold-trimmed mage robe with jewel collar brooch",
    },
    "gothic_lolita": {
        "name": "Iron Blood Gothic Lolita (铁血哥特萝莉)",
        "description": (
            "charming gothic lolita anime girl with black-and-pink twin-tails, black lace rose headdress, "
            "dark crimson-and-black Victorian ruffled dress with cross ribbon bow"
        ),
        "hair_color": "black and pink twin-tails",
        "eye_color": "ruby crimson red",
        "outfit": "Victorian gothic dress with black lace frills, crimson ribbons, and ruffled collar",
    },
}

DEFAULT_STYLE = (
    "Official Azur Lane Live2D PSD dismantling sprite sheet style (碧蓝航线Live2D拆件立绘标准), "
    "clean crisp 2D anime cel-shading, masterwork Vtuber character asset art, "
    "sharp high-contrast clean line art, solid pure white background (#ffffff), "
    "generous white padding around every component inside its cell so nothing touches cell borders, "
    "absolutely no text labels, no numbers, no grid lines, no watermarks."
)


def extract_visual_character_desc(raw_prompt: str) -> str:
    """
    Remove pure action/motion-request clauses (e.g. '增加一个...动作', '添加...动作') from the image prompt
    so gemini-nano-banana-2.1 focuses 100% on the character's visual appearance and clothing components.
    """
    if not raw_prompt:
        return ""
    cleaned = re.sub(
        r"[，,。；;\s]*(?:并且|同时|另外|再)?(?:请)?(?:帮我)?(?:增加|添加|新增|加上|生成|制作|设计|附带|要求)[^，,。；;]*?(?:动作|动画|表情|姿势)[^。；;]*",
        "",
        raw_prompt,
    ).strip(" ，,。；;")
    return cleaned or raw_prompt.strip()


def build_live2d_grid_prompt(
    character_description: str,
    preset: Optional[str] = None,
    style_override: Optional[str] = None,
) -> str:
    """
    Construct an Azur Lane (banerwei_3) standard 3x3 Live2D component sprite sheet prompt for TEXT-TO-IMAGE (文生图).
    IMPORTANT: When character_description is provided by the user, strictly use the user's description
    and NEVER override or prepend any default demo preset!
    """
    visual_desc = extract_visual_character_desc(character_description)
    if visual_desc:
        desc = visual_desc
    elif preset and preset in CHARACTER_PRESETS:
        desc = CHARACTER_PRESETS[preset]["description"]
    else:
        desc = "cute anime girl"

    style = style_override or DEFAULT_STYLE

    prompt = (
        f"A professional 3x3 grid Live2D component dismantling sprite sheet (Live2D立绘九宫格拆件图) strictly depicting the following character: {desc}.\n"
        f"CRITICAL CHARACTER IDENTITY RULE: Every single hair part, eye part, headwear/ear part, torso outfit, and arm sleeve in this 3x3 sheet MUST strictly match the exact hair color, hairstyle, eye color, accessories, and clothing described in: [{desc}].\n"
        f"Style: {style}\n"
        f"CRITICAL ANATOMICAL DECOMPOSITION RULES (Azur Lane Live2D Standard):\n"
        f"Arrange exactly 9 isolated character parts of [{desc}] in an invisible 3-row by 3-column grid on a solid pure white background (#ffffff). "
        f"Leave at least 15% pure white margin on all 4 sides of every part so no part ever touches another part or the edge:\n"
        f"- Cell (Row 1, Col 1) [BACK HAIR ONLY / 后发与背发层]: ONLY the rear hair dome and any back hair/ponytail/twin-tails/long hair belonging to [{desc}] viewed from the front. "
        f"The center forehead area must be a smooth solid back-hair silhouette matching the character's exact hair color with NO front bangs, NO face skin, and NO eyes.\n"
        f"- Cell (Row 1, Col 2) [FACELESS HEAD & NARROW NECK / 无五官脸部底图与窄脖子]: ONLY a smooth blank oval anime face skin with two ears, subtle pink cheek blush, chin, and a narrow vertical cylindrical neck stub at the bottom. "
        f"STRICTLY NO eyes, NO eyebrows, NO mouth, NO hair, and NO wide shoulders or collarbones.\n"
        f"- Cell (Row 1, Col 3) [FRONT BANGS, SIDE LOCKS & HEADWEAR / 前发刘海、鬓发与头饰耳饰]: ONLY the front forehead bangs, side locks, and any headwear/animal ears/horns/hats/hairpins belonging to [{desc}]. "
        f"The lower-middle face region must be an open empty U-shaped space. STRICTLY NO face skin, NO eyes, and NO long rear hair.\n"
        f"- Cell (Row 2, Col 1) [OPEN EYES & EYEBROWS / 默认睁眼与眉毛]: Pair of large sparkling anime open eyes matching the exact eye color of [{desc}] with detailed pupils, highlights, upper eyelashes, and a pair of arched eyebrows above them.\n"
        f"- Cell (Row 2, Col 2) [CLOSED SMILING EYES & EYEBROWS / 闭眼微笑与眉毛]: Pair of happy curved closed smiling eye lashes and eyebrows for blinking, matching the exact scale and horizontal spacing of Cell (Row 2, Col 1).\n"
        f"- Cell (Row 2, Col 3) [MOUTH / 口开默认]: One small cute anime open smiling mouth with pink tongue, compact and centered in the cell.\n"
        f"- Cell (Row 3, Col 1) [ARMLESS TORSO, OUTFIT & LEGS / 无手臂躯干与服装全身下装]: Mannequin-style ARMLESS upper torso and lower body wearing the EXACT outfit, collar/neckline, top/dress/robe/armor, skirt/pants, legwear, and shoes of [{desc}] standing straight. "
        f"CRITICAL: DO NOT DRAW ANY ARMS OR HANDS ON THIS TORSO! The torso must be completely ARMLESS (clean shoulder sockets only, no sleeves, no arms, no hands, no head) because the left and right arms are drawn separately in Cells (Row 3, Col 2) and (Row 3, Col 3).\n"
        f"- Cell (Row 3, Col 2) [DETACHED LEFT ARM / 独立左臂与袖子]: Single isolated left arm wearing the matching left sleeve/cuff/glove of [{desc}] and open hand, angled slightly outward, with a clean rounded shoulder joint cap at the top.\n"
        f"- Cell (Row 3, Col 3) [DETACHED RIGHT ARM / 独立右臂与袖子]: Single isolated right arm wearing the matching right sleeve/cuff/glove of [{desc}] and expressive hand gesture, with a clean rounded shoulder joint cap at the top.\n"
        f"Strict verification: All 9 parts belong to [{desc}]; Cell (Row 3, Col 1) torso has ZERO arms and ZERO hands; every part has generous white margin all around; solid #ffffff background."
    )
    return prompt


def build_image_to_live2d_prompt(
    reference_hint: Optional[str] = None,
    style_override: Optional[str] = None,
) -> str:
    """
    Construct prompt for IMAGE-TO-IMAGE (图生图): decomposing an uploaded reference character image
    into an Azur Lane 3x3 Live2D component grid while preserving character identity and applying user hints.
    """
    visual_hint = extract_visual_character_desc(reference_hint or "")
    extra = f" with additional user specification: ({visual_hint})" if visual_hint else ""
    return build_live2d_grid_prompt(
        character_description=(
            f"REFERENCE CHARACTER LOCK: the exact character from the provided reference image decomposed into 9 clean Azur Lane Live2D parts, "
            f"strictly preserving the reference image's exact hair color, hairstyle, headwear/accessories, eye color, and outfit design{extra}"
        ),
        preset=None,
        style_override=style_override,
    )
