#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
banano2live2D Entry Point.
"""

import sys
import os

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from banano2live2D.cli import main

if __name__ == "__main__":
    main()
