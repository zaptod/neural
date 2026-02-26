"""
Neural Fights — Aethermoor World Map Launcher
Executa o mapa do mundo em pygame.

Uso:
    python RUN_WORLDMAP.py
"""
import subprocess, sys, os

script = os.path.join(os.path.dirname(__file__), "world_map_pygame", "RUN_WORLDMAP.py")
subprocess.run([sys.executable, script])
