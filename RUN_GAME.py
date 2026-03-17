"""
Neural Fights - launcher principal.
Execute este arquivo a partir da pasta raiz `neural/`.
"""
import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "neural_v3_rework", "run.py")
subprocess.run([sys.executable, script])
