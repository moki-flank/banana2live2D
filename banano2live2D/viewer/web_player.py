# -*- coding: utf-8 -*-
"""
Local HTTP Server for Interactive Live2D Web Player.
"""

import os
import sys
import webbrowser
import http.server
import socketserver
from typing import Optional


def serve_live2d_model(
    model_dir: str,
    port: int = 8088,
    open_browser: bool = True,
):
    """
    Start local HTTP server in model_dir and launch web browser.
    """
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    # Copy template.html to index.html in model_dir if not present
    index_path = os.path.join(model_dir, "index.html")
    if not os.path.isfile(index_path):
        template_path = os.path.join(os.path.dirname(__file__), "template.html")
        if os.path.isfile(template_path):
            with open(template_path, "r", encoding="utf-8") as f_in, open(index_path, "w", encoding="utf-8") as f_out:
                f_out.write(f_in.read())

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=model_dir, **kwargs)

        def log_message(self, format, *args):
            # Suppress noisy request logs
            pass

    # Find open port
    effective_port = port
    for p in range(port, port + 50):
        try:
            with socketserver.TCPServer(("", p), CustomHandler) as httpd:
                effective_port = p
                url = f"http://localhost:{effective_port}/index.html"
                print(f"\n✨ banano2live2D Player running at: {url}")
                print(f"📁 Serving directory: {os.path.abspath(model_dir)}")
                print("Press Ctrl+C to stop server.\n")

                if open_browser:
                    webbrowser.open(url)

                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nServer stopped.")
                return
        except OSError:
            continue
