# -*- coding: utf-8 -*-
"""
banano2live2D Interactive Studio Backend Server.
Provides:
  - Static file serving for the Web Studio UI (/web/index.html) and generated outputs (/output/...)
  - Transparent Step-by-Step Pipeline API (supporting 3x3 9-part & 4x4 16-part grids + 1K / 4K 4096x4096):
      1. POST /api/step1_generate_image -> Calls gemini-nano-banana-2.1 (Text-to-Image when no attachment; Image-to-Image when attachment uploaded)
      2. POST /api/step2_slice_and_matte -> Adaptive Valley Slicing + BFS Matting + Halo Cleaning -> 9 or 16 RGBA parts + Matted Contact Sheet
      3. POST /api/step3_rig_and_motions -> Unified Multimodal Call to gemini-3.8-flash with (Sliced/Matted Images + User Prompt) -> Rigging + Physics + Custom Motion .motion3.json files
  - Unified POST /api/generate endpoint (runs Step 1 -> Step 2 -> Step 3 end-to-end)
  - GET /api/ping health check
"""

import os
import json
import time
import base64
import traceback
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Dict, Any
from PIL import Image

from ..core import Banano2Live2D
from ..sdk.client import DEFAULT_API_KEY, DEFAULT_BASE_URL
from ..prompts.engine import (
    build_live2d_grid_prompt,
    build_image_to_live2d_prompt,
    normalize_grid_spec,
    CHARACTER_PRESETS,
)
from ..cutter.slicer import slice_3x3_grid
from ..rigger.gemini_rigger import (
    build_matted_contact_sheet,
    COMPONENT_ORDER_3X3,
    COMPONENT_ORDER_4X4,
)
from ..rigger.model_builder import build_live2d_model_package, pack_texture_atlas
from .exporter import export_model_zip


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# In-memory cache of sliced parts_data per character_name for fast Step 2 -> Step 3 handoff
_SESSION_PARTS_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}


def file_to_data_url(path: str, mime: str = "image/png") -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def load_parts_data_from_disk(parts_dir: str, grid: str = "3x3") -> Dict[str, Dict[str, Any]]:
    """Reload sliced RGBA parts from disk if not in memory cache."""
    grid_mode = normalize_grid_spec(grid)
    order = COMPONENT_ORDER_4X4 if grid_mode == "4x4" else COMPONENT_ORDER_3X3
    grid_n = 4 if grid_mode == "4x4" else 3
    parts_data: Dict[str, Dict[str, Any]] = {}
    for idx, name in enumerate(order):
        pfile = os.path.join(parts_dir, f"{name}.png")
        if os.path.isfile(pfile):
            img = Image.open(pfile).convert("RGBA")
            r, c = divmod(idx, grid_n)
            parts_data[name] = {
                "image": img,
                "cell": (r, c),
                "bbox": (0, 0, img.width, img.height),
                "size": img.size,
                "grid": grid_mode,
            }
    return parts_data


class StudioRequestHandler(SimpleHTTPRequestHandler):
    project_root: str = os.getcwd()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            self._send_json(200, {
                "ok": True,
                "service": "banano2live2D-studio",
                "models": {
                    "image": "gemini-nano-banana-2.1",
                    "multimodal_llm": "gemini-3.8-flash",
                },
                "supported_grids": ["3x3", "4x4"],
                "supported_resolutions": ["1024x1024", "4096x4096"],
                "pipeline": [
                    "step1_generate_image",
                    "step2_slice_and_matte",
                    "step3_rig_and_motions",
                ],
            })
            return
        if self.path in ("/", "/index.html"):
            self.path = "/web/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/step1_generate_image"):
            self._handle_step1_generate_image()
            return
        if self.path.startswith("/api/step2_slice_and_matte"):
            self._handle_step2_slice_and_matte()
            return
        if self.path.startswith("/api/step3_rig_and_motions"):
            self._handle_step3_rig_and_motions()
            return
        if self.path.startswith("/api/generate"):
            self._handle_generate()
            return
        self._send_json(404, {"ok": False, "error": f"Unknown endpoint: {self.path}"})

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        return json.loads(raw_body)

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_step1_generate_image(self):
        """
        Stage 1: Call gemini-nano-banana-2.1 to generate the single 3x3 or 4x4 component sheet (1K or 4K 4096x4096):
          - If NO attachment is provided -> Text-to-Image (文生图) strictly from user's prompt.
          - If attachment IS provided -> Image-to-Image (图生图) using attachment + user's prompt.
        """
        t0 = time.time()
        try:
            req_data = self._read_json_body()
            api_key = (req_data.get("api_key") or DEFAULT_API_KEY).strip()
            base_url = (req_data.get("base_url") or DEFAULT_BASE_URL).strip()
            prompt = (req_data.get("prompt") or "").strip()
            raw_preset = req_data.get("preset")
            preset = raw_preset if (not prompt and raw_preset) else None
            attachment_b64 = req_data.get("attachment")
            attachment_mode = req_data.get("attachment_mode") or "reference"
            char_name = (req_data.get("character_name") or f"char_{int(time.time())}").strip()
            grid_mode = normalize_grid_spec(req_data.get("grid") or "3x3")
            is_4k = bool(req_data.get("is_4k", False))

            output_dir = os.path.join(self.project_root, "output", char_name)
            os.makedirs(output_dir, exist_ok=True)

            engine = Banano2Live2D(
                api_key=api_key,
                base_url=base_url,
                img_model="gemini-nano-banana-2.1",
                llm_model="gemini-3.8-flash",
            )

            if attachment_b64 and attachment_mode == "grid_sheet":
                sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.png")
                raw_b64 = attachment_b64.split(",", 1)[-1]
                with open(sheet_path, "wb") as f:
                    f.write(base64.b64decode(raw_b64))
                sheet_mime = "image/png"
                prompt_used = f"[Uploaded {grid_mode} Grid Sheet - Direct Slice Mode]"
                called_img_model = False
                generation_mode = "direct_grid_upload"
            elif attachment_b64:
                sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.jpg")
                prompt_used = build_image_to_live2d_prompt(reference_hint=prompt, grid=grid_mode, is_4k=is_4k)
                print(f"[Studio Step 1] Mode=Image-to-Image (图生图) | grid={grid_mode} | 4K={is_4k} | char={char_name}")
                engine.generate_component_sheet(
                    prompt=prompt,
                    preset=None,
                    reference_image=attachment_b64,
                    output_path=sheet_path,
                    grid=grid_mode,
                    is_4k=is_4k,
                )
                sheet_mime = "image/jpeg"
                called_img_model = True
                generation_mode = "image_to_image"
            else:
                sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.jpg")
                prompt_used = build_live2d_grid_prompt(character_description=prompt, preset=preset, grid=grid_mode, is_4k=is_4k)
                print(f"[Studio Step 1] Mode=Text-to-Image (文生图) | grid={grid_mode} | 4K={is_4k} | char={char_name}")
                engine.generate_component_sheet(
                    prompt=prompt,
                    preset=preset,
                    reference_image=None,
                    output_path=sheet_path,
                    grid=grid_mode,
                    is_4k=is_4k,
                )
                sheet_mime = "image/jpeg"
                called_img_model = True
                generation_mode = "text_to_image"

            with Image.open(sheet_path) as im:
                sheet_res = list(im.size)

            sheet_data_url = file_to_data_url(sheet_path, sheet_mime)
            elapsed = round(time.time() - t0, 2)

            self._send_json(200, {
                "ok": True,
                "step": 1,
                "character_name": char_name,
                "grid": grid_mode,
                "is_4k": is_4k,
                "sheet_resolution": sheet_res,
                "generation_mode": generation_mode,
                "called_img_model": called_img_model,
                "img_model": "gemini-nano-banana-2.1",
                "sheet_path": os.path.abspath(sheet_path),
                "sheet_data_url": sheet_data_url,
                "prompt_used": prompt_used,
                "elapsed_sec": elapsed,
            })
        except Exception as e:
            traceback.print_exc()
            self._send_json(500, {
                "ok": False,
                "step": 1,
                "error": str(e),
                "trace": traceback.format_exc(),
            })

    def _handle_step2_slice_and_matte(self):
        """
        Stage 2: Slice the 3x3 (9-part) or 4x4 (16-part) component sheet via Adaptive Valley Slicing
        + Exterior BFS Matting + see-through Seam Cleaning, and build the Matted Contact Sheet for Stage 3.
        """
        t0 = time.time()
        try:
            req_data = self._read_json_body()
            char_name = (req_data.get("character_name") or f"char_{int(time.time())}").strip()
            grid_mode = normalize_grid_spec(req_data.get("grid") or "3x3")
            sheet_path = req_data.get("sheet_path")
            attachment_b64 = req_data.get("attachment")

            output_dir = os.path.join(self.project_root, "output", char_name)
            parts_dir = os.path.join(output_dir, "parts")
            textures_dir = os.path.join(output_dir, "textures")
            os.makedirs(parts_dir, exist_ok=True)
            os.makedirs(textures_dir, exist_ok=True)

            if not sheet_path or not os.path.isfile(sheet_path):
                candidate = os.path.join(output_dir, f"component_{grid_mode}_sheet.jpg")
                if os.path.isfile(candidate):
                    sheet_path = candidate
                elif attachment_b64:
                    sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.png")
                    raw_b64 = attachment_b64.split(",", 1)[-1]
                    with open(sheet_path, "wb") as f:
                        f.write(base64.b64decode(raw_b64))
                else:
                    raise FileNotFoundError(f"Component sheet not found for {char_name}")

            parts_data = slice_3x3_grid(
                image_path=sheet_path,
                output_dir=parts_dir,
                apply_matting=True,
                apply_cleaning=True,
                grid=grid_mode,
            )
            _SESSION_PARTS_CACHE[char_name] = parts_data

            matted_sheet_path = os.path.join(output_dir, "matted_contact_sheet.jpg")
            matted_sheet_uri, parts_summary = build_matted_contact_sheet(
                parts_data,
                output_path=matted_sheet_path,
                grid=grid_mode,
            )

            parts_images = {k: v["image"] for k, v in parts_data.items()}
            atlas_img, _ = pack_texture_atlas(parts_images, atlas_size=1024)
            atlas_path = os.path.join(textures_dir, "texture_00.png")
            atlas_img.save(atlas_path)
            atlas_data_url = file_to_data_url(atlas_path, "image/png")

            order = COMPONENT_ORDER_4X4 if grid_mode == "4x4" else COMPONENT_ORDER_3X3
            parts_b64: Dict[str, str] = {}
            for pname in order:
                pfile = os.path.join(parts_dir, f"{pname}.png")
                if os.path.isfile(pfile):
                    parts_b64[pname] = file_to_data_url(pfile, "image/png")

            elapsed = round(time.time() - t0, 2)
            self._send_json(200, {
                "ok": True,
                "step": 2,
                "character_name": char_name,
                "grid": grid_mode,
                "parts_count": len(parts_b64),
                "sheet_path": os.path.abspath(sheet_path),
                "parts_b64": parts_b64,
                "parts_summary": parts_summary,
                "matted_sheet_data_url": matted_sheet_uri,
                "atlas_data_url": atlas_data_url,
                "atlas_resolution": list(atlas_img.size),
                "elapsed_sec": elapsed,
            })
        except Exception as e:
            traceback.print_exc()
            self._send_json(500, {
                "ok": False,
                "step": 2,
                "error": str(e),
                "trace": traceback.format_exc(),
            })

    def _handle_step3_rig_and_motions(self):
        """
        Stage 3: Send BOTH the sliced/matted components (matted_contact_sheet.jpg + parts_summary)
        AND the user's prompt to gemini-3.8-flash in ONE unified multimodal request.
        Generates calibrated rigging, physics3.json, cdi3.json, action_spec.json, and all
        standard + custom .motion3.json files.
        """
        t0 = time.time()
        try:
            req_data = self._read_json_body()
            api_key = (req_data.get("api_key") or DEFAULT_API_KEY).strip()
            base_url = (req_data.get("base_url") or DEFAULT_BASE_URL).strip()
            char_name = (req_data.get("character_name") or f"char_{int(time.time())}").strip()
            prompt = (req_data.get("prompt") or "Azur Lane anime character").strip()
            grid_mode = normalize_grid_spec(req_data.get("grid") or "3x3")

            output_dir = os.path.join(self.project_root, "output", char_name)
            parts_dir = os.path.join(output_dir, "parts")
            matted_sheet_path = os.path.join(output_dir, "matted_contact_sheet.jpg")

            parts_data = _SESSION_PARTS_CACHE.get(char_name)
            if not parts_data:
                parts_data = load_parts_data_from_disk(parts_dir, grid=grid_mode)
            if not parts_data:
                raise RuntimeError(f"No sliced parts found for {char_name}. Please run Step 2 first.")

            engine = Banano2Live2D(
                api_key=api_key,
                base_url=base_url,
                img_model="gemini-nano-banana-2.1",
                llm_model="gemini-3.8-flash",
            )

            sheet_fallback = os.path.join(output_dir, f"component_{grid_mode}_sheet.jpg")
            if not os.path.isfile(sheet_fallback):
                sheet_fallback = os.path.join(output_dir, "component_3x3_sheet.jpg")

            rig_config = engine.rigger.rig(
                grid_image_path=sheet_fallback if os.path.isfile(sheet_fallback) else matted_sheet_path,
                character_hint=prompt,
                model="gemini-3.8-flash",
                parts_data=parts_data,
                matted_sheet_path=matted_sheet_path,
                grid=grid_mode,
            )

            result = build_live2d_model_package(
                character_name=char_name,
                parts_data=parts_data,
                rig_config=rig_config,
                output_dir=output_dir,
            )
            zip_path = export_model_zip(output_dir)

            with open(result["character_data"], "r", encoding="utf-8") as f:
                character_data = json.load(f)
            with open(result["model3_json"], "r", encoding="utf-8") as f:
                model3_json = json.load(f)
            with open(result["physics3_json"], "r", encoding="utf-8") as f:
                physics3_json = json.load(f)
            with open(result["cdi3_json"], "r", encoding="utf-8") as f:
                cdi3_json = json.load(f)
            with open(result["action_spec_json"], "r", encoding="utf-8") as f:
                action_spec = json.load(f)

            motions_data = {}
            for mname, mrel in character_data.get("motions", {}).items():
                mfile = os.path.join(output_dir, mrel)
                if os.path.isfile(mfile):
                    with open(mfile, "r", encoding="utf-8") as mf:
                        motions_data[mname] = json.load(mf)

            preview_data_url = file_to_data_url(result["preview_path"], "image/png")
            atlas_data_url = file_to_data_url(result["texture_atlas"], "image/png")
            elapsed = round(time.time() - t0, 2)

            self._send_json(200, {
                "ok": True,
                "step": 3,
                "character_name": char_name,
                "grid": grid_mode,
                "llm_model": "gemini-3.8-flash",
                "output_dir": os.path.abspath(output_dir),
                "zip_url": f"/output/{char_name}.zip",
                "preview_data_url": preview_data_url,
                "atlas_data_url": atlas_data_url,
                "character_data": character_data,
                "model3_json": model3_json,
                "physics3_json": physics3_json,
                "cdi3_json": cdi3_json,
                "action_spec": action_spec,
                "custom_motions": action_spec.get("custom_motions", []),
                "motions_data": motions_data,
                "elapsed_sec": elapsed,
            })
        except Exception as e:
            traceback.print_exc()
            self._send_json(500, {
                "ok": False,
                "step": 3,
                "error": str(e),
                "trace": traceback.format_exc(),
            })

    def _handle_generate(self):
        try:
            req_data = self._read_json_body()

            api_key = (req_data.get("api_key") or DEFAULT_API_KEY).strip()
            base_url = (req_data.get("base_url") or DEFAULT_BASE_URL).strip()
            prompt = (req_data.get("prompt") or "").strip()
            raw_preset = req_data.get("preset")
            preset = raw_preset if (not prompt and raw_preset) else None
            attachment_b64 = req_data.get("attachment")
            attachment_mode = req_data.get("attachment_mode") or "reference"
            char_name = (req_data.get("character_name") or f"char_{int(time.time())}").strip()
            grid_mode = normalize_grid_spec(req_data.get("grid") or "3x3")
            is_4k = bool(req_data.get("is_4k", False))

            output_dir = os.path.join(self.project_root, "output", char_name)
            os.makedirs(output_dir, exist_ok=True)

            engine = Banano2Live2D(
                api_key=api_key,
                base_url=base_url,
                img_model="gemini-nano-banana-2.1",
                llm_model="gemini-3.8-flash",
            )

            if attachment_b64 and attachment_mode == "grid_sheet":
                sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.png")
                raw_b64 = attachment_b64.split(",", 1)[-1]
                with open(sheet_path, "wb") as f:
                    f.write(base64.b64decode(raw_b64))
                result = engine.from_grid_image(
                    grid_image_path=sheet_path,
                    character_name=char_name,
                    character_hint=prompt or "Azur Lane anime character",
                    output_dir=output_dir,
                    serve=False,
                    grid=grid_mode,
                )
            else:
                result = engine.create_live2d(
                    prompt=prompt,
                    preset=preset,
                    reference_image=attachment_b64 if attachment_b64 else None,
                    character_name=char_name,
                    output_dir=output_dir,
                    serve=False,
                    grid=grid_mode,
                    is_4k=is_4k,
                )
                sheet_path = os.path.join(output_dir, f"component_{grid_mode}_sheet.jpg")

            with open(result["character_data"], "r", encoding="utf-8") as f:
                character_data = json.load(f)
            with open(result["model3_json"], "r", encoding="utf-8") as f:
                model3_json = json.load(f)
            with open(result["physics3_json"], "r", encoding="utf-8") as f:
                physics3_json = json.load(f)
            with open(result["cdi3_json"], "r", encoding="utf-8") as f:
                cdi3_json = json.load(f)
            with open(result["action_spec_json"], "r", encoding="utf-8") as f:
                action_spec = json.load(f)

            parts_b64 = {}
            parts_dir = os.path.join(output_dir, "parts")
            for pname in character_data.get("parts", {}):
                pfile = os.path.join(parts_dir, f"{pname}.png")
                if os.path.isfile(pfile):
                    parts_b64[pname] = file_to_data_url(pfile, "image/png")

            motions_data = {}
            for mname, mrel in character_data.get("motions", {}).items():
                mfile = os.path.join(output_dir, mrel)
                if os.path.isfile(mfile):
                    with open(mfile, "r", encoding="utf-8") as mf:
                        motions_data[mname] = json.load(mf)

            sheet_mime = "image/png" if sheet_path.endswith(".png") else "image/jpeg"
            sheet_data_url = file_to_data_url(sheet_path, sheet_mime) if os.path.isfile(sheet_path) else ""
            preview_data_url = file_to_data_url(result["preview_path"], "image/png")
            atlas_data_url = file_to_data_url(result["texture_atlas"], "image/png")

            self._send_json(200, {
                "ok": True,
                "character_name": char_name,
                "grid": grid_mode,
                "is_4k": is_4k,
                "output_dir": os.path.abspath(output_dir),
                "zip_url": f"/output/{char_name}.zip",
                "sheet_data_url": sheet_data_url,
                "preview_data_url": preview_data_url,
                "atlas_data_url": atlas_data_url,
                "parts_b64": parts_b64,
                "character_data": character_data,
                "model3_json": model3_json,
                "physics3_json": physics3_json,
                "cdi3_json": cdi3_json,
                "action_spec": action_spec,
                "custom_motions": action_spec.get("custom_motions", []),
                "motions_data": motions_data,
            })
        except Exception as e:
            traceback.print_exc()
            self._send_json(500, {
                "ok": False,
                "error": str(e),
                "trace": traceback.format_exc(),
            })


def serve_studio(project_root: str, port: int = 8090):
    os.chdir(project_root)
    StudioRequestHandler.project_root = project_root
    server = ThreadedHTTPServer(("0.0.0.0", port), StudioRequestHandler)
    print(f"[banano2live2D Studio] Running at http://127.0.0.1:{port}")
    server.serve_forever()
