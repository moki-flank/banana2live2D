# -*- coding: utf-8 -*-
"""
Live2D 3x3 (9-Part) & 4x4 (16-Part) Component Grid Prompt Engine (Azur Lane / banerwei_3 Standard).
Supports:
  1. Pure Text-to-Image (文生图): Generates 3x3 or 4x4 component sprite sheet strictly matching the user's text description.
  2. Image-to-Image (图生图): Generates 3x3 or 4x4 component sprite sheet strictly preserving the uploaded reference character image.
  3. 4K UHD (4096x4096) ultra-high resolution mode.
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


def normalize_grid_spec(grid: Optional[str]) -> str:
    """Return '4x4' if 4x4 / 16-part is requested, else '3x3'."""
    if not grid:
        return "3x3"
    g = str(grid).strip().lower()
    if "4" in g or g == "16":
        return "4x4"
    return "3x3"


def build_live2d_grid_prompt(
    character_description: str,
    preset: Optional[str] = None,
    style_override: Optional[str] = None,
    grid: str = "3x3",
    is_4k: bool = False,
) -> str:
    """
    Construct an Azur Lane (banerwei_3) standard 3x3 (9-part) or 4x4 (16-part) Live2D component
    sprite sheet prompt for TEXT-TO-IMAGE (文生图).
    """
    visual_desc = extract_visual_character_desc(character_description)
    if visual_desc:
        desc = visual_desc
    elif preset and preset in CHARACTER_PRESETS:
        desc = CHARACTER_PRESETS[preset]["description"]
    else:
        desc = "cute anime girl"

    grid_mode = normalize_grid_spec(grid)
    res_tag = "4K UHD 4096x4096 ultra-high resolution razor-sharp vector line art, " if is_4k else ""
    style = f"{res_tag}{style_override or DEFAULT_STYLE}"

    if grid_mode == "4x4":
        return (
            f"A professional 4x4 grid Live2D 16-component dismantling sprite sheet (Live2D立绘16宫格高精拆件图) strictly depicting the following character: {desc}.\n"
            f"CRITICAL CHARACTER IDENTITY RULE: Every single hair part, facial feature, headwear/ear part, upper bodice, skirt/apron, legs, arms, tail/wings, and prop in this 4x4 sheet MUST strictly match the exact hair color, hairstyle, eye color, accessories, and clothing described in: [{desc}].\n"
            f"Style: {style}\n"
            f"CRITICAL 16-CELL ANATOMICAL DECOMPOSITION RULES (Azur Lane High-Flexibility 4x4 Live2D Standard):\n"
            f"Arrange exactly 16 isolated character components of [{desc}] in an invisible 4-row by 4-column grid on a solid pure white background (#ffffff). "
            f"Leave at least 14% pure white margin on all 4 sides of every component so no part ever touches another part or the cell border:\n"
            f"- Cell (Row 1, Col 1) [BACK HAIR ONLY / 后发主体]: ONLY the rear hair mass, long back hair, ponytail, or twin-tails of [{desc}] viewed from the front. Smooth back-hair dome silhouette with NO face skin, NO eyes, and NO front bangs.\n"
            f"- Cell (Row 1, Col 2) [FACELESS HEAD & NARROW NECK / 无五官脸部底图与窄颈]: ONLY a smooth blank oval anime face skin with two human ears, subtle cheek blush, chin, and a narrow vertical cylindrical neck stub at the bottom. STRICTLY NO eyes, NO eyebrows, NO mouth, NO hair, and NO shoulders.\n"
            f"- Cell (Row 1, Col 3) [FRONT FOREHEAD BANGS ONLY / 前额刘海与呆毛]: ONLY the center forehead bangs and top crown hair of [{desc}], with an empty U-shaped space below for the face. NO face skin, NO eyes, NO long rear hair.\n"
            f"- Cell (Row 1, Col 4) [LEFT & RIGHT SIDE HAIR LOCKS / 左右两侧垂发鬓发]: ONLY the symmetrical left and right cheek-framing side hair locks (鬓发/垂发) of [{desc}] with clean white space between them.\n"
            f"- Cell (Row 2, Col 1) [OPEN EYES PAIR ONLY / 默认睁眼双眸]: A horizontal pair of large sparkling anime open eyes matching the exact eye color of [{desc}] with detailed pupils, highlights, and upper eyelashes ONLY.\n"
            f"- Cell (Row 2, Col 2) [CLOSED SMILING EYES PAIR / 闭眼微笑弧线]: A horizontal pair of happy curved closed smiling eye arcs for blinking, matching the exact spacing of Cell (Row 2, Col 1).\n"
            f"- Cell (Row 2, Col 3) [EYEBROWS ONLY / 独立双眉]: ONLY a horizontal pair of expressive anime eyebrows matching [{desc}]'s hair color. STRICTLY NO blush ovals and NO eyes.\n"
            f"- Cell (Row 2, Col 4) [SINGLE MOUTH ONLY / 单个嘴型组件]: ONLY ONE single cute anime open smiling mouth with pink tongue centered in the cell (STRICTLY DO NOT draw multiple mouths).\n"
            f"- Cell (Row 3, Col 1) [ARMLESS UPPER TORSO BODICE / 无手臂无肩袖上半身胸衣]: Clean sleeveless upper bodice from collar down to waist wearing the exact top/bodice of [{desc}]. STRICTLY NO bare skin shoulder stumps sticking out left or right, NO neck above the collar, NO arms, NO hands, and NO lower skirt.\n"
            f"- Cell (Row 3, Col 2) [DETACHED SKIRT / APRON / LOWER HEM / 独立裙摆或围裙下摆]: Standalone waist-to-thigh skirt, frilled maid apron, or lower coat hem of [{desc}], detached so it can sway independently.\n"
            f"- Cell (Row 3, Col 3) [DETACHED LEFT ARM / 独立左臂与袖子]: Single isolated left arm wearing the matching left sleeve/cuff/glove of [{desc}] and open hand, with a clean rounded shoulder cap.\n"
            f"- Cell (Row 3, Col 4) [DETACHED RIGHT ARM / 独立右臂与袖子]: Single isolated right arm wearing the matching right sleeve/cuff/glove of [{desc}] and waving/expressive hand gesture, with a clean rounded shoulder cap.\n"
            f"- Cell (Row 4, Col 1) [LOWER LEGS, STOCKINGS & SHOES / 独立双腿与丝袜鞋靴]: Front-facing pair of anime legs from upper thighs down to stockings/socks and shoes of [{desc}], isolated without torso or skirt.\n"
            f"- Cell (Row 4, Col 2) [DETACHED HEADWEAR / ANIMAL EARS / CROWN / 独立头饰或兽耳发箍]: Standalone top head accessory of [{desc}] (such as fluffy cat/fox ears, lace maid headband, ribbons, halo, hat, or crown) with NO hair or face attached.\n"
            f"- Cell (Row 4, Col 3) [DETACHED REAR TAIL / WINGS / CAPE BOW / 独立尾巴或翅膀后背大蝴蝶结]: Standalone rear accessory of [{desc}] (such as a fluffy tail, angel/demon wings, flowing capelet, or giant waist ribbon bow).\n"
            f"- Cell (Row 4, Col 4) [DETACHED HAND PROP / FLOATING CHARM / 独立手持道具或胸前铃铛挂件]: Standalone signature accessory or floating prop of [{desc}] (such as a collar ribbon with golden bell, magic wand, teacup tray, or glowing emblem).\n"
            f"Strict verification: All 16 cells strictly arranged in 4 rows x 4 columns; Cell (Row 3, Col 1) upper torso is completely ARMLESS; solid pure #ffffff white background; zero grid lines, zero text labels, zero numbers."
        )

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
    grid: str = "3x3",
    is_4k: bool = False,
) -> str:
    """
    Construct prompt for IMAGE-TO-IMAGE (图生图): decomposing an uploaded reference character image
    into an Azur Lane 3x3 (9-part) or 4x4 (16-part) Live2D component grid while preserving character identity.
    """
    grid_mode = normalize_grid_spec(grid)
    part_count = 16 if grid_mode == "4x4" else 9
    visual_hint = extract_visual_character_desc(reference_hint or "")
    extra = f" with additional user specification: ({visual_hint})" if visual_hint else ""
    return build_live2d_grid_prompt(
        character_description=(
            f"REFERENCE CHARACTER LOCK: the exact character from the provided reference image decomposed into {part_count} clean Azur Lane Live2D parts, "
            f"strictly preserving the reference image's exact hair color, hairstyle, headwear/accessories, eye color, and outfit design{extra}"
        ),
        preset=None,
        style_override=style_override,
        grid=grid_mode,
        is_4k=is_4k,
    )