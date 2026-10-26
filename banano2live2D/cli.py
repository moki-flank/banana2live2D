# -*- coding: utf-8 -*-
"""
banano2live2D Command Line Interface.
"""

import argparse
import sys
import os

from .core import Banano2Live2D
from .prompts.engine import CHARACTER_PRESETS
from .viewer.web_player import serve_live2d_model
from .viewer.studio_server import serve_studio


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="banano2live2d",
        description="banano2live2D: Componentized Live2D Generation powered by Gemini Image & Multimodal Models.",
    )
    parser.add_argument("--key", type=str, default=None, help="HrioAPI key (sk-...)")
    parser.add_argument("--base-url", type=str, default=None, help="HrioAPI Base URL")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: create (End-to-End generation)
    p_create = subparsers.add_parser("create", help="Generate 3x3 sheet and build complete Live2D model")
    p_create.add_argument("-p", "--prompt", type=str, default="", help="Character description prompt")
    p_create.add_argument("--preset", type=str, choices=list(CHARACTER_PRESETS.keys()), default=None, help="Character preset")
    p_create.add_argument("-i", "--image", type=str, default=None, help="Reference character image for Image-to-Live2D")
    p_create.add_argument("-n", "--name", type=str, default="chibi_character", help="Character model name")
    p_create.add_argument("-o", "--output", type=str, default="output/model", help="Output directory")
    p_create.add_argument("--serve", action="store_true", help="Launch interactive web viewer after build")
    p_create.add_argument("--port", type=int, default=8088, help="Web viewer port")

    # Command: from-grid (Build from existing 3x3 sheet)
    p_grid = subparsers.add_parser("from-grid", help="Assemble Live2D model from an existing 3x3 component sheet")
    p_grid.add_argument("grid_image", type=str, help="Path to 3x3 component sprite sheet")
    p_grid.add_argument("-n", "--name", type=str, default="chibi_character", help="Character model name")
    p_grid.add_argument("-o", "--output", type=str, default="output/model", help="Output directory")
    p_grid.add_argument("--serve", action="store_true", help="Launch interactive web viewer after build")
    p_grid.add_argument("--port", type=int, default=8088, help="Web viewer port")

    # Command: serve (Launch web viewer)
    p_serve = subparsers.add_parser("serve", help="Launch interactive Live2D Web Player")
    p_serve.add_argument("model_dir", type=str, default="output/model", nargs="?", help="Path to Live2D model directory")
    p_serve.add_argument("--port", type=int, default=8088, help="Web player port")

    # Command: studio (Interactive Dialog + Attachment Live2D Studio Server)
    p_studio = subparsers.add_parser("studio", help="Launch interactive Dialog + Attachment Live2D Studio Server")
    p_studio.add_argument("--port", type=int, default=8090, help="Studio web server port")

    # Command: presets
    p_presets = subparsers.add_parser("presets", help="List all available character presets")

    args = parser.parse_args()

    if args.command == "presets":
        print("\nAvailable banano2live2D Character Presets:")
        for k, v in CHARACTER_PRESETS.items():
            print(f"  * {k:16s} : {v['name']} ({v['description']})")
        print()
        return

    if args.command == "studio":
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        serve_studio(project_root, port=args.port)
        return

    if args.command == "serve":
        serve_live2d_model(args.model_dir, port=args.port)
        return

    app = Banano2Live2D(api_key=args.key, base_url=args.base_url)

    if args.command == "from-grid":
        app.from_grid_image(
            grid_image_path=args.grid_image,
            character_name=args.name,
            output_dir=args.output,
            serve=args.serve,
            port=args.port,
        )
        return

    if args.command == "create":
        prompt = args.prompt
        if not prompt and not args.image:
            prompt = CHARACTER_PRESETS.get(args.preset or "sailor_girl", {}).get("description", "cute anime girl")
        app.create_live2d(
            prompt=prompt,
            preset=args.preset,
            reference_image=args.image,
            character_name=args.name,
            output_dir=args.output,
            serve=args.serve,
            port=args.port,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
