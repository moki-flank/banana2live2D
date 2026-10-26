# -*- coding: utf-8 -*-
"""
banano2live2D Core Pipeline.
Unifies:
  1. Component Sheet Generation (gemini-nano-banana-2.1)
  2. 3x3 Grid Slicing & Exterior BFS Matting + see-through Cleaning
  3. Gemini 3.8 Flash Multimodal Live2D Rigging (Z-order, Bounding Boxes, Pivots, Scale)
  4. Cubism Model3 Package Building (Atlas, Motions, Physics)
  5. Interactive Web Live2D Player & Distribution Exporter
"""

import os
import sys
import shutil
import urllib.request
from typing import Optional, Dict, Any

from .sdk.client import HrioClient, DEFAULT_BASE_URL, DEFAULT_API_KEY
from .prompts.engine import (
    build_live2d_grid_prompt,
    build_image_to_live2d_prompt,
    CHARACTER_PRESETS,
)
from .cutter.slicer import slice_3x3_grid
from .rigger.gemini_rigger import GeminiRigger
from .rigger.model_builder import build_live2d_model_package
from .viewer.exporter import export_model_zip
from .viewer.web_player import serve_live2d_model


class Banano2Live2D:
    """
    Main Live2D Generative Engine.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        img_model: str = "gemini-nano-banana-2.1",
        llm_model: str = "gemini-3.8-flash",
    ):
        self.api_key = api_key or DEFAULT_API_KEY
        self.client = HrioClient(api_key=self.api_key, base_url=base_url)
        self.rigger = GeminiRigger(self.client)
        self.img_model = img_model
        self.llm_model = llm_model

    def generate_component_sheet(
        self,
        prompt: str,
        preset: Optional[str] = None,
        reference_image: Optional[str] = None,
        output_path: str = "character_3x3_grid.jpg",
    ) -> str:
        """
        Generate 3x3 component sprite sheet using gemini-nano-banana-2.1.
        """
        if reference_image:
            full_prompt = build_image_to_live2d_prompt(reference_hint=prompt)
            images = [reference_image]
        else:
            full_prompt = build_live2d_grid_prompt(character_description=prompt, preset=preset)
            images = None

        print(f"[banano2live2D] [1/4] Generating 3x3 Component Sheet via {self.img_model}...")
        resp = self.client.generate_image(
            model=self.img_model,
            prompt=full_prompt,
            images=images,
            parameters={"size": "1024x1024"},
        )

        img_url, img_bytes = self.client.extract_image_bytes_or_url(resp)
        if img_bytes:
            with open(output_path, "wb") as f:
                f.write(img_bytes)
        elif img_url:
            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as s, open(output_path, "wb") as f:
                f.write(s.read())
        else:
            raise RuntimeError(f"Failed to retrieve image from API: {resp}")

        print(f"[banano2live2D] Saved component sheet to: {output_path}")
        return output_path

    def from_grid_image(
        self,
        grid_image_path: str,
        character_name: str = "chibi_character",
        character_hint: str = "chibi anime girl",
        output_dir: str = "output/model",
        serve: bool = False,
        port: int = 8088,
    ) -> Dict[str, Any]:
        """
        Build full Live2D package from an existing 3x3 component grid sheet.
        """
        if not os.path.isfile(grid_image_path):
            raise FileNotFoundError(f"Component grid sheet not found: {grid_image_path}")

        os.makedirs(output_dir, exist_ok=True)
        parts_dir = os.path.join(output_dir, "parts")

        print(f"[banano2live2D] [2/4] Slicing 3x3 grid & applying Exterior BFS Matting + Cleaning...")
        parts_data = slice_3x3_grid(
            image_path=grid_image_path,
            output_dir=parts_dir,
            apply_matting=True,
            apply_cleaning=True,
        )
        print(f"[banano2live2D]       Extracted {len(parts_data)} clean component layers.")

        matted_sheet_path = os.path.join(output_dir, "matted_contact_sheet.jpg")
        print(f"[banano2live2D] [3/4] Unified Multimodal Rigging & Motion Generation via {self.llm_model} (sending sliced/matted parts + user prompt)...")
        rig_config = self.rigger.rig(
            grid_image_path=grid_image_path,
            character_hint=character_hint,
            model=self.llm_model,
            parts_data=parts_data,
            matted_sheet_path=matted_sheet_path,
        )
        print(f"[banano2live2D]       Rigging calculated for: {rig_config.get('character_name', character_name)}")

        print(f"[banano2live2D] [4/4] Assembling Live2D Cubism package & Texture Atlas...")
        result = build_live2d_model_package(
            character_name=character_name,
            parts_data=parts_data,
            rig_config=rig_config,
            output_dir=output_dir,
        )

        # Copy web player template into output_dir with embedded offline-compatible data
        viewer_template = os.path.join(os.path.dirname(__file__), "viewer", "template.html")
        viewer_target = os.path.join(output_dir, "index.html")
        if os.path.isfile(viewer_template):
            import json as _json, base64 as _b64
            with open(viewer_template, "r", encoding="utf-8") as _tf:
                _tpl = _tf.read()
            with open(result["character_data"], "r", encoding="utf-8") as _cf:
                _cdata = _json.load(_cf)
            _parts_b64 = {}
            for _pk, _pv in (_cdata.get("parts") or {}).items():
                _pf = os.path.join(output_dir, _pv.get("texture_file", f"parts/{_pk}.png"))
                if os.path.isfile(_pf):
                    with open(_pf, "rb") as _imgf:
                        _parts_b64[_pk] = "data:image/png;base64," + _b64.b64encode(_imgf.read()).decode("utf-8")
            _motions_map = {}
            for _mk, _mrel in (_cdata.get("motions") or {}).items():
                _mf = os.path.join(output_dir, _mrel)
                if os.path.isfile(_mf):
                    with open(_mf, "r", encoding="utf-8") as _mjf:
                        _motions_map[_mk] = _json.load(_mjf)
            _embed = (
                "<script>\n"
                f"window.__EMBEDDED_CHARACTER_DATA__ = {_json.dumps(_cdata, ensure_ascii=False)};\n"
                f"window.__EMBEDDED_PARTS_B64__ = {_json.dumps(_parts_b64, ensure_ascii=False)};\n"
                f"window.__EMBEDDED_MOTIONS__ = {_json.dumps(_motions_map, ensure_ascii=False)};\n"
                "</script>\n  <script>"
            )
            with open(viewer_target, "w", encoding="utf-8") as _outf:
                _outf.write(_tpl.replace("<script>", _embed, 1))

        # Export ZIP package
        zip_path = export_model_zip(output_dir)
        result["zip_path"] = zip_path

        print(f"[banano2live2D] SUCCESS: Live2D Model built successfully!")
        print(f"   Model directory: {os.path.abspath(output_dir)}")
        print(f"   Web Player:      {os.path.abspath(viewer_target)}")
        print(f"   Export ZIP:      {os.path.abspath(zip_path)}")

        if serve:
            serve_live2d_model(output_dir, port=port)

        return result

    def create_live2d(
        self,
        prompt: str,
        preset: Optional[str] = None,
        reference_image: Optional[str] = None,
        character_name: str = "live2d_character",
        output_dir: str = "output/live2d_model",
        serve: bool = False,
        port: int = 8088,
    ) -> Dict[str, Any]:
        """
        Complete end-to-end Text/Image -> Live2D workflow.
        """
        os.makedirs(output_dir, exist_ok=True)
        sheet_path = os.path.join(output_dir, "component_3x3_sheet.jpg")

        self.generate_component_sheet(
            prompt=prompt,
            preset=preset,
            reference_image=reference_image,
            output_path=sheet_path,
        )

        char_hint = prompt or (CHARACTER_PRESETS.get(preset, {}).get("description", "chibi anime girl"))

        return self.from_grid_image(
            grid_image_path=sheet_path,
            character_name=character_name,
            character_hint=char_hint,
            output_dir=output_dir,
            serve=serve,
            port=port,
        )
