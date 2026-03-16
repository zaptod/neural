"""
Neural Fights — Main Game Launcher
Run this from the neural_fights_complete/ directory.
"""
import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "neural_v3_rework", "run.py")
subprocess.run([sys.executable, script])
