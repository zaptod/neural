"""
Aethermoor — World Map Launcher
Runs the pixel-art world map (pygame).

Usage:  python RUN_WORLDMAP.py
"""
import subprocess, sys, os

script = os.path.join(os.path.dirname(__file__), "world_map_pygame", "main.py")
subprocess.run([sys.executable, script])
