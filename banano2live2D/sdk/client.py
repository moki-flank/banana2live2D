# -*- coding: utf-8 -*-
"""
HrioAPI Client SDK for banano2live2D.
Supports:
  1. Image Generation (gemini-nano-banana-2.1)
  2. Multimodal Chat Completions (gemini-3.8-flash with image vision & low-latency reasoning control)
Zero third-party dependencies required; uses standard Python urllib.
"""

import os
import re
import json
import base64
import mimetypes
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple, List, Union

DEFAULT_BASE_URL = "https://hrioapi.hrio.site/v1"
def _load_default_api_key() -> str:
    env_key = os.environ.get("HRIO_API_KEY", "").strip()
    if env_key:
        return env_key
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8-sig") as ef:
                for line in ef:
                    line = line.strip()
                    if line.startswith("HRIO_API_KEY="):
                        return line.split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass
    return ""


DEFAULT_API_KEY = _load_default_api_key()
OFFICIAL_WEBSITE = "https://hrioapi.hrio.site"


class HrioAPIError(Exception):
    """Exception raised for errors in the HrioAPI requests."""
    pass


def file_to_data_uri(file_path: str) -> str:
    """Convert local image file to base64 Data URI."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg" if file_path.lower().endswith((".jpg", ".jpeg")) else "image/png"

    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def strip_json_fences(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    if not text:
        return "{}"
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    return cleaned.strip()


class HrioClient:
    """
    Self-contained HrioAPI Client supporting both image gen and multimodal LLMs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 180,
    ):
        self.api_key = (api_key or os.environ.get("HRIO_API_KEY") or DEFAULT_API_KEY).strip()
        self.base_url = (base_url or os.environ.get("HRIO_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout

    def check_auth(self):
        if not self.api_key:
            raise HrioAPIError(
                f"\n[Error] No valid API Key detected.\n"
                f"Please obtain your API Key from: {OFFICIAL_WEBSITE}\n"
            )

    def generate_image(
        self,
        model: str = "gemini-nano-banana-2.1",
        prompt: str = "",
        images: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call Image Generation endpoint (/v1/images/generations).
        Supports both text-to-image and image-to-image (via 'image' and 'images' fields).
        """
        self.check_auth()

        url = f"{self.base_url}/images/generations"
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }

        if images:
            formatted_images: List[str] = []
            for img in images:
                if not img:
                    continue
                img_str = str(img).strip()
                if img_str.startswith(("http://", "https://", "data:")):
                    formatted_images.append(img_str)
                elif os.path.isfile(img_str):
                    formatted_images.append(file_to_data_uri(img_str))
                else:
                    formatted_images.append(img_str)
            if formatted_images:
                # Official contract for gemini-nano-banana-2.1 uses 'image' (single) as primary binding
                payload["image"] = formatted_images[0]
                payload["images"] = formatted_images

        if parameters:
            payload.update(parameters)

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "banano2live2D-sdk/1.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise HrioAPIError(
                f"HTTP Request failed ({e.code}): {err_body}\n"
                f"Please verify your key at: {OFFICIAL_WEBSITE}"
            ) from e
        except Exception as e:
            raise HrioAPIError(f"Request failed: {e}") from e

    def extract_image_bytes_or_url(self, resp_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
        """Extract image URL or base64 bytes from API response."""
        if not isinstance(resp_data, dict):
            return None, None

        items = resp_data.get("data")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                if first.get("b64_json"):
                    return None, base64.b64decode(first["b64_json"])
                if first.get("url"):
                    return first["url"], None

        for k in ("url", "image_url", "output_url"):
            val = resp_data.get(k)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val, None

        return None, None

    def chat_completions(
        self,
        model: str = "gemini-3.8-flash",
        messages: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = "low",
    ) -> Dict[str, Any]:
        """
        Call Chat Completions endpoint (/v1/chat/completions).
        Defaults reasoning_effort='low' for fast interactive Live2D rigging & motion generation.
        """
        self.check_auth()

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages or [],
        }
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        if response_format:
            payload["response_format"] = response_format
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "banano2live2D-sdk/1.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise HrioAPIError(f"Chat HTTP Request failed ({e.code}): {err_body}") from e
        except Exception as e:
            raise HrioAPIError(f"Chat Request failed: {e}") from e

    def multimodal_chat(
        self,
        prompt: str,
        image_path_or_url: Union[str, List[str]],
        model: str = "gemini-3.8-flash",
        system_prompt: Optional[str] = None,
        response_format_json: bool = True,
        reasoning_effort: str = "low",
    ) -> str:
        """
        Send image(s) + text prompt to gemini-3.8-flash and return the text/JSON response.
        """
        images_list = [image_path_or_url] if isinstance(image_path_or_url, str) else list(image_path_or_url)
        content_items: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

        for img_item in images_list[:1]:  # Contract specifies max_items=1 for message_content image
            if not img_item:
                continue
            if os.path.isfile(img_item):
                img_uri = file_to_data_uri(img_item)
            else:
                img_uri = img_item
            content_items.append({
                "type": "image_url",
                "image_url": {"url": img_uri},
            })

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": content_items,
        })

        resp_fmt = {"type": "json_object"} if response_format_json else None
        resp = self.chat_completions(
            model=model,
            messages=messages,
            response_format=resp_fmt,
            temperature=0.25,
            reasoning_effort=reasoning_effort,
        )

        try:
            raw_text = resp["choices"][0]["message"]["content"]
            return strip_json_fences(raw_text) if response_format_json else raw_text
        except (KeyError, IndexError) as e:
            raise HrioAPIError(f"Unexpected chat response structure: {resp}") from e
