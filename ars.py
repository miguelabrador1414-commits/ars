#!/usr/bin/env python3
"""
Allwinner Recovery Studio - Lanzador principal
"""

import sys
import os

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from gui.main_window import main

if __name__ == "__main__":
    print("Starting Allwinner Recovery Studio...")
    print("=" * 50)
    main()
