# -*- coding: utf-8 -*-
"""
banano2live2D: Componentized Live2D Generation Engine.
"""

from .core import Banano2Live2D
from .sdk.client import HrioClient
from .prompts.engine import build_live2d_grid_prompt, CHARACTER_PRESETS
from .cutter.slicer import slice_3x3_grid
from .cutter.matting import remove_background
from .rigger.gemini_rigger import GeminiRigger
from .viewer.web_player import serve_live2d_model
from .viewer.exporter import export_model_zip

__version__ = "1.0.0"
__all__ = [
    "Banano2Live2D",
    "HrioClient",
    "build_live2d_grid_prompt",
    "CHARACTER_PRESETS",
    "slice_3x3_grid",
    "remove_background",
    "GeminiRigger",
    "serve_live2d_model",
    "export_model_zip",
]
