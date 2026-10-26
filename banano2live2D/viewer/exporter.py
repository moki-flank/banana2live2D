# -*- coding: utf-8 -*-
"""
Live2D Model Exporter & Packager.
Exports the complete model package into a distributable ZIP file.
"""

import os
import shutil
import zipfile
from typing import Optional


def export_model_zip(
    model_dir: str,
    output_zip_path: Optional[str] = None,
) -> str:
    """
    Package model_dir into a single .zip archive.
    """
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Directory not found: {model_dir}")

    if not output_zip_path:
        base_name = os.path.basename(os.path.abspath(model_dir))
        output_zip_path = os.path.join(os.path.dirname(os.path.abspath(model_dir)), f"{base_name}.zip")

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(model_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, model_dir)
                zf.write(abs_path, rel_path)

    return output_zip_path
